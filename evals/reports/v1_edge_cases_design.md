# v1 Edge Cases Dataset — Design Report

**Date:** 2026-09-05  
**Dataset:** `evals/datasets/v1_edge_cases.jsonl` (114 cases)  
**Builder:** `evals/datasets/_build_v1_edge_cases.py` (reproducible generation)  
**Validator:** `evals/datasets/validate_dataset.py`  
**Baseline prompt:** `evals/prompts/classifier_v03.txt` (88% on `v0_challenge`, 0 false allows, 0 false blocks)  
**Prior eval:** `evals/reports/azure_openai_20260905_112326.csv`

---

## Why this dataset exists

`v0_seed` (100 cases) was tuned until the baseline hit 100% — useful for plumbing, useless for science.  
`v0_challenge` (50 cases) exposed generalization gaps (baseline 46%, Azure v03 88%) but is still small and mostly single-surface.

**v1_edge_cases** is the next hardness layer: same-screen / same-app **paired promises** where the only thing that changes is `userGoal`, `commitmentType`, counters, or guardrails. That is exactly how PhoneCodex works in production — not “block YouTube,” but “honor what the user actually promised.”

If a model scores well on v1, it is reasoning about **promise modality**, not memorizing app reputations.

---

## Dataset composition (114 cases)

| Decision | Count |
|----------|------:|
| ALLOW | 47 |
| WARN | 35 |
| BLOCK | 29 |
| LOCK | 3 |

| Commitment type | Count |
|-----------------|------:|
| focus_session | 72 |
| permanent_guardrail | 19 |
| monk_mode | 12 |
| quota_entertainment | 8 |
| time_threshold | 1 |
| emergency_override | 2 |

| App surface (top) | Cases |
|-------------------|------:|
| Chrome | 26 |
| YouTube | 25 |
| WhatsApp | 16 |
| Instagram | 13 |
| Play Store | 12 |
| ChatGPT | 8 |
| Settings | 7 |
| Launcher / Phone | 7 |

**Severity tags** (informal, embedded in `notes` as `[severity:…]` until schema supports a field):

| Level | Count | Meaning |
|-------|------:|---------|
| critical | 12 | Safety / tamper / guardrail override — false ALLOW is unacceptable |
| high | 26 | Clear product boundary (Shorts player, monk, real adult) |
| medium | 58 | Quota, drift nudges, paired screens |
| low | 18 | Benign navigation, launcher, emergency dialer |

---

## Required scenario coverage

### 1. YouTube — long lecture + Shorts shelf (not opened)

**Cases:** `v1_yt_lecture_shelf_001`–`004` (same `screenText`, four promises)

| ID | Promise gist | Expected |
|----|--------------|----------|
| `_001` | Long lectures fine | ALLOW |
| `_002` | Warn if I tap Shorts shelf | WARN |
| `_003` | Zero short-form during exam week | BLOCK |
| `_004` | Monk mode study only | BLOCK |

**Why it matters:** The #1 false-block risk in real usage is punishing a student on a 58-minute lecture because a Shorts row exists below the player. The classifier must separate **foreground activity** from **nearby affordance**.

**v03 weak spot:** `ch_yt_shelf_wording_warn_001` passed on challenge; shelf + drift wording is still the highest-regression cluster when prompts get stricter.

---

### 2. YouTube — actual Shorts player

**Cases:** `v1_yt_shorts_*` (11 player screens)

Includes:
- Study ban → BLOCK (`v1_yt_shorts_study_block_001`)
- **“Allow up to 40 Shorts today”** quota allow/block pair (`quota40_allow` / `quota40_block`)
- Guardrail overrides quota (`quota40_adult_block`)
- Monk block, time-threshold WARN, attempt LOCK
- Guardrail-only allow (`no porn for 1 year; otherwise my choice`)

**Why it matters:** Shorts detection must not depend on the word “Shorts” alone — screens use “vertical swipe feed,” “short-form videos,” etc. Quota promises must read **counters**, not regex “allow N shorts.”

**v03 weak spot:** Generally strong on challenge Shorts variants; quota + adult override is the stress test for **guardrail > entertainment quota** ordering.

---

### 3. Chrome — adult false positives

**Cases:** `v1_ch_false_adult_*` (4)

Examples:
- News headline “adult learners return to college”
- “Mature discussion forum” (topic maturity ≠ age-restricted)
- “shortlisted candidates” (substring trap for “short”)
- Biology “adult stem cells” article

**Why it matters:** Naive keyword classifiers destroy trust. One false BLOCK on a research article and the user uninstalls.

**v03 weak spot:** `ch_chrome_false_adult_mature_discussion_001` and `ch_chrome_shortlisted_trap_allow_001` were **false BLOCK/WARN** on v03 challenge run — this cluster is explicitly expanded in v1.

---

### 4. Chrome — real adult / sexual intent

**Cases:** `v1_ch_real_adult_*` (4)

Examples:
- Age-gate “18+ verify”
- Explicit streaming landing
- Search results for porn intent
- Dating/hookup site under `no_adult_content` guardrail

