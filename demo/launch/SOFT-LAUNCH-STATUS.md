# Soft-launch status snapshot — 2026-09-21 ~23:40 IST

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
| GPU VMs in RG | **None** — only `vm-zevi-cloudphone` = `Standard_D4nls_v6` (running) |

## Applied in Azure this pass

- Action group `ag-strlix-ops` + 4 alerts (see `OPS-ALERTS.md`).

## Docs-only this pass

- `OPS-ALERTS.md`, `PRIVATE-REDIS-PATH.md`, this file.
- `demo/credit-burn/REMAINING.md` refresh (free-first-month + remaining list).

## Blockers

| Area | State |
|------|--------|
| Custom domain / branded URL | Still on `*.azurefd.net` — not configured this pass |
| Entra / portal | No block for Monitor alerts (CLI OK) |
| Azure GPU NCasT4 / NVadsA10 | **Still limit 0** in eastus2 — Support **2609210040005251**; do not create GPU VM |
| AWS G/VT On-Demand | Quota **now 4** (case **179000526000600** / req `ab584e62…` **CASE_CLOSED**); still **do not create** GPU worker until product asks |
| Private Redis cutover | Region split CAE eastus2 vs VNet/Redis eastus — see `PRIVATE-REDIS-PATH.md` |
| Stripe live | **Deferred** — pay_mode stays `test` |
