# Remaining credit-burn work

Only these items remain:

1. **GPU wait** — monitor Azure Support **2609210040005251** and AWS Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K`; create no GPU VM until quota is approved.
2. **Key Vault PE (optional / later)** — SKIP for now: `kv-zevi-strlix` is eastus2 vs VNet eastus. Revisit only with CAE VNet integration or same-region KV; avoid a new eastus2 VNet if it pushes >$15/mo complexity.
3. **Disable Redis public access (gated)** — only after market-api can reach `pe-redis-strlix-amr` privately (CAE↔eastus VNet path). Today public access stays **Enabled**.
4. **Live Stripe keys (gated)** — provide live secrets through Key Vault only when ready; keep `pay_mode=test` and live-charge gates OFF.
5. **Real-device latency proof** — run the physical-device measurement needed to certify the sub-100 ms target; emulator results do not qualify.
