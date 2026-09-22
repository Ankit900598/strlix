#!/usr/bin/env bash
# OPTIONAL. Not required for the soft launch.
# Public legal pages are /market/legal/*.html, already matched by /market/*
# on route-market. This script only adds a direct /legal/* alias.
# Do not pass --apply unless you explicitly want that extra pattern.
# SAFE DEFAULT: dry-run. Does not remove /health. Does not delete routes.
# RG lock: rg-zevi-cloudphone only.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
PROFILE="${PROFILE:-afd-zevi-strlix}"
ENDPOINT="${ENDPOINT:-strlix-edge}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "OPTIONAL alias only. Soft-launch pages are already at /market/legal/*.html."
echo "This adds /legal/* beside the existing patterns. /health stays listed."
echo "Do not --apply unless you want that extra pattern."

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
echo "Public page (no route change required, after the market-api image includes web-market/legal):"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html"
echo "Smoke after an optional --apply of the /legal/* alias:"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/legal/terms.html"
[[ "$APPLY" -eq 0 ]] && echo "Dry-run only."
