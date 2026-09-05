# Classifier v04 — Recommendation

**Date:** 2026-09-05  
**Prompt:** `evals/prompts/classifier_v04.txt`  
**Prior:** `classifier_v03.txt`  
**Design basis:** v1_edge_cases v03 failures across all three Azure deployments

---

## 1. Did v04 beat v03 on v1_edge_cases?

**Yes — decisively on cheap; modestly on strong/vision.**

| Deployment | v03 accuracy | v04 accuracy | Δ | v03 FA→FB | v04 FA→FB |
|------------|-------------|-------------|---|-----------|-----------|
| **pc-lab-cheap** | 84.2% (96/114) | **94.7% (108/114)** | **+10.5pp** | 2 / 5 | **0 / 1** |
| pc-lab-strong | 89.5% (102/114) | 90.4% (103/114) | +0.9pp | 1 / 0 | 0 / 0 |
| pc-lab-vision | 89.5% (102/114) | 91.2% (104/114) | +1.7pp | 2 / 0 | 0 / 0 |

**Reports:**

| Run | CSV |
|-----|-----|
| v04 cheap v1 | `azure_openai_pc-lab-cheap_classifier_v04_v1_edge_cases_20260905_120442.csv` |
| v04 strong v1 | `azure_openai_pc-lab-strong_classifier_v04_v1_edge_cases_20260905_120824.csv` |
| v04 vision v1 | `azure_openai_pc-lab-vision_classifier_v04_v1_edge_cases_20260905_121219.csv` |

**What v04 fixed (cheap):**

- `yt_lecture_shelf_003/004` — absolute ban + shelf → BLOCK (eliminated false allows)
- `yt_shorts_guardrail_allow`, `ch_movie_guardrail_allow` — guardrail-only entertainment → ALLOW
- `yt_shorts_time_warn` — time threshold → WARN
- `extra_003/004` — false adult + Coursera monk → ALLOW
- `ig_pair_feed_allow` — feed without Reels player → ALLOW
- `wa_sticker_monk_block` — monk stickers → BLOCK

**v04 change philosophy:** Targeted rules from v1 failure clusters — not longer for its own sake. Same line count ballpark as v03; restructured guardrail, shelf, monk, and time-threshold sections.

---

## 2. Did false allows remain controlled?

**Yes.**

| Prompt | cheap FA | strong FA | vision FA |
|--------|----------|-----------|-----------|
| v03 | 2 | 1 | 2 |
| v04 | **0** | **0** | **0** |

Zero false allows across all deployments on v1 with v04. This meets the shipping bar for advisor prompts on the expanded dataset.

**Remaining risk (not false allows):** WARN↔BLOCK over-enforcement on discouraged memes/flirt (strong/vision still BLOCK when WARN expected) — UX friction, not safety hole.

---

## 3. Did false blocks reduce?

**Yes on cheap; already zero on strong/vision.**

| Prompt | cheap FB | strong FB | vision FB |
|--------|----------|-----------|-----------|
| v03 | 5 | 0 | 0 |
| v04 | **1** | 0 | 0 |

**Remaining cheap false block:** `v1_ps_tiktok_guardrail_allow_001` — TikTok install page under guardrail-only promise. Model still maps TikTok → adult. v04 rule says guardrail-only + non-adult entertainment app → ALLOW; mini model occasionally disobeying.

**Fix path:** PolicyEngine install_gate should ALLOW non-adult apps under guardrail-only without cloud call — see §7.

---

## 4. Which deployment should Android/backend use now?

| Layer | Choice | Config |
|-------|--------|--------|
| **Default cloud classify** | `pc-lab-cheap` | `--deployment pc-lab-cheap` + `classifier_v04.txt` |
| **Escalation path** | `pc-lab-strong` | When `confidence < 0.85` OR decision is BLOCK with `reasonCategory=ambiguous` |
| **Vision path** | `pc-lab-vision` | Defer until screenshot pipeline ships |
| **Prompt version** | **v04** | Replace v03 in all eval + staging |

**Economics (114-case run):**

| Deployment | Avg latency | Est. cost tier |
|------------|-------------|----------------|
| cheap | ~1920ms | $ |
| strong | ~1770ms | $$ |
| vision | ~1944ms | $$ |

Default to cheap + v04. Escalate ~10–15% of ambiguous cases to strong (estimate — implement AiConfidenceGate next).

**Backend `/classify` stub should accept:**

```json
{
  "promptVersion": "v04",
  "deployment": "pc-lab-cheap",
  "escalationDeployment": "pc-lab-strong"
}
```

