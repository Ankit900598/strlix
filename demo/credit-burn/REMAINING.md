# Remaining work — soft-launch ledger

**Updated:** 2026-09-21 ~23:40 IST  
**Billing:** Ankit **first month FREE** (soft-launch). Keep burn low; Stripe **live deferred** (`pay_mode=test`, no live charge gates).

Launch ops notes (alerts / private Redis path): `../launch/OPS-ALERTS.md`, `../launch/PRIVATE-REDIS-PATH.md`, `../launch/SOFT-LAUNCH-STATUS.md`.

## Remaining list

1. **GPU wait (Azure still 0)** — Support **2609210040005251**: eastus2 NCasT4v3 / NVadsA10v5 still **limit 0**. **Do not create** a GPU VM.  
   - AWS G/VT On-Demand quota is **4** (case **179000526000600** / `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K` CASE_CLOSED) — capacity available on paper; still no auto-provision until explicitly requested.
2. **Custom domain + TLS on AFD** — still on `strlix-edge-….azurefd.net`; brand domain not attached.
3. **Private Redis cutover (gated)** — PE exists on eastus `pe-subnet`; CAE is eastus2 without VNet. Keep AMR **public Enabled** until CAE↔PE path proven (`../launch/PRIVATE-REDIS-PATH.md`). Do **not** disable public access yet.
4. **Key Vault PE (optional / later)** — SKIP: `kv-zevi-strlix` eastus2 vs VNet eastus; revisit with CAE VNet work only if needed.
5. **Live Stripe keys (gated / deferred)** — Key Vault only when ready; keep live-charge gates OFF for free-first-month.
6. **Real-device latency proof** — physical-device measurement for sub-100 ms; emulator does not qualify.
7. **Action-group email confirm** — confirm `ay186mnc@gmail.com` received Azure Monitor “confirm” for `ag-strlix-ops` if not already.

## Done enough for soft-launch (do not redo)

- AFD + WAF edge healthy; market-api on Managed Redis (`redis:true`).
- Cheap Monitor alerts applied (`ag-strlix-ops` + AFD origin / 5xx / CA restarts / Redis resource health).
- No accidental GPU VMs in RG.
