# Soft-launch ops alerts — applied 2026-09-21 ~23:38 IST

**RG:** `rg-zevi-cloudphone` only  
**Sub:** `a3dc5296-f948-427e-8656-c6bc52afee21`  
**Goal:** few cheap alerts (metric + one activity-log). No SMS / webhook / Logic Apps.

## Action group

| Field | Value |
|-------|--------|
| Name | `ag-strlix-ops` |
| Short name | `strlixops` |
| Email | `ay186mnc@gmail.com` (receiver `ops-primary`, Enabled) |
| Resource ID | `/subscriptions/a3dc5296-f948-427e-8656-c6bc52afee21/resourceGroups/rg-zevi-cloudphone/providers/microsoft.insights/actionGroups/ag-strlix-ops` |

**Note:** first email from a new action group may require inbox confirmation (“Microsoft Azure” / “Azure Monitor”). If alerts fire but no mail arrives, check spam and confirm the subscription link.

## Alert rules (4)

| Name | Type | Scope | Condition | Window / eval | Sev |
|------|------|-------|-----------|---------------|-----|
| `alert-afd-origin-unhealthy` | Metric | `afd-zevi-strlix` | `avg OriginHealthPercentage < 80` | 5m / 1m | 2 |
| `alert-afd-5xx` | Metric | `afd-zevi-strlix` | `avg Percentage5XX > 10` | 5m / 1m | 2 |
| `alert-ca-market-restarts` | Metric | `ca-market-api` | `total RestartCount > 3` | 15m / 5m | 2 |
| `alert-redis-resource-health` | Activity log | `redis-strlix-amr` | `category=ResourceHealth` | n/a | n/a |

### Why these three failure modes

1. **AFD origin unhealthy** — probe failures on market/android origins surface as `OriginHealthPercentage`.
2. **market-api 5xx / instability** — ACA has no first-class Http5xx metric; edge `Percentage5XX` covers customer-visible 5xx. Restart storms covered separately via `RestartCount`.
3. **Redis unavailable** — Managed Redis (`Microsoft.Cache/redisEnterprise`) has no simple “up/down” metric; Resource Health activity-log alert is the cheap signal. Public access remains Enabled (see `PRIVATE-REDIS-PATH.md`).

## Exact recreate commands (if portal/API ever wiped them)

```bash
RG=rg-zevi-cloudphone
SUB=a3dc5296-f948-427e-8656-c6bc52afee21
EMAIL=ay186mnc@gmail.com

az monitor action-group create -g "$RG" -n ag-strlix-ops \
  --short-name strlixops --action email ops-primary "$EMAIL"

AG_ID=$(az monitor action-group show -g "$RG" -n ag-strlix-ops --query id -o tsv)
AFD_ID="/subscriptions/$SUB/resourcegroups/$RG/providers/Microsoft.Cdn/profiles/afd-zevi-strlix"
CA_ID=$(az containerapp show -g "$RG" -n ca-market-api --query id -o tsv)
REDIS_ID=$(az redisenterprise show -g "$RG" -n redis-strlix-amr --query id -o tsv)

az monitor metrics alert create -g "$RG" -n alert-afd-origin-unhealthy \
  --scopes "$AFD_ID" --condition "avg OriginHealthPercentage < 80" \
  --window-size 5m --evaluation-frequency 1m --severity 2 \
  --description "AFD origin health <80% (5m)" --action "$AG_ID" --auto-mitigate true

az monitor metrics alert create -g "$RG" -n alert-afd-5xx \
  --scopes "$AFD_ID" --condition "avg Percentage5XX > 10" \
  --window-size 5m --evaluation-frequency 1m --severity 2 \
  --description "AFD Percentage5XX >10 (5m)" --action "$AG_ID" --auto-mitigate true

az monitor metrics alert create -g "$RG" -n alert-ca-market-restarts \
  --scopes "$CA_ID" --condition "total RestartCount > 3" \
  --window-size 15m --evaluation-frequency 5m --severity 2 \
  --description "ca-market-api restart storm" --action "$AG_ID" --auto-mitigate true

az monitor activity-log alert create -g "$RG" -n alert-redis-resource-health \
  --scope "$REDIS_ID" --condition category=ResourceHealth \
  --action-group "$AG_ID" \
  --description "redis-strlix-amr Resource Health"
```

## Blockers / non-goals

- **No Entra / portal block** on create (CLI as `ay186mnc@gmail.com` succeeded).
- Did **not** add SMS, Teams, or PagerDuty (cost / setup).
- Did **not** create App Insights availability tests (extra cost).
- Did **not** touch Stripe live gates / payment alerts.
- Custom domain / custom AFD hostname: **out of scope** for this alert pass (still on `*.azurefd.net`).

## Verify

```bash
az monitor action-group list -g rg-zevi-cloudphone -o table
az monitor metrics alert list -g rg-zevi-cloudphone -o table
az monitor activity-log alert list -g rg-zevi-cloudphone -o table
```
