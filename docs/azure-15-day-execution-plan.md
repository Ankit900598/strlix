# PhoneCodex Azure 15-Day Execution Plan

**Owner:** Ankit Yadav  
**Window:** 5 Sep 2026 → **22 Sep 2026** (credit expiry)  
**Account:** `ay186mnc-1561-resource` / `phonecodex-dev` / **westus3**  
**Strategy:** Burn **$1,000–1,800** on evidence and product acceleration. Not minimum spend — **maximum learning per dollar**. No VMs, AKS, GPU, PTU, Sora, always-on infra.

**Baseline entering Day 1:**

| Artifact | Status |
|----------|--------|
| classifier_v03 | 88% v0_challenge, 0 FA, 0 FB |
| Deployments | `pc-lab-cheap`, `pc-lab-strong`, `pc-lab-vision` (Standard SKU) |
| Model matrix | `evals/reports/azure_model_matrix.md` |
| Datasets | v0_seed (100), v0_challenge (50) |

---

## Spend envelope

| Line | Target | Hard stop |
|------|--------|-----------|
| Inference / eval API calls | $800–1,400 | — |
| Blob + Functions + Insights | $100–300 | — |
| Quota requests / budgets | $0 | — |
| **Total** | **$1,000–1,800** | **$2,000** |

**Rule:** Every dollar → CSV row, eval report, or logged prototype call. No idle infra.

---

## Phase overview

| Phase | Days | Focus | Target spend |
|-------|------|-------|--------------|
| **1** | 1–3 | Model comparison + prompt hardening | $50–150 |
| **2** | 4–6 | Screenshot / vision classifier | $150–350 |
| **3** | 7–9 | Backend deployment + logging | $100–250 |
| **4** | 10–12 | Feedback loop + analytics | $200–400 |
| **5** | 13–15 | Production reliability + cost/perf tradeoff | $150–350 |
| **Buffer** | 16–17 (to 22 Sep) | Overflow evals, premium tier if quota lands | $0–200 |

---

## Days 1–3 — Model comparison + prompt hardening

**Goal:** Know whether model tier matters after v03, or prompt is still the bottleneck.

### Day 1 (5 Sep) — Lab ready ✅

| Item | Detail |
|------|--------|
| **Azure services** | Azure OpenAI (existing 3 deployments) |
| **Output** | Model capability audit, deployment plan, matrix doc |
| **Success** | 3 tiers running; v03 baseline documented |
| **Do NOT** | Create PTU, Sora, delete deployments, spin VMs |

**Remaining today:** Create budget alerts if time permits.

---

### Day 2 (6 Sep) — Full model matrix (M1–M6)

| Item | Detail |
|------|--------|
| **Azure services** | Azure OpenAI — pc-lab-cheap, pc-lab-strong, pc-lab-vision |
| **Commands** | See `evals/reports/azure_model_matrix.md` M-series block |
| **Output** | 6 CSVs; filled results table; run_log with timestamps |
| **Success criteria** | All 6 runs complete; **0 FA on every run**; accuracy logged per tier |
| **Do NOT** | Change prompt mid-matrix; run without budget alerts |

**Expected finding:** If all tiers ≈ 88% ± 2%, model tier is not the lever — prompt v04 is.

**Spend:** $5–15

---

### Day 3 (7 Sep) — Consistency + prompt v04

| Item | Detail |
|------|--------|
| **Azure services** | Azure OpenAI (top 2 tiers from Day 2) |
| **Output** | 6 consistency CSVs; `classifier_v04.txt` draft; `v0_hard_subset.jsonl` (15 cases) |
| **Success criteria** | Consistency σ < 3%; v04 fixes `ch_wa_meme_monk_block_001`; v0_challenge_v2 schema started |
| **Do NOT** | Declare winner without 3× runs; fine-tune models |

**Prompt v04 targets:** monk meme → BLOCK; IG DM → WARN; a11y list browse → WARN (not ALLOW).

**Spend:** $15–40

---

## Days 4–6 — Screenshot / vision classifier experiments

**Goal:** Prove whether screenshots beat OCR text for ambiguous phone UI.

### Day 4 (8 Sep) — Vision dataset v0

