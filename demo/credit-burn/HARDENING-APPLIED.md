# Day-1 Hardening Applied — Strlix / Zevi Cloud Phone

**When:** 2026-09-21 ~22:00 IST (Redis PE pass; prior cutover ~21:15 IST; AFD/Redis create ~20:05 IST)  
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

### Cutover status — **DONE** (2026-09-21 ~21:15 IST)

1. Built `rediss://:<KV redis-primary-key>@redis-strlix-amr.eastus.redis.azure.net:10000/0` (host/port confirmed via `az redisenterprise`).
2. Updated `ca-market-api` secrets `redis-url` + `redis-password` (password aligned to AMR primary so `STRLIX_REDIS_PASSWORD` kwargs do not override URL auth with the old sidecar password).
3. Forced revision **`ca-market-api--0000003`** (`STRLIX_HARDENING_MARK=amr-cutover-20260921T2130IST`). Secret host verified: `redis-strlix-amr.eastus.redis.azure.net`.
4. Smoke: origin + AFD `/health` → **200** `redis:true`, `redis_error:null`, `pay_mode=test`. AMR reachable (box `PING` ok; connected_clients ≥1).
5. Scaled **`ca-redis` minReplicas→0** (max=1). Resource **not deleted**. App may still show Running until idle scale-to-zero settles.
6. Note: the live `ca-market-api` still has unused `redis-sidecar` container (127.0.0.1); traffic uses Managed Redis. The checked-in ACA template now omits the sidecar; no live revision was changed by this cleanup.
7. Rollback (if needed): restore prior secrets `redis-url=redis://127.0.0.1:6379/0` + prior `redis-password`, then `az containerapp update` to new revision.

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
| AFD `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | **200** (rechecked 2026-09-21 ~21:15 IST; was 404 during initial propagation) |

Re-check later:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
az afd route show -g rg-zevi-cloudphone --profile-name afd-zevi-strlix \
  --endpoint-name strlix-edge -n route-market --query deploymentStatus -o tsv
```

Est. cost: ~$35/mo AFD Standard base + egress + ~$2.5 WAF policy.

---

## 3) Private endpoints — **Redis PE APPLIED** (2026-09-21 ~22:00 IST)

### Applied — Azure Managed Redis PE (eastus)

| Resource | Value |
|----------|-------|
| Subnet | `pe-subnet` = **10.0.1.0/27** on `vm-zevi-cloudphone-vnet` (eastus); `privateEndpointNetworkPolicies=Disabled` |
| Private endpoint | `pe-redis-strlix-amr` (eastus) — **Succeeded / Approved** |
| Target | `redis-strlix-amr` (`Microsoft.Cache/redisEnterprise`) |
| group-id | `redisEnterprise` (not classic `redisCache`) |
| Private IP | `10.0.1.4` → `redis-strlix-amr.eastus.redis.azure.net` |
| Private DNS | zone `privatelink.redis.azure.net` + VNet link + dns-zone-group `redis-amr-zone-group` |
| A record | `redis-strlix-amr.eastus.privatelink.redis.azure.net` → 10.0.1.4 |
| Redis `publicNetworkAccess` | **Enabled** (left on — market-api / CAE eastus2 still needs public path) |
| Est. cost | ~**$7–8/mo** PE + pennies DNS (no extra VNet) |

Smoke after PE: origin `/health` → `redis:true`; AFD `/health` → **200**. Public Redis path unbroken.

CLI recipe (also in `infra/hardening/CREATE-private-endpoints.sh`):

