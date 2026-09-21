#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/packages/common:${ROOT}/services/android-api:${PYTHONPATH:-}"
# shellcheck disable=SC1091
source "${ROOT}/.venv/bin/activate"
exec uvicorn android_api.main:app --host 0.0.0.0 --port "${ANDROID_API_PORT:-8788}" --app-dir "${ROOT}/services/android-api"
