#!/usr/bin/env bash
# Add Front Door WAF custom rate-limit rules for anonymous and signup paths.
# SAFE DEFAULT: dry-run. Pass --apply to create rules.
# Does not match /health. Does not change SKU, mode, or delete the policy.
# RG lock: rg-zevi-cloudphone only.
#
# az CLI note (2026): `rule create` takes --match-variable / --operator / --values
# (and optional --negate). There is NO --match-condition JSON flag on current
# front-door extension; that was the prior --apply failure mode.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
WAF="${WAF:-wafzevistrlix}"
PROFILE="${PROFILE:-afd-zevi-strlix}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

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

echo "WAF $WAF in $RG (AFD profile $PROFILE) — custom rate limits only."
echo "/health is NOT a match value. Managed OWASP needs Front Door Premium; SKU unchanged."
echo "Edge threshold: 100 req / 1 min / IP (RateLimitRule)."

EXISTING_RULES=""
if command -v az >/dev/null 2>&1; then
  EXISTING_RULES="$(az network front-door waf-policy show -g "$RG" -n "$WAF" \
    --query 'customRules.rules[].name' -o tsv 2>/dev/null || true)"
fi

# Current az network front-door waf-policy rule create:
#   --match-variable RequestUri --operator Contains --values <path>
add_rule() {
  local name="$1" priority="$2" needle="$3"
  if printf '%s\n' "$EXISTING_RULES" | grep -qx "$name"; then
    echo "SKIP $name — already present on $WAF"
    return 0
  fi
  run az network front-door waf-policy rule create \
    -g "$RG" --policy-name "$WAF" \
    -n "$name" --priority "$priority" \
    --rule-type RateLimitRule \
    --rate-limit-duration 1 \
    --rate-limit-threshold 100 \
    --action Block \
    --match-variable RequestUri \
    --operator Contains \
    --values "$needle"
}

add_rule RateLimitAuthAnon 110 "/v1/auth/anon"
add_rule RateLimitWaitlist 120 "/v1/waitlist"
add_rule RateLimitAuthLogin 130 "/v1/auth/login"

echo
echo "Working az commands (document for operators if --apply skipped):"
echo "  az network front-door waf-policy rule create -g $RG --policy-name $WAF \\"
echo "    -n RateLimitWaitlist --priority 120 --rule-type RateLimitRule \\"
echo "    --rate-limit-duration 1 --rate-limit-threshold 100 --action Block \\"
echo "    --match-variable RequestUri --operator Contains --values /v1/waitlist"
echo
echo "After --apply, smoke (must stay 200):"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health"
echo "If a rule 403s /health, delete only that rule:"
echo "  az network front-door waf-policy rule delete -g $RG --policy-name $WAF -n <RuleName>"
if [[ "$APPLY" -eq 0 ]]; then
  echo "Dry-run only. Re-run with --apply to create the three rules."
else
  echo "Apply finished. Re-check customRules on $WAF if needed."
fi
exit 0