**Expected:** BLOCK + `adult_content` (guardrail wins even when userGoal is permissive on other content).

**v03 weak spot:** Strong on challenge; v1 adds wording variants without seed tokens from v0.

---

### 5. WhatsApp — useful vs distracting

**Cases:** 16 (`v1_wa_*`)

Pairs include:
- Lab partner PDF schedule → ALLOW vs tea gossip → WARN (same app, different chat)
- Family pickup ALLOW under locked revision
- Meme forward chain → BLOCK under monk (v03 missed: `ch_wa_meme_monk_block` → WARN)
- Incomplete preview → WARN
- Useful chat under monk → WARN (friction, not BLOCK)

**Why it matters:** WhatsApp is never “bad app.” The model must read **message content + promise strictness**, not package name.

---

### 6. Instagram — DM useful vs Reels/feed

**Cases:** 13 (`v1_ig_*`)

Includes:
- Reels tab active → BLOCK under focus
- Quota clips allow (counter-driven)
- Feed with “reel” thumbnail word but not in player → ALLOW
- DM about group project → WARN (social friction during narrow promise)
- Story tray / explore grid variants

**v03 weak spot:** `ch_ig_dm_project_allow_001` expected WARN, got ALLOW — social-channel friction during narrow promises.

---

### 7. Settings — safe browse vs PhoneCodex tamper

**Cases:** `v1_set_*`

- Wi‑Fi / display brightness browse → WARN (neutral detour)
- Accessibility list “checking PhoneCodex status” → WARN (v03: ALLOW on `ch_set_a11y_list`)
- **Stop overlay / force-stop / uninstall PhoneCodex** → LOCK (`v1_set_tamper_lock_*`)

**Why it matters:** LOCK is rare but safety-critical. Confusing settings browse with tamper is a product killer.

---

### 8. Play Store — productivity vs entertainment/adult/dating

**Cases:** 12 (`v1_ps_*`)

- Anki / Notion / Forest → ALLOW (`install_page_productivity`)
- TikTok / BGMI → BLOCK under vertical-video or gaming ban
- Tinder / adult game → BLOCK under `no_adult_content`
- TikTok listing → ALLOW under guardrail-only (“no porn for 1 year”)

**Why it matters:** Install gate is a different commitment type (`install_gate`). Same store UI, opposite outcomes.

---

### 9. Quota promises — “allow 40 Shorts”

**Cases:** 6 explicit `40 Shorts` wordings across YouTube + Instagram quota pairs.

Uses `sessionCounters.shorthsWatched` / `shortsLimit` and `limitState` — not prompt regex.

---

### 10. Permanent guardrail — “no porn for 1 year”

**Cases:** 19 `permanent_guardrail` commitment rows.

Pattern: userGoal says “no porn / no adult; otherwise my choice” → entertainment surfaces ALLOW unless explicit adult signal.

---

### 11. Monk mode promises

**Cases:** 13 monk-related rows across YouTube Shorts, WhatsApp memes, ChatGPT roleplay, Instagram Reels.

Monk = **zero entertainment / laser focus**, not merely “no Shorts.” Expect BLOCK for active fun content, WARN for borderline useful social.

---

## Design patterns used

### Paired-screen methodology

Same `screenText` (or minimal variant) with 2–4 different `userGoal` strings.  
Forces the eval to measure **promise parsing**, not OCR novelty.

Examples:
- `v1_yt_lecture_shelf_001`–`004`
- `v1_yt_shorts_quota40_allow` / `quota40_block`
- `v1_ch_movie_guardrail_allow` vs `ch_movie_edu_block` (same movie site)

### Anti-memorization wording

Deliberately avoids v0 seed phrases (“shorts shelf,” “r/memes,” “turn off PhoneCodex”) so prompt edits cannot cheat via token lists.

### Counter-grounded limits

Quota and time cases always ship `sessionCounters` + `limitState` so the model must use structured state, not count mentions in `userGoal`.

---

## Expected weak spots (hypothesis for v03 on v1)

Based on v0_challenge failures and v1 cluster design:

| Cluster | Risk | Metric to watch |
|---------|------|-----------------|
| Chrome false adult / substring | False BLOCK or WARN | `falseBlock` |
| Instagram DM / useful social | WARN → ALLOW | accuracy on WARN rows |
| Monk + WhatsApp memes | BLOCK → WARN | `falseAllow` adjacent |
| Settings browse vs tamper | WARN ↔ ALLOW confusion | LOCK must stay 100% |
| Shelf visible + strict ban | ALLOW → BLOCK overreach | `falseBlock` |
| Quota exhausted wording | BLOCK → ALLOW | `falseAllow` on quota_block rows |
| Guardrail + permissive goal | Adult miss | `falseAllow` on `severity:critical` |

**Target bar for v1 (suggested, not yet run):**

