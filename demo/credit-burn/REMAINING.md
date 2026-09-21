# Remaining work — soft-launch ledger

**Updated:** 2026-09-22 ~00:15 IST  
**Billing:** first month **FREE**. Keep `pay_mode=test` and live-charge gates OFF until after the free period.

Free-month path (flag, waitlist, no-card grant, legal pages, Entra-ready auth defaulting to anon) is in the repo. Split of done vs blocked vs deferred: `demo/launch/LAUNCH-CHECKLIST.md`.  
Ops notes: `../launch/OPS-ALERTS.md`, `../launch/PRIVATE-REDIS-PATH.md`, `../launch/SOFT-LAUNCH-STATUS.md`.

## Remaining list

1. **Azure GPU wait** — Support **2609210040005251**: eastus2 NCasT4 / NVadsA10 still **limit 0**. Do not create an Azure GPU VM until cleared.  
   - **AWS:** G/VT On-Demand quota **4**; worker **`strlix-gpu-worker-1`** (`i-0531c567f620877c3`, g4dn.xlarge) already created — stop when idle (~$0.526/hr).
2. **Custom domain + TLS on AFD** — still on `strlix-edge-….azurefd.net`. Runbook: `infra/hardening/ATTACH-CUSTOM-DOMAIN.sh` (needs Ankit DNS).
3. **Private Redis cutover (gated)** — PE on eastus `pe-subnet`; CAE eastus2 has no VNet. Keep AMR **public Enabled**. Script: `infra/hardening/PRIVATE-REDIS-PATH.sh` (`CONFIRM=yes`; no-ops without CAE VNet).
4. **Key Vault PE (optional)** — SKIP: KV eastus2 vs VNet eastus.
5. **Live Stripe — deferred** until after free month. Key Vault only when ready (`PAYMENTS-KEYVAULT.md`).
6. **Real-device latency proof** — physical phone required; emulator does not qualify.
7. **Domain DNS + Entra portal** — Ankit owns DNS/clicks; code defaults stay `anon` / placeholder DOMAIN.
8. **Postgres migration 006** — apply `services/market-api/migrations/006_free_month.sql` on `psql-zevi-strlix` before production waitlist.
9. **Action-group email** — confirm `ay186mnc@gmail.com` received Monitor confirm for `ag-strlix-ops` if needed.

## Done enough for soft-launch (do not redo)

- AFD + WAF healthy; market-api on Managed Redis (`redis:true`).
- Monitor alerts (`ag-strlix-ops`).
- Free-month / waitlist / legal / Entra-ready code merged.
- AWS g4dn.xlarge GPU worker provisioned (SSM-only).