```bash
az network vnet subnet create -g rg-zevi-cloudphone --vnet-name vm-zevi-cloudphone-vnet \
  -n pe-subnet --address-prefixes 10.0.1.0/27 --private-endpoint-network-policies Disabled
REDIS_ID=$(az redisenterprise show -g rg-zevi-cloudphone -n redis-strlix-amr --query id -o tsv)
az network private-endpoint create -g rg-zevi-cloudphone -n pe-redis-strlix-amr -l eastus \
  --vnet-name vm-zevi-cloudphone-vnet --subnet pe-subnet \
  --private-connection-resource-id "$REDIS_ID" \
  --group-id redisEnterprise --connection-name pe-conn-redis-amr
# DNS: privatelink.redis.azure.net + link + dns-zone-group
```

### SKIP — Key Vault PE (eastus2)

| Check | Decision |
|-------|----------|
| KV region | `kv-zevi-strlix` is **eastus2**; VNet is **eastus** |
| Cross-region PE | Painful / not useful without same-region VNet or peering |
| Extra eastus2 VNet + pe-subnet + PE | Complexity + ~$7–8 PE (+ VNet plumbing) → typically **>$15/mo** vs benefit today |
| **Decision** | **SKIP** — document only; revisit when CAE has VNet integration or KV moves eastus |

### SKIP — Postgres PE

`psql-zevi-strlix` is **centralus** — unchanged SKIP.

## 4) GPU quota requests (no VMs created — limit still 0)

### Azure eastus2

| Attempt | Result | ID |
|---------|--------|-----|
| `az quota update` Standard NCASv3_T4 → 8 | **Failed** `QuotaNotAvailableForResource` | `e5f1e109-cd66-43eb-9f20-2a44385f9f10` (2026-09-21 15:39:25Z / ~21:09 IST) |
| `az quota update` StandardNVADSA10v5 → 6 | **Failed** `ContactSupport` | `f8d83db5-c9e3-4817-ae47-38f3f6366577` (2026-09-21 15:40:59Z / ~21:11 IST) |
| `az support in-subscription tickets create` (Compute-VM cores) | **Blocked** `InvalidSupportPlan` (subscription is **Developer** — Support API needs higher plan) | n/a |

**Portal follow-up:** Azure Portal → Help + support → Quota increase → Compute-VM (cores) → eastus2 → NCASv3_T4 → 8 / NVADSA10v5 → 6. Do **not** create GPU VM until `az vm list-usage -l eastus2` shows limit > 0.

**Current Support ticket:** **2609210040005251 — OPEN** (self-serve rejected). Spot/LP remains **0/3 usable**. Contact: `ay186mnc@gmail.com`.

### AWS us-east-1

| Attempt | Result | IDs |
|---------|--------|-----|
| `aws service-quotas request-service-quota-increase` EC2 `L-DB2E81BA` (Running On-Demand G and VT) 0→4 | **CASE_OPENED** / PENDING | Request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K` · Case `179000526000600` |

## 5) Explicitly NOT done / still gated

- No GPU resources created (Azure N* limit still **0**; AWS G/VT request pending)  
- Stripe live gates remain OFF (`pay_mode=test`)  
- Redis Managed Redis PE applied (public access still Enabled); KV PE skipped (cross-region)  
- No deletes in any RG  

---

## Success checklist

- [x] Managed Redis low-cost SKU in `rg-zevi-cloudphone` (B0 eastus; Basic C0 unavailable)  
- [x] Primary key in `kv-zevi-strlix` / `redis-primary-key`  
- [x] rediss URL documented  
- [x] `ca-redis` scaled to minReplicas=0 after cutover (not deleted)  
- [x] market-api Redis cutover to Managed Redis + smoke OK  
- [x] AFD profile + endpoint + origins + routes  
- [x] WAF policy + security-policy association  
- [x] AFD endpoint hostname reported  
- [x] AFD `/health` 200  
- [x] Azure + AWS GPU quota requests attempted (Azure portal follow-up needed)  
- [x] Redis PE (`pe-redis-strlix-amr` + `pe-subnet` 10.0.1.0/27); public access kept Enabled  
- [ ] Key Vault PE (SKIP — eastus2 cross-region; avoid >$15/mo extra VNet)  
