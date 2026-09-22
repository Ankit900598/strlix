# Soft-launch status snapshot — 2026-09-22 ~10:37 IST

**Operator:** box agent (not CloudAgent) · **RG lock:** `rg-zevi-cloudphone`  
**Billing posture:** Ankit first calendar month **FREE** (soft-launch); do not enable Stripe **live** charges.  
**CloudAgent note:** new launch docs live under `demo/launch/`. Prefer editing here over duplicating into `demo/credit-burn/` mid-flight to avoid merge fights; `REMAINING.md` was updated in credit-burn as the single remaining-work ledger.


## Update 2026-09-22 ~10:37 IST — soft-launch smoke + Redroid grant FK

- Public AFD smoke: `/health` 200 (market-api **0.6.4**, `billing_mode=free_month`, `pay_mode=test`, `redis:true`, `live_charges_allowed:false`), `/market/` 200, `/market/legal/{terms,privacy,support,capabilities}.html` 200 (banner present), `/v1/devices` includes **`aws-redroid-t4-1`** available.
- `POST /v1/waitlist` 200 (`example.com` smoke email). `POST /v1/access/grant` for `pixel-7a-a14` 200; **`aws-redroid-t4-1` was 500** (`orders_device_id_fkey` — missing `devices_catalog` row).
- **Fixed live:** upserted `aws-redroid-t4-1` into `market.devices_catalog` on `psql-zevi-strlix`; grant now **200** `granted_free`. Migration `007_seed_aws_redroid_catalog.sql` + `scripts/sync-devices-catalog.sh` committed for operators.
- ADB SSM smoke: `127.0.0.1:5556 device product:redroid_x86_64_only`, `boot_completed=1`; session terminated (no orphan). AWS `i-0531c567f620877c3` still **RUNNING** ≈$0.526/hr — **stop when idle**.
- Stream glue tip: **`a9619b5`**. Domain: Name.com Cloudflare Turnstile still blocks DNS apply for `app.zevilabs.dev` (AFD custom domain Pending; validation token `_48ncbg9vt1u4zxek55jon1osqixlr88` expires ~2026-09-29). Soft launch stays on `*.azurefd.net`.

## Update 2026-09-22 ~10:30 IST — Phase-1 Redroid stream glue

- `DevicePool` labels/kind/region env-driven (`STRLIX_PILOT_DEVICE_ID` + `ADB_SERIAL`; optional `STRLIX_PILOT_KIND` / `STRLIX_STREAM_ADB`).
- `scripts/run-pilot.sh` selects Azure tunnel vs `adb-aws-redroid.sh` from those env vars (Azure remains default).
- Stream-host runbook: `demo/launch/GLOBAL-LAUNCH-TODAY.md` + `infra/ops/CAPACITY-PHONE-POOL.md`.
- Catalog smoke: `scripts/smoke-catalog-redroid.sh`.
- Multi-lease Azure+AWS still **single-env Phase-1** (no dual broker seats).

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

## Health (verified this pass — 2026-09-22 ~10:37 IST)

| Check | Result |
|-------|--------|
| AFD `https://strlix-edge-fwf6grbbbggxbs.z03.azurefd.net/health` | **200** · `ok:true` · `pay_mode=test` · `redis:true` · market-api **0.6.4** · `billing_mode=free_month` · `free_month_active:true` · `live_charges_allowed:false` |
| AFD `/market/` | **200** |
| AFD `/v1/devices` | includes **`aws-redroid-t4-1`** `available:true` `preview:live` `kind:redroid` |
| AFD `/market/legal/*.html` | **200** · Soft-launch banner present (directory `/market/legal/` alone is 404 — use `terms.html` etc.) |
| AFD `POST /v1/waitlist` | **200** joined (card_required=false) |
| AFD `POST /v1/access/grant` `aws-redroid-t4-1` | **200** `granted_free` (after catalog FK seed) |
| Origin `ca-market-api` | rev **`ca-market-api--0000010`** · image 0.6.4 |
| Managed Redis `redis-strlix-amr` | **publicNetworkAccess=Enabled** — do not disable |
| Azure GPU VMs in RG | **None** — do not create |
| AWS GPU `i-0531c567f620877c3` / `strlix-gpu-worker-1` (`g4dn.xlarge`, us-east-1) | **RUNNING** · pub `44.204.83.61` · SSM Online · Redroid **UP** ADB `127.0.0.1:5556` boot=1 · ≈ **$0.526/hr** — **stop when idle** (do not terminate) |
| Stream glue | tip **`a9619b5`** |
| Stripe live | **OFF** · `pay_mode=test` · `billing_mode=free_month` |
| Custom domain | AFD Pending / Name.com Turnstile — soft launch on `*.azurefd.net` |

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

## Blockers (true external only)

| Area | State |
|------|--------|
| Custom domain `app.zevilabs.dev` | Name.com **Cloudflare Turnstile** blocks DNS apply; AFD custom domain **Pending**; validation token `_48ncbg9vt1u4zxek55jon1osqixlr88` expires ~**2026-09-29**. Soft launch stays on `*.azurefd.net` (do not buy domains / do not run ATTACH-CUSTOM-DOMAIN). |
| Physical USB phone | External — latency proof not certified |
| Azure GPU NCasT4 / NVadsA10 | **limit 0** eastus2 (ticket 2609210040005251) — do not create GPU VM |
| Lawyer / counsel pass | Soft-launch legal is operator draft only |
| Live Stripe | **Deferred** — `pay_mode=test` |
| Private Redis | CAE eastus2 vs VNet/Redis eastus mismatch — subnet reserved only; public Redis stays Enabled |
| AWS idle cost | `i-0531c567f620877c3` **RUNNING** ≈$0.526/hr — stop when idle (do not terminate) |

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
