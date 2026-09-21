#!/usr/bin/env bash
# Private Endpoint stubs for Key Vault + Redis (eastus2). Postgres SKIP this sprint.
# SAFE DEFAULT: dry-run + cost notes. Pass --apply to create.
# RG: rg-zevi-cloudphone only. Do not delete resources.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
LOC="${LOC:-eastus2}"
VNET="${VNET:-vm-zevi-cloudphone-vnet}"   # may need a dedicated eastus2 vnet/peering — verify
SUBNET="${SUBNET:-pe-subnet}"             # must exist with privateEndpointNetworkPolicies=Disabled
KV="${KV:-kv-zevi-strlix}"
REDIS="${REDIS:-redis-zevi-strlix}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

run() {
  if [[ "$APPLY" -eq 1 ]]; then echo "+ $*"; eval "$@"; else echo "[dry-run] $*"; fi
}

cat <<COST
=== Cost notes (retail, approx) ===
- Private Endpoint: ~\$7.30/mo each + \$0.01/GB data processing
- Private DNS zone: pennies
- Recommendation this sprint: CREATE KV + Redis PEs in eastus2 (same as CAE)
- SKIP Postgres PE: psql-zevi-strlix is in centralus → cross-region PE pain; migrate region Day-4+
- 2 PEs ≈ \$15–20/mo — fits Day-1 hardening bucket
COST

echo
echo "Prereq: subnet $SUBNET in a VNet that CAE can reach (peer if needed)."
echo "Verify: az network vnet subnet show -g $RG --vnet-name <vnet> -n $SUBNET"

KV_ID=$(az keyvault show -g "$RG" -n "$KV" --query id -o tsv 2>/dev/null || echo "/subscriptions/.../resourceGroups/$RG/providers/Microsoft.KeyVault/vaults/$KV")
REDIS_ID="pending-until-redis-created"

run az network private-endpoint create -g "$RG" -n pe-kv-zevi-strlix -l "$LOC" \
  --vnet-name "$VNET" --subnet "$SUBNET" \
  --private-connection-resource-id "$KV_ID" \
  --group-id vault --connection-name pe-conn-kv

run az network private-dns zone create -g "$RG" -n privatelink.vaultcore.azure.net
run az network private-endpoint dns-zone-group create -g "$RG" \
  --endpoint-name pe-kv-zevi-strlix -n kv-zone-group \
  --private-dns-zone privatelink.vaultcore.azure.net --zone-name vault

echo
echo "[stub] Redis PE (after CREATE-redis.sh --apply):"
echo "  az network private-endpoint create -g $RG -n pe-redis-zevi-strlix -l $LOC \\"
echo "    --vnet-name <eastus2-vnet> --subnet $SUBNET \\"
echo "    --private-connection-resource-id \$REDIS_ID \\"
echo "    --group-id redisCache --connection-name pe-conn-redis"
echo "  DNS zone: privatelink.redis.cache.windows.net"
echo
echo "[SKIP] Postgres PE — server region centralus; document only."
[[ "$APPLY" -eq 0 ]] && echo "Dry-run only. Fix VNet/subnet names, then --apply for KV PE."
