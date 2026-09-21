#!/usr/bin/env bash
# Action group + metric alert stubs for the soft launch.
# SAFE DEFAULT: dry-run. --apply requires CONFIRM=yes.
# Does not delete alerts, apps, or the Log Analytics workspace.
# RG lock: rg-zevi-cloudphone only.
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
AG="${AG:-ag-strlix-launch}"
EMAIL="${SUPPORT_EMAIL:-support@strlix.app}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

echo "Alert stubs in $RG. Email: $EMAIL"
if [[ "$EMAIL" == "support@strlix.app" ]]; then
  echo "NOTE: support@strlix.app is a placeholder. Set SUPPORT_EMAIL before --apply."
fi
echo "Metric names should be confirmed in the portal before you depend on them."

if [[ "$APPLY" -eq 1 && "${CONFIRM:-}" != "yes" ]]; then
  echo "Refusing --apply without CONFIRM=yes."
  exit 2
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

SUB="$(az account show --query id -o tsv 2>/dev/null || echo '<subscription-id>')"
SCOPE_MARKET="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.App/containerApps/ca-market-api"
SCOPE_ANDROID="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.App/containerApps/ca-android-api"
SCOPE_AFD="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Cdn/profiles/afd-zevi-strlix"
SCOPE_REDIS="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.Cache/redisEnterprise/redis-strlix-amr"
SCOPE_PG="/subscriptions/${SUB}/resourceGroups/${RG}/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-zevi-strlix"

run az monitor action-group create -g "$RG" -n "$AG" --short-name strlix \
  --action email support "$EMAIL"

# Restart loops on the two APIs.
run az monitor metrics alert create -g "$RG" -n alert-market-restarts \
  --scopes "$SCOPE_MARKET" --description "ca-market-api restart count" \
  --condition "total RestartCount > 3" --window-size 15m --evaluation-frequency 5m \
  --action "$AG" --severity 2
run az monitor metrics alert create -g "$RG" -n alert-android-restarts \
  --scopes "$SCOPE_ANDROID" --description "ca-android-api restart count" \
  --condition "total RestartCount > 3" --window-size 15m --evaluation-frequency 5m \
  --action "$AG" --severity 2

# Edge 5xx. Confirm the metric + dimension in the portal; threshold is a stub.
run az monitor metrics alert create -g "$RG" -n alert-afd-5xx \
  --scopes "$SCOPE_AFD" --description "AFD 5xx percentage" \
  --condition "avg Percentage5XX > 5" --window-size 15m --evaluation-frequency 5m \
  --action "$AG" --severity 2

# Postgres storage on the small B1ms. CPU is noisy on burstable; storage filling is the page.
run az monitor metrics alert create -g "$RG" -n alert-pg-storage \
  --scopes "$SCOPE_PG" --description "Postgres storage percent" \
  --condition "avg storage_percent > 80" --window-size 15m --evaluation-frequency 15m \
  --action "$AG" --severity 2

# Redis. connectedclients name can differ on Managed Redis — confirm before paging.
run az monitor metrics alert create -g "$RG" -n alert-redis-server-load \
  --scopes "$SCOPE_REDIS" --description "Managed Redis server load" \
  --condition "avg serverLoad > 80" --window-size 15m --evaluation-frequency 5m \
  --action "$AG" --severity 2

echo
echo "These alerts do not prove /health redis:true. Keep a manual curl after each revision:"
echo "  curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health"
[[ "$APPLY" -eq 0 ]] && echo "Dry-run only."
