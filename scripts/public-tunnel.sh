#!/usr/bin/env bash
# Cloudflare quick tunnel → Zevi Cloud Phone on localhost:8787
# Usage: ./scripts/public-tunnel.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/demo/cloudflared.log"
URLFILE="$ROOT/demo/public-url.txt"
mkdir -p "$ROOT/demo"

# Stop prior quick tunnels for this service only
pkill -f 'cloudflared tunnel --url http://127.0.0.1:8787' 2>/dev/null || true
sleep 1

# Prefer HTTP/2 when UDP/QUIC to Cloudflare edge is blocked
PROTO="${CLOUDFLARED_PROTOCOL:-http2}"
nohup cloudflared tunnel --url http://127.0.0.1:8787 --protocol "$PROTO" --no-autoupdate \
  > "$LOG" 2>&1 &
echo "cloudflared pid $! (protocol=$PROTO) — waiting for URL…"

for i in $(seq 1 30); do
  URL=$(grep -oE 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$LOG" | head -1 || true)
  if [ -n "${URL:-}" ]; then
    echo "$URL" | tee "$URLFILE"
    echo "Log: $LOG"
    exit 0
  fi
  sleep 1
done
echo "No trycloudflare URL yet — see $LOG" >&2
tail -40 "$LOG" >&2
exit 1
