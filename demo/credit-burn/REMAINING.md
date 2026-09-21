# Remaining credit-burn work

Only these items remain:

1. **GPU wait** — monitor Azure Support **2609210040005251** and AWS Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K`; create no GPU VM until quota is approved.
2. **Private-endpoint subnet** — provide a correctly placed `pe-subnet` and reconcile the eastus/eastus2 network and Managed Redis target before applying PEs.
3. **Live Stripe keys (gated)** — provide live secrets through Key Vault only when ready; keep `pay_mode=test` and live-charge gates OFF.
4. **Real-device latency proof** — run the physical-device measurement needed to certify the sub-100 ms target; emulator results do not qualify.
