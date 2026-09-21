# Remaining work after the free-month decision

**Product decision (locked):** the first month is free for everyone. Do not enable live Stripe. Keep `pay_mode=test` and the live-charge gates off (`PAYMENTS_LIVE`, `STRLIX_ALLOW_LIVE_CHARGES`). Payments are deferred until after the free period.

The free-month path (flag, waitlist, no-card grant, legal pages, Entra-ready auth defaulting to anon) is in the repo. The full split of what is done vs blocked vs deferred is `demo/launch/LAUNCH-CHECKLIST.md`.

Still outside this repo, or unsafe to flip from here:

1. **GPU wait** — monitor Azure Support **2609210040005251** and AWS Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K`. Create no GPU VM until quota is approved.
2. **Key Vault PE (optional / later)** — SKIP for now: `kv-zevi-strlix` is eastus2 vs VNet eastus. Revisit only with CAE VNet integration or same-region KV. Do not add an eastus2 VNet just to spend the credit.
3. **Disable Redis public access (gated)** — only after market-api can reach `pe-redis-strlix-amr` privately. `cae-zevi-strlix` has no VNet today; do not recreate it to force this. Public access stays **Enabled**. Script: `infra/hardening/PRIVATE-REDIS-PATH.sh` (`CONFIRM=yes` required, and it no-ops without a CAE VNet).
4. **Live Stripe — deferred until after the free month.** Do not load live keys and do not set the three live gates. Test-mode checkout may stay deployed; it is not required for a session or a phone grant. When the free month ends, use Key Vault only (`infra/hardening/PAYMENTS-KEYVAULT.md`).
5. **Real-device latency proof** — a physical phone is required to certify sub-100 ms. The current pool is one emulator. Emulator results do not qualify.
6. **Domain DNS and Entra portal** — Ankit has to own the DNS and click through Entra. Code and runbooks are ready; flags stay at the safe defaults (`anon`, placeholder `DOMAIN`).
7. **Postgres migration 006** — apply `services/market-api/migrations/006_free_month.sql` on `psql-zevi-strlix` before the production waitlist is used.
