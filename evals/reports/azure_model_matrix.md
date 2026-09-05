# Azure Model Matrix — PhoneCodex Eval & Production Selection

**Audit date:** 2026-09-05  
**Account:** `ay186mnc-1561-resource`  
**Region:** westus3  
**Catalog source:** `evals/reports/azure_model_capability_audit.json` (139 model/version entries)  
**Current classifier:** `classifier_v03` — **88%** on `v0_challenge`, **0 false allows**, **0 false blocks**

---

## Executive summary

PhoneCodex needs models that reason about **user promises**, not app categories. The same YouTube screen is ALLOW, WARN, or BLOCK depending on commitment text, guardrails, and counters.

**Live today (Standard SKU, serverless, pay-per-call):**

| Role | Deployment | Model | Status |
|------|------------|-------|--------|
| Cheap production classifier | `pc-lab-cheap` | gpt-4.1-mini | ✅ Running |
| Strong reasoning classifier | `pc-lab-strong` | gpt-4.1 | ✅ Running |
| Vision screenshot classifier | `pc-lab-vision` | gpt-4o | ✅ Running |
| Fallback | `pc-lab-cheap` | (same) | ✅ No separate deploy needed |

**Blocked (quota 0 — manual request required):** gpt-5.4, gpt-5.1, gpt-6-astra, Claude Opus 5, Claude Sonnet 5.

**Do not deploy:** Sora/video models, provisioned throughput (PTU), deprecated o1/o4-mini new instances, gpt-4o-mini (deprecated version).

---

## Phase 1 — Model capability audit

### Audit methodology

```powershell
py -3.12 evals/reports/_audit_models.py
# Output: evals/reports/azure_model_capability_audit.json
```

Categories in catalog: **14 openai_chat**, **9 openai_vision**, **28 openai_reasoning**, **13 claude**, **6 embedding**, **69 other** (Llama, Mistral, Codestral, etc.), **0 sora** in PhoneCodex-relevant set.

### Tier A — Deployed & recommended (Standard SKU)

| Model | Version | Deployment | SKU | Latency class | Cost class | PhoneCodex use case |
|-------|---------|------------|-----|---------------|------------|---------------------|
| **gpt-4.1-mini** | 2025-04-14 | `pc-lab-cheap` | Standard | Fast (~1–2s) | **$** (~$0.40–1/1k decisions) | Production default, high-volume eval sweeps, on-device advisor v1 |
| **gpt-4.1** | 2025-04-14 | `pc-lab-strong` | Standard | Medium (~2–3s) | **$$** (~$2–5/1k) | Ambiguous ALLOW/WARN/BLOCK, promise disambiguation, hard-case escalation |
| **gpt-4o** | 2024-11-20 | `pc-lab-vision` | Standard | Medium (~2–3s) | **$$** (~$2.5–6/1k) | Screenshot + OCR multimodal, UI element detection (Shorts player chrome, 18+ gates) |

**Why these three:** Only models with **Standard SKU + active quota + non-deprecated** in westus3. They cover the full PhoneCodex inference ladder: cheap always-on → strong text → vision escalation.

### Tier B — Catalog visible, quota blocked (GlobalStandard serverless when approved)

| Model | Version | Planned deployment | SKU | Latency | Cost | PhoneCodex use case |
|-------|---------|-------------------|-----|---------|------|---------------------|
| **gpt-5.4** | 2026-03-05 | `pc-lab-reasoning` | GlobalStandard | Slow (~3–8s) | **$$$** (~$8–15/1k) | Strongest OpenAI reasoning; test if 88% ceiling breaks on monk/guardrail traps |
| **gpt-5.1** | 2025-11-13 | `pc-lab-fallback` | Standard* | Medium | **$$$** | Has Standard SKU but **quota 0**; alternative reasoning tier |
| **gpt-6-astra** | 2026-09-03 | `pc-lab-premium` | GlobalStandard | Unknown | **$$$$** | Newest catalog entry; eval only after 5.4 baseline |
| **claude-opus-5** | 2 | `pc-lab-claude-opus` | GlobalStandard | Slow | **$$$** | Best Claude; different reasoning style for promise parsing |
| **claude-sonnet-5** | 2 | `pc-lab-claude-sonnet` | GlobalStandard | Medium | **$$** | Cheaper Claude for volume after Opus proves value |
| **gpt-5.4-mini** | 2026-03-17 | — | GlobalStandard | Medium | **$$** | Cost-optimized reasoning if full 5.4 wins |

