# v1 Edge Cases — Model Comparison Summary

**Date:** 2026-09-05  
**Dataset:** `evals/datasets/v1_edge_cases.jsonl` (114 cases)  
**Prompt:** `evals/prompts/classifier_v03.txt`  
**Runner:** `evals/runner/run_eval.py` with `--deployment` + per-case `latencyMs`

---

## Executive summary

v1_edge_cases is **harder than v0_challenge** by design. On v03:

| Deployment | Model | Accuracy | False allows | False blocks | Total latency | Avg/case |
|------------|-------|----------|--------------|--------------|---------------|----------|
| **pc-lab-cheap** | gpt-4.1-mini | **84.2%** (96/114) | **2** | **5** | 201s | 1766ms |
| **pc-lab-strong** | gpt-4.1 | **89.5%** (102/114) | **1** | **0** | 213s | 1867ms |
| **pc-lab-vision** | gpt-4o | **89.5%** (102/114) | **2** | **0** | 216s | 1891ms |

**Reference (v0_challenge, v03, cheap):** 88.0%, 0 FA, 0 FB — `azure_openai_20260905_112326.csv`

v1 dropped cheap accuracy **−3.8pp** vs challenge but exposed **7 safety/UX failures** (FA+FB) that challenge hid. Strong/vision tie on accuracy; cheap is **not** safe enough alone on v1.

---

## Reports generated

| Run | CSV | Meta |
|-----|-----|------|
| v03 + cheap + v1 | `azure_openai_pc-lab-cheap_classifier_v03_v1_edge_cases_20260905_115205.csv` | `.meta.json` sibling |
| v03 + strong + v1 | `azure_openai_pc-lab-strong_classifier_v03_v1_edge_cases_20260905_115554.csv` | |
| v03 + vision + v1 | `azure_openai_pc-lab-vision_classifier_v03_v1_edge_cases_20260905_115949.csv` | |

Re-run command:

```bash
py -3.12 evals/runner/run_eval.py \
  --dataset evals/datasets/v1_edge_cases.jsonl \
  --adapter azure_openai \
  --prompt evals/prompts/classifier_v03.txt \
  --deployment pc-lab-cheap
```

---

## Failure clusters (v03, all deployments)

Clusters sorted by frequency across **all three runs combined** (same-case failures):

### 1. `yt_lecture_shelf` — **universal weak spot**

| Case | Expected | Cheap | Strong | Vision |
|------|----------|-------|--------|--------|
| `_002` drift nudge promise | WARN | ALLOW | ALLOW | ALLOW |
| `_003` zero short-form ban | BLOCK | **ALLOW (FA)** | WARN | **ALLOW (FA)** |
| `_004` monk study only | BLOCK | **ALLOW (FA)** | **ALLOW (FA)** | **ALLOW (FA)** |

**Root cause:** Models overweight foreground lecture alignment and ignore **absolute short-form ban + visible Shorts shelf** on the same screen. v03 says shelf-not-opened → ALLOW; v1 labels say absolute ban → BLOCK.

**Product risk:** False ALLOW on monk/zero-short-form — user sees Shorts shelf while “protected.”

---

### 2. `set_a11y_list_warn` — settings friction

Expected WARN (neutral detour during LOCKED focus). All three models → **ALLOW**.

**Root cause:** “Not tampering” collapses to ALLOW; v03 under-specifies friction for settings browse during focus.

---

### 3. `wa_flirt_warn` / social boundary

Expected WARN (discouraged flirt). Strong + vision → **BLOCK** (over-enforcement). Cheap → BLOCK too.

**Root cause:** “Exam prep no flirting” read as hard ban not gentle friction.

---

### 4. `extra_*` batch — mixed boundaries

| Pattern | Example | Failure mode |
|---------|---------|--------------|
| Guardrail false positive | `extra_003` IMDb mature themes | Cheap BLOCK (FB) |
| Monk misapplied | `extra_004` Coursera under monk | Cheap BLOCK (FB) |
| Home launcher | `extra_014` clean exam home | Cheap/strong/vision WARN |
| Settings | `extra_019` battery saver | ALLOW vs WARN split |

---

### 5. Cheap-only clusters (strong/vision pass)

