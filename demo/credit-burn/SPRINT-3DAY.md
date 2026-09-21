# Strlix credit-burn sprint — 3-day breaking-point plan

**Authoritative for:** Ankit Yadav / `ay186mnc@gmail.com`  
**Scope lock:** Azure RG `rg-zevi-cloudphone` **only** — never touch `phonecodex-*`, `rg-android-dev-prod`, or `NetworkWatcherRG`.  
**Written:** 2026-09-21 ~19:35 IST (Asia/Calcutta)  
**Do not delete resources.** GPU create is **NO-GO tonight** (see §6).

---

## 1) Subscription / credits (verified)

| Field | Value |
|--------|--------|
| Account user | `ay186mnc@gmail.com` |
| Subscription name | `Azure subscription 1` |
| Subscription ID | `a3dc5296-f948-427e-8656-c6bc52afee21` |
| Tenant ID | `d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2` |
| State | Enabled |
| **quotaId** | **`Sponsored_2016-01-01`** → Microsoft **Sponsored / Startups** offer |
| spendingLimit | `Off` |
| Billing account | MCA · Individual · display **ZAVI AI** / ankit yadav · soldTo IN · billing currency **INR** |
| Credits REST (`.../credits/balanceSummary`, balances) | **Not Found** — remaining balance **not exposed via CLI** for this MCA+Sponsored path |
| Budgets | none configured |

### What “~$1000 in 3 days” likely maps to

| Hypothesis | Evidence | Likelihood |
|------------|----------|------------|
| **A. Credit expiry window** — ~$1000 left on Sponsored/Startups grant that **expires ~Sep 24** | Sponsored quotaId; API cannot show balance; user timebox “3 days” | **Most likely** |
| **B. Planned burn rate** — intentionally spend ~$333/day | Current measured burn ≪ $333/day | Possible as *intent*, not as *status quo* |
| **C. Still ~$10k Microsoft for Startups remaining** | Prior narrative; **not** confirmed by any API; do not plan as if $10k is banked | Unverified — treat as **unknown upside** |

**Working assumption for this sprint:** treat **~$1000 as the remaining Sponsored balance**, with a hard wall in **~3 days**. Confirm in portal: Cost Management → Credits / Microsoft for Startups benefit page. Until portal confirms, keep a **$200 safety buffer** and prefer create-on-demand + deallocate.

### Current measured spend (Consumption usageDetails, last ~8 calendar days)

| Resource group | USD (~8d) | ~USD/day |
|----------------|-----------|----------|
| `rg-android-dev-prod` | **$15.62** | ~$3.1 |
| **`rg-zevi-cloudphone`** | **$6.59** | **~$1.3** |
| `phonecodex-dev` | $3.18 | ~$0.6 |
| **Subscription total** | **~$25.38** | — |

Daily sub totals seen: Sep 18 $4.04 · Sep 19 $5.18 · Sep 20 $11.64 · Sep 21 $4.51 (partial).

**`rg-zevi-cloudphone` meters (same window):**

| Meter | USD |
|-------|-----|
| Compute `D4nls v6` (VM) | $5.82 |
| OpenAI/Foundry token meters | ~$0.43 |
| P4 LRS Disk | $0.20 |
| Standard static public IP | $0.13 |
| Speech TTS chars | ~$0.00 |

> Note: ACA / Postgres / ACR often lag or sit under free grants; retail estimates below are for planning, not a perfect match to usageDetails.

---

## 2) Inventory — `rg-zevi-cloudphone`

RG location tag: **eastus2**. Resources span **eastus** (VM), **eastus2** (ACA stack), **centralus** (Postgres).

