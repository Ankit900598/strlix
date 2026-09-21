# Day-1 Hardening Applied — Strlix / Zevi Cloud Phone

**When:** 2026-09-21 ~20:05 IST  
**Subscription:** `a3dc5296-f948-427e-8656-c6bc52afee21`  
**RG lock:** `rg-zevi-cloudphone` ONLY (no other RGs touched)  
**Constraints honored:** no deletes · no GPU · Stripe live OFF (pay_mode remains `test`)

---

## 1) Azure Managed Redis (replaces retired Basic C0)

### Why not `az redis` Basic C0?

`az redis create ... --sku Basic --vm-size c0` is **blocked** by Azure:

> Azure Cache for Redis is retiring, create Azure Managed Redis instance instead.

Closest low-cost replacement: **Azure Managed Redis `Balanced_B0`** via `az redisenterprise`.

### Applied instance

| Field | Value |
|-------|-------|
| Name | `redis-strlix-amr` |
| SKU | `Balanced_B0` |
| Location | **eastus** (eastus2 B0 returned `InsufficientCapacity`) |
| Host | `redis-strlix-amr.eastus.redis.azure.net` |
| Port | `10000` (TLS / Encrypted client protocol) |
| Clustering | `NoCluster` |
| Access keys | Enabled |
| Public network access | Enabled |
| Provisioning | Succeeded / Running |
| Est. cost | ~$0.016/hr ≈ **~$12/mo** (eastus B0 Cache Instance) |

### Key Vault

| Secret | Vault | Status |
|--------|-------|--------|
| `redis-primary-key` | `kv-zevi-strlix` | Set 2026-09-21 20:01 IST (updated `2026-09-21T14:31:59Z`) |

### rediss URL (document — do not paste key in git)

```
rediss://:<PRIMARY_KEY>@redis-strlix-amr.eastus.redis.azure.net:10000/0
```

Retrieve key:

```bash
az keyvault secret show --vault-name kv-zevi-strlix -n redis-primary-key --query value -o tsv
```

### Cutover status — **NOT done**

- `ca-redis` Container App still **Running** (minReplicas=1). Kept intentionally.
- `ca-market-api` still on sidecar Redis (`/health` → `"redis":true` via ca-redis).
- **Do not** point `STRLIX_REDIS_URL` at Managed Redis until a documented smoke passes:
  1. Set env from KV secret + host/port above
  2. `GET /health` → `redis:true`, no `redis_error`
  3. Then scale `ca-redis` minReplicas→0 (still do not delete)

### Leftover stub (not deleted)

| Name | State | Notes |
|------|-------|-------|
| `redis-zevi-strlix` | CreateFailed (eastus2 B0 capacity) | Left in place — **do not delete** without explicit approval |
| `redis-zevi-strlix-probe` | Was Deleting after capacity probe | Transient probe name; not used |

Script updated: `infra/hardening/CREATE-redis.sh` → Managed Redis recipe (`Balanced_B0`, `--public-network-access Enabled`, default name `redis-strlix-amr` / `eastus`).

---

## 2) Azure Front Door Standard + WAF

| Resource | Name | Status |
|----------|------|--------|
| Profile | `afd-zevi-strlix` (Standard_AzureFrontDoor) | Succeeded / Active |
| Endpoint | `strlix-edge` | Succeeded / Enabled |
| **Endpoint hostname** | **`strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net`** | Live DNS name |
| WAF policy | `wafzevistrlix` (Prevention) | Succeeded |
| Security policy | `sp-waf` (WAF → endpoint) | Succeeded (after CLI JSON fix) |

### Origins

| Origin group | Origin | Host |
|--------------|--------|------|
| `og-market-api` | `origin-market-api` | `ca-market-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io` |
| `og-android-api` | `origin-android-api` | `ca-android-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io` |

Health probes: HTTPS `GET /health` every 60s.

### Routes

| Route | Patterns | Origin group |
|-------|----------|--------------|
| `route-market` | `/v1/*`, `/market/*`, `/health`, `/ready` | `og-market-api` |
| `route-android` | `/android/*`, `/agent/*` | `og-android-api` |

Protocols: Http+Https, https-redirect Enabled, forwarding HttpsOnly, link-to-default-domain Enabled.

### CLI fixes applied in `CREATE-afd-waf.sh`

1. `--patterns-to-match` / `--supported-protocols` → JSON array shorthand.
2. Security-policy: modern CLI needs `--web-application-firewall @file.json` with nested `{"wafPolicy":{"id":...},"associations":[...]}` (not `--domains` / `--waf-policy`).
3. Soft-fail retained if association still fails; Day-1 association **succeeded** on retry.

### Smoke notes (2026-09-21 ~20:05 IST)

| Check | Result |
|-------|--------|
| Origin market `/health` | **200** `ok:true` (pay_mode=test, redis via ca-redis) |
| Origin android `/health` | **200** |
| AFD `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **404** Azure default page — route `deploymentStatus` still `NotStarted` (propagation lag; endpoint hostname is live) |

Re-check later:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
az afd route show -g rg-zevi-cloudphone --profile-name afd-zevi-strlix \
  --endpoint-name strlix-edge -n route-market --query deploymentStatus -o tsv
```

Est. cost: ~$35/mo AFD Standard base + egress + ~$2.5 WAF policy.

---

## 3) Explicitly NOT done

- No GPU resources created  
- Stripe live gates remain OFF (`pay_mode=test`)  
- No private endpoints applied this run  
- No deletes in any RG  
- No market-api Redis cutover  

---

## Success checklist

- [x] Managed Redis low-cost SKU in `rg-zevi-cloudphone` (B0 eastus; Basic C0 unavailable)  
- [x] Primary key in `kv-zevi-strlix` / `redis-primary-key`  
- [x] rediss URL documented  
- [x] `ca-redis` kept running  
- [x] AFD profile + endpoint + origins + routes  
- [x] WAF policy + security-policy association  
- [x] AFD endpoint hostname reported  
- [ ] AFD `/health` 200 (pending Front Door route deployment propagation)  
