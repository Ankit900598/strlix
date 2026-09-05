# Baseline Classifier Generalization Review

**Date:** 2026-09-05  
**Reviewer stance:** Senior ML eval engineer  
**Artifacts:** `evals/runner/baseline_classifier.py`, `evals/datasets/v0_seed.jsonl`, `evals/datasets/v0_challenge.jsonl`

## Executive summary

The commitment-aware baseline scores **100% on `v0_seed`** but **46% on `v0_challenge`** (23/50). That 54-point gap is not noise — it is evidence of **dataset-specific overfitting** through shared phrasing between labels and keyword rules.

**Do not treat 100% seed accuracy as product readiness.** Use seed for regression on known teaching cases; use challenge (and future held-out sets) for generalization.

| Dataset | Accuracy | False allows | False blocks | Cases |
|---------|----------|--------------|--------------|-------|
| `v0_seed` | 100.0% (100/100) | 0 | 0 | 100 |
| `v0_challenge` | 46.0% (23/50) | 1 | 0 | 50 |

Commands:

```bash
python evals/runner/run_eval.py --dataset evals/datasets/v0_seed.jsonl --adapter baseline
python evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter baseline
```

Latest challenge report: `evals/reports/baseline_20260905_043252.csv`

---

## What logic is robust

These patterns generalize because they use **structured fields** more than screen prose:

| Mechanism | Why it travels |
|-----------|----------------|
| `commitmentType` + `limitState` + `sessionCounters` | Quota/time/lock paths fire when `in_shorts_player` / `in_reels_player` is already true — logic is sound, detection is not |
| `activeGuardrails: no_adult_content` + explicit age-gate text (`18+`, `explicit`, `verify you are 18+`) | Adult override on quota works on challenge (`ch_yt_adult_quota_real_block_001`, `ch_chrome_real_adult_block_001`) |
| `commitmentType: monk_mode` + entertainment tokens in screen | Blocks via `entertainment_foreground` even when Shorts UI wording changes (`ch_yt_monk_laser_focus_block_001`) |
| `commitmentType: emergency_override` | SOS / in-call flows largely independent of phrasing (when package is whitelisted) |
| Guardrail-only ALLOW on non-adult entertainment pages | Works when promise matches seed phrases (`block porn only`) — see brittleness below |
| Paired-case *architecture* (promise-first pipeline) | Correct product shape; implementation is keyword-heavy |

---

## What logic is brittle

### 1. Short-form player detection is seed-scripted

```python
# baseline_classifier.py — _is_shorts_player / _is_reels_player
"vertical swipe feed", lowered.startswith("shorts"), "for you", "swipe up"
```

`v0_seed` uses `"Shorts\nVertical swipe feed"`. Challenge uses `"Short-form videos\nFeed\nSwipe ↑"` → **player not detected**, quota/time/monk branches never run → default **WARN**.

**7 challenge failures** directly from this.

### 2. `parse_promise()` is a phrase checklist

| Intent | Seed phrase | Challenge wording | Result |
|--------|-------------|-------------------|--------|
| Quota | `Allow up to 40 Shorts` | `daily budget of 25 vertical clips` | Regex misses → quota logic skipped |
| Monk | `Monk mode` | `Laser focus: no fun content` | Saved only when `commitmentType==monk_mode` |
| Lock attempts | `lock after 3 attempts` | `freeze session after 3 tries` | Regex misses → LOCK never fires |
| Study session | `Study DSA` | `Finish assignment before sleep` | `allows_study_tools` false unless `assignment` heuristics hit |
| Guardrail-only | `Only permanent guardrail` | `Block porn only — everything else is my call` | Partial match via `only block adult` |

Rules mirror **exact dataset vocabulary**, not user intent.

### 3. Screen profiles are token bags tuned to seed

- **Study:** `lecture`, `merge sort`, `stack overflow` (with space — fails on `StackOverflow`)
- **Academic WhatsApp:** `study group`, `assignment pdf` — misses `Lab partner`, `Protocol steps`
- **Family:** `mom`, `dad` — misses `Parent`
- **ChatGPT coding:** `implement`, `debug` — misses `kotlin NPE on line 42`
- **ChatGPT fun:** `joke`, `funny story` — misses `make me laugh`
- **Movie sites:** `watch latest movies`, `free hd` — misses `watchfreefilms.net`
- **Install gate:** requires `"install"` in text — misses Play Store `Get` button copy

