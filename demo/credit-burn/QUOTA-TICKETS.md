# GPU quota tickets

**Scope:** `rg-zevi-cloudphone` only · **Contact:** `ay186mnc@gmail.com`  
**Rule:** wait for quota approval; do not create a GPU VM while limits remain unavailable.

| Provider | Ticket / request | Requested capacity | Region | Status |
|----------|------------------|--------------------|--------|--------|
| Azure Support | **2609210040005251** | NCasT4v3 **0→8**; NVadsA10v5 **0→6** | `eastus2` | **OPEN**; self-serve rejected |
| AWS | Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K` | G/VT On-Demand **0→4** | `us-east-1` | Pending / open |

Azure Spot/Low-priority remains **0/3 usable**: the regional limit is still 3 vCPUs, so it cannot satisfy the NC4as T4 worker requirement. No GPU VM has been created.