| Metric | v0_challenge (v03) | v1 goal |
|--------|-------------------|---------|
| Accuracy | 88% | ≥75% (harder set) |
| False allows | 0 | 0 |
| False blocks | 0 | ≤3 |

Accuracy will drop — that is intentional. The gap between seed/challenge/v1 is the scientific signal.

---

## How this helps Azure model comparison

Run the same dataset across deployments (`pc-lab-cheap`, `pc-lab-strong`, `pc-lab-vision`):

```bash
py -3.12 evals/runner/run_eval.py \
  --dataset evals/datasets/v1_edge_cases.jsonl \
  --adapter azure_openai \
  --prompt evals/prompts/classifier_v03.txt
```

Compare reports on:

1. **Overall accuracy** — general reasoning
2. **False allows / false blocks** — safety-weighted (false allows dominate)
3. **Per-cluster accuracy** — filter CSV by `id` prefix (`v1_ch_false_adult`, `v1_set_tamper`, etc.)
4. **Severity-weighted score** (manual until schema field exists):

   ```
   score = 1.0 * correct
         - 5.0 * falseAllow_on_critical
         - 2.0 * falseBlock_on_medium
   ```

5. **Paired-screen consistency** — for lecture shelf quartet, does the model flip decisions monotonically (ALLOW < WARN < BLOCK) as strictness increases?

Cheap vs strong model may tie on v0_challenge but diverge on v1 paired promises — that is the comparison we actually care about for production.

---

## Mapping to product goal

```
User speaks promise → NLU + PolicyEngine → classifier advises ALLOW/WARN/BLOCK/LOCK
                              ↑
                    v1_edge_cases tests this arrow
```

| Product requirement | v1 test |
|--------------------|---------|
| “Long lectures OK, don’t punish shelf” | `v1_yt_lecture_shelf_001` |
| “40 Shorts then stop” | quota pairs + counters |
| “No porn for a year” | guardrail rows |
| “Monk mode until exam” | monk rows across apps |
| “Warn me if I drift” | WARN rows with `ambiguous` |
| “Don’t let me disable the app” | LOCK tamper rows |
| Useful WhatsApp / distracting WhatsApp | `v1_wa_*` pairs |

A classifier that passes v1 reliably is one we can ship behind PolicyEngine without embarrassing false blocks on study content or false allows on adult/tamper surfaces.

---

## Schema validation

```bash
python evals/datasets/validate_dataset.py
```

Result (2026-09-05):

```
OK: v0_seed.jsonl (100 cases, 0 errors)
OK: v0_challenge.jsonl (50 cases, 0 errors)
OK: v1_edge_cases.jsonl (114 cases, 0 errors)
```

Validator checks: required fields, enum values, unique IDs, no extra keys (`additionalProperties: false`).

---

## Proposed schema change (report only — do not apply yet)

Current schema (`evals/datasets/schema.json`) has `additionalProperties: false` and **no severity field**. Severity is temporarily encoded in `notes` as `[severity:level]`.

**Proposed additions** (v2 schema, backward-compatible for runner if fields optional):

```json
"severityLevel": {
  "type": "string",
  "enum": ["critical", "high", "medium", "low"],
  "description": "Weight for false-allow/false-block in aggregate scoring."
},
"failureCluster": {
  "type": "string",
  "description": "Stable slug for grouping regressions (e.g. yt_shelf_paired, ch_false_adult)."
},
"pairedGroupId": {
  "type": "string",
  "description": "Links same-screen cases that differ only by promise."
}
```

**Why not added now:** Runner and CSV export do not consume these fields yet. Adding them requires updating `schema.json`, validator, and optionally `run_eval.py` aggregations. Dataset ships with informal severity in `notes` to avoid breaking the runner.

**Migration path:**
1. Add optional fields to schema
2. Extend `validate_dataset.py`
3. Teach `run_eval.py` to emit cluster + severity breakdown CSV
4. Strip `[severity:…]` prefix from notes when backfilling

---

## Files touched (evals only)

| File | Action |
|------|--------|
| `evals/datasets/v1_edge_cases.jsonl` | Created (114 cases) |
| `evals/datasets/_build_v1_edge_cases.py` | Created (generator) |
| `evals/datasets/validate_dataset.py` | Created (stdlib validator) |
| `evals/reports/v1_edge_cases_design.md` | This report |

**Not touched:** `app/**`, `backend/**`, Android, Azure deployments.

---

## Recommended next eval commands

```bash
# Establish v1 baseline (rule-based)
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v1_edge_cases.jsonl --adapter baseline

# Azure v03 on cheap vs strong
set AZURE_OPENAI_DEPLOYMENT=pc-lab-cheap
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v1_edge_cases.jsonl --adapter azure_openai --prompt evals/prompts/classifier_v03.txt

set AZURE_OPENAI_DEPLOYMENT=pc-lab-strong
py -3.12 evals/runner/run_eval.py --dataset evals/datasets/v1_edge_cases.jsonl --adapter azure_openai --prompt evals/prompts/classifier_v03.txt
```

Compare false allows first. Accuracy second.
