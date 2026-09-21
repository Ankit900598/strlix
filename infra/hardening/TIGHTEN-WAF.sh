#!/usr/bin/env bash
# Add Front Door WAF custom rate-limit rules for anonymous and signup paths.
# SAFE DEFAULT: dry-run. Pass --apply to create rules.
# Does not match /health. Does not change SKU, mode, or delete the policy.
# RG lock: rg-zevi-cloudphone only.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
WAF="${WAF:-wafzevistrlix}"
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

echo "WAF $WAF in $RG — custom rate limits only. /health is not a match condition."
echo "Managed OWASP rules need Front Door Premium. This script does not change SKU."
echo "Edge threshold is 100/min/IP, looser than market-api so a demo is not blocked."

add_rule() {
  local name="$1" priority="$2" needle="$3"
  run az network front-door waf-policy rule create \
    -g "$RG" --policy-name "$WAF" \
    -n "$name" --priority "$priority" \
    --rule-type RateLimitRule \
    --rate-limit-duration 1 \
    --rate-limit-threshold 100 \
    --action Block \
    --match-condition "[{\"matchVariable\":\"RequestUri\",\"operator\":\"Contains\",\"matchValue\":[\"${needle}\"],\"negateCondition\":false}]"
}

add_rule RateLimitAuthAnon 110 "/v1/auth/anon"
add_rule RateLimitWaitlist 120 "/v1/waitlist"
add_rule RateLimitAuthLogin 130 "/v1/auth/login"

echo
echo "After --apply, smoke (must stay 200):"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health"
echo "If a rule 403s /health, delete only that rule:"
echo "  az network front-door waf-policy rule delete -g $RG --policy-name $WAF -n <RuleName>"
[[ "$APPLY" -eq 0 ]] && echo "Dry-run only. Re-run with --apply to create the three rules."
