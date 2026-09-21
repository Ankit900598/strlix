# Strlix Azure Backend — Billion-User Security & Privacy Foundation

**Updated:** 2026-09-21 14:36 IST  
**Subscription:** `a3dc5296-f948-427e-8656-c6bc52afee21`  
**Resource group (ONLY):** `rg-zevi-cloudphone`  
**Identity:** `ay186mnc@gmail.com`  
**Hard rule:** Never touch other RGs / `phonecodex-*`. Spend Microsoft for Startups credits carefully.

---

## Honest capacity vs architecture

| Layer | Today (foundation SKUs) | Path toward ~1B users |
|-------|-------------------------|------------------------|
| **Per-user data isolation** | Postgres RLS via `app.user_id` | Same policy model; shard/partition by `user_id`; regional PG fleets |
| **Auth sessions** | JWT access 15m + refresh 7d; key `sess:{user_id}:{jti}` | Managed Redis Cluster; Entra External ID; key rotation |
| **market-api** | ACA 0.25 vCPU / 0.5 Gi, min 0 | Split android-api / desktop-api / market-api / session-broker; Front Door+WAF; multi-region CAE |
| **Device pool** | 1 emulator VM | Regional fleets; broker routes lease → region |
| **Chat QPS** | Shared Azure OpenAI | PTU / regional AOAI; per-user Redis rate limits |
| **Viewer streams** | ~12 watch / 1 control per device | Grows only with device count — not with bigger API SKUs |

> **These SKUs are a production-grade security foundation, not a billion-user invoice.**  
> The design (RLS, Key Vault, managed identity, short JWT, audit, privacy APIs, dual backends) scales; SKUs grow later.

---

## Live inventory (`rg-zevi-cloudphone`)

| Resource | Type | Region | Role |
|----------|------|--------|------|
| `kv-zevi-strlix` | Key Vault (RBAC, soft-delete, purge protection) | eastus2 | DB URL, JWT, Redis secrets |
| `psql-zevi-strlix` | Postgres Flexible **B1ms** / 32 GiB / v16 | **centralus** | Tenant DB + RLS (`eastus2` create restricted on this sub) |
| `appi-zevi-strlix` | Application Insights → `law-zevi-strlix` | eastus2 | Telemetry (no tokens/PII) |
| `ca-redis` | Container App Redis 7 (internal TCP) | eastus2 | Sessions / rate limits (classic Cache *create* retiring) |
| `ca-market-api` | Container App | eastus2 | Catalog / auth / checkout |
| `cae-zevi-strlix` | Container Apps Environment | eastus2 | Shared runtime |
| `acrzevistrlix` | ACR Basic | eastus2 | Images (`market-api:0.2.0`) |
| `ca-android-api` | Container App | eastus2 | In-phone API (unchanged) |
| `vm-zevi-cloudphone` | VM | eastus | Emulator host |
| `oai-zevi-phonepilot` / `speech-zevi-strlix` | Cognitive | eastus2 | Pilot AI / voice |

**market-api URL:** https://ca-market-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io  

Verified: `/health` → `db=postgres`. RLS demo: Bob cannot read Alice orders (`scripts/test-market-rls.py`).

---

## Security & privacy design

```
           [Phase-2: Front Door + WAF]
                     |
            ca-market-api (ACA + system MI)
           /         |          \
   Key Vault     Postgres      ca-redis (internal TCP)
   (RBAC)        Flexible      sess:{user_id}:{jti}
                 + FORCE RLS
                     \
                  audit_log (no tokens / raw PII)
```

1. **Per-user isolation** — request sets `app.user_id`; RLS `user_id = current_setting('app.user_id')::uuid`; FORCE RLS; catalog global read; login via `market.find_or_create_user` (SECURITY DEFINER).
2. **Secrets** — Key Vault; ACA secret refs; app role `strlix_app` (not admin) in `database-url`.
3. **Auth** — HS256 JWT with `aud`/`iss`/`jti`/`typ`; access 900s; refresh 7d; revoke on logout/soft-delete. Entra External ID = phase-2 (claim shape stable).
4. **Encryption** — TLS to Postgres (`require_secure_transport=on`, `sslmode=require`); Azure-managed at-rest; CMEK later.
5. **Network** — No CAE VNet today → PG public firewall (Azure services + bootstrap IP). Redis = internal ACA TCP + requirepass (no PE on this SKU story). Phase-2: VNet CAE + Private Endpoints (needs eligible PG/Redis SKUs).
6. **Privacy** — minimal PII; `audit_log`; `POST /v1/privacy/soft-delete`; hard-delete stub; never log Authorization / tokens.
7. **Dual backends remain** — android-api / desktop-api / session-broker / market-api.

**Redis note:** `ca-redis` is provisioned internal; market-api currently reports `redis:false` (in-process session fallback still enforces JWT + RLS). Wire/fix internal DNS next; phase-2 Managed Redis for PE/SLA.

---

## Scale-out path (phase 2+)

1. Front Door + WAF  
2. PG read replicas → `user_id` partitioning → Citus / regional shards  
3. Managed Redis Cluster + private endpoints  
4. Regional CAEs; regional device pools; broker affinity  
5. Per-user rate limits (hooks already keyed by `sub`)  
6. CMEK + KV HSM  
7. Entra External ID / social login  

**Do not** stand up Front Door / AKS / global Cosmos yet unless free/trivial.

---

## IaC & code

| Path | Purpose |
|------|---------|
| `deploy/azure/bicep/market-backend.bicep` | KV + Postgres (centralus) + App Insights |
| `deploy/azure/bicep/modules/*.bicep` | keyvault, postgres, appinsights, market-api-aca, redis-aca |
| `services/market-api/` | FastAPI market-api 0.2.0 |
| `services/market-api/migrations/001–003` | RLS schema, seed, login helper |
| `scripts/test-market-rls.py` | Cross-tenant isolation proof |

---

## Cost estimate (new foundation only, rough USD/mo)

| Resource | SKU | Est. $/mo |
|----------|-----|-----------|
| Postgres Flexible | B1ms 32GB centralus | ~$15–25 |
| ACA Redis | 0.25 vCPU / 0.5Gi always-on | ~$8–15 |
| ca-market-api | 0.25/0.5 scale-to-zero | ~$0–10 |
| Key Vault | Standard | ~$0–1 |
| App Insights | light share of LAW | ~$0–5 |
| **New burn** | | **≈ $25–55/mo** |

Existing VM / OpenAI / Speech / ACR / LAW / android-api burn is separate and unchanged.

---

## Ops snippets

```bash
# Health
curl -s https://ca-market-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io/health

# RLS proof (uses KV secrets)
export STRLIX_DATABASE_URL="$(az keyvault secret show -n database-url --vault-name kv-zevi-strlix --query value -o tsv)"
export STRLIX_JWT_SECRET="$(az keyvault secret show -n jwt-secret --vault-name kv-zevi-strlix --query value -o tsv)"
.venv/bin/python scripts/test-market-rls.py
```

SQLite fallback when `STRLIX_DATABASE_URL` unset (dev only — no RLS).
