# Status — 2026-09-21 ~21:15 IST

**RG:** `rg-zevi-cloudphone` only · Stripe live OFF · No GPU VMs

| Item | State |
|------|--------|
| Managed Redis `redis-strlix-amr` (B0 eastus) | Running; KV `redis-primary-key` set |
| **market-api Redis cutover** | **DONE** → `rediss://…@redis-strlix-amr.eastus.redis.azure.net:10000/0`; rev `ca-market-api--0000003`; `/health` redis:true |
| `ca-redis` | minReplicas=**0** (not deleted); may idle-scale later |
| AFD `strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **200** |
| Private endpoints | **SKIPPED** — no `pe-subnet`; VNet eastus vs KV eastus2; script Redis stub wrong |
| Azure GPU quota NCASv3_T4 / NVADSA10v5 → 8 | API fail (`e5f1e109…`, `f8d83db5…`); Support API blocked (Developer plan) → **portal** |
| AWS G/VT On-Demand → 4 us-east-1 | Request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K` · Case **179000526000600** · CASE_OPENED |

Details: `HARDENING-APPLIED.md`.
