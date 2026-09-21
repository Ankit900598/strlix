#!/usr/bin/env bash
# Polish Pixel home for Strlix product demo.
# - ONLY Strlix search bar (Google QSB covered + GSA disabled)
# - No floating Z bubble
# - Tidy 4-icon dock, no duplicate apps / empty gaps
# - Clean modern wallpaper
set -euo pipefail
ADB="${ADB:-/workspace/zevi-cloudphone/platform-tools/adb}"
SERIAL="${ADB_SERIAL:-127.0.0.1:5555}"
PKG=com.zevi.agent
APK="${APK:-/workspace/zevi-cloudphone/android-agent/app/build/outputs/apk/debug/app-debug.apk}"
WALLPAPER="${WALLPAPER:-/workspace/zevi-cloudphone/demo/pixel_dark_wallpaper.png}"
LAUNCHER=com.google.android.apps.nexuslauncher
DB_REMOTE_DIR=/data/data/$LAUNCHER/databases

echo "== connect =="
"$ADB" -s "$SERIAL" reverse tcp:8787 tcp:8787 2>/dev/null || true
"$ADB" connect "$SERIAL" >/dev/null || true
"$ADB" -s "$SERIAL" wait-for-device

echo "== stop overlays / agent =="
"$ADB" -s "$SERIAL" shell am stopservice "$PKG/.OverlayService" 2>/dev/null || true
"$ADB" -s "$SERIAL" shell am force-stop "$PKG" 2>/dev/null || true

echo "== reinstall =="
"$ADB" -s "$SERIAL" install -r "$APK"
"$ADB" -s "$SERIAL" shell appops set "$PKG" SYSTEM_ALERT_WINDOW allow || true
"$ADB" -s "$SERIAL" shell settings put secure enabled_accessibility_services \
  "$PKG/$PKG.ZeviAccessibilityService"
"$ADB" -s "$SERIAL" shell settings put secure accessibility_enabled 1

echo "== disable Google app (QSB backend) =="
"$ADB" -s "$SERIAL" shell pm disable-user --user 0 com.google.android.googlequicksearchbox 2>/dev/null || true

echo "== push wallpaper + set via app =="
"$ADB" -s "$SERIAL" push "$WALLPAPER" /sdcard/Download/strlix_wallpaper.png >/dev/null
"$ADB" -s "$SERIAL" shell am start -n "$PKG/.MainActivity" \
  --ez set_demo_wallpaper true \
  --es wallpaper_path /sdcard/Download/strlix_wallpaper.png \
  --ez start_bubble false >/dev/null
sleep 2
"$ADB" -s "$SERIAL" shell am force-stop "$PKG"

echo "== rewrite launcher DB =="
LDB=""
for cand in launcher_4_by_5.db launcher.db; do
  if "$ADB" -s "$SERIAL" shell su 0 test -f "$DB_REMOTE_DIR/$cand"; then
    LDB=$cand; break
  fi
done
[[ -n "$LDB" ]] || { echo "launcher db missing"; exit 1; }

"$ADB" -s "$SERIAL" shell su 0 cp "$DB_REMOTE_DIR/$LDB" /sdcard/polish_launcher.db
"$ADB" -s "$SERIAL" shell su 0 chmod 666 /sdcard/polish_launcher.db
"$ADB" -s "$SERIAL" pull /sdcard/polish_launcher.db /tmp/polish_launcher.db >/dev/null

python3 - <<'PY'
import sqlite3
con = sqlite3.connect('/tmp/polish_launcher.db')
cur = con.cursor()
cur.execute("DELETE FROM favorites WHERE container=-100 AND itemType=0")
rows = cur.execute(
    "SELECT _id FROM favorites WHERE appWidgetProvider LIKE '%ZeviSearchWidget%' ORDER BY _id"
).fetchall()
if len(rows) > 1:
    keep = rows[0][0]
    cur.execute(
        "DELETE FROM favorites WHERE appWidgetProvider LIKE '%ZeviSearchWidget%' AND _id!=?",
        (keep,),
    )
cur.execute(
    """UPDATE favorites SET screen=0, cellX=0, cellY=4, spanX=4, spanY=1, container=-100
       WHERE appWidgetProvider LIKE '%ZeviSearchWidget%'"""
)
cur.execute("DELETE FROM favorites WHERE container=-101")