| Name | Type | Location | SKU / size | Est. monthly burn (retail, idle-ish) |
|------|------|----------|------------|--------------------------------------|
| `vm-zevi-cloudphone` | VM | eastus | **Standard_D4nls_v6** · **Running** · Linux | **~$164**/mo @ $0.227/hr |
| OS disk `...OsDisk_1_...` | Disk | eastus | Premium_LRS **P4** 30 GB | ~$5.3/mo |
| `vm-zevi-cloudphone-ip` | Public IP | eastus | Standard static | ~$3.6/mo |
| `vm-zevi-cloudphone-vnet` + NIC + NSG + SSH key | Network | eastus | — | ~$0 |
| `cae-zevi-strlix` | Container Apps Env | eastus2 | Consumption profile | Env mgmt list price **$0.10/hr** (~$72/mo) — often discounted / grant; watch closely |
| `ca-android-api` | Container App | eastus2 | 0.5 vCPU / 1Gi · min=1 max=3 · public FQDN | ~$15–40/mo (always-on min replica) |
| `ca-market-api` | Container App | eastus2 | 0.25 / 0.5Gi · min=1 max=1 · public | ~$8–20/mo |
| `ca-redis` | Container App | eastus2 | 0.25 / 0.5Gi · min=1 · **internal** Redis | ~$8–20/mo (not managed Redis) |
| `acrzevistrlix` | ACR | eastus2 | **Basic** | ~$5/mo |
| `psql-zevi-strlix` | Postgres Flexible | **centralus** | **Standard_B1ms** Burstable · 32 GB · HA off | ~$12–18/mo + storage |
| `kv-zevi-strlix` | Key Vault | eastus2 | Standard | pennies (ops-based) |
| `oai-zevi-phonepilot` | Azure OpenAI | eastus2 | S0 | **usage** (seen ~$0.4/week recently) |
| `speech-zevi-strlix` | Speech | eastus2 | S0 | **usage** (near zero recently) |
| `law-zevi-strlix` | Log Analytics | eastus2 | — | data ingest |
| `appi-zevi-strlix` | App Insights | eastus2 | — | data ingest |
| Smart Detection action group | Insights | global | — | $0 |

**Est. steady stack (no new GPU):** roughly **$220–350/mo** retail if CAE env hour fully bills; **observed** last week only ~**$40/mo** run-rate on this RG — so either free grants / lag, or CAE not fully charged yet. Plan with **observed + headroom**, not worst-case panic.

**Other RGs (observe only — do not touch):** `rg-android-dev-prod` is the **largest** recent burner (~$15.6/8d). That alone can eat the last $1000 if left running for months; for a 3-day sprint it is secondary noise (~$3/day).

---

## 3) Daily burn budget (3-day sprint)

Assume portal confirms **$1000** remaining and ~**72 hours** of credit life.

| Bucket | 3-day $ | Notes |
|--------|---------|--------|
| Safety buffer (do not spend) | **$200** | Portal lag, INR FX, other RGs, OpenAI spikes |
| Keep existing stack alive | **$15–40** | Based on observed + small headroom |
| **A) GPU worker (48–72h)** | **$15–45** | See §4A — OD T4 ~$25–38/48–72h |
| **B) Hardening (AFD+WAF, managed Redis, 1–2 PEs)** | **$40–80** | Prorated / first-month create; survives after credits |
| **C) Payments wiring (code + KV secrets)** | **~$0–5** | Stripe fees outside Azure credits |
| Demo OpenAI/Speech spikes | **$50–100** | Controllable |
| **Discretionary / demo peak** | **$500–650** | Only if A–C done and portal still shows cushion |

**Recommended daily target:** **$150–250/day max** intentional new spend, with **GPU deallocate when idle**. Do **not** try to zero the $1000 with idle fleets.

---

## 4) Prioritized create vs skip

### A) GPU worker — cloud-phone / inference / encoding

**Goal:** one demonstrable GPU path (encode / light inference / Android graphics assist), wired to existing CAE or VM — **not** a fleet.

| Candidate (eastus2 preferred for CAE; eastus next to current VM) | On-demand Linux | Spot (approx.) | Low-priority | 48h OD cost | 72h OD cost |
|----------------------------------------------------------------|-----------------|----------------|--------------|-------------|-------------|
| **Standard_NC4as_T4_v3** (1× T4 16GB) — **preferred cheap CUDA** | **$0.526/hr** | ~$0.26/hr | **$0.105/hr** | **~$25** | **~$38** |
| Standard_NC8as_T4_v3 | $0.752/hr | ~$0.38 | $0.15 | ~$36 | ~$54 |
| **Standard_NV6ads_A10_v5** (1/6 A10 — graphics/encode) | **$0.454/hr** | ~$0.084 | $0.091 | **~$22** | **~$33** |
| Standard_NV12ads_A10_v5 | $0.908/hr | ~$0.17 | $0.182 | ~$44 | ~$65 |