### 4. Per-package handler cascade + default WARN

Most challenge misses end as:

> No strong allow or block signal relative to promise

That is a **27-case WARN collapse**: the baseline prefers ambiguous WARN over wrong BLOCK, but eval treats WARN≠ALLOW/BLOCK/LOCK as incorrect. Structurally, unknown screens converge to the same prediction.

### 5. Guardrail-only false allow (dangerous)

`ch_ps_tinder_guardrail_block_001`: promise `Block porn only — everything else is my call` triggers `guardrail_only`, Tinder install has no `dating` keyword → **ALLOW** instead of **BLOCK**.

Dating/adult policy belongs partly in **PolicyEngine guardrail catalog**, not keyword `dating in lowered`.

### 6. Substring traps not modeled

- `shortlisted` contains `short` — no rule, but shows fragility if substring rules are added naively
- `#shorts` in comments — no positive rule for “mention ≠ viewing”; lecture path fails without `lecture` token

### 7. Package whitelist holes

`SAFE_PACKAGES` lists three dialer packages. `com.samsung.android.dialer` relies on `emergency_override` commitment type, not package — fragile for normal calls.

---

## What makes `v0_seed` too easy

1. **Template screen text** — repeated `Shorts\nVertical swipe feed\nPrank compilation` across 15+ cases; classifier detects player once, varies only promise fields.
2. **Template promise text** — `Study DSA`, `Monk mode`, `Allow up to N Shorts` align with regexes and token lists.
3. **Explicit disambiguators** — `Browsing only`, `No PhoneCodex toggle`, `not opened` exist solely to steer keyword rules.
4. **Single app handlers** — YouTube/Chrome/WhatsApp/ChatGPT branches match seed vocabulary in `screenText` and `userGoal` jointly.
5. **No incomplete OCR** — almost every row is clean newline-separated labels.
6. **Paired cases teach the harness** — same screen string repeated; baseline can pass without semantic understanding.
7. **100% is a red flag** — in real classification, perfect in-domain keyword match usually means label leakage or memorization.

---

## Hidden-style cases that break the baseline (from `v0_challenge`)

| Case ID | Break mechanism |
|---------|-----------------|
| `ch_yt_shorts_ui_variant_*` | UI copy change → no player → WARN instead of ALLOW/BLOCK/LOCK |
| `ch_yt_comment_shorts_mention_allow_001` | `#shorts` in comments; no lecture token |
| `ch_yt_shelf_wording_allow_001` | `micro-clips carousel` not `shorts shelf` |
| `ch_yt_attempt_lock_wording_001` | `freeze session after 3 tries` not in lock regex |
| `ch_ig_reels_tab_wording_block_001` | `IG Reels\nDiscover` not `for you` / `swipe up` |
| `ch_chrome_movie_wording_block_001` | Movie site without seed movie phrases |
| `ch_chrome_false_adult_learners_001` | Correctly ALLOW — baseline passes |
| `ch_chrome_false_adult_mature_discussion_001` | Philosophy “mature discussion” → WARN (no study tokens in screen) |
| `ch_chrome_so_with_meme_ad_allow_001` | `StackOverflow` ≠ `stack overflow` token |
| `ch_ps_tinder_guardrail_block_001` | **False allow** — guardrail-only too broad |
| `ch_set_tamper_wording_lock_001` | `Stop overlay service` not in tamper phrase list |
| `ch_phone_samsung_dialer_allow_001` | Non-whitelisted dialer package |
| `ch_gpt_*` | Paraphrased prompts bypass assistant token lists |

---

## Policy vs classifier vs AI model

| Responsibility | Should handle | Examples |
|----------------|---------------|----------|
| **PolicyEngine (Kotlin)** | Deterministic law: guardrail IDs, quota counters, time limits, LOCK after N attempts, tamper on known PhoneCodex disable flows | `limitState: reached` → BLOCK regardless of classifier; `no_adult_content` on catalogued domains; attempt counter LOCK |
| **Classifier (AI advisor)** | Semantic screen understanding under promise context | Short-form **viewing** vs mention; study vs entertainment paraphrase; incomplete OCR; messy accessibility text |
| **Keyword baseline (eval only)** | Cheap regression floor, adapter comparison | Must not ship as product classifier; useful to prove Azure adds value |

