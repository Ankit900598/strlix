# Soft-launch status snapshot — 2026-09-22 ~00:16 IST

**Operator:** box agent (not CloudAgent) · **RG lock:** `rg-zevi-cloudphone`  
**Billing posture:** Ankit first calendar month **FREE** (soft-launch); do not enable Stripe **live** charges.  
**CloudAgent note:** new launch docs live under `demo/launch/`. Prefer editing here over duplicating into `demo/credit-burn/` mid-flight to avoid merge fights; `REMAINING.md` was updated in credit-burn as the single remaining-work ledger.

## Health (verified this pass)

| Check | Result |
|-------|--------|
| AFD `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **200** · `ok:true` · `pay_mode=test` · `redis:true` · `redis_error:null` · market-api **0.6.0** · `billing_mode=free_month` · `free_month_active:true` · `live_charges_allowed:false` |
| Origin `ca-market-api…/health` | **200** · same payload · rev **`ca-market-api--0000004`** Healthy · traffic 100% |
| Waitlist `POST /v1/waitlist` via AFD | **200** · `{"status":"joined",…,"card_required":false}` (dry smoke email) |
| Origin `ca-android-api…/health` | unchanged this pass (not re-verified) |
| Managed Redis `redis-strlix-amr` | left alone (public Enabled) — do not disable |
| GPU VMs in RG | **None** (Azure) — only `vm-zevi-cloudphone` = `Standard_D4nls_v6` |
| Stripe live | **OFF** · `STRLIX_PAY_MODE=test` · code defaults `billing_mode=free_month` |

## Applied this pass

- **Postgres migration 006** on `psql-zevi-strlix` / db `strlix`: `market.waitlist` + `orders_plan_check` includes `free_month`; RLS insert policy + `GRANT INSERT` to `strlix_app`. Applied via Key Vault `database-url-admin` from the box (secrets not printed).
- **market-api image** `acrzevistrlix.azurecr.io/market-api:0.6.0` built from `/workspace/zevi-cloudphone` and pushed; `ca-market-api` revision **`ca-market-api--0000004`** (image + `STRLIX_PAY_MODE=test`, hardening mark `soft-launch-006-20260921T1842IST`).
- **WAF:** `TIGHTEN-WAF.sh --apply` **skipped / failed** — Azure CLI rejected `--match-condition` JSON on this az version. No custom WAF rules added; `/health` untouched. Script remains dry-run-safe for a later CLI-compatible fix.

## Docs this pass

- This file updated with migration + deploy + smoke results.

## Blockers

| Area | State |
|------|--------|
| Custom domain / branded URL | Still on `*.azurefd.net` — not configured this pass |
| WAF rate-limit rules | `TIGHTEN-WAF.sh` CLI syntax mismatch — no RateLimit* rules on `wafzevistrlix` yet |
| Azure GPU NCasT4 / NVadsA10 | **Still limit 0** in eastus2 — do not create GPU VM |
| Private Redis cutover | Region split CAE eastus2 vs VNet/Redis eastus — see `PRIVATE-REDIS-PATH.md` |
| Stripe live | **Deferred** — pay_mode stays `test` |

## Curl helpers

```bash
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
curl -sS -X POST https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
```
