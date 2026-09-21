# GPU quota request (do this before any create)

**Subscription:** `a3dc5296-f948-427e-8656-c6bc52afee21` (Sponsored)  
**RG:** `rg-zevi-cloudphone`  
**Preferred region:** `eastus2` (CAE co-location)

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