*gpt-5.1 Standard exists in catalog but TPM quota = 0 in this subscription.

**Blocker:** `InsufficientQuota` — all return quota limit 0.  
**Human action:** Foundry portal → Quotas → request ≥1 K TPM for gpt-5.4 GlobalStandard + Claude Opus 5. Deploy with `evals/reports/_deploy_gpt54_reasoning.json` and `_deploy_claude_opus.json` (API `2025-10-01-preview`).

### Tier C — Not recommended for PhoneCodex

| Model | Reason |
|-------|--------|
| **o1 / o4-mini** | `ServiceModelDeprecating` — new deployments rejected |
| **gpt-4o-mini** | Version 2024-07-18 deprecated; redeploy fails in westus3 |
| **gpt-4.1-nano** | No Standard SKU; quota 0 on GlobalStandard |
| **Sora / video gen** | Out of scope — not classification |
| **Codestral / gpt-5.x-codex** | Code generation, not promise reasoning |
| **Embeddings only** | Useful later for failure clustering, not classifier |
| **Llama-3.2-90B-Vision** | GlobalStandard quota 0; gpt-4o already deployed for vision |
| **PTU / ProvisionedManaged** | Forbidden — always-on cost, no benefit for eval |

### Tier D — Future multimodal phone understanding

| Capability | Model path | When |
|------------|------------|------|
| Screenshot classification | gpt-4o via `pc-lab-vision` | Week 1 (Day 4–6) |
| OCR + vision hybrid | gpt-4o multimodal + on-device OCR | Week 2 |
| Premium ambiguous cases | gpt-5.4 or Claude Opus 5 | After quota + text baseline |
| On-device fallback | No Azure — local rules + small model | Post-credit, Android-side |
| Custom fine-tune | Azure OpenAI fine-tuning | Only if 500+ labels AND cloud ceiling proven |

---

## Phase 2 — Deployment plan

### Current state (verified 2026-09-05)

```
ay186mnc-1561-resource (westus3, S0 pay-as-you-go)
├── pc-lab-cheap   → gpt-4.1-mini  Standard 100k TPM  Running
├── pc-lab-strong  → gpt-4.1       Standard 100k TPM  Running
└── pc-lab-vision  → gpt-4o         Standard 100k TPM  Running
```

**No new deployments created this session** — existing set satisfies all four roles (fallback = cheap).

### Recommended deployment set (final target)

| # | Role | Deployment | Model | Priority |
|---|------|------------|-------|----------|
| 1 | Cheap production | `pc-lab-cheap` | gpt-4.1-mini | ✅ Live |
| 2 | Strong reasoning | `pc-lab-strong` | gpt-4.1 | ✅ Live |
| 3 | Vision classifier | `pc-lab-vision` | gpt-4o | ✅ Live |
| 4 | Optional fallback | `pc-lab-cheap` | (same) | ✅ Use cheap tier |
| 5 | Premium reasoning | `pc-lab-reasoning` | gpt-5.4 | ⏳ Quota request |
| 6 | Alt reasoning (Claude) | `pc-lab-claude-opus` | claude-opus-5 v2 | ⏳ Quota + adapter |

### Manual steps for Tier B (when quota approved)

**gpt-5.4:**
```powershell
py -3.12 evals/reports/_probe_deploy.py  # verify quota first
# Or ARM PUT with evals/reports/_deploy_gpt54_reasoning.json
```

**Claude Opus 5:**
```powershell
# Requires modelProviderData — see evals/reports/_deploy_claude_opus.json
# API version: 2025-10-01-preview
# Endpoint: https://ay186mnc-1561-resource.services.ai.azure.com/anthropic/v1/messages
# Needs new adapter: azure_anthropic (not wired yet)
```

### Inference endpoints (no secrets)

**OpenAI-format (all 3 live deployments):**
```
POST https://ay186mnc-1561-resource.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=2024-08-01-preview
Header: api-key: <from Portal>
```

