#!/usr/bin/env bash
# Attach a custom domain + AFD managed certificate to the existing endpoint.
# Endpoint hostname: strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net
# SAFE DEFAULT: dry-run. --apply refuses to run unless DOMAIN is set in the
# environment (the placeholder printed below is not implicit consent).
# Does not assume you own the DNS zone. Does not delete Front Door resources.
# RG lock: rg-zevi-cloudphone only.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
PROFILE="${PROFILE:-afd-zevi-strlix}"
ENDPOINT="${ENDPOINT:-strlix-edge}"
AFD_HOST="${AFD_HOST:-strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net}"
DOMAIN_NAME="${DOMAIN_NAME:-strlix-app}"
DOMAIN_EXPLICIT="${DOMAIN:-}"
DOMAIN="${DOMAIN:-app.strlix.app}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

if [[ "$APPLY" -eq 1 && -z "$DOMAIN_EXPLICIT" ]]; then
  echo "Refusing --apply: export DOMAIN to the hostname you control."
  echo "Example: DOMAIN=app.strlix.app $0 --apply"
  echo "app.strlix.app in this file is a placeholder, not proof of DNS ownership."
  exit 2
fi

echo "Custom domain plan for AFD endpoint $AFD_HOST"
echo "  hostname: $DOMAIN"
echo "  Azure name: $DOMAIN_NAME"
echo "  profile: $PROFILE  endpoint: $ENDPOINT  rg: $RG"
if [[ -z "$DOMAIN_EXPLICIT" ]]; then
  echo "  DOMAIN is unset — printing the placeholder host only."
fi

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

run az afd custom-domain create -g "$RG" --profile-name "$PROFILE" \
  --custom-domain-name "$DOMAIN_NAME" \
  --host-name "$DOMAIN" \
  --certificate-type ManagedCertificate \
  --minimum-tls-version TLS12

echo
echo "DNS you must create at the registrar that owns the parent zone (not in this repo):"
echo "  CNAME  ${DOMAIN}  ->  ${AFD_HOST}"
echo "  TXT    _dnsauth.${DOMAIN}  ->  <validation token from the command below>"
echo
echo "Read the token (after the domain resource exists):"
echo "  az afd custom-domain show -g $RG --profile-name $PROFILE --custom-domain-name $DOMAIN_NAME \\"
echo "    --query '{state:domainValidationState,token:validationProperties.validationToken}' -o json"
echo
echo "Managed cert provisions only after the TXT (and CNAME) validate. Re-check:"
echo "  az afd custom-domain show -g $RG --profile-name $PROFILE -n $DOMAIN_NAME --query domainValidationState -o tsv"

echo
echo "Associate the domain with the market route without dropping the *.azurefd.net name:"
run az afd route update -g "$RG" --profile-name "$PROFILE" --endpoint-name "$ENDPOINT" \
  -n route-market \
  --custom-domains "$DOMAIN_NAME" \
  --link-to-default-domain Enabled

echo
echo "Legal pages are served by market-api at /legal/*. Extend the route patterns"
echo "with infra/hardening/EXTEND-AFD-ROUTES.sh so the custom host can reach them."
echo "The phone viewer itself is desktop-api and is not an origin on this Front Door."
[[ "$APPLY" -eq 0 ]] && echo "Dry-run only."