**Spot / LP risk:** eviction mid-demo; Low-priority regional quota today is only **3 vCPUs** (both eastus & eastus2) — **NC4as needs 4**, NV6 needs 6 → **Spot/LP blocked until LP + GPU family quota raised**.

#### HARD BLOCK — GPU quota is **0**

Verified `az vm list-usage` in **eastus** and **eastus2**:

- `Standard NCASv3_T4 Family` → **limit 0**
- `StandardNVADSA10v5Family` → **limit 0**
- All other N* GPU families → **limit 0**
- `Total Regional Low-priority vCPUs` → **limit 3**

**Any `az vm create` for GPU will fail tonight** until quota increase is approved (hours–days).

**CREATE (after quota):** 1× `Standard_NC4as_T4_v3` Ubuntu 22.04 in **eastus2**, same RG, new subnet or peer to VM vnet carefully; NVIDIA driver + CUDA; expose only via private IP / SSH jump from existing VM; tag `project=strlix` `role=gpu-worker` `auto-shutdown=true`.

**SKIP:** multi-GPU, A100/H100, always-on GPU after demo, GPU Container Apps dedicated profile ($4+/hr).

### B) Production hardening (survives after credits)

| Item | Action | Est. $ | Verdict |
|------|--------|--------|---------|
| **Azure Front Door Standard + WAF policy** | Front CA public endpoints (`ca-android-api`, `ca-market-api`) | ~$35/mo base + traffic + ~$2.5 WAF policy | **CREATE** Day 1–2 |
| **Azure Cache for Redis Basic C0** | Replace `ca-redis` container for durability | ~$0.022/hr ≈ **$16/mo** | **CREATE** |
| Private Endpoints (KV, Postgres, Redis) | Only if PE + DNS cheap enough; Postgres is **centralus** → PE cost + cross-region pain | $7–20/mo each + DNS | **CREATE 1–2 max** (KV + Redis in eastus2); **SKIP Postgres PE** this sprint (wrong region) |
| Move Postgres to eastus2 | High value long-term, migration risk | time + brief dual-run $ | **SKIP this sprint** (document as Day-4+) |
| Entra External ID | Notes + minimal app registration path; full CIAM tenant is product work | $0–low | **NOTES + stub only** |
| App Gateway WAF_v2 | Overlap with AFD | higher | **SKIP** (AFD wins) |

**Entra External ID path (minimal):** create External ID tenant *or* use workforce tenant app registration → app registration for `ca-market-api` → redirect URIs for web-market → store client secret in `kv-zevi-strlix` → wire `AUTH_MODE=entra` later. Do **not** force production login mid-demo.

### C) Live payments readiness (gated)

Already present: Stripe/Razorpay **test** stubs in `web-market` + `services/market-api` (`pay_mode=test`; live returns **503** `"live charges disabled in this build"`). Webhooks are stubs.

**CREATE (code + secrets, still gated):**

1. Add KV secrets: `stripe-publishable-key`, `stripe-secret-key`, `stripe-webhook-secret` (test values first).
2. ACA env from Key Vault references on `ca-market-api`.
3. Implement real Stripe Checkout Session + webhook signature verify behind `pay_mode=live` **and** a second gate `ALLOW_LIVE_CHARGES=false` until Ankit flips both.
4. Keep test path default.

**SKIP:** enabling live charges; storing live keys in git/`.env` on box.

### D) Explicit skips (credit hygiene)

- Giant / idle GPU fleets  
- Premium ACR, Postgres HA, zone-redundant CAE  
- Touching `phonecodex-*` or android-dev RG  
- Deleting anything  

---

## 5) Recommended 72-hour sequence

