# GPU quota tickets

**Scope:** `rg-zevi-cloudphone` only · **Contact:** `ay186mnc@gmail.com`  
**Rule:** do not create a GPU VM until product explicitly asks — even if a quota shows >0.

| Provider | Ticket / request | Requested capacity | Region | Status |
|----------|------------------|--------------------|--------|--------|
| Azure Support | **2609210040005251** | NCasT4v3 **0→8**; NVadsA10v5 **0→6** | `eastus2` | **OPEN / unresolved via API**; self-serve rejected; **limits still 0** (verified 2026-09-21 ~23:38 IST) |
| AWS | Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K` | G/VT On-Demand **0→4** | `us-east-1` | **CASE_CLOSED**; quota **Value=4** (verified via `GetServiceQuota` L-DB2E81BA) |

Azure Spot/Low-priority remains unusable for NC4as T4 (regional LP still tiny). No GPU VM has been created in the RG (only `Standard_D4nls_v6`).
