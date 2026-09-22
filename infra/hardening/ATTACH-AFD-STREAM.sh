#!/usr/bin/env bash
# Attach desktop-api (phone stream + viewer) to the existing Azure Front Door
# under same-origin paths used by web-market:
#   /stream   /stream/*   → viewer HTML (origin path rewrite → /)
#   /ws/*                 → H.264 / JPEG / live / stt websockets
#   /adb/*                → tap/swipe/key/preview
#   /voice/*              → Live voice helpers (pilot + desktop)
#   /replay/*             → replay artifacts
#   /demo/*               → demo screenshots (optional)
#   /static/*             → barge worklet etc.
#
# SAFE DEFAULT: dry-run. Pass --apply to execute.
# Does NOT touch market /v1/* (session bind stays local to stream host if needed).
# RG lock: rg-zevi-cloudphone ONLY. Do not delete resources.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
PROFILE="${PROFILE:-afd-zevi-strlix}"
ENDPOINT="${ENDPOINT:-strlix-edge}"
# Default: public HTTP desktop-api on the phone VM (AFD terminates HTTPS).
# Override with a Cloudflare tunnel hostname if the VM port is closed.
STREAM_ORIGIN_HOST="${STREAM_ORIGIN_HOST:-20.115.117.71}"
STREAM_ORIGIN_HTTP_PORT="${STREAM_ORIGIN_HTTP_PORT:-8789}"
ORIGIN_GROUP="${ORIGIN_GROUP:-og-desktop-stream}"
ORIGIN_NAME="${ORIGIN_NAME:-origin-desktop-stream}"
ROUTE_NAME="${ROUTE_NAME:-route-desktop-stream}"
RULE_SET="${RULE_SET:-rsStreamStrip}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "== Attach stream origin to AFD =="
echo "profile=$PROFILE endpoint=$ENDPOINT"
echo "origin host=$STREAM_ORIGIN_HOST port=$STREAM_ORIGIN_HTTP_PORT"
echo "public paths: /stream /stream/* /ws/* /adb/* /voice/* /replay/* /demo/* /static/*"
echo

run() {
  if [[ "$APPLY" -eq 1 ]]; then
    echo "+ $*"
    eval "$@"
  else
    echo "[dry-run] $*"
  fi
}

# Origin group + origin (HTTP backend; AFD presents HTTPS to browsers)
run az afd origin-group create -g "$RG" --profile-name "$PROFILE" -n "$ORIGIN_GROUP" \
  --probe-request-type GET --probe-protocol Http --probe-path /health \
  --probe-interval-in-seconds 60 --sample-size 4 --successful-samples-required 3 \
  --additional-latency-in-milliseconds 50 \
  2>/dev/null || echo "(origin-group may already exist)"

run az afd origin create -g "$RG" --profile-name "$PROFILE" --origin-group-name "$ORIGIN_GROUP" \
  -n "$ORIGIN_NAME" \
  --host-name "$STREAM_ORIGIN_HOST" \
  --origin-host-header "$STREAM_ORIGIN_HOST" \
  --http-port "$STREAM_ORIGIN_HTTP_PORT" \
  --https-port 443 \
  --priority 1 --weight 1000 --enabled-state Enabled \
  2>/dev/null || echo "(origin may already exist — update host if needed)"

# Path patterns that must NOT collide with market /v1/* or /market/*
run az afd route create -g "$RG" --profile-name "$PROFILE" --endpoint-name "$ENDPOINT" \
  -n "$ROUTE_NAME" \
  --origin-group "$ORIGIN_GROUP" \
  --supported-protocols '[Http,Https]' --https-redirect Enabled \
  --forwarding-protocol HttpOnly \
  --link-to-default-domain Enabled \
  --patterns-to-match "['/stream','/stream/*','/ws/*','/adb/*','/voice/*','/replay/*','/demo/*','/static/*']" \
  2>/dev/null || {
  echo "NOTE: route create soft-failed (may already exist). Update patterns if needed:"
  echo "  az afd route update -g $RG --profile-name $PROFILE --endpoint-name $ENDPOINT -n $ROUTE_NAME \\"
  echo "    --patterns-to-match \"['/stream','/stream/*','/ws/*','/adb/*','/voice/*','/replay/*','/demo/*','/static/*']\""
}

# Strip /stream prefix so desktop-api still serves / and /health at origin root.
# Viewer JS connects to wss://<afd-host>/ws/* (not under /stream) — those are
# routed directly above.
run az afd rule-set create -g "$RG" --profile-name "$PROFILE" -n "$RULE_SET" \
  2>/dev/null || echo "(rule-set may already exist)"

run az afd rule create -g "$RG" --profile-name "$PROFILE" --rule-set-name "$RULE_SET" \
  -n stripStreamPrefix --order 1 --match-variable UrlPath --operator BeginsWith \
  --match-values /stream --transforms Lowercase \
  2>/dev/null || echo "(rule may already exist)"

run az afd rule action add -g "$RG" --profile-name "$PROFILE" --rule-set-name "$RULE_SET" \
  --rule-name stripStreamPrefix --action-name UrlRewrite \
  --source-pattern "/stream" --destination "/" --preserve-unmatched-path true \
  2>/dev/null || echo "(rewrite action may already exist)"

run az afd route update -g "$RG" --profile-name "$PROFILE" --endpoint-name "$ENDPOINT" \
  -n "$ROUTE_NAME" --rule-sets "$RULE_SET" \
  2>/dev/null || echo "(route↔rule-set link may need portal)"

echo
echo "Verify after --apply (expect 200):"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/stream/"
echo "  curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/stream/health"
echo "  curl -sS -o /dev/null -w '%{http_code}\\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/adb/size"
echo
echo "If the VM NSG blocks AFD, open HTTP $STREAM_ORIGIN_HTTP_PORT from Azure Front Door"
echo "service tags, or set STREAM_ORIGIN_HOST to a Cloudflare tunnel hostname and"
echo "STREAM_ORIGIN_HTTP_PORT=80 with --forwarding-protocol HttpsOnly."
[[ "$APPLY" -eq 0 ]] && echo "Re-run with --apply to execute."
exit 0
