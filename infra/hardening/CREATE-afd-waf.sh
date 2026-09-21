#!/usr/bin/env bash
# Create Azure Front Door Standard + WAF for market-api / android-api fronts.
# SAFE DEFAULT: dry-run prints commands. Pass --apply to execute.
# RG lock: rg-zevi-cloudphone ONLY. Do not delete resources.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
PROFILE="${PROFILE:-afd-zevi-strlix}"
ENDPOINT="${ENDPOINT:-strlix-edge}"
WAF="${WAF:-wafzevistrlix}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "== Resolve Container App FQDNs in $RG =="
MARKET_FQDN=$(az containerapp show -g "$RG" -n ca-market-api --query properties.configuration.ingress.fqdn -o tsv)
ANDROID_FQDN=$(az containerapp show -g "$RG" -n ca-android-api --query properties.configuration.ingress.fqdn -o tsv)
echo "market origin:  $MARKET_FQDN"
echo "android origin: $ANDROID_FQDN"

run() {
  if [[ "$APPLY" -eq 1 ]]; then
    echo "+ $*"
    eval "$@"
  else
    echo "[dry-run] $*"
  fi
}

run az afd profile create -g "$RG" -n "$PROFILE" --sku Standard_AzureFrontDoor
run az afd endpoint create -g "$RG" --profile-name "$PROFILE" -n "$ENDPOINT" --enabled-state Enabled

run az network front-door waf-policy create -g "$RG" -n "$WAF" --sku Standard_AzureFrontDoor --mode Prevention

# Origin groups
run az afd origin-group create -g "$RG" --profile-name "$PROFILE" -n og-market-api \
  --probe-request-type GET --probe-protocol Https --probe-path /health --probe-interval-in-seconds 60 \
  --sample-size 4 --successful-samples-required 3 --additional-latency-in-milliseconds 50
run az afd origin create -g "$RG" --profile-name "$PROFILE" --origin-group-name og-market-api -n origin-market-api \
  --host-name "$MARKET_FQDN" --origin-host-header "$MARKET_FQDN" --priority 1 --weight 1000 --enabled-state Enabled --https-port 443

run az afd origin-group create -g "$RG" --profile-name "$PROFILE" -n og-android-api \
  --probe-request-type GET --probe-protocol Https --probe-path /health --probe-interval-in-seconds 60 \
  --sample-size 4 --successful-samples-required 3 --additional-latency-in-milliseconds 50
run az afd origin create -g "$RG" --profile-name "$PROFILE" --origin-group-name og-android-api -n origin-android-api \
  --host-name "$ANDROID_FQDN" --origin-host-header "$ANDROID_FQDN" --priority 1 --weight 1000 --enabled-state Enabled --https-port 443

# Routes (path split — refine after first traffic)
run az afd route create -g "$RG" --profile-name "$PROFILE" --endpoint-name "$ENDPOINT" -n route-market \
  --origin-group og-market-api --supported-protocols Http Https --https-redirect Enabled \
  --forwarding-protocol HttpsOnly --link-to-default-domain Enabled \
  --patterns-to-match '/v1/*' '/market/*' '/health' '/ready'

run az afd route create -g "$RG" --profile-name "$PROFILE" --endpoint-name "$ENDPOINT" -n route-android \
  --origin-group og-android-api --supported-protocols Http Https --https-redirect Enabled \
  --forwarding-protocol HttpsOnly --link-to-default-domain Enabled \
  --patterns-to-match '/android/*' '/agent/*'

# Security policy association (WAF → endpoint) — may need portal if CLI schema drifts
run az afd security-policy create -g "$RG" --profile-name "$PROFILE" -n sp-waf \
  --domains "/subscriptions/\$(az account show --query id -o tsv)/resourceGroups/$RG/providers/Microsoft.Cdn/profiles/$PROFILE/afdEndpoints/$ENDPOINT" \
  --waf-policy "/subscriptions/\$(az account show --query id -o tsv)/resourceGroups/$RG/providers/Microsoft.Network/frontdoorwebapplicationfirewallpolicies/$WAF" || true

echo
echo "Est. cost: ~\$35/mo AFD Standard base + egress + ~\$2.5 WAF policy."
echo "Bicep alternative: az deployment group create -g $RG -f infra/hardening/afd-waf.bicep \\
  -p marketOriginHost=$MARKET_FQDN androidOriginHost=$ANDROID_FQDN"
[[ "$APPLY" -eq 0 ]] && echo "Re-run with --apply to execute (after portal credit check)."
