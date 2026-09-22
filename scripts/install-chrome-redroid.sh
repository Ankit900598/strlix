#!/usr/bin/env bash
# Install / launch a browser on the AWS Redroid (or any ADB) cloud phone.
# Use when the in-phone "browser not working" symptom is missing Chrome /
# Browser APK — not when the web viewer iframe is broken (that is AFD /stream).
#
# Prereq: ADB connected (e.g. ./scripts/adb-aws-redroid.sh).
# Env: ADB_SERIAL (default 127.0.0.1:5556), ADB_BIN, CHROME_APK
set -euo pipefail

ADB_BIN="${ADB_BIN:-}"
if [[ -z "$ADB_BIN" ]]; then
  for cand in \
    /workspace/strlix/platform-tools/adb \
    /workspace/platform-tools/adb \
    "$(command -v adb 2>/dev/null || true)"; do
    if [[ -n "$cand" && -x "$cand" ]]; then ADB_BIN="$cand"; break; fi
  done
fi
[[ -n "$ADB_BIN" ]] || { echo "adb not found; set ADB_BIN" >&2; exit 1; }

SERIAL="${ADB_SERIAL:-127.0.0.1:5556}"
adb() { "$ADB_BIN" -s "$SERIAL" "$@"; }

echo "== Device =="
adb get-state
adb shell getprop ro.build.version.release
adb shell getprop ro.product.cpu.abi

echo
echo "== Installed browsers =="
adb shell pm list packages | grep -E 'chrome|browser|webview' || echo "(none matched)"

CHROME_PKG="com.android.chrome"
if adb shell pm path "$CHROME_PKG" >/dev/null 2>&1; then
  echo "Chrome already installed: $CHROME_PKG"
else
  APK="${CHROME_APK:-}"
  if [[ -z "$APK" ]]; then
    cat <<EOF
Chrome package missing on this image.

Fix (pick one):
  1) Download a matching Chrome APK (same ABI as ro.product.cpu.abi) and:
       export CHROME_APK=/path/to/chrome.apk
       $0
  2) Or install Chromium / Browser from a trusted APK the same way.
  3) Redroid images often ship WebView only — a full browser APK is required
     for "open Chrome" demos.

Refusing to curl random APKs from the network in this script.
EOF
    exit 2
  fi
  [[ -f "$APK" ]] || { echo "CHROME_APK not a file: $APK" >&2; exit 1; }
  echo "Installing $APK …"
  adb install -r "$APK"
fi

echo
echo "== Launch Chrome =="
adb shell monkey -p "$CHROME_PKG" -c android.intent.category.LAUNCHER 1 \
  || adb shell am start -a android.intent.action.VIEW -d 'https://example.com' \
       -n com.android.chrome/com.google.android.apps.chrome.Main

echo "Done. If the web viewer still fails on a real phone, the issue is public"
echo "/stream routing (see web-market/DEPLOY.md), not the on-device browser APK."