| Cluster | Issue |
|---------|-------|
| `yt_shorts_guardrail_allow` | Guardrail-only Shorts → cheap BLOCK (FB) |
| `ch_movie_guardrail_allow` | Free movies under guardrail-only → cheap BLOCK (FB) |
| `yt_shorts_time_warn` | Time threshold → cheap BLOCK (should WARN) |
| `ig_pair_feed_allow` | IG feed without Reels player → cheap BLOCK (FB) |
| `wa_sticker_monk_block` | Monk stickers → cheap WARN (should BLOCK) |

Strong model fixes guardrail and quota interpretation; cheap mini model **confuses guardrail with entertainment ban**.

---

## False allow analysis

**Definition:** expected BLOCK or LOCK, predicted ALLOW.

| Deployment | Count | Cases |
|------------|------:|-------|
| pc-lab-cheap | 2 | `v1_yt_lecture_shelf_003`, `v1_yt_lecture_shelf_004` |
| pc-lab-strong | 1 | `v1_yt_lecture_shelf_004` |
| pc-lab-vision | 2 | `v1_yt_lecture_shelf_003`, `v1_yt_lecture_shelf_004` |

**Severity:** All tagged `[severity:high]` in dataset notes.

**Pattern:** Absolute short-form / monk promise + YouTube with **Shorts shelf visible** + long lecture foreground.

**Why it matters:** This is the core PhoneCodex promise — “monk mode” must not be defeated because foreground looks educational. Shelf visibility is an affordance violation under absolute bans.

**Mitigation (→ v04):** Explicit YouTube shelf rule: absolute ban or monk → BLOCK when shelf/row visible regardless of lecture foreground.

---

## False block analysis

**Definition:** expected ALLOW, predicted BLOCK.

| Deployment | Count | Cases |
|------------|------:|-------|
| pc-lab-cheap | 5 | `guardrail_allow`, `movie_guardrail_allow`, `extra_003`, `extra_004`, `ig_pair_feed_allow` |
| pc-lab-strong | 0 | — |
| pc-lab-vision | 0 | — |

**Patterns:**

1. **Guardrail overreach** — treating all Shorts/movies as adult_content under `no_adult_content` only promise.
2. **Monk overreach** — blocking Coursera (study) as entertainment.
3. **IG feed vs Reels player** — blocking Feed when only Reels player is forbidden.

**Cheap-only:** Strong model already fixes guardrail false blocks; **mini model needs prompt clarity**, not necessarily stronger model.

---

## ALLOW ↔ WARN boundary errors

| Theme | Cases | Typical error |
|-------|-------|---------------|
| Drift nudge promise | `yt_lecture_shelf_002` | ALLOW instead of WARN |
| Social friction | `wa_gossip_warn`, `ig_dm_work_warn` | ALLOW instead of WARN |
| Settings detour | `set_a11y_list`, `set_display`, `set_dev`, `extra_019` | ALLOW instead of WARN |
| Home launcher | `extra_014` | WARN instead of ALLOW (over-friction) |
| Sidebar ads | `ch_so_with_meme_ad` (challenge) | WARN instead of ALLOW |

**Count (v03):** cheap 8 · strong 6 · vision 5

**Insight:** WARN is the hardest decision — requires reading **friction intent** from userGoal, not content alignment alone.

---

## WARN ↔ BLOCK boundary errors

| Theme | Cases | Typical error |
|-------|-------|---------------|
| Discouraged memes/flirt | `ch_meme_warn`, `wa_flirt_warn`, `reddit_meme_warn` | BLOCK instead of WARN |
| Time threshold | `yt_shorts_time_warn` | BLOCK instead of WARN (cheap) |
| Monk stickers | `wa_sticker_monk_block` | WARN instead of BLOCK (cheap) |
| Cheating-adjacent AI | `gpt_cheating_warn` | BLOCK instead of WARN (strong) |

**Count (v03):** cheap 3 · strong 5 · vision 5

**Insight:** Strong/vision **over-block** on “X no / discouraged” language. Cheap **under-blocks** monk spam. Different failure shapes by model tier.

---

## Where cheap model is enough

