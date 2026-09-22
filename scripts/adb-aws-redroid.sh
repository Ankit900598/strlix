#!/usr/bin/env bash
# SSM port-forward ADB from strlix-gpu-worker-1 Redroid → local 127.0.0.1:5556, then adb connect.
# Preferred secure path: no public SG inbound for ADB. Safe to re-run (idempotent).
#
# Env overrides:
#   AWS_REGION / INSTANCE_ID / REMOTE_PORT / LOCAL_ADB_PORT / ADB_BIN
# Optional: --watch keeps reconnecting if tunnel or adb drops
# Optional: --bg only starts the forward (no adb connect / no wait)
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
INSTANCE_ID="${INSTANCE_ID:-i-0531c567f620877c3}"
REMOTE_PORT="${REMOTE_PORT:-5556}"
LOCAL_PORT="${LOCAL_ADB_PORT:-5556}"
ADB_BIN="${ADB_BIN:-}"
if [[ -z "$ADB_BIN" ]]; then
  for cand in \
    /workspace/strlix/platform-tools/adb \
    /workspace/zevi-cloudphone/platform-tools/adb \
    "$(command -v adb 2>/dev/null || true)"; do
    if [[ -n "$cand" && -x "$cand" ]]; then ADB_BIN="$cand"; break; fi
  done
fi
if [[ -z "${ADB_BIN}" ]]; then
  echo "adb not found; set ADB_BIN" >&2
  exit 1
fi

LOG="${SSM_ADB_LOG:-/tmp/ssm-adb-aws-redroid-${LOCAL_PORT}.log}"
PID_FILE="${SSM_ADB_PID:-/tmp/ssm-adb-aws-redroid-${LOCAL_PORT}.pid}"

need_plugin() {
  if ! command -v session-manager-plugin >/dev/null 2>&1; then
    echo "session-manager-plugin missing. Install:" >&2
    echo "  https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html" >&2
    exit 1
  fi
}

forward_listening() {
  ss -tln 2>/dev/null | grep -qE "127\\.0\\.0\\.1:${LOCAL_PORT}\\s" \
    || ss -tln 2>/dev/null | grep -qE ":${LOCAL_PORT}\\s"
}

ensure_forward() {
  if forward_listening; then
    echo "SSM ADB forward already listening on 127.0.0.1:${LOCAL_PORT}"
    return 0
  fi
  need_plugin
  command -v aws >/dev/null || { echo "aws CLI missing" >&2; exit 1; }
  echo "Starting SSM port-forward ${INSTANCE_ID}:${REMOTE_PORT} → 127.0.0.1:${LOCAL_PORT}"
  nohup aws ssm start-session --region "$REGION" --target "$INSTANCE_ID" \
    --document-name AWS-StartPortForwardingSession \
    --parameters "{\"portNumber\":[\"${REMOTE_PORT}\"],\"localPortNumber\":[\"${LOCAL_PORT}\"]}" \
    >"$LOG" 2>&1 &
  echo $! >"$PID_FILE"
  for _ in $(seq 1 30); do
    if forward_listening; then
      echo "Tunnel up: 127.0.0.1:${LOCAL_PORT} → ${INSTANCE_ID}:${REMOTE_PORT} (SSM)"
      return 0
    fi
    sleep 0.5
  done
  echo "SSM forward failed to bind :${LOCAL_PORT}. Log:" >&2
  tail -n 40 "$LOG" >&2 || true
  exit 1
}

ensure_forward

if [[ "${1:-}" == "--bg" ]]; then
  exit 0
fi

"$ADB_BIN" connect "127.0.0.1:${LOCAL_PORT}" || true
"$ADB_BIN" devices -l
echo -n "boot_completed="
"$ADB_BIN" -s "127.0.0.1:${LOCAL_PORT}" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || echo "?"

# Export helpers for android-api / pilot
export ADB_SERIAL="127.0.0.1:${LOCAL_PORT}"
export STRLIX_PILOT_DEVICE_ID="${STRLIX_PILOT_DEVICE_ID:-aws-redroid-t4-1}"
echo "ADB_SERIAL=${ADB_SERIAL}  STRLIX_PILOT_DEVICE_ID=${STRLIX_PILOT_DEVICE_ID}"

if [[ "${1:-}" == "--watch" ]]; then
  echo "Watching SSM tunnel/ADB (Ctrl+C to stop)…"
  while true; do
    sleep 15
    if ! forward_listening; then
      echo "$(date -Is) tunnel down — reconnecting"
      ensure_forward || true
    fi
    state="$("$ADB_BIN" -s "127.0.0.1:${LOCAL_PORT}" get-state 2>/dev/null || true)"
    if [[ "$state" != "device" ]]; then
      echo "$(date -Is) adb state=$state — connect"
      "$ADB_BIN" connect "127.0.0.1:${LOCAL_PORT}" || true
    fi
  done
fi
