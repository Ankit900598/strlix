# Monitoring and alerts — soft launch stubs

**RG lock:** `rg-zevi-cloudphone` only. Do not delete resources.  
**Workspace already in the RG:** Application Insights `appi-zevi-strlix` → Log Analytics `law-zevi-strlix` (eastus2).  
Action group and metric alerts below are **stubs**. The script does not apply them unless `CONFIRM=yes`.

Email on the action group defaults to the placeholder `support@strlix.app`. Replace it before apply.

## What to watch

| Signal | Resource | Why |
|--------|----------|-----|
| `/health` not 200 | AFD `afd-zevi-strlix` and origin `ca-market-api` | Probe path. WAF must not block it. |
| `redis: false` on market `/health` | `ca-market-api` logs + `redis-strlix-amr` | Sessions and rate limits fail closed (429) when Redis is configured but down. |
| 5xx ratio | `ca-market-api`, `ca-android-api` | API process or dependency failure. |
| Restart count | both container apps | Crash loop after an env change (Entra, Redis URL). |
| CPU / storage / failed connections | `psql-zevi-strlix` (centralus, B1ms) | Tenant data. HA is off. |
| Server load / connected clients | `redis-strlix-amr` (eastus, B0) | Rate-limit and session store. |
| Origin health | AFD origin groups `og-market-api`, `og-android-api` | Edge can be 200 on a cached error page only if probes lie — check origin too. |

`pay_mode` on `/health` must stay `test` and `card_required` must stay false during the free month. An alert on log text is optional; a human check after every ACA revision is enough for this launch.

## Script

```bash
./infra/ops/CREATE-ALERTS.sh
CONFIRM=yes SUPPORT_EMAIL=you@your-domain ./infra/ops/CREATE-ALERTS.sh --apply
```

Confirm metric names in the portal Metrics blade before trusting a fired alert. Names in the script match the common Azure metric IDs as of this writing and can drift.

## Logs (no tokens, no emails in queries you paste into tickets)

```bash
az monitor app-insights query -g rg-zevi-cloudphone -a appi-zevi-strlix \
  --analytics-query "requests | where timestamp > ago(1h) | summarize count() by resultCode, name | order by count_ desc"
```

Do not query or export request bodies. Waitlist emails are in Postgres, not in App Insights, if the API is doing its job.