def hotseat(title, component, slot):
    intent = (
        "#Intent;action=android.intent.action.MAIN;"
        "category=android.intent.category.LAUNCHER;"
        "launchFlags=0x10200000;component=%s;end" % component
    )
    cur.execute(
        """INSERT INTO favorites
           (title,intent,container,screen,cellX,cellY,spanX,spanY,itemType,appWidgetId,modified,restored,profileId,rank,options,appWidgetSource)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (title, intent, -101, slot, slot, 0, 1, 1, 0, -1, 0, 0, 0, slot, 0, -1),
    )

def workspace(title, component, x, y):
    intent = (
        "#Intent;action=android.intent.action.MAIN;"
        "category=android.intent.category.LAUNCHER;"
        "launchFlags=0x10200000;component=%s;end" % component
    )
    cur.execute(
        """INSERT INTO favorites
           (title,intent,container,screen,cellX,cellY,spanX,spanY,itemType,appWidgetId,modified,restored,profileId,rank,options,appWidgetSource)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (title, intent, -100, 0, x, y, 1, 1, 0, -1, 0, 0, 0, 0, 0, -1),
    )

hotseat('Phone', 'com.google.android.dialer/.extensions.GoogleDialtactsActivity', 0)
hotseat('Messages', 'com.google.android.apps.messaging/.ui.ConversationListActivity', 1)
hotseat('Chrome', 'com.android.chrome/com.google.android.apps.chrome.Main', 2)
hotseat('Camera', 'com.android.camera2/com.android.camera.CameraLauncher', 3)
workspace('Gmail', 'com.google.android.gm/.ConversationListActivityGmail', 0, 2)
workspace('Photos', 'com.google.android.apps.photos/.home.HomeActivity', 1, 2)
workspace('YouTube', 'com.google.android.youtube/.app.honeycomb.Shell$HomeActivity', 2, 2)
workspace('Maps', 'com.google.android.apps.maps/com.google.android.maps.MapsActivity', 3, 2)
con.commit(); con.close()
print('launcher db rewritten')
PY

"$ADB" -s "$SERIAL" push /tmp/polish_launcher.db /sdcard/polish_launcher.db >/dev/null
"$ADB" -s "$SERIAL" shell su 0 cp /sdcard/polish_launcher.db "$DB_REMOTE_DIR/$LDB"
OWNER=$("$ADB" -s "$SERIAL" shell su 0 stat -c %u:%g /data/data/$LAUNCHER | tr -d '\r')
"$ADB" -s "$SERIAL" shell su 0 chown "$OWNER" "$DB_REMOTE_DIR/$LDB"
"$ADB" -s "$SERIAL" shell su 0 rm -f \
  "$DB_REMOTE_DIR/${LDB}-journal" "$DB_REMOTE_DIR/${LDB}-wal" "$DB_REMOTE_DIR/${LDB}-shm"

"$ADB" -s "$SERIAL" shell su 0 sh -c "cat > /data/data/$LAUNCHER/shared_prefs/com.android.launcher3.device.prefs.xml" <<'XML'
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <int name="pref_persistent_flags" value="24" />
    <boolean name="last_prediction_enabled_state" value="false" />
    <string name="pref_icon_shape_path">M50 0C77.6 0 100 22.4 100 50C100 77.6 77.6 100 50 100C22.4 100 0 77.6 0 50C0 22.4 22.4 0 50 0Z,no-theme</string>
</map>
XML
"$ADB" -s "$SERIAL" shell su 0 sh -c "cat > /data/data/$LAUNCHER/shared_prefs/com.android.launcher3.prefs.xml" <<'XML'
<?xml version='1.0' encoding='utf-8' standalone='yes' ?>
<map>
    <boolean name="launcher.search_edu_seen" value="true" />
    <boolean name="pref_enable_minus_one" value="false" />
    <string name="migration_src_workspace_size">4,5</string>
    <int name="migration_src_hotseat_count" value="4" />
    <string name="migration_src_db_file">launcher_4_by_5.db</string>
    <string name="idp_grid_name">practical</string>
    <int name="migration_src_device_type" value="0" />
</map>
XML
"$ADB" -s "$SERIAL" shell su 0 chown -R "$OWNER" /data/data/$LAUNCHER/shared_prefs/

echo "== restart launcher =="
"$ADB" -s "$SERIAL" shell am force-stop "$LAUNCHER"
sleep 1
"$ADB" -s "$SERIAL" shell input keyevent KEYCODE_HOME
sleep 1

echo "== QSB mask overlay (covers Google bar; no Z bubble) =="
"$ADB" -s "$SERIAL" shell am start-foreground-service -n "$PKG/.OverlayService" --es mode qsb_mask

"$ADB" -s "$SERIAL" shell input keyevent KEYCODE_HOME
sleep 1
echo "== refresh Strlix widget click handlers =="
"$ADB" -s "$SERIAL" reverse tcp:8787 tcp:8787 2>/dev/null || true
"$ADB" -s "$SERIAL" shell am start -n "$PKG/.MainActivity" --ez refresh_widget true >/dev/null
sleep 1
"$ADB" -s "$SERIAL" shell input keyevent KEYCODE_HOME
sleep 0.5

echo "polish-home done — screenshot with: adb shell screencap -p /sdcard/strlix_home_clean.png"