| When (IST) | Action | $ impact |
|------------|--------|----------|
| **Tonight** | Confirm remaining credits in portal; file **GPU quota** request (NCasT4 ≥8, NVadsA10 ≥6, LP cores ≥8) eastus2; draft IaC (done under `infra/`); wire Stripe test secrets to KV if keys available | $0–5 |
| **Day 1** | AFD Standard + WAF → market + android FQDNs; create Redis **Basic C0**; point market-api to managed Redis; keep `ca-redis` until cutover verified | ~$40–60 create/prorate |
| **Day 2** | If GPU quota approved → create **1× NC4as_T4_v3** (OD first for stable demo; switch Spot only after LP quota ≥4); smoke encode/inference; **deallocate** when idle | ~$12–25 for ~24h OD |
| **Day 3** | Payments live-wiring behind gates; demo script; deallocate GPU; leave AFD+Redis+stack | GPU off; hardening remains |

---

## 6) GO / NO-GO — GPU create tonight

| Check | Status |
|-------|--------|
| Credits clearly ≥ 48h cheapest useful GPU + stack (~$50–80) | **UNKNOWN** (API blind; user says ~$1000 — plausible but unproven) |
| GPU family quota eastus / eastus2 | **FAIL — all N* limits = 0** |
| Low-priority/Spot regional cores | **FAIL — limit 3** (need ≥4 for NC4as) |
| High demo value | **YES** |
| Affordable *if* quota + ~$1000 claim true | **YES** (~$25–38 OD / 48–72h) |

### **NO-GO for GPU create tonight**

**Reasons:** (1) quota will reject create; (2) remaining balance not CLI-verified.  
**Next:** portal credit confirm + quota ticket → then **GO** for single `NC4as_T4_v3` OD in `rg-zevi-cloudphone` / eastus2.

Exact commands (not executed): `infra/gpu-worker/CREATE-gpu-worker.sh`  
Quota request helper: `infra/gpu-worker/REQUEST-quota.md`

---

## 7) Risks

| Risk | Mitigation |
|------|------------|
| Credits expire mid-sprint | Prefer hardening that survives; GPU deallocate; buffer $200 |
| GPU quota delay | Parallelize AFD/Redis/payments; don’t block sprint on GPU |
| Spot eviction mid-investor demo | Use OD for live demos; Spot only for soak |
| CAE $0.10/hr env fee surprises | Watch Cost Management daily; scale minReplicas to 0 overnight if needed |
| Cross-region Postgres (centralus) | Skip PE; plan migrate post-credits |
| Other RGs silent burn | Do not expand them; optional deallocate *only if user asks* |
| Live Stripe accidents | Dual gate `pay_mode` + `ALLOW_LIVE_CHARGES` |

---

## 8) Box / workspace health

| Check | Status |
|-------|--------|
| Disk `/` | **126G** total · **56G** used · **64G** avail · **47%** |
| `/workspace/zevi-cloudphone` | Present · ~**500MB** · healthy tree (`app`, `services`, `demo`, `deploy`, `web-market`, …) |
| `demo/credit-burn/` | Created this sprint |
| `infra/` | Created (`gpu-worker`, `hardening`) |
| az identity | Logged in as `ay186mnc@gmail.com` on Sponsored sub |

---

## 9) Artifacts produced

- This file: `demo/credit-burn/SPRINT-3DAY.md`
- `infra/gpu-worker/CREATE-gpu-worker.sh` — exact `az` commands (safe: no auto-run)
- `infra/gpu-worker/REQUEST-quota.md` — quota ask text
- `infra/gpu-worker/gpu-worker.bicep` — draft IaC
- `infra/hardening/NOTES.md` — AFD / Redis / Entra / payments checklist

---

## 10) One-line executive summary

**Sponsored sub `a3dc5296-…` · remaining $ not API-visible (assume user’s ~$1000/3d expiry) · RG burn ~$1.3/day · GPU is high-value (~$25/48h T4) but `NO-GO tonight` (GPU quota=0) · burn plan: quota+AFD+Redis+gated Stripe first, then 1× T4.**