**Claude (when deployed):**
```
POST https://ay186mnc-1561-resource.services.ai.azure.com/anthropic/v1/messages
Headers: api-key, anthropic-version: 2023-06-01
Body model field = deployment name (pc-lab-claude-opus)
```

---

## Phase 3 — Evaluation matrix

### Datasets

| Dataset | Cases | Purpose | When to run |
|---------|-------|---------|-------------|
| `v0_seed.jsonl` | 100 | Safety regression (adult, tamper, short-form BLOCK) | Every model change |
| `v0_challenge.jsonl` | 50 | Boundary cases (ALLOW/WARN/BLOCK ambiguity) | Primary comparison |
| `v0_hard_subset.jsonl` | ~15 (build Day 3) | Cross-model failure union | After Phase 1 |
| `v0_vision_v1.jsonl` | 10→50 (build Day 4–6) | Screenshot multimodal | Vision tier only |
| `v0_challenge_v2.jsonl` | 75+ (build Day 3) | Expanded boundaries | Week 2 |

### Run matrix (M-series)

| Run | Deployment | Model | Dataset | Prompt | Cases |
|-----|------------|-------|---------|--------|-------|
| M1 | pc-lab-cheap | gpt-4.1-mini | v0_challenge | v03 | 50 |
| M2 | pc-lab-strong | gpt-4.1 | v0_challenge | v03 | 50 |
| M3 | pc-lab-vision | gpt-4o | v0_challenge | v03 | 50 |
| M4 | pc-lab-cheap | gpt-4.1-mini | v0_seed | v03 | 100 |
| M5 | pc-lab-strong | gpt-4.1 | v0_seed | v03 | 100 |
| M6 | pc-lab-vision | gpt-4o | v0_seed | v03 | 100 |
| M7 | pc-lab-reasoning | gpt-5.4 | v0_challenge | v03 | 50 |
| M8 | pc-lab-claude-opus | claude-opus-5 | v0_challenge | v03 | 50 |
| V1–V3 | pc-lab-vision | gpt-4o | v0_vision_v1 | v03 | 10–50 |
| C1–C6 | top 2 configs | — | v0_challenge | v03 | 50 × 3 each |

### Exact commands

```powershell
cd C:\Users\HP\strlix
$Prompt = "evals/prompts/classifier_v03.txt"

# Full text comparison (M1–M6)
foreach ($dep in @('pc-lab-cheap','pc-lab-strong','pc-lab-vision')) {
  $env:AZURE_OPENAI_DEPLOYMENT = $dep
  py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt $Prompt
  py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter azure_openai --prompt $Prompt
}

# Consistency (after picking top 2)
$env:AZURE_OPENAI_DEPLOYMENT = 'pc-lab-strong'
1..3 | ForEach-Object {
  py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt $Prompt
}
```

**Requirements:** `.env` at repo root with endpoint + api-key (never commit). Use `py -3.12` only.

### Metrics definitions

| Metric | Definition | Hard gate | Target |
|--------|------------|-----------|--------|
| **Accuracy** | exact decision match / total | — | ≥ 90% on v0_challenge |
| **False allows (FA)** | expected BLOCK/LOCK → predicted ALLOW | **Must be 0** | 0 |
| **False blocks (FB)** | expected ALLOW → predicted BLOCK | **Must be 0** | 0 |
| **Dangerous miss rate** | FA + (BLOCK → WARN) on safety cases | — | 0 |
| **Latency p50** | median ms per classify call | — | < 2000ms |
| **Latency p95** | 95th percentile | — | < 4000ms |
| **Cost / 1k decisions** | (input+output tokens) × price | — | document per tier |
| **Reliability** | API error rate over run | — | < 1% |
| **Consistency σ** | stddev accuracy over 3 identical runs | — | < 3% |

### Severity-weighted score (when accuracy ties)

| Error | Weight |
|-------|--------|
| False allow | 10× |
| BLOCK → WARN (monk, adult, short-form) | 5× |
| WARN → ALLOW (social friction) | 2× |
| ALLOW → WARN | 1× |
| Category mismatch only | 0.5× |

