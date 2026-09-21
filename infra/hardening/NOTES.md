# Hardening + payments checklist (survives after credits)

**Updated:** 2026-09-21 ~19:45 IST · RG lock `rg-zevi-cloudphone` only · do not delete resources.

## Scripts / IaC in this folder

| Artifact | Purpose | Apply? |
|----------|---------|--------|
| `CREATE-afd-waf.sh` | Front Door Standard + WAF for market/android FQDNs | dry-run default; `--apply` Day 1 |
| `afd-waf.bicep` | Same as Bicep skeleton | after FQDN params |
| `CREATE-redis.sh` | Azure Cache for Redis Basic C0 | `--apply` Day 1; keep `ca-redis` until cutover |
| `CREATE-private-endpoints.sh` | PE stubs KV (+ Redis); Postgres SKIP | cost-documented |
| `ENTRA-EXTERNAL-ID.md` | Minimal Entra / CIAM path | portal-only |
| `PAYMENTS-KEYVAULT.md` | Flip Stripe keys via KV; triple live gate | code shipped; live OFF |

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

## Entra External ID (NOTES only)

See `ENTRA-EXTERNAL-ID.md`. Feature-flag auth later; keep anon preview for demos.

## Payments live-readiness (gated — code shipped)

Triple gate (all required):

1. `STRLIX_PAY_MODE=live`
2. `PAYMENTS_LIVE=true`
3. `STRLIX_ALLOW_LIVE_CHARGES=true`

Module: `services/market-api/market_api/payments.py`  
KV runbook: `PAYMENTS-KEYVAULT.md`  
Default remains TEST — no real live charges in this build until Ankit flips gates + KV secrets.
