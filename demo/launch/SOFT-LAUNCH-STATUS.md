# Soft-launch status snapshot — 2026-09-21 ~23:46 IST

**Operator:** box agent (not CloudAgent) · **RG lock:** `rg-zevi-cloudphone`  
**Billing posture:** Ankit first calendar month **FREE** (soft-launch); do not enable Stripe **live** charges.  
**CloudAgent note:** new launch docs live under `demo/launch/`. Prefer editing here over duplicating into `demo/credit-burn/` mid-flight to avoid merge fights; `REMAINING.md` was updated in credit-burn as the single remaining-work ledger.

## Health (verified this pass)

| Check | Result |
|-------|--------|
| AFD `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **200** · `ok:true` · `pay_mode=test` · `redis:true` · `redis_error:null` · market-api 0.3.0 |
| Origin `ca-market-api…/health` | **200** · same payload · rev `ca-market-api--0000003` Healthy |
| Origin `ca-android-api…/health` | **200** |
| Managed Redis `redis-strlix-amr` | **Running** / Succeeded · SKU Balanced_B0 · eastus · public Enabled |
| GPU VMs in RG | **None** (Azure) — only `vm-zevi-cloudphone` = `Standard_D4nls_v6` (running) |
| AWS GPU worker | **`i-0531c567f620877c3`** `g4dn.xlarge` **running** us-east-1b · pub `44.201.216.57` · priv `172.31.82.79` · ≈$0.526/hr |

## Applied this pass

- Azure: action group `ag-strlix-ops` + 4 alerts (see `OPS-ALERTS.md`) — unchanged this GPU pass.
- AWS: created **one** `g4dn.xlarge` `strlix-gpu-worker-1` (`i-0531c567f620877c3`) + SSM IAM + SG (no public inbound). Runbook: `infra/gpu-worker/aws/CREATE-aws-gpu-worker.md`.

## Docs this pass

- `infra/gpu-worker/aws/CREATE-aws-gpu-worker.md` + `CREATE-aws-gpu-worker.sh`
- Quota/status: `QUOTA-TICKETS.md`, `REQUEST-quota.md`, this file.

## Blockers

| Area | State |
|------|--------|
| Custom domain / branded URL | Still on `*.azurefd.net` — not configured this pass |
| Entra / portal | No block for Monitor alerts (CLI OK) |
| Azure GPU NCasT4 / NVadsA10 | **Still limit 0** in eastus2 — Support **2609210040005251**; do not create GPU VM |
| AWS G/VT On-Demand | Quota **4** (case **179000526000600** **CASE_CLOSED**); **worker created** `i-0531c567f620877c3` — see `infra/gpu-worker/aws/CREATE-aws-gpu-worker.md` |
| Private Redis cutover | Region split CAE eastus2 vs VNet/Redis eastus — see `PRIVATE-REDIS-PATH.md` |
| Stripe live | **Deferred** — pay_mode stays `test` |
