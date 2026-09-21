#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/packages/common:${ROOT}/services/session-broker:${PYTHONPATH:-}"
source "${ROOT}/.venv/bin/activate"
exec uvicorn session_broker.main:app --host 0.0.0.0 --port "${SESSION_BROKER_PORT:-8791}" --app-dir "${ROOT}/services/session-broker"
