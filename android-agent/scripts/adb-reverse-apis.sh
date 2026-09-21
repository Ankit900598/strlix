#!/usr/bin/env bash
# Map emulator/device localhost → host android-api (:8788) and pilot (:8787).
set -euo pipefail
ADB="${ADB:-/workspace/zevi-cloudphone/platform-tools/adb}"
SERIAL="${ADB_SERIAL:-127.0.0.1:5555}"
"$ADB" -s "$SERIAL" reverse tcp:8788 tcp:8788
"$ADB" -s "$SERIAL" reverse tcp:8787 tcp:8787
echo "reversed:"
"$ADB" -s "$SERIAL" reverse --list
