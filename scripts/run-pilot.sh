#!/usr/bin/env bash
# Start pilot stream host (app.main :8787).
# Default: Azure emulator via scripts/adb-tunnel.sh (127.0.0.1:5555).
# Redroid: set STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1 and/or
#          ADB_SERIAL=127.0.0.1:5556 (or STRLIX_STREAM_ADB=aws-redroid).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a
# shellcheck disable=SC1091
source .env
set +a
export ADB_BIN="${ADB_BIN:-${ROOT}/platform-tools/adb}"

DEVICE_ID="${STRLIX_PILOT_DEVICE_ID:-pilot-emulator-1}"
SERIAL="${ADB_SERIAL:-127.0.0.1:5555}"
BACKEND="${STRLIX_STREAM_ADB:-}"

use_redroid=0
if [[ "${BACKEND}" == "aws-redroid" || "${BACKEND}" == "redroid" ]]; then
  use_redroid=1
elif [[ "${DEVICE_ID}" == *"redroid"* ]]; then
  use_redroid=1
elif [[ "${SERIAL}" == *":5556" ]]; then
  use_redroid=1
fi

if [[ "${use_redroid}" -eq 1 ]]; then
  export ADB_SERIAL="${ADB_SERIAL:-127.0.0.1:5556}"
  export STRLIX_PILOT_DEVICE_ID="${STRLIX_PILOT_DEVICE_ID:-aws-redroid-t4-1}"
  export STRLIX_PILOT_KIND="${STRLIX_PILOT_KIND:-redroid}"
  echo "pilot stream backend: AWS Redroid (ADB_SERIAL=${ADB_SERIAL} id=${STRLIX_PILOT_DEVICE_ID})"
  ./scripts/adb-aws-redroid.sh || true
else
  export ADB_SERIAL="${ADB_SERIAL:-127.0.0.1:5555}"
  export STRLIX_PILOT_DEVICE_ID="${STRLIX_PILOT_DEVICE_ID:-pilot-emulator-1}"
  export STRLIX_PILOT_KIND="${STRLIX_PILOT_KIND:-emulator}"
  echo "pilot stream backend: Azure emulator (ADB_SERIAL=${ADB_SERIAL} id=${STRLIX_PILOT_DEVICE_ID})"
  ./scripts/adb-tunnel.sh || true
fi

exec .venv/bin/uvicorn app.main:app --host "${PILOT_HOST:-0.0.0.0}" --port "${PILOT_PORT:-8787}"
