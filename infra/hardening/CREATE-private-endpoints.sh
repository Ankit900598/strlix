#!/usr/bin/env bash
# Private Endpoints for Azure Managed Redis (eastus) + optional Key Vault (eastus2 SKIP).
# SAFE DEFAULT: dry-run + cost notes. Pass --apply to create Redis PE.
# RG: rg-zevi-cloudphone only. Do not delete resources. Do not disable Redis public access
# while market-api (CAE eastus2) still reaches Redis over the public endpoint.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
LOC_REDIS="${LOC_REDIS:-eastus}"          # redis-strlix-amr + vm-zevi-cloudphone-vnet
LOC_KV="${LOC_KV:-eastus2}"               # kv-zevi-strlix (cross-region — SKIP PE by default)
VNET="${VNET:-vm-zevi-cloudphone-vnet}"
SUBNET="${SUBNET:-pe-subnet}"             # 10.0.1.0/27; privateEndpointNetworkPolicies=Disabled
REDIS="${REDIS:-redis-strlix-amr}"        # Microsoft.Cache/redisEnterprise (Azure Managed Redis)
KV="${KV:-kv-zevi-strlix}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

run() {
  if [[ "$APPLY" -eq 1 ]]; then echo "+ $*"; eval "$@"; else echo "[dry-run] $*"; fi
}

ensure_pe_subnet() {
  local exists
  exists=$(az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SUBNET" --query name -o tsv 2>/dev/null || true)
  if [[ -n "$exists" ]]; then
    echo "OK: subnet $SUBNET already on $VNET"
    return 0
  fi
  run az network vnet subnet create -g "$RG" --vnet-name "$VNET" -n "$SUBNET" \
    --address-prefixes 10.0.1.0/27 \
    --private-endpoint-network-policies Disabled
}

cat <<COST
=== Cost notes (retail, approx) ===
- Private Endpoint: ~\$7.30/mo each + \$0.01/GB data processing
- Private DNS zone: pennies
- pe-subnet on existing VNet: \$0 (no extra VNet)
- Recommendation: CREATE Redis PE in eastus (same region as AMR + VNet) ≈ \$7–8/mo
- SKIP Key Vault PE: kv-zevi-strlix is eastus2; a dedicated eastus2 VNet+pe-subnet
  (+ optional peering) adds complexity and typically >\$15/mo when counted with a
  second PE. Prefer SKIP until CAE VNet integration / same-region KV.
- SKIP Postgres PE: psql-zevi-strlix is centralus — unchanged
- Do NOT set Redis publicNetworkAccess=Disabled until market-api can reach PE
  (CAE is eastus2; PE lives on eastus VNet — public path still required today)
COST

echo
ensure_pe_subnet

REDIS_ID=$(az redisenterprise show -g "$RG" -n "$REDIS" --query id -o tsv 2>/dev/null || echo "")
if [[ -z "$REDIS_ID" ]]; then
  echo "ERROR: Managed Redis $REDIS not found in $RG — abort Redis PE."
  exit 1
fi

# Azure Managed Redis / Redis Enterprise PE:
#   group-id: redisEnterprise
#   DNS zone: privatelink.redis.azure.net
# (classic Cache for Redis used group-id redisCache + privatelink.redis.cache.windows.net)
run az network private-endpoint create -g "$RG" -n pe-redis-strlix-amr -l "$LOC_REDIS" \
  --vnet-name "$VNET" --subnet "$SUBNET" \
  --private-connection-resource-id "$REDIS_ID" \
  --group-id redisEnterprise --connection-name pe-conn-redis-amr

run az network private-dns zone create -g "$RG" -n privatelink.redis.azure.net
run az network private-dns link vnet create -g "$RG" \
  -n "link-${VNET}" -z privatelink.redis.azure.net \
  --virtual-network "$VNET" --registration-enabled false
run az network private-endpoint dns-zone-group create -g "$RG" \
  --endpoint-name pe-redis-strlix-amr -n redis-amr-zone-group \
  --private-dns-zone privatelink.redis.azure.net --zone-name redis

echo
echo "[SKIP] Key Vault PE — $KV is in $LOC_KV; VNet $VNET is $LOC_REDIS (cross-region)."
echo "  Prefer SKIP vs new eastus2 VNet+pe-subnet (extra complexity / >\$15/mo with PE)."
echo "  To revisit later: create eastus2 VNet, pe-subnet, PE with --group-id vault,"
echo "  DNS privatelink.vaultcore.azure.net; do not disable KV public access until CAE"
echo "  VNet integration can resolve the private zone."
echo
echo "[SKIP] Postgres PE — server region centralus; document only."
echo
echo "IMPORTANT: leave Redis publicNetworkAccess=Enabled so market-api (eastus2 CAE)"
echo "keeps connectivity. PE enables private path for eastus VNet clients (VM / future)."
[[ "$APPLY" -eq 0 ]] && echo "Dry-run only. Re-run with --apply to create Redis PE."