Do not hardcode in Android — fetch from remote config when backend exists.

---

## 5. v0_challenge regression check

| Prompt | Dataset | Accuracy | FA | FB |
|--------|---------|----------|----|----|
| v03 | v0_challenge | **88.0%** | 0 | 0 |
| v04 | v0_challenge | 84.0% | 0 | 0 |

**Tradeoff:** v04 gains +10.5pp on v1 but loses **−4pp** on v0_challenge (cheap).

**v04 challenge failures (8):** mostly WARN boundary — IG DM friction, settings a11y, SO meme sidebar, monk useful WA, mature discussion, shortlisted trap.

**Verdict:** Acceptable trade for now. v1 is closer to production risk. Next prompt iteration (v04.1) should recover challenge WARN cases without reopening shelf false allows.

---

## 6. Remaining dataset weaknesses

| Gap | Why it matters |
|-----|----------------|
| **No real screenshots** | Vision deployment untested meaningfully |
| **Clean screenText** | Live OCR noise not simulated enough (`v1_yt_loading_warn` is one case) |
| **English-only** | Hindi/Hinglish promises untested |
| **Single-turn** | No session sequence (opened Shorts after lecture) |
| **PolicyEngine not in loop** | Eval tests classifier alone; merge bugs invisible |
| **Paired labels debatable** | `yt_lecture_shelf_003` BLOCK while lecture plays — product must confirm UX intent |
| **`extra_*` batch** | 20 generic cases — good fuzz, less curated than core clusters |
| **No latency SLA cases** | Slow network / timeout behavior not labeled |

---

## 7. What next dataset should be built?

**Priority: `v2_noisy_ocr.jsonl` (80–120 cases)**

Sample from:

- Truncated accessibility trees (max 200 chars)
- Missing appLabel / garbled package hints
- WebView "about:blank", "Loading…", cookie banners obscuring content
- Hindi userGoal + English screenText
- **Session pairs:** case A lecture ALLOW → case B same user opened Shorts → BLOCK

**Second: `v0_vision_v1.jsonl` (30–50 cases)**

- Attach `screenshotPath` to Shorts player vs shelf vs false adult Chrome
- Run only on `pc-lab-vision`
- Measure lift over text-only on same case IDs

**Third: `v1_policy_merge.jsonl`**

- Same screen + conflicting signals (AI says ALLOW, counter says limit reached)
- Expected decision = **PolicyEngine output**, not raw classifier — tests integration

---

## 8. What app behavior should NOT depend on AI?

These must be **deterministic in PolicyEngine / Android** — never delegated to LLM:

| Behavior | Why |
|----------|-----|
| **Quota counters** (12/40 Shorts) | Math must be exact; AI reads counters, never counts |
| **Tamper → LOCK** | Disable overlay / force-stop / uninstall attempt — pattern match + LOCKED flag |
| **Emergency ALLOW** | Phone, SOS, 112 — hard override, no API call |
| **Permanent guardrail catalog** | `no_adult_content` id → rule exists before AI |
| **Attempt lock after N tries** | `attemptCount` threshold — structural |
| **Time-based block schedule** | User-set quiet hours — cron, not LLM |
| **Recovery World entry** | Failure streak counter — local state |
| **Family whitelist packages** | If user pins "always allow Mom WhatsApp" — local rule |
| **Install block list** | Dating apps under guardrail — can short-circuit before AI |
| **Confidence gate** | Low confidence → WARN only, never auto-BLOCK in v1 product |
| **Logging / telemetry** | No AI decision on what to upload — user consent flags |

**AI should only advise on:** ambiguous screen interpretation, WARN vs ALLOW friction, reason string for Decision Inspector.

**Product rule:** `finalDecision = merge(policyRules, aiAdvice, confidenceGate)` — if AI unavailable, degrade to WARN + local rules, not silent ALLOW on known bad surfaces.

---

## Decision

| Question | Answer |
|----------|--------|
| Ship v04? | **Yes** — default prompt for eval + staging |
| Ship cheap alone? | **Yes** with v04 + escalation to strong on low confidence |
| Ship vision? | **Not yet** — no screenshot pipeline |
| Ship v03? | **Retire** on v1 evidence |

---

*Prompt: `evals/prompts/classifier_v04.txt`*  
*Comparison: `evals/reports/v1_model_comparison_summary.md`*  
*Run: `py -3.12 evals/runner/run_eval.py --deployment pc-lab-cheap --prompt evals/prompts/classifier_v04.txt --dataset evals/datasets/v1_edge_cases.jsonl`*