On **v0_challenge** with v03, cheap already matches strong (88%, 0 FA, 0 FB). Cheap is enough when:

- Dataset size is small and phrasing overlaps seed training patterns
- Failures are WARN boundaries, not safety BLOCK/ALLOW swaps
- Guardrail + quota rules are simple

On **v1**, cheap is **not** enough for production:

- 2 false allows (shelf + monk)
- 5 false blocks (guardrail confusion)
- 10.5pp behind v04-tuned cheap (see v04 recommendation)

**Cheap is enough for:** high-volume prompt iteration smoke tests, regression on v0_seed, cost/latency floor measurement.

---

## Where stronger model helps

| Scenario | Cheap | Strong |
|----------|-------|--------|
| Guardrail-only + Shorts ALLOW | BLOCK (FB) | ALLOW ✓ |
| Guardrail-only + free movies | BLOCK (FB) | ALLOW ✓ |
| IG feed vs Reels player | BLOCK (FB) | ALLOW ✓ |
| Absolute shelf ban | ALLOW (FA) | WARN (better, still FA on _004) |
| Discouraged meme subreddit | WARN ✓ | BLOCK ✗ |

Strong helps **guardrail interpretation** and **install/feed disambiguation** without prompt fixes. It does **not** eliminate shelf false allows — prompt issue, not model issue.

**Latency cost:** +101ms/case avg (+5.7%) — negligible vs safety.

---

## Is vision model useless without screenshots?

**Yes, for current eval pipeline.** All cases pass `screenText` only; no `screenshotPath` fixtures loaded.

| Metric | pc-lab-strong | pc-lab-vision |
|--------|---------------|---------------|
| v03 accuracy | 89.5% | 89.5% |
| v03 false allows | 1 | 2 |
| Avg latency | 1867ms | 1891ms |

Vision (gpt-4o) provides **no accuracy lift** on text-only v1. Same failure clusters. Slightly **worse** false allows (2 vs 1).

**When vision becomes useful:**

- OCR garbled / incomplete `screenText` (loading screens, WebView noise)
- Distinguishing Shorts **player chrome** vs shelf thumbnail visually
- 18+ age gate UI patterns missed by text heuristics
- Eval dataset `v0_vision_v1` with real screenshot fixtures

**Recommendation:** Keep `pc-lab-vision` deployed for Day-4+ multimodal evals. Do **not** route production text-only classify through gpt-4o — higher cost, no gain today.

---

## Production default model recommendation (v03 era)

| Role | Deployment | Rationale |
|------|------------|-----------|
| **Default advisor** | `pc-lab-cheap` + **classifier_v04** | v04 cheap hits 94.7% v1, 0 FA — see v04 report |
| **Escalation** | `pc-lab-strong` + v04 | When confidence < threshold OR PolicyEngine flags ambiguous |
| **Vision** | `pc-lab-vision` | Only when screenshot attached AND OCR confidence low |
| **Do not ship** | v03 + cheap alone on v1 | 2 false allows unacceptable |

**PolicyEngine must still enforce:** counters, guardrails, tamper LOCK — never trust model for quota math or disable detection.

---

## Comparison to v0_challenge (why we needed v1)

| Metric | v0_challenge | v1_edge_cases |
|--------|--------------|---------------|
| Cases | 50 | 114 |
| v03 cheap accuracy | 88% | 84.2% |
| v03 cheap FA | 0 | **2** |
| v03 cheap FB | 0 | **5** |
| Paired-screen tests | Few | Many |
| Guardrail-only ent. | Some | Stress-tested |
| Monk + shelf | Limited | Core cluster |

v0_challenge gave **false confidence**. v1 is the first dataset that matches production risk.

---

## Next steps

1. Ship **classifier_v04** as default prompt (Phase 5 complete).
2. Re-run v04 on v0_challenge + v0_seed for regression tracking.
3. Build **v2_live_ocr** dataset with noisy/incomplete screenText.
4. Add screenshot fixtures → unlock vision eval meaningfully.
5. Add `severityLevel` to schema for weighted scoring.

---

*Analyzer: `evals/runner/analyze_report.py`*  
*Related: `evals/reports/classifier_v04_recommendation.md`, `evals/reports/v1_edge_cases_design.md`*
