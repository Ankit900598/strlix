#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADB="${ADB:-/workspace/zevi-cloudphone/platform-tools/adb}"
SERIAL="${ADB_SERIAL:-127.0.0.1:5555}"
APK="$ROOT/app/build/outputs/apk/debug/app-debug.apk"
PKG=com.zevi.agent
A11Y="$PKG/$PKG.ZeviAccessibilityService"


place_widget_bottom() {
  # Nexus Launcher 5x5: move our single widget to main page, row near bottom
  local db=/sdcard/strlix_launcher.db
  local ldb=""
  for cand in launcher_4_by_5.db launcher.db; do
    if "$ADB" -s "$SERIAL" shell su 0 test -f /data/data/com.google.android.apps.nexuslauncher/databases/$cand; then
      ldb=$cand; break
    fi
  done
  [[ -z "$ldb" ]] && return 0
  "$ADB" -s "$SERIAL" shell su 0 cp     /data/data/com.google.android.apps.nexuslauncher/databases/$ldb "$db" 2>/dev/null || return 0
  "$ADB" -s "$SERIAL" pull "$db" /tmp/strlix_launcher.db >/dev/null 2>&1 || return 0
  if ! command -v sqlite3 >/dev/null 2>&1; then return 0; fi
  local n
  n=$(sqlite3 /tmp/strlix_launcher.db "SELECT COUNT(*) FROM favorites WHERE appWidgetProvider LIKE '%ZeviSearchWidget%';" 2>/dev/null || echo 0)
  if [[ "$n" -eq 0 ]]; then return 0; fi
  # Keep only first if somehow >1 rows
  if [[ "$n" -gt 1 ]]; then
    local keep
    keep=$(sqlite3 /tmp/strlix_launcher.db "SELECT _id FROM favorites WHERE appWidgetProvider LIKE '%ZeviSearchWidget%' ORDER BY _id LIMIT 1;")
    sqlite3 /tmp/strlix_launcher.db "DELETE FROM favorites WHERE appWidgetProvider LIKE '%ZeviSearchWidget%' AND _id != $keep;"
  fi
  sqlite3 /tmp/strlix_launcher.db "UPDATE favorites SET screen=0, cellX=0, cellY=3, spanX=4, spanY=1 WHERE appWidgetProvider LIKE '%ZeviSearchWidget%';"
  "$ADB" -s "$SERIAL" push /tmp/strlix_launcher.db "$db" >/dev/null
  "$ADB" -s "$SERIAL" shell su 0 cp "$db" /data/data/com.google.android.apps.nexuslauncher/databases/$ldb
  "$ADB" -s "$SERIAL" shell su 0 rm -f     /data/data/com.google.android.apps.nexuslauncher/databases/${ldb}-journal     /data/data/com.google.android.apps.nexuslauncher/databases/${ldb}-wal     /data/data/com.google.android.apps.nexuslauncher/databases/${ldb}-shm
  "$ADB" -s "$SERIAL" shell am force-stop com.google.android.apps.nexuslauncher || true
  sleep 1
  echo "placed Strlix bar on home screen 0, row 3"
}

count_widgets() {
  # Count host-bound instances of our provider (not the provider registry line)
  "$ADB" -s "$SERIAL" shell dumpsys appwidget 2>/dev/null \
    | awk '
      /^Widgets:/{inw=1; next}
      /^Hosts:/{inw=0}
      inw && /provider=ProviderId\{[^}]*com\.zevi\.agent\/com\.zevi\.agent\.ZeviSearchWidget/ {c++}
      END {print c+0}
    '
}

if [[ ! -f "$APK" ]]; then
  echo "APK missing — run ./gradlew :app:assembleDebug first" >&2
  exit 1
fi

echo "== reverse android-api 8788 + pilot 8787 =="
"$ADB" -s "$SERIAL" reverse --remove-all 2>/dev/null || true
"$ADB" -s "$SERIAL" reverse tcp:8788 tcp:8788 || true
"$ADB" -s "$SERIAL" reverse tcp:8787 tcp:8787 || true
"$ADB" -s "$SERIAL" reverse --list || true

echo "== uninstall (clears duplicate home widgets) =="
"$ADB" -s "$SERIAL" uninstall "$PKG" 2>/dev/null || true

