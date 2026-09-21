#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/packages/common:${ROOT}/services/desktop-api:${ROOT}:${PYTHONPATH:-}"
source "${ROOT}/.venv/bin/activate"
exec uvicorn desktop_api.main:app --host 0.0.0.0 --port "${DESKTOP_API_PORT:-8789}" --app-dir "${ROOT}/services/desktop-api"
