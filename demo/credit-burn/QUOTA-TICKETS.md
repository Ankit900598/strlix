# GPU quota tickets

**Scope:** `rg-zevi-cloudphone` (Azure) + AWS account `787235610343` · **Contact:** `ay186mnc@gmail.com`  
**Rule (updated soft-launch):** Azure GPU still **do not create** (limit 0). AWS: product asked to finish launch — **one** On-Demand G worker created after quota **4**.

| Provider | Ticket / request | Requested capacity | Region | Status |
|----------|------------------|--------------------|--------|--------|
| Azure Support | **2609210040005251** | NCasT4v3 **0→8**; NVadsA10v5 **0→6** | `eastus2` | **OPEN / unresolved via API** (Developer plan; API readable); latest Microsoft text (2026-09-21 22:20 IST): “We’re reviewing your request and we’ll reach out to you within the next two business days for the next steps.”; self-serve rejected; **limits still 0** (verified 2026-09-22 09:09 IST) — **do not create Azure GPU** |
| AWS | Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K` | G/VT On-Demand **0→4** | `us-east-1` | **CASE_CLOSED**; quota **Value=4** (L-DB2E81BA). Worker **`i-0531c567f620877c3`** `g4dn.xlarge` **`strlix-gpu-worker-1`** → **RUNNING** (started 2026-09-22 ~09:27 IST; SSM Online; `nvidia-smi` green T4 / driver 595.91.07 / CUDA 13.2). Public IP `44.204.83.61` · private `172.31.82.79`. Wired as GPU capacity + Redroid UP (`127.0.0.1:5556`) — see `infra/gpu-worker/aws/WORKER-LIVE.md`. ≈ **$0.526/hr**. Do **not** terminate. Azure GPU still **0** — do not create. |

Azure Spot/Low-priority remains unusable for NC4as T4. No Azure GPU VM in the RG (only `Standard_D4nls_v6`).