The baseline currently **blurs policy and classification** — e.g. it implements quota math (policy) but only after keyword player detection (classification).

**Recommended split for production:**

- Classifier outputs: `{ activityType, contentCategory, confidence, signals[] }`
- PolicyEngine maps activity + promise + counters → ALLOW/WARN/BLOCK/LOCK

---

## Top 10 failure types on `v0_challenge`

Ranked by frequency in the 27 misses:

| # | Failure type | Count | Severity | Example IDs |
|---|--------------|-------|----------|-------------|
| 1 | Short-form player UI variant not detected → default WARN | 7 | High | `ch_yt_shorts_ui_variant_*`, `ch_ig_reels_*`, `ch_yt_attempt_lock_wording_001` |
| 2 | Study/academic paraphrase — no token match | 8 | Medium | `ch_yt_comment_shorts_*`, `ch_chrome_compsci_*`, `ch_chrome_so_with_meme_ad_*`, `ch_home_study_*` |
| 3 | ChatGPT prompt paraphrase — falls to WARN | 4 | Medium | `ch_gpt_kotlin_*`, `ch_gpt_laugh_*`, `ch_gpt_eigenvalues_*` |
| 4 | WhatsApp social/academic phrase list miss | 3 | Medium | `ch_wa_lab_partner_*`, `ch_wa_parent_*`, `ch_wa_meme_monk_*` |
| 5 | Promise wording not in regex/checklist | 3 | High | quota `vertical clips`, lock `freeze session after 3 tries` |
| 6 | Play Store copy variant (`Get` not `Install`) | 2 | Medium | `ch_ps_tiktok_*`, `ch_ps_spanish_*` |
| 7 | Guardrail-only over-ALLOW (dating) | 1 | **Critical** | `ch_ps_tinder_guardrail_block_001` |
| 8 | Tamper phrase variant | 1 | **Critical** | `ch_set_tamper_wording_lock_001` |
| 9 | Movie/entertainment site paraphrase | 1 | Medium | `ch_chrome_movie_wording_block_001` |
| 10 | False adult / ambiguous mature language | 1 | Low | `ch_chrome_false_adult_mature_discussion_001` |

**Note:** 26/27 failures are WARN (under-block or wrong friction). One false allow on dating install is the only dangerous miss direction.

---

## What Azure model should be tested on first

Priority order for first Azure OpenAI eval spend:

1. **Short-form disambiguation** — player vs shelf vs comment vs hashtag (`v0_challenge` YouTube/IG rows). Highest product risk; seed gives false confidence.
2. **Promise-relative paraphrase** — same commitment intent, new wording (quota, monk, lock, edu-only). Tests whether the model reads `userGoal` semantically.
3. **False adult traps** — `adult learners`, `mature discussion`, news headlines vs real age gates. Measure false BLOCK rate separately.
4. **ChatGPT / assistant intent** — coding vs entertainment vs roleplay under same app package.
5. **Incomplete / messy OCR** — `…loading…`, `3 unread`, `about:blank`. Expect WARN-heavy; compare to baseline WARN collapse.
6. **Tamper vs benign settings** — LOCK precision is safety-critical; run with `strictnessLevel: LOCKED` subset only.

**First Azure run command (when wired):**

```bash
python evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai
```

**Success criteria for Azure vs baseline:** beat 46% overall, **zero false allows** on adult/dating/tamper subset, false blocks on study-aligned ≤ baseline.

---

## Recommendations (do not fix by adding seed phrases)

1. **Stop expanding keyword lists to chase seed accuracy** — each new phrase is another overfit vector.
2. **Report two metrics always:** `v0_seed` (regression) + `v0_challenge` (generalization).
3. **Add `v1` held-out** written by someone who did not author baseline rules.
4. **Move counters/limits/tamper thresholds to policy simulator tests** — classify activity, let policy decide.
5. **Wire Azure adapter on challenge first** — if model cannot beat 46%, prompt/model work precedes Android integration.

---

## Verdict

The baseline is a **useful eval harness artifact**, not a generalizable classifier. `v0_seed` 100% is an expected artifact of co-designed labels and rules. `v0_challenge` 46% is the honest number for stakeholder conversations and Azure ROI justification.