| Item | Detail |
|------|--------|
| **Azure services** | Azure Blob Storage (private container `phonecodex-eval-screenshots`) |
| **Output** | `evals/fixtures/screenshots/` (20 PNGs); `v0_vision_v1.jsonl` (10 pilot cases); schema doc |
| **Success criteria** | 10 cases with screenshot + promise + expected decision; no PII in repo |
| **Do NOT** | Public blob; real user screenshots without redaction |

**Spend:** $1–5 (storage negligible)

---

### Day 5 (9 Sep) — Vision adapter + pilot eval

| Item | Detail |
|------|--------|
| **Azure services** | Azure OpenAI — pc-lab-vision (gpt-4o multimodal) |
| **Output** | Vision adapter extension; 10-case pilot CSV; text vs vision comparison table |
| **Success criteria** | Adapter sends base64 PNG + promise JSON; ≥1 case where vision beats text |
| **Do NOT** | Vision on every frame — eval only |

**Spend:** $10–25

---

### Day 6 (10 Sep) — Vision scale to 50 cases

| Item | Detail |
|------|--------|
| **Azure services** | Blob + gpt-4o via pc-lab-vision |
| **Output** | `v0_vision_v1.jsonl` (50 cases); V1–V3 eval CSVs; vision go/no-go memo (1 page) |
| **Success criteria** | All Shorts-player-no-OCR, loading-blank, 18+-gate categories covered; vision gain ≥5% on subset OR documented "text-first wins" |
| **Do NOT** | Build production vision pipeline in Android |

**Spend:** $30–80

---

## Days 7–9 — Backend deployment + logging

**Goal:** Real `/classify` endpoint with same prompt/model as eval winner — measure true latency.

### Day 7 (11 Sep) — Hosted classify prototype

| Item | Detail |
|------|--------|
| **Azure services** | Azure Functions (Python, **Consumption**, min instances 0) OR Container Apps minReplicas=0 |
| **Output** | `POST /classify` accepting promise + screenText JSON; returns classifier decision |
| **Success criteria** | 20 curl tests pass; p50 logged; Key Vault reference for API key (not in code/repo) |
| **Do NOT** | Always-on App Service; API key in source code |

**Spend:** $5–15

---

### Day 8 (12 Sep) — Application Insights + token logging

| Item | Detail |
|------|--------|
| **Azure services** | Application Insights linked to Functions |
| **Output** | Eval runner logs `latencyMs`, `promptTokens`, `completionTokens` per case; Insights dashboard |
| **Success criteria** | Every eval row has latency; hosted endpoint traces visible in Insights |
| **Do NOT** | Log screen content or user goals to public telemetry — hash case IDs only |

**Spend:** $5–10

---

### Day 9 (13 Sep) — Latency + cost benchmark report

| Item | Detail |
|------|--------|
| **Azure services** | Functions + OpenAI + Insights |
| **Output** | `evals/reports/cost_latency.md` — p50/p95 per tier, $/1k decisions |
| **Success criteria** | p95 < 4s from hosted endpoint; cost table for cheap/strong/vision |
| **Do NOT** | Optimize latency with PTU |

**Spend:** $20–50 (100-call load test)

---

## Days 10–12 — Feedback loop + analytics

**Goal:** Close the loop: eval → failure clusters → prompt fix → re-eval. Simulate policy merge.

### Day 10 (14 Sep) — Failure cluster analysis

| Item | Detail |
|------|--------|
| **Azure services** | OpenAI (embedding optional: text-embedding-3-small if quota) |
| **Output** | `evals/reports/failure_clusters.md` — top 30 patterns ranked with examples |
| **Success criteria** | Each cluster has: count, severity, suggested prompt/rule fix, example case IDs |
| **Do NOT** | RAG over docs for ALLOW/WARN/BLOCK |

**Spend:** $10–30

---

### Day 11 (15 Sep) — Policy replay simulator

| Item | Detail |
|------|--------|
| **Azure services** | Local script + optional Functions |
| **Output** | `evals/runner/policy_replay.py` — classifier output → PolicyEngine merge → final decision |
| **Success criteria** | Post-policy dangerous miss rate = 0 on seed; counters/guardrails applied correctly |
| **Do NOT** | Move policy engine to cloud permanently |

**Spend:** $5–15

---

### Day 12 (16 Sep) — Feedback loop v1