echo "== install =="
"$ADB" -s "$SERIAL" install "$APK"

echo "== grant overlay + mic + notifications =="
"$ADB" -s "$SERIAL" shell appops set "$PKG" SYSTEM_ALERT_WINDOW allow || true
"$ADB" -s "$SERIAL" shell pm grant "$PKG" android.permission.POST_NOTIFICATIONS 2>/dev/null || true
"$ADB" -s "$SERIAL" shell pm grant "$PKG" android.permission.RECORD_AUDIO 2>/dev/null || true

echo "== enable Accessibility (emulator, no UI) =="
"$ADB" -s "$SERIAL" shell settings put secure enabled_accessibility_services "$A11Y"
"$ADB" -s "$SERIAL" shell settings put secure accessibility_enabled 1
echo "a11y=$("$ADB" -s "$SERIAL" shell settings get secure enabled_accessibility_services | tr -d '\r')"

WC="$(count_widgets)"
echo "== widgets before pin: $WC =="
if [[ "$WC" -eq 0 ]]; then
  echo "== launch MainActivity (pin ONE widget) =="
  "$ADB" -s "$SERIAL" shell am start -n "$PKG/.MainActivity" \
    --ez start_bubble false --ez pin_widget true
  # Accept launcher "Add" / "Add automatically" if shown
  sleep 1.5
  for label in "Add to home screen" "Add automatically" "ADD AUTOMATICALLY" "Add" "ADD" "OK"; do
    if "$ADB" -s "$SERIAL" shell uiautomator dump /sdcard/uidump.xml >/dev/null 2>&1; then
      if "$ADB" -s "$SERIAL" shell cat /sdcard/uidump.xml 2>/dev/null | grep -q "$label"; then
        coords="$("$ADB" -s "$SERIAL" shell cat /sdcard/uidump.xml 2>/dev/null \
          | tr '>' '\n' \
          | grep -F "text=\"$label\"" \
          | head -1 \
          | sed -n 's/.*bounds="\[\([0-9]*\),\([0-9]*\)\]\[\([0-9]*\),\([0-9]*\)\]".*/\1 \2 \3 \4/p')"
        if [[ -n "$coords" ]]; then
          read -r x1 y1 x2 y2 <<<"$coords"
          cx=$(( (x1 + x2) / 2 )); cy=$(( (y1 + y2) / 2 ))
          echo "tapping '$label' at $cx,$cy"
          "$ADB" -s "$SERIAL" shell input tap "$cx" "$cy" || true
          break
        fi
      fi
    fi
  done
  sleep 1
else
  echo "== already have $WC widget(s); not pinning again =="
  "$ADB" -s "$SERIAL" shell am start -n "$PKG/.MainActivity" --ez start_bubble false
fi

WC2="$(count_widgets)"
echo "== widgets after pin: $WC2 =="
if [[ "$WC2" -gt 1 ]]; then
  echo "WARN: more than one Strlix widget ($WC2). Uninstall+reinstall recommended." >&2
fi

echo "== place single bar near bottom =="
place_widget_bottom || true

echo "== go Home =="
"$ADB" -s "$SERIAL" shell input keyevent KEYCODE_HOME || true
sleep 0.5

echo "== hide Google QSB (mask; no floating bubble) =="
"$ADB" -s "$SERIAL" shell am stopservice "$PKG/.OverlayService" 2>/dev/null || true
"$ADB" -s "$SERIAL" shell am start-foreground-service -n "$PKG/.OverlayService" --es mode qsb_mask 2>/dev/null \
  || "$ADB" -s "$SERIAL" shell am startservice -n "$PKG/.OverlayService" --es mode qsb_mask || true
"$ADB" -s "$SERIAL" shell pm disable-user --user 0 com.google.android.googlequicksearchbox 2>/dev/null || true

echo "== refresh widget PendingIntents =="
"$ADB" -s "$SERIAL" shell am start -n "$PKG/.MainActivity" --ez refresh_widget true >/dev/null || true
sleep 1
"$ADB" -s "$SERIAL" shell input keyevent KEYCODE_HOME || true

echo "Done. Expect exactly ONE Strlix search bar on Home (count=$WC2)."
