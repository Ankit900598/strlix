# Soft-launch status snapshot — 2026-09-22 ~07:46 IST

**Operator:** box agent (not CloudAgent) · **RG lock:** `rg-zevi-cloudphone`  
**Billing posture:** Ankit first calendar month **FREE** (soft-launch); do not enable Stripe **live** charges.  
**CloudAgent note:** new launch docs live under `demo/launch/`. Prefer editing here over duplicating into `demo/credit-burn/` mid-flight to avoid merge fights; `REMAINING.md` was updated in credit-burn as the single remaining-work ledger.

## Health (verified this pass)

| Check | Result |
|-------|--------|
| AFD `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **200** · `ok:true` · `pay_mode=test` · `redis:true` · `redis_error:null` · market-api **0.6.0** · `billing_mode=free_month` · `free_month_active:true` · `live_charges_allowed:false` |
| Origin `ca-market-api…/health` | prior pass **200** · rev **`ca-market-api--0000004`** |
| Waitlist `POST /v1/waitlist` via AFD | prior pass **200** · `card_required:false` |
| Managed Redis `redis-strlix-amr` | **publicNetworkAccess=Enabled** (unchanged) — do not disable |
| Azure GPU VMs in RG | **None** — do not create |
| AWS GPU `i-0531c567f620877c3` / `strlix-gpu-worker-1` (`g4dn.xlarge`, us-east-1) | **stopped** (idle hygiene 2026-09-22) — start with `aws ec2 start-instances --instance-ids i-0531c567f620877c3 --region us-east-1` when needed |
| Stripe live | **OFF** · `STRLIX_PAY_MODE=test` · `billing_mode=free_month` |

## Applied this pass (2026-09-22 ~07:46 IST)

- **AWS GPU idle stop:** `i-0531c567f620877c3` → **stopped** (not terminated). Confirmed `State=stopped`.
- **WAF tighten:** fixed `TIGHTEN-WAF.sh` for current az (`--match-variable` / `--operator` / `--values`; no `--match-condition` JSON). Dry-run then `--apply` on `wafzevistrlix` / AFD `afd-zevi-strlix`. Rules: **RateLimitAuthAnon** (110), **RateLimitWaitlist** (120), **RateLimitAuthLogin** (130) — 100/min/IP, RequestUri Contains, `/health` not matched. Post-apply AFD `/health` **200**.
- **Private Redis NEXT:** reserved empty subnet **`cae-infra-subnet` `10.0.2.0/23`** on `vm-zevi-cloudphone-vnet` (eastus), delegated `Microsoft.App/environments`. CAE unchanged (`vnetConfiguration: null`, eastus2). Redis public access **still Enabled**. Script: `infra/hardening/PRIVATE-REDIS-NEXT.sh` (`CONFIRM=yes` gate).

## Docs this pass

- This file; `QUOTA-TICKETS.md` GPU stopped note; `PRIVATE-REDIS-PATH.md` next-step pointer; new `PRIVATE-REDIS-NEXT.sh`; fixed `TIGHTEN-WAF.sh`.

## Blockers

| Area | State |
|------|--------|
| Custom domain / branded URL | Still on `*.azurefd.net` |
| Azure GPU NCasT4 / NVadsA10 | **Still limit 0** in eastus2 — do not create GPU VM |
| Private Redis cutover | Region split CAE eastus2 vs VNet/Redis eastus — reserved `cae-infra-subnet` only; **no** public-access disable until eastus CAE Option B |
| Stripe live | **Deferred** — pay_mode stays `test` |

## Curl helpers

```bash
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
curl -sS -X POST https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
# Restart AWS GPU worker when needed:
aws ec2 start-instances --instance-ids i-0531c567f620877c3 --region us-east-1
```
