# Hardening + payments checklist (survives after credits)

**Updated:** 2026-09-21 ~19:45 IST · RG lock `rg-zevi-cloudphone` only · do not delete resources.

## Scripts / IaC in this folder

| Artifact | Purpose | Apply? |
|----------|---------|--------|
| `CREATE-afd-waf.sh` | Front Door Standard + WAF for market/android FQDNs | dry-run default; `--apply` Day 1 |
| `afd-waf.bicep` | Same as Bicep skeleton | after FQDN params |
| `CREATE-redis.sh` | Azure Cache for Redis Basic C0 | `--apply` Day 1; keep `ca-redis` until cutover |
| `CREATE-private-endpoints.sh` | PE stubs KV (+ Redis); Postgres SKIP | cost-documented |
| `ENTRA-EXTERNAL-ID.md` | Entra JWT validation, default `STRLIX_AUTH_MODE=anon` | code shipped; portal still Ankit |
| `PAYMENTS-KEYVAULT.md` | Flip Stripe keys via KV; triple live gate | code shipped; live OFF; deferred for free month |
| `ABUSE-CONTROLS.md` | Redis rate limits + WAF notes | doc |
| `TIGHTEN-WAF.sh` | Custom rate-limit rules; never matches `/health` | dry-run |
| `ATTACH-CUSTOM-DOMAIN.sh` | Managed cert on `strlix-edge` when `DOMAIN` is set | dry-run; `--apply` needs `DOMAIN` |
| `CUSTOM-DOMAIN.md` | DNS CNAME + TXT runbook | doc; domain not owned here |
| `EXTEND-AFD-ROUTES.sh` | Optional `/legal/*` alias. Public pages are already `/market/legal/*` | dry-run; do not apply for this soft launch |
| `ATTACH-AFD-STREAM.sh` | Attach desktop-api under `/stream` + `/ws/*` + `/adb/*` for phone viewers | dry-run; `--apply` when stream VM/tunnel is ready |
| `PRIVATE-REDIS-PATH.sh` | CAE↔eastus path; public access off only with `CONFIRM=yes` | dry-run; no-ops without CAE VNet |
| `PRIVATE-REDIS.md` | Why public Redis stays Enabled | doc |

## Front Door + WAF (CREATE Day 1)

```bash
./infra/hardening/CREATE-afd-waf.sh          # dry-run
./infra/hardening/CREATE-afd-waf.sh --apply  # after credit confirm
```

Est.: ~$35/mo base + egress + ~$2.5 WAF policy.

## Managed Redis Basic C0 (CREATE)

```bash
./infra/hardening/CREATE-redis.sh --apply
# Store primary key in kv-zevi-strlix; update ca-market-api REDIS_URL; then scale ca-redis to 0
```

Est.: ~$16/mo.

## Private Endpoints (CREATE selectively)

- **Yes:** Key Vault + Redis in eastus2 (same region as CAE).
- **No this sprint:** Postgres PE (server is **centralus** — fix region later).
- Cost: ~$7–20/mo each + DNS — see script header.

## Entra External ID (code shipped, default anon)

See `ENTRA-EXTERNAL-ID.md`. `STRLIX_AUTH_MODE=entra` validates RS256 access tokens and still serves `/v1/auth/anon`. Do not flip demos to entra.

## Free month

`STRLIX_BILLING_MODE=free_month` and `STRLIX_FREE_LAUNCH_MODE=true` are the launch defaults. Checklist: `demo/launch/LAUNCH-CHECKLIST.md`. Ops stubs: `infra/ops/`.

## Payments live-readiness (gated — code shipped)

Triple gate (all required):

1. `STRLIX_PAY_MODE=live`
2. `PAYMENTS_LIVE=true`
3. `STRLIX_ALLOW_LIVE_CHARGES=true`

Module: `services/market-api/market_api/payments.py`  
KV runbook: `PAYMENTS-KEYVAULT.md`  
Default remains TEST — no real live charges in this build until Ankit flips gates + KV secrets.
