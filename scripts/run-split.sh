#!/usr/bin/env bash
# Start session-broker + android-api + desktop-api WITHOUT touching pilot :8787.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source "${ROOT}/.venv/bin/activate"
mkdir -p "${ROOT}/demo/scale/logs"

export PYTHONPATH="${ROOT}/packages/common:${ROOT}/services/android-api:${ROOT}/services/desktop-api:${ROOT}/services/session-broker:${ROOT}:${PYTHONPATH:-}"

start_one() {
  local name="$1" port="$2" module="$3" appdir="$4"
  local pidfile="${ROOT}/demo/scale/logs/${name}.pid"
  local logfile="${ROOT}/demo/scale/logs/${name}.log"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running pid=$(cat "$pidfile") :$port"
    return 0
  fi
  # Free port if a stale process holds it (never touch 8787)
  if [[ "$port" != "8787" ]]; then
    fuser -k "${port}/tcp" 2>/dev/null || true
  fi
  nohup uvicorn "$module" --host 0.0.0.0 --port "$port" --app-dir "$appdir" \
    >"$logfile" 2>&1 &
  echo $! >"$pidfile"
  echo "started $name pid=$! :$port → $logfile"
}

start_one session-broker 8791 session_broker.main:app "${ROOT}/services/session-broker"
sleep 0.4
start_one android-api 8788 android_api.main:app "${ROOT}/services/android-api"
sleep 0.4
start_one desktop-api 8789 desktop_api.main:app "${ROOT}/services/desktop-api"

sleep 1.2
echo "── health ──"
for url in \
  http://127.0.0.1:8791/health \
  http://127.0.0.1:8788/health \
  http://127.0.0.1:8789/health \
  http://127.0.0.1:8787/health
do
  echo -n "$url → "
  curl -s -m 3 "$url" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("service", d.get("ok")), "ok="+str(d.get("ok")))' 2>/dev/null || echo "FAIL"
done
