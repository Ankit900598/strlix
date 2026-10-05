#!/usr/bin/env bash
# Wait until the emulator has fully booted, then make it ready for a viewer:
# guest profile (normal feel), screen awake and unlocked, launcher on Home.
# Run by strlix-phone-ready.service after every emulator (re)start. Idempotent.
# Before this, the profile ran from desktop-api ExecStartPost, which at VM boot
# fired ~1 s after power-on and failed with "device 'emulator-5554' not found".
set -uo pipefail
S="${1:-${ADB_SERIAL:-emulator-5554}}"
ADB="${ADB_BIN:-/usr/local/bin/adb}"
DEADLINE=$(( $(date +%s) + ${PHONE_READY_TIMEOUT_S:-240} ))
"$ADB" start-server >/dev/null 2>&1 || true
until [ "$("$ADB" -s "$S" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then echo "phone-ready: $S did not boot in time"; exit 1; fi
  sleep 3
done
echo "phone-ready: $S booted after ${SECONDS}s"
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/normal-feel-profile.sh" "$S" || echo "phone-ready: profile step failed (continuing)"
"$ADB" -s "$S" shell input keyevent KEYCODE_WAKEUP >/dev/null 2>&1 || true
"$ADB" -s "$S" shell wm dismiss-keyguard >/dev/null 2>&1 || true
"$ADB" -s "$S" shell input keyevent HOME >/dev/null 2>&1 || true
echo "phone-ready: done in ${SECONDS}s"