**Disqualification rule:** Any FA > 0 → model config rejected regardless of accuracy.

### Scientific comparison protocol

1. **Fixed prompt** — same `classifier_v03.txt` for all models in a phase (no mid-matrix prompt edits).
2. **Fixed dataset hash** — record SHA256 of JSONL in run log.
3. **Same adapter** — `azure_openai` for OpenAI deployments; separate adapter for Claude when live.
4. **Temperature 0** — already set in adapter.
5. **3× consistency** on top 2 configs before declaring winner.
6. **Blind failure review** — tag failures as prompt vs model vs dataset label dispute.
7. **Document everything** — one CSV per run in `evals/reports/`.

### Decision rubric: expensive model vs cheap

**Stay on cheap (gpt-4.1-mini) if:**

- Accuracy within **±2%** of strong tier on v0_challenge with v03
- Same failure cases on monk/guardrail/social friction
- 0 FA and 0 FB on both tiers
- Cost per 1k > 3× with < 4% accuracy gain

**Upgrade to strong (gpt-4.1) if:**

- ≥ **4% accuracy gain** with 0 FA / 0 FB
- Fixes `ch_wa_meme_monk_block_001` (BLOCK→WARN) without prompt change
- Consistency σ lower on strong tier

**Upgrade to premium (gpt-5.4 / Claude) if:**

- Strong tier plateaus ≥ 88% after prompt v04
- Premium gains ≥ **3%** on v0_hard_subset with 0 FA
- Fixes high-severity misses cheap+strong both fail
- Cost justified: user pays for commitment OS — $5–15/1k decisions acceptable for advisor calls if accuracy ≥ 92%

**Use vision tier when:**

- Text-only accuracy ≥ 90% but vision cases (no OCR keywords) fail
- Screenshot eval shows ≥ **10% gain** over OCR-only on same cases
- Hybrid architecture: cheap text first → vision escalation on low confidence

**Current evidence (v03, cheap only @ 88%):** Model tier comparison M2/M3 not yet run with v03. Prior v01 runs showed **no gain** from mini→4.1→4o — prompt engineering (v01→v03) gave +14% instead.

---

## Results log (fill as runs complete)

| Run | Deployment | Dataset | Accuracy | FA | FB | Latency (total) | Report CSV |
|-----|------------|---------|----------|----|----|-----------------|------------|
| baseline | pc-lab-cheap | v0_challenge | **88%** | 0 | 0 | ~105s/50 | `azure_openai_20260905_112326.csv` |
| M2 | pc-lab-strong | v0_challenge | _TBD_ | | | | |
| M3 | pc-lab-vision | v0_challenge | _TBD_ | | | | |
| M4–M6 | all tiers | v0_seed | _TBD_ | | | | |

---

## Cost estimate (full matrix)

| Phase | Runs | Est. API calls | Est. spend |
|-------|------|----------------|------------|
| M1–M6 (text) | 6 | 450 | $1–5 |
| Consistency C1–C6 | 6 | 300 | $1–4 |
| Vision V1–V3 | 3 | 150 | $2–8 |
| Premium M7–M8 | 2 | 100 | $5–20 |
| Hosted prototype load test | 1 | 1000 | $10–30 |
| **Total comparison program** | — | ~2000 | **$20–70** |

Remaining ~$930–1,970 credit budget goes to: dataset expansion evals, prompt sweeps, vision fixtures, Application Insights, blob storage, Functions prototype.

---

## Blockers & human actions

| Blocker | Impact | Action |
|---------|--------|--------|
| Premium quota = 0 | No gpt-5.4 / Claude / gpt-6-astra | Foundry → Quotas → request TPM |
| No budget alerts | Spend risk | Cost Management → 3 budgets ($1.5k/$1.8k/$2k) |
| No vision dataset | Vision tier untested | Build `v0_vision_v1.jsonl` Day 4 |
| No latency in CSV | Incomplete comparison | Extend eval runner (Day 7) |
| Claude adapter missing | Can't eval Claude | Add `azure_anthropic.py` after deploy |
| `.env.example` may contain real key | Security | Rotate key in Portal; sanitize example |

---

*Run M1–M6. Fill the table. Pick the model with numbers.*
