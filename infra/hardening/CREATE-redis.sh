#!/usr/bin/env bash
# Azure Cache for Redis Basic C0 — optional replace of ca-redis sidecar.
# SAFE DEFAULT: dry-run. Pass --apply to create. RG: rg-zevi-cloudphone only.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
NAME="${NAME:-redis-zevi-strlix}"
LOC="${LOC:-eastus2}"
SKU="${SKU:-Basic}"
SIZE="${SIZE:-c0}"
KV="${KV:-kv-zevi-strlix}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

run() {
  if [[ "$APPLY" -eq 1 ]]; then echo "+ $*"; eval "$@"; else echo "[dry-run] $*"; fi
}

echo "Creating managed Redis $NAME ($SKU $SIZE) in $RG / $LOC"
echo "Est.: ~\$0.022/hr ≈ \$16/mo. Prefer over ca-redis container for post-credit survival."

run az redis create -g "$RG" -n "$NAME" -l "$LOC" --sku "$SKU" --vm-size "$SIZE" --enable-non-ssl-port false --minimum-tls-version 1.2

echo
echo "After create:"
echo "  1) PRIMARY_KEY=\$(az redis list-keys -g $RG -n $NAME --query primaryKey -o tsv)"
echo "  2) az keyvault secret set --vault-name $KV -n redis-primary-key --value \"\$PRIMARY_KEY\""
echo "  3) HOST=\$(az redis show -g $RG -n $NAME --query hostName -o tsv)"
echo "  4) Point ca-market-api STRLIX_REDIS_URL=rediss://:\$PRIMARY_KEY@\$HOST:6380/0"
echo "  5) Smoke /health redis:true — THEN scale ca-redis minReplicas→0 (do not delete yet)"
echo
[[ "$APPLY" -eq 0 ]] && echo "Re-run with --apply after Day-1 budget OK."
