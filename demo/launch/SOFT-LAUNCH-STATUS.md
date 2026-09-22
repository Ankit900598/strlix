# Soft-launch status snapshot — 2026-09-22 ~09:55 IST

**Operator:** box agent (not CloudAgent) · **RG lock:** `rg-zevi-cloudphone`  
**Billing posture:** Ankit first calendar month **FREE** (soft-launch); do not enable Stripe **live** charges.  
**CloudAgent note:** new launch docs live under `demo/launch/`. Prefer editing here over duplicating into `demo/credit-burn/` mid-flight to avoid merge fights; `REMAINING.md` was updated in credit-burn as the single remaining-work ledger.


## Update 2026-09-22 ~09:55 IST — AWS Redroid in phone path

- SSM ADB port-forward from box → `127.0.0.1:5556` **proven** (`boot_completed=1`, product `redroid_x86_64_only`).
- Catalog id **`aws-redroid-t4-1`** in `web-market/devices.json` (free-month grant target); market-api **0.6.4** / `ca-market-api--0000010` redeployed (devices.json in image).
- Script: `scripts/adb-aws-redroid.sh`. Runbook: `GLOBAL-LAUNCH-TODAY.md` + `WORKER-LIVE.md`.
- SG ADB inbound still **closed** (SSM preferred). Stripe live still OFF. No Azure GPU create.

## Update 2026-09-22 ~09:42 IST

- Merged PR #2 legal rewrite onto main as **`05a8646`** (head `1c495a8` + conflict resolve + market-api **0.6.3**).
- Deployed **market-api 0.6.3** → revision **`ca-market-api--0000007`** (image `acrzevistrlix.azurecr.io/market-api:0.6.3`). Old `0000006` deactivated.
- AFD + origin `/market/legal/terms.html` **200** with banner: `Soft-launch terms — not a substitute for independent legal advice.`
- **Domain SKIPPED by Ankit** — stay on `*.azurefd.net`; do not buy domains / do not run ATTACH-CUSTOM-DOMAIN. zevilabs.dev DNS is human Name.com only.
- `pay_mode=test`, `billing_mode=free_month`, `free_month_active=true`, `live_charges_allowed=false` unchanged.

## Health (verified this pass)

| Check | Result |
|-------|--------|
| AFD `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **200** · `ok:true` · `pay_mode=test` · `redis:true` · market-api **0.6.4** · `billing_mode=free_month` · `free_month_active:true` · `live_charges_allowed:false` |
| AFD `/v1/devices` | includes **`aws-redroid-t4-1`** `available:true` `preview:live` |
| AFD `/market/legal/terms.html` | **200** · Soft-launch banner present |
| Origin `ca-market-api` `/health` | **200** · rev **`ca-market-api--0000010`** · Healthy / RunningAtMaxScale |
| Managed Redis `redis-strlix-amr` | **publicNetworkAccess=Enabled** (unchanged) — do not disable |
| Azure GPU VMs in RG | **None** — do not create |
| AWS GPU `i-0531c567f620877c3` / `strlix-gpu-worker-1` (`g4dn.xlarge`, us-east-1) | **RUNNING** · pub `44.204.83.61` · priv `172.31.82.79` · SSM Online · Redroid **UP** ADB via SSM `127.0.0.1:5556` boot=1 Android 12 · ≈ **$0.526/hr** — `infra/gpu-worker/aws/WORKER-LIVE.md` |
| Stripe live | **OFF** · `STRLIX_PAY_MODE=test` · `billing_mode=free_month` |
| Custom domain | **SKIPPED** — azurefd.net only |

## Applied this pass (2026-09-22 ~09:30–09:55 IST)

- **AWS Redroid phone path:** SSM forward proven; catalog `aws-redroid-t4-1`; market-api **0.6.4** / `ca-market-api--0000010`.
- **Legal deploy:** market-api **0.6.3** / `ca-market-api--0000007` earlier; PR #2 on main; AFD legal soft-launch banner smoked.
- **AWS GPU start:** `i-0531c567f620877c3` **stopped → running**. Redroid `strlix-redroid-1` **UP**. Runbook: `infra/gpu-worker/aws/WORKER-LIVE.md`.
- **Azure GPU:** still **limit 0** — **do not create**.
- **Stripe live:** still **OFF**.
- **Domain:** SKIPPED — stay on azurefd.net.

## Prior applied (2026-09-22 ~07:46 IST)

- **WAF tighten:** fixed `TIGHTEN-WAF.sh` for current az; `--apply` on `wafzevistrlix` / AFD `afd-zevi-strlix`. Rules: **RateLimitAuthAnon** (110), **RateLimitWaitlist** (120), **RateLimitAuthLogin** (130).
- **Private Redis NEXT:** reserved empty subnet **`cae-infra-subnet` `10.0.2.0/23`**. Redis public access **still Enabled**.

## Docs this pass

- This file; `GLOBAL-LAUNCH-TODAY.md`; `scripts/adb-aws-redroid.sh`; market-api 0.6.4 + devices.json; `CAPACITY-PHONE-POOL.md`; `WORKER-LIVE.md`. Domain SKIPPED in checklist / CUSTOM-DOMAIN / REMAINING.

## Blockers

| Area | State |
|------|--------|
| Custom domain / branded URL | **SKIPPED by Ankit** — stay on `*.azurefd.net` (do not buy; zevilabs.dev = human Name.com only) |
| Azure GPU NCasT4 / NVadsA10 | **Still limit 0** in eastus2 — do not create GPU VM |
| Private Redis cutover | Region split CAE eastus2 vs VNet/Redis eastus — reserved `cae-infra-subnet` only; **no** public-access disable until eastus CAE Option B |
| Stripe live | **Deferred** — pay_mode stays `test` |
| Physical phone / counsel | Still external |
| Broker multi-device | Phase-1 pool still seeds **one** env device — point at Redroid via env |

## Curl helpers

```bash
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/devices | jq '.devices[]|select(.id=="aws-redroid-t4-1")'
curl -sS -o /dev/null -w '%{http_code}\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html
curl -sS -X POST https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
./scripts/adb-aws-redroid.sh
# Idle stop (do not terminate):
# aws ec2 stop-instances --region us-east-1 --instance-ids i-0531c567f620877c3
```
