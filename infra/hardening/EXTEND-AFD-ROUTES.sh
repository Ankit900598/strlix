#!/usr/bin/env bash
# Add /legal/* to the existing market Front Door route.
# SAFE DEFAULT: dry-run. Does not remove /health. Does not delete routes.
# RG lock: rg-zevi-cloudphone only.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
PROFILE="${PROFILE:-afd-zevi-strlix}"
ENDPOINT="${ENDPOINT:-strlix-edge}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "Keep existing patterns and add /legal/* so Terms/Privacy/Support/Limits"
echo "on market-api are reachable via the Front Door host. /health stays listed."

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

run az afd route update -g "$RG" --profile-name "$PROFILE" --endpoint-name "$ENDPOINT" \
  -n route-market \
  --patterns-to-match "['/v1/*','/market/*','/health','/ready','/legal/*']" \
  --link-to-default-domain Enabled

echo
echo "Smoke after apply:"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/legal/terms.html"
[[ "$APPLY" -eq 0 ]] && echo "Dry-run only."
