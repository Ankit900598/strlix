#!/usr/bin/env bash
# Self-heal for the phone stack (strlix-watchdog.timer, every 60 s).
# - emulator: if adb can't see a booted device, first try `adb reconnect offline`;
#   if it has been failing for EMU_FAIL_S (default 300 s) and the emulator unit
#   has been up > 4 min, restart strlix-emulator (a cold boot costs ~1 min).
# - desktop-api: if http://127.0.0.1:8789/health has been failing for
#   API_FAIL_S (default 120 s), restart strlix-desktop-api.
# Failure is measured as wall time since the first failed check (not a count),
# so running the script several times quickly can never trigger a restart.
# State lives in /run/strlix-watchdog (tmpfs, reset on boot). Logs: journal.
set -uo pipefail
S="${ADB_SERIAL:-emulator-5554}"
ADB="${ADB_BIN:-/usr/local/bin/adb}"
D=/run/strlix-watchdog; mkdir -p "$D"
EMU_FAIL_S="${EMU_FAIL_S:-300}"; API_FAIL_S="${API_FAIL_S:-120}"
# failing_for NAME -> seconds since the first failure of NAME (records it if new)
bump() { local now first; now=$(date +%s); first=$(cat "$D/$1" 2>/dev/null || echo "$now"); \
         [ -f "$D/$1" ] || echo "$now" > "$D/$1"; echo $(( now - first )); }
clear_() { rm -f "$D/$1"; }
up_s() { local ts; ts=$(systemctl show -p ActiveEnterTimestampMonotonic --value "$1"); \
         echo $(( ( $(cut -d' ' -f1 /proc/uptime | cut -d. -f1) * 1000000 - ${ts:-0} ) / 1000000 )); }

if [ "$(timeout 10 "$ADB" -s "$S" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; then
  clear_ emu
elif [ "$(up_s strlix-emulator)" -gt 240 ]; then
  "$ADB" reconnect offline >/dev/null 2>&1 || true
  n=$(bump emu); echo "watchdog: phone $S not booted/visible for ${n}s (limit ${EMU_FAIL_S}s)"
  if [ "$n" -ge "$EMU_FAIL_S" ]; then echo "watchdog: restarting strlix-emulator"; clear_ emu; systemctl restart strlix-emulator; fi
fi

if curl -fsS -m 8 -o /dev/null http://127.0.0.1:8789/health; then
  clear_ api
else
  n=$(bump api); echo "watchdog: desktop-api /health failing for ${n}s (limit ${API_FAIL_S}s)"
  if [ "$n" -ge "$API_FAIL_S" ]; then echo "watchdog: restarting strlix-desktop-api"; clear_ api; systemctl restart strlix-desktop-api; fi
fi

# perf1: a DHCP renew can rewrite the default route without initcwnd.
if [ -x /home/azureuser/strlix/scripts/net-tune.sh ] && ! ip route show default | grep -q initcwnd; then
  echo "watchdog: re-applying net-tune"; /home/azureuser/strlix/scripts/net-tune.sh || true
fi
