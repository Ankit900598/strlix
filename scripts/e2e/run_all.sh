#!/usr/bin/env bash
# One-command live regression for the Strlix phone stream.
# Usage: STRLIX_VM=azureuser@<vm-ip> [STRLIX_VM_KEY=~/.ssh/strlix-vm.pem] scripts/e2e/run_all.sh [quick|full]
# Writes $STRLIX_E2E_OUT/<run-id>/{summary.md,summary.json,*.log}; exit code 0 = all hard checks passed.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-full}"
: "${STRLIX_VM:?set STRLIX_VM=user@host}"
export STRLIX_VM_KEY="${STRLIX_VM_KEY:-$HOME/.ssh/strlix-vm.pem}"
export STRLIX_STREAM_URL="${STRLIX_STREAM_URL:-https://strlix-stream-euapehawccbcbuer.z02.azurefd.net}"
STRLIX_EDGE_URL="${STRLIX_EDGE_URL:-https://strlix-edge-gjfueaccgwg9gmfv.z02.azurefd.net}"
PY="${PYTHON:-python3}"
RUN="$(date +%Y%m%d-%H%M%S)"
export STRLIX_E2E_OUT="${STRLIX_E2E_OUT:-/tmp/strlix-e2e}/$RUN"
mkdir -p "$STRLIX_E2E_OUT"; OUT="$STRLIX_E2E_OUT"
WSS="${STRLIX_STREAM_URL/https:/wss:}/ws/h264"
SSH=(ssh -i "$STRLIX_VM_KEY" -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new "$STRLIX_VM")
RESULTS=()   # "name|PASS/FAIL/INFO|detail"
add() { RESULTS+=("$1|$2|$3"); printf '%-22s %-4s %s\n' "$1" "$2" "$3"; }

# 1. Preflight: endpoints and phone
for u in "$STRLIX_EDGE_URL/market/" "$STRLIX_EDGE_URL/health" "$STRLIX_EDGE_URL/android/health" "$STRLIX_STREAM_URL/health"; do
  c=$(curl -s -o /dev/null -m 20 -w '%{http_code}' "$u"); [[ "$c" == 200 ]] && add "http ${u#https://}" PASS "$c" || add "http ${u#https://}" FAIL "$c"
done
dev=$("${SSH[@]}" "adb devices | grep -c 'emulator-5554.device'; adb shell getprop sys.boot_completed" 2>/dev/null | tr '\n' ' ')
[[ "$dev" == "1 1 " ]] && add "phone adb+boot" PASS "$dev" || add "phone adb+boot" FAIL "'$dev'"

# 2. Latency (raw WS through AFD): tap and drag breakdown
for m in tap drag; do
  MODE_ENV=""; [[ $m == drag ]] && MODE_ENV=drag
  MODE=$MODE_ENV timeout 300 "$PY" "$HERE/trace_probe.py" "$WSS" 6 > "$OUT/lat-$m.log" 2>&1
  s=$(grep '^SUMMARY' "$OUT/lat-$m.log" | sed 's/^SUMMARY //')
  [[ -n "$s" ]] && add "latency $m" INFO "$s" || add "latency $m" FAIL "see lat-$m.log"
done

# 3. Feel regression (headless Chrome, real touch through the viewer)
timeout 900 "$PY" "$HERE/feel_e2e.py" feel "$RUN" > "$OUT/feel.log" 2>&1
if [[ -f "$OUT/feel/result.json" ]]; then
  while IFS='|' read -r n st d; do add "$n" "$st" "$d"; done < <("$PY" - "$OUT/feel/result.json" <<'PYEOF'
import json, sys
R = json.load(open(sys.argv[1]))
for k, v in R.get("steps", {}).items():
    if isinstance(v, dict) and "ok" in v: print(f"feel {k}|{'PASS' if v['ok'] else 'FAIL'}|")
ff = [round(x.get("first_frame_s") or 0, 2) for x in R.get("first_frame", [])]
if ff: print(f"first frame s|{'PASS' if ff and min(ff) < 3 else 'FAIL'}|{ff}")
print(f"tap up->frame median ms|INFO|{R.get('lat_summary', {}).get('median_up_to_frame_ms')}")
PYEOF
)
else add "feel" FAIL "no result.json (see feel.log)"; fi

if [[ "$MODE" == full ]]; then
  # 4. Recents dismiss through the viewer (button + swipe-up from an app)
  timeout 900 "$PY" "$HERE/recents_bench.py" bench 3 > "$OUT/recents.log" 2>&1
  r=$(tail -1 "$OUT/recents.log")
  "$PY" -c 'import json,sys; d=json.loads(sys.argv[1]); ok=all(v.split("/")[0]==v.split("/")[1].split()[0] for k,v in d.items() if k in("button","gesture")); sys.exit(0 if ok else 1)' "$r" 2>/dev/null \
    && add "recents dismiss" PASS "${r:0:90}" || add "recents dismiss" FAIL "${r:0:90}"
  # 5. Launcher poisoning (on the VM, local WS): bad slow drag, then a fling 0.3 s later
  scp -q -i "$STRLIX_VM_KEY" "$HERE/poison_bench.py" "$STRLIX_VM:/tmp/poison_bench.py"
  p=$("${SSH[@]}" "cd /tmp && timeout 300 python3 poison_bench.py 1 0.3 6" 2>/dev/null | tail -1)
  echo "$p" > "$OUT/poison.json"
  pk=$("$PY" -c 'import json,sys; d=json.loads(sys.argv[1]); print("%s/%s" % (d["ok"], d["n"]))' "$p" 2>/dev/null || echo "?")
  [[ "$pk" == 6/6 || "$pk" == 5/6 ]] && add "recents after bad drag" PASS "$pk" || add "recents after bad drag" FAIL "$pk"
fi

# Summary
{
  echo "# Strlix e2e $RUN ($MODE)"; echo; echo "| Check | Result | Detail |"; echo "|---|---|---|"
  for r in "${RESULTS[@]}"; do IFS='|' read -r n st d <<<"$r"; echo "| $n | $st | ${d//|//} |"; done
} > "$OUT/summary.md"
printf '%s\n' "${RESULTS[@]}" | "$PY" -c 'import json,sys; print(json.dumps([dict(zip(("check","result","detail"),l.rstrip("\n").split("|",2))) for l in sys.stdin], indent=1))' > "$OUT/summary.json"
FAILS=$(printf '%s\n' "${RESULTS[@]}" | grep -c '|FAIL|')
echo; echo "Summary: $OUT/summary.md  ($FAILS failed)"
exit $(( FAILS > 0 ))
