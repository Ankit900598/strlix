# Soft-launch status snapshot — 2026-09-22 ~09:30 IST

**Operator:** box agent (not CloudAgent) · **RG lock:** `rg-zevi-cloudphone`  
**Billing posture:** Ankit first calendar month **FREE** (soft-launch); do not enable Stripe **live** charges.  
**CloudAgent note:** new launch docs live under `demo/launch/`. Prefer editing here over duplicating into `demo/credit-burn/` mid-flight to avoid merge fights; `REMAINING.md` was updated in credit-burn as the single remaining-work ledger.


## Update 2026-09-22 ~09:12 IST

- Deployed **market-api 0.6.2** (`ca-market-api--0000006`) with `static/legal` in image; origin `/legal/*.html` **200**.
- AFD `route-market` patterns include `/legal/*`; `/health` **200**. Edge `/legal/*` still Azure-404s; use `/market/legal/*` (web-market/legal) until resolved. See CUSTOM-DOMAIN.md.
- Waitlist + grant smoked via AFD. Stripe live still OFF. AWS GPU still stopped.
## Health (verified this pass)

| Check | Result |
|-------|--------|
| AFD `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **200** · `ok:true` · `pay_mode=test` · `redis:true` · `redis_error:null` · market-api **0.6.2** · `billing_mode=free_month` · `free_month_active:true` · `live_charges_allowed:false` |
| Origin `ca-market-api…/health` | prior pass **200** · rev **`ca-market-api--0000006`** |
| Waitlist `POST /v1/waitlist` via AFD | prior pass **200** · `card_required:false` |
| Managed Redis `redis-strlix-amr` | **publicNetworkAccess=Enabled** (unchanged) — do not disable |
| Azure GPU VMs in RG | **None** — do not create |
| AWS GPU `i-0531c567f620877c3` / `strlix-gpu-worker-1` (`g4dn.xlarge`, us-east-1) | **RUNNING** · pub `44.204.83.61` · priv `172.31.82.79` · SSM Online · `nvidia-smi` green (T4 / 595.91.07 / CUDA 13.2) · Redroid **UP** ADB `127.0.0.1:5556` boot=1 Android 12 · ≈ **$0.526/hr** — `infra/gpu-worker/aws/WORKER-LIVE.md` |
| Stripe live | **OFF** · `STRLIX_PAY_MODE=test` · `billing_mode=free_month` |

## Applied this pass (2026-09-22 ~09:30 IST)

- **AWS GPU start (item 3 → AWS):** `i-0531c567f620877c3` **stopped → running**. SSM Online. `nvidia-smi` green (Tesla T4, driver 595.91.07, CUDA 13.2). Docker + nvidia runtime verified. Redroid container `strlix-redroid-1` **UP** (`guest` GPU mode; ADB `127.0.0.1:5556`, `boot_completed=1`, Android 12). Host `:5555` = nv-hostengine. Runbook: `infra/gpu-worker/aws/WORKER-LIVE.md`.
- **Azure GPU:** still **limit 0** — **do not create**.
- **Stripe live:** still **OFF**.

## Prior applied (2026-09-22 ~07:46 IST)


- **AWS GPU idle stop:** `i-0531c567f620877c3` → **stopped** (not terminated). Confirmed `State=stopped`.
- **WAF tighten:** fixed `TIGHTEN-WAF.sh` for current az (`--match-variable` / `--operator` / `--values`; no `--match-condition` JSON). Dry-run then `--apply` on `wafzevistrlix` / AFD `afd-zevi-strlix`. Rules: **RateLimitAuthAnon** (110), **RateLimitWaitlist** (120), **RateLimitAuthLogin** (130) — 100/min/IP, RequestUri Contains, `/health` not matched. Post-apply AFD `/health` **200**.
- **Private Redis NEXT:** reserved empty subnet **`cae-infra-subnet` `10.0.2.0/23`** on `vm-zevi-cloudphone-vnet` (eastus), delegated `Microsoft.App/environments`. CAE unchanged (`vnetConfiguration: null`, eastus2). Redis public access **still Enabled**. Script: `infra/hardening/PRIVATE-REDIS-NEXT.sh` (`CONFIRM=yes` gate).

## Docs this pass

- This file; `QUOTA-TICKETS.md` AWS GPU **RUNNING**; new `infra/gpu-worker/aws/WORKER-LIVE.md` (nvidia + Redroid next commands). Prior: `PRIVATE-REDIS-PATH.md` / `PRIVATE-REDIS-NEXT.sh`; `TIGHTEN-WAF.sh`.

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
# AWS GPU worker is RUNNING — health / session:
aws ssm send-command --region us-east-1 --instance-ids i-0531c567f620877c3 --document-name AWS-RunShellScript --parameters 'commands=["nvidia-smi"]'
# Idle stop (do not terminate):
# aws ec2 stop-instances --region us-east-1 --instance-ids i-0531c567f620877c3
```
