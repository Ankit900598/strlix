#!/usr/bin/env bash
set -euo pipefail
cd /workspace/zevi-cloudphone
set -a
source .env
set +a
export ADB_BIN="${ADB_BIN:-/workspace/zevi-cloudphone/platform-tools/adb}"
./scripts/adb-tunnel.sh || true
exec .venv/bin/uvicorn app.main:app --host "${PILOT_HOST:-0.0.0.0}" --port "${PILOT_PORT:-8787}"
