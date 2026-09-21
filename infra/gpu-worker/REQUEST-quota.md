# GPU quota request (do this before any create)

**Subscription:** `a3dc5296-f948-427e-8656-c6bc52afee21` (Sponsored)  
**RG:** `rg-zevi-cloudphone`  
**Preferred region:** `eastus2` (CAE co-location)  
**Contact:** `ay186mnc@gmail.com`

## Ticket status (2026-09-21)

| Provider | Ticket / request | Scope | Status |
|----------|------------------|-------|--------|
| Azure Support | **2609210040005251** | `eastus2`: NCasT4v3 **0→8**, NVadsA10v5 **0→6** | **OPEN**; self-serve quota request rejected |
| AWS | Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K` | `us-east-1`: G/VT On-Demand **0→4** | Pending / open |

Spot/Low-priority capacity is still **0/3 usable** (regional limit remains 3 vCPUs); it is not enough for the preferred NC4as T4 worker. No GPU VM has been created.


## Portal path

Azure Portal → Subscriptions → Azure subscription 1 → **Usage + quotas** → search region **East US 2** → request increase:

| Quota name | Current | Request | Why |
|------------|---------|---------|-----|
| Standard NCASv3_T4 Family vCPUs | **0** | **8** | 1× NC4as_T4_v3 (4 vCPU) + headroom for resize to NC8 |
| Standard NVADSA10v5 Family vCPUs | **0** | **6** | Optional graphics path NV6ads_A10_v5 |
| Total Regional Low-priority vCPUs | **3** | **8** | Spot/LP needs ≥4 for NC4as |
| Total Regional vCPUs | 65 | (keep) | enough if GPU family unlocked |

## CLI (support request — adjust if your az extension differs)

```bash
# Inspect (already verified 2026-09-21):
az vm list-usage -l eastus2 -o table | rg -i 'NC|NV|priority|Regional'

# Open portal deep-link style reminder:
echo "https://portal.azure.com/#view/Microsoft_Azure_Support/NewSupportRequestV3Blade"
```

Sponsored subscriptions sometimes need Microsoft for Startups / quota form rather than self-serve — if portal rejects, use Support → Service and subscription limits (quotas).

## After approval

Run `CREATE-gpu-worker.sh` **manually** (script refuses to run unless `CONFIRM_GPU_CREATE=yes`).