| Item | Detail |
|------|--------|
| **Azure services** | Blob (eval artifacts) + Functions |
| **Output** | Pipeline: new failure → tag → JSONL row → re-eval → CSV delta; expand v0_challenge to 75 cases |
| **Success criteria** | 25 new cases added from failure clusters; v04/v05 prompt re-run shows ≥2% gain OR 0 new FA |
| **Do NOT** | Auto-label without human review |

**Spend:** $40–100 (expanded eval sweeps)

---

## Days 13–15 — Production reliability, monitoring, tradeoffs

**Goal:** Pick production config with numbers. Document what ships in PhoneCodex v1.

### Day 13 (17 Sep) — Premium tier eval (if quota approved)

| Item | Detail |
|------|--------|
| **Azure services** | Deploy pc-lab-reasoning (gpt-5.4) and/or pc-lab-claude-opus |
| **Output** | M7/M8 CSVs; premium vs strong comparison |
| **Success criteria** | Premium evaluated OR quota blocker documented with ticket ID |
| **Do NOT** | Wait idle if quota denied — proceed to Day 14 |

**If blocked:** Request quota again; run extra consistency on gpt-4.1 instead.

**Spend:** $30–80 (premium) or $15 (extra 4.1 runs)

---

### Day 14 (18 Sep) — Production recommendation memo

| Item | Detail |
|------|--------|
| **Azure services** | None (synthesis) |
| **Output** | `evals/reports/production_recommendation.md` — exact model, prompt, deployment, escalation rules |
| **Success criteria** | Answers: default tier, when to escalate to strong/vision, cost/latency budget, 0 FA proof |
| **Do NOT** | Ship Android changes |

**Production architecture target:**
```
On-device OCR → cheap classifier (gpt-4.1-mini)
  → confidence < threshold OR vision-flag case → strong (gpt-4.1) or vision (gpt-4o)
  → PolicyEngine merge → overlay
```

**Spend:** $0

---

### Day 15 (19 Sep) — Monitoring + cost/perf tradeoff dashboard

| Item | Detail |
|------|--------|
| **Azure services** | Application Insights + Cost Management |
| **Output** | Static HTML eval dashboard; budget vs actual spend chart; final Go/No-Go |
| **Success criteria** | Dashboard shows all CSVs; total spend $1k+ OR documented reason if under; alerts firing |
| **Do NOT** | Force spend on useless infra to hit $1k |

**Spend:** $20–50 (final eval passes)

---

## Days 16–17 — Buffer (20–22 Sep)

| If under $1k spent | Run expanded vision (100 cases), 3× consistency on v05, premium if quota lands |
| If $1.5k+ spent | Docs only, stop inference |
| 22 Sep | Credit expiry — archive reports, snapshot dashboard, handoff doc for Android |

---

## Daily template

Every day, answer:

1. **Goal** — one sentence
2. **Azure services** — which, why
3. **Output** — file path
4. **Success criteria** — measurable
5. **Do NOT** — waste guard

---

## Program success criteria (18-day total)

| # | Criterion | Measurement |
|---|-----------|-------------|
| 1 | Winning model + prompt chosen | production_recommendation.md |
| 2 | 0 false allows on final config | 150+ seed + 75+ challenge |
| 3 | 0 false blocks on final config | Same |
| 4 | Accuracy ≥ 90% on v0_challenge_v2 | CSV proof |
| 5 | Vision go/no-go decided | 50-case table |
| 6 | Hosted /classify working | p95 < 4s |
| 7 | Cost per 1k decisions documented | cost_latency.md |
| 8 | Failure clusters ranked | failure_clusters.md |
| 9 | $1,000+ productive spend | Cost Management export |
| 10 | Zero infra waste | No VMs/AKS/PTU created |

---

## Quick reference

| Resource | Value |
|----------|-------|
| Model matrix | `evals/reports/azure_model_matrix.md` |
| CTO strategy | `docs/cto-strategy-phonecodex-ai.md` |
| Eval command | `py -3.12 evals/runner/run_eval.py --adapter azure_openai --prompt evals/prompts/classifier_v03.txt` |
| Deployments | pc-lab-cheap / pc-lab-strong / pc-lab-vision |

---

*17 days. Expiring credit. One classifier worth trusting.*
