#!/usr/bin/env bash
# Smoke: catalog on AFD (or local) lists aws-redroid-t4-1 as available.
# Usage:
#   ./scripts/smoke-catalog-redroid.sh
#   MARKET_BASE=https://strlix-edge-....azurefd.net ./scripts/smoke-catalog-redroid.sh
set -euo pipefail

BASE="${MARKET_BASE:-https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net}"
WANT_ID="${STRLIX_SMOKE_DEVICE_ID:-aws-redroid-t4-1}"

echo "GET ${BASE}/v1/devices"
body="$(curl -sS --max-time 30 "${BASE}/v1/devices")"
echo "${body}" | python3 -c "
import json, sys
want = '${WANT_ID}'
data = json.load(sys.stdin)
# market-api may return {devices:[...]} or a bare list
devs = data.get('devices', data) if isinstance(data, dict) else data
if not isinstance(devs, list):
    raise SystemExit(f'unexpected /v1/devices shape: {type(data).__name__}')
match = [d for d in devs if isinstance(d, dict) and d.get('id') == want]
if not match:
    ids = [d.get('id') for d in devs if isinstance(d, dict)]
    raise SystemExit(f'MISSING {want} in catalog; have {ids[:12]}…')
d = match[0]
ok = d.get('available') is True
preview = d.get('preview')
print(f'FOUND {want} available={d.get(\"available\")} preview={preview} tier={d.get(\"tier\")} kind={d.get(\"kind\")}')
if not ok:
    raise SystemExit(f'{want} present but available!=true')
print('OK')
"
