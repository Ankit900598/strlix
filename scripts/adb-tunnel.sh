#!/usr/bin/env bash
# SSH local-forward for ADB + connect. Safe to re-run (idempotent).
set -euo pipefail
KEY="${SSH_KEY:-/home/box/Downloads/vm-zevi-cloudphone-key.pem}"
HOST="${SSH_HOST:-20.115.117.71}"
USER="${SSH_USER:-azureuser}"
LOCAL_PORT="${LOCAL_ADB_PORT:-5555}"
ADB_BIN="${ADB_BIN:-/workspace/zevi-cloudphone/platform-tools/adb}"
chmod 600 "$KEY" 2>/dev/null || true

ensure_tunnel() {
  if ss -tlnp 2>/dev/null | grep -q ":${LOCAL_PORT} "; then
    echo "Port $LOCAL_PORT already listening"
    return 0
  fi
  ssh -fN \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=20 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -o TCPKeepAlive=yes \
    -i "$KEY" -L "${LOCAL_PORT}:127.0.0.1:5555" "${USER}@${HOST}"
  echo "Tunnel up: 127.0.0.1:${LOCAL_PORT} -> ${HOST}:5555"
}

ensure_tunnel
"$ADB_BIN" connect "127.0.0.1:${LOCAL_PORT}" || true
"$ADB_BIN" devices -l

# Optional: --watch keeps reconnecting if tunnel or adb drops
if [[ "${1:-}" == "--watch" ]]; then
  echo "Watching tunnel/ADB (Ctrl+C to stop)…"
  while true; do
    sleep 15
    if ! ss -tlnp 2>/dev/null | grep -q ":${LOCAL_PORT} "; then
      echo "$(date -Is) tunnel down — reconnecting"
      ensure_tunnel || true
    fi
    state="$("$ADB_BIN" -s "127.0.0.1:${LOCAL_PORT}" get-state 2>/dev/null || true)"
    if [[ "$state" != "device" ]]; then
      echo "$(date -Is) adb state=$state — connect"
      "$ADB_BIN" connect "127.0.0.1:${LOCAL_PORT}" || true
    fi
  done
fi
