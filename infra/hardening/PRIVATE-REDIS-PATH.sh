#!/usr/bin/env bash
# Document and optionally wire CAE (eastus2) to the eastus Redis private endpoint.
# SAFE DEFAULT: dry-run / inspect. Never deletes resources.
# Disabling Redis publicNetworkAccess requires --apply AND CONFIRM=yes,
# and is skipped when the Container Apps environment has no VNet.
# RG lock: rg-zevi-cloudphone only.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
CAE="${CAE:-cae-zevi-strlix}"
VNET_EASTUS="${VNET_EASTUS:-vm-zevi-cloudphone-vnet}"
REDIS="${REDIS:-redis-strlix-amr}"
PE="${PE:-pe-redis-strlix-amr}"
DNS_ZONE="${DNS_ZONE:-privatelink.redis.azure.net}"
APP="${APP:-ca-market-api}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "Private Redis path for $PE → $REDIS. Public access stays Enabled unless CONFIRM=yes."
echo "Do not delete $CAE, $REDIS, $PE, or ca-redis."

if ! command -v az >/dev/null 2>&1; then
  echo "az CLI not on PATH — printing the plan only."
  APPLY=0
fi

echo
echo "== Inspect CAE VNet (expect null on the current consumption env) =="
if command -v az >/dev/null 2>&1; then
  az containerapp env show -g "$RG" -n "$CAE" \
    --query "{name:name,location:location,vnet:properties.vnetConfiguration}" -o json \
    || echo "WARN: could not read $CAE"
else
  echo "[dry-run] az containerapp env show -g $RG -n $CAE --query properties.vnetConfiguration"
fi

CAE_VNET=""
if [[ "$APPLY" -eq 1 ]]; then
  CAE_VNET="$(az containerapp env show -g "$RG" -n "$CAE" --query "properties.vnetConfiguration.infrastructureSubnetId" -o tsv 2>/dev/null || true)"
fi

if [[ "$APPLY" -eq 1 && -z "$CAE_VNET" ]]; then
  echo
  echo "BLOCKED: $CAE has no infrastructure subnet."
  echo "Azure cannot add VNet integration to this existing consumption environment in place."
  echo "Do not delete or recreate $CAE in this step. Leave Redis publicNetworkAccess=Enabled."
  echo "Revisit when a VNet-integrated environment exists, then re-run --apply."
  exit 0
fi

echo
echo "== When a CAE VNet exists: peer eastus2 ↔ eastus and link private DNS =="
echo "Cross-region peering is extra cost. It does not by itself disable public Redis."

run() {
  if [[ "$APPLY" -eq 1 ]]; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  else
    printf '[dry-run]'
    printf ' %q' "$@"
    printf '\n'
  fi
}

# Names are only used when --apply discovered a subnet id. Dry-run prints the shape.
echo "CAE subnet id: ${CAE_VNET:-<none — dry-run or missing>}"
if [[ "$APPLY" -eq 1 ]]; then
  CAE_VNET_ID="$(az network vnet show --ids "$(dirname "$(dirname "$CAE_VNET")")" --query id -o tsv)"
  # infrastructureSubnetId is .../virtualNetworks/<name>/subnets/<subnet>
  CAE_VNET_NAME="$(echo "$CAE_VNET" | sed -n 's#.*/virtualNetworks/\([^/]*\)/subnets/.*#\1#p')"
  CAE_VNET_RG="$(echo "$CAE_VNET" | sed -n 's#.*/resourceGroups/\([^/]*\)/.*#\1#p')"
  EASTUS_ID="$(az network vnet show -g "$RG" -n "$VNET_EASTUS" --query id -o tsv)"
  run az network vnet peering create -g "$CAE_VNET_RG" -n peer-cae-to-eastus \
    --vnet-name "$CAE_VNET_NAME" --remote-vnet "$EASTUS_ID" --allow-vnet-access
  run az network vnet peering create -g "$RG" -n peer-eastus-to-cae \
    --vnet-name "$VNET_EASTUS" --remote-vnet "$CAE_VNET_ID" --allow-vnet-access
  run az network private-dns link vnet create -g "$RG" -z "$DNS_ZONE" \
    -n link-cae-redis --virtual-network "$CAE_VNET_ID" --registration-enabled false
  echo "Smoke market-api /health (redis must stay true) BEFORE any public-access change:"
  echo "  curl -sS https://\$(az containerapp show -g $RG -n $APP --query properties.configuration.ingress.fqdn -o tsv)/health"
fi

echo
if [[ "${CONFIRM:-}" != "yes" ]]; then
  echo "Skipping publicNetworkAccess=Disabled (set CONFIRM=yes and --apply, after the smoke above)."
  echo "Rollback if you ever disable it and health fails:"
  echo "  az redisenterprise update -g $RG -n $REDIS --public-network-access Enabled"
  exit 0
fi

if [[ "$APPLY" -ne 1 ]]; then
  echo "CONFIRM=yes seen but --apply not set. Not changing public access."
  exit 0
fi

echo "CONFIRM=yes — disabling public network access on $REDIS."
echo "Only do this after /health from $APP shows redis:true over the private path."
run az redisenterprise update -g "$RG" -n "$REDIS" --public-network-access Disabled
echo "Re-check /health. If redis:false, re-enable public access immediately (command printed above)."
