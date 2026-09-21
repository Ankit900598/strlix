#!/usr/bin/env bash
# Azure Managed Redis Balanced_B0 (Azure Cache for Redis Basic C0 is retired).
# SAFE DEFAULT: dry-run. Pass --apply to create. RG: rg-zevi-cloudphone only.
# Day-1 applied as redis-strlix-amr in eastus (eastus2 B0 hit InsufficientCapacity;
# redis-zevi-strlix left as CreateFailed stub — do not delete without approval).
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
NAME="${NAME:-redis-strlix-amr}"
LOC="${LOC:-eastus}"
SKU="${SKU:-Balanced_B0}"
KV="${KV:-kv-zevi-strlix}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

run() {
  if [[ "$APPLY" -eq 1 ]]; then echo "+ $*"; eval "$@"; else echo "[dry-run] $*"; fi
}

echo "Creating Azure Managed Redis $NAME ($SKU) in $RG / $LOC"
echo "NOTE: Legacy az redis Basic C0 is retired; Balanced_B0 is the closest low-cost Managed Redis SKU."
echo "Est.: ~\$0.016/hr ≈ \$12/mo (eastus). Prefer over ca-redis container for post-credit survival."

run az redisenterprise create -g "$RG" -n "$NAME" -l "$LOC" --sku "$SKU" \
  --minimum-tls-version 1.2 \
  --client-protocol Encrypted \
  --clustering-policy NoCluster \
  --access-keys-authentication Enabled \
  --public-network-access Enabled

echo
echo "After create:"
echo "  1) PRIMARY_KEY=\$(az redisenterprise database list-keys -g $RG --cluster-name $NAME --query primaryKey -o tsv)"
echo "  2) az keyvault secret set --vault-name $KV -n redis-primary-key --value \"\$PRIMARY_KEY\""
echo "  3) HOST=\$(az redisenterprise show -g $RG -n $NAME --query hostName -o tsv)"
echo "  4) PORT=10000 (default database)"
echo "  5) STRLIX_REDIS_URL=rediss://:\$PRIMARY_KEY@\$HOST:\$PORT/0  — do NOT cut over until smoke clean"
echo "  6) Keep ca-redis running until cutover documented"
echo
[[ "$APPLY" -eq 0 ]] && echo "Re-run with --apply after Day-1 budget OK."
