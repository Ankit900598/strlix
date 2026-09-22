#!/usr/bin/env bash
# Cheap, reversible next step on the private Redis path — WITHOUT disabling
# publicNetworkAccess and WITHOUT recreating CAE.
#
# SAFE DEFAULT: inspect + print plan only.
#   ./PRIVATE-REDIS-NEXT.sh
#   CONFIRM=yes ./PRIVATE-REDIS-NEXT.sh --apply
#     → creates empty reserved subnet cae-infra-subnet 10.0.2.0/23 on
#       vm-zevi-cloudphone-vnet (eastus) delegated to Microsoft.App/environments.
#       $0 networking cost; deleteable while empty. Does NOT create/recreate CAE.
#
# Still blocked for cutover: CAE is eastus2 with vnetConfiguration=null.
# Option B (later, operator-gated): new CAE in eastus on this subnet, then PE DNS.
# RG lock: rg-zevi-cloudphone only. Never touch publicNetworkAccess here.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
VNET="${VNET:-vm-zevi-cloudphone-vnet}"
SUBNET_NAME="${SUBNET_NAME:-cae-infra-subnet}"
SUBNET_PREFIX="${SUBNET_PREFIX:-10.0.2.0/23}"
CAE="${CAE:-cae-zevi-strlix}"
REDIS="${REDIS:-redis-strlix-amr}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "== Private Redis NEXT (docs + optional reserved subnet) =="
echo "RG=$RG VNET=$VNET planned subnet=$SUBNET_NAME $SUBNET_PREFIX"
echo "Will NOT disable $REDIS publicNetworkAccess. Will NOT delete/recreate $CAE."

if command -v az >/dev/null 2>&1; then
  echo
  echo "-- Current CAE (expect vnet=null, eastus2) --"
  az containerapp env show -g "$RG" -n "$CAE" \
    --query "{name:name,location:location,vnet:properties.vnetConfiguration}" -o json \
    || echo "WARN: could not read $CAE"
  echo
  echo "-- Current VNet subnets --"
  az network vnet subnet list -g "$RG" --vnet-name "$VNET" \
    --query "[].{name:name,prefix:addressPrefix,delegations:delegations[].serviceName}" -o table \
    || true
  echo
  echo "-- Redis public access (must stay Enabled) --"
  az redisenterprise show -g "$RG" -n "$REDIS" \
    --query "{name:name,publicNetworkAccess:properties.publicNetworkAccess,host:properties.hostName}" -o json \
    2>/dev/null || az redisenterprise show -g "$RG" -n "$REDIS" -o json 2>/dev/null | head -40 || true
else
  echo "az CLI missing — plan only."
  APPLY=0
fi

echo
echo "Plan:"
echo "  1. Keep public Redis Enabled (status quo / soft-launch)."
echo "  2. Reserve $SUBNET_NAME $SUBNET_PREFIX on $VNET for a *future* eastus CAE"
echo "     (Microsoft.App/environments). pe-subnet stays 10.0.1.0/27 for PE only —"
echo "     do not enlarge pe-subnet; CAE needs dedicated ≥/23 infra subnet."
echo "  3. Later Option B (separate approval): create NEW CAE in eastus on that"
echo "     subnet, migrate apps, smoke PE DNS, THEN consider CONFIRM=yes on"
echo "     PRIVATE-REDIS-PATH.sh to disable public access."
echo
echo "Rollback reserved subnet (only if empty / unused):"
echo "  az network vnet subnet delete -g $RG --vnet-name $VNET -n $SUBNET_NAME"

if [[ "$APPLY" -ne 1 ]]; then
  echo
  echo "Dry-run only. Re-run: CONFIRM=yes $0 --apply"
  exit 0
fi

if [[ "${CONFIRM:-}" != "yes" ]]; then
  echo
  echo "BLOCKED: --apply without CONFIRM=yes. No Azure changes."
  exit 0
fi

existing="$(az network vnet subnet show -g "$RG" --vnet-name "$VNET" -n "$SUBNET_NAME" --query name -o tsv 2>/dev/null || true)"
if [[ -n "$existing" ]]; then
  echo "SKIP: $SUBNET_NAME already exists."
  exit 0
fi

echo
echo "CONFIRM=yes — creating empty reserved subnet $SUBNET_NAME ($SUBNET_PREFIX)."
az network vnet subnet create \
  -g "$RG" --vnet-name "$VNET" -n "$SUBNET_NAME" \
  --address-prefixes "$SUBNET_PREFIX" \
  --delegations Microsoft.App/environments

echo "Done. CAE unchanged. Redis publicNetworkAccess unchanged."
echo "Next human gate: eastus CAE recreate plan — not this script."
