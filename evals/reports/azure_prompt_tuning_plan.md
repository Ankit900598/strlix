# Azure Prompt Tuning Plan

**Date:** 2026-09-05  
**Baseline prompt:** `evals/prompts/classifier_v01.txt`  
**Proposed prompt:** `evals/prompts/classifier_v02.txt`  
**Latest eval:** `evals/reports/azure_openai_20260905_074500.csv`  
**Dataset:** `evals/datasets/v0_challenge.jsonl` (50 cases)

## Current metrics (v01 + Azure)

| Metric | Value |
|--------|-------|
| Accuracy | 74% (37/50) |
| False allows | **0** |
| False blocks | **3** |
| Other misses | 10 (wrong decision, not safety-critical direction) |

**Priority:** Fix the 3 false blocks first (ALLOW expected → BLOCK predicted). They are user-trust killers. Keep false allows at zero.

---

## Failure clusters (latest Azure eval)

### Cluster A — False blocks (3) — **P0**

| Case ID | Screen | Promise | Got | Root cause |
|---------|--------|---------|-----|------------|
| `ch_chrome_movie_guardrail_allow_001` | Free movie streaming site | Guardrail-only: block porn, user chooses rest | BLOCK (`adult_content`) | Model treats any streaming site as adult under `no_adult_content` |
| `ch_chrome_false_adult_mature_discussion_001` | Philosophy forum “mature discussion” | Research/docs only tonight | BLOCK (`study_aligned` misapplied) | “Mature” read as adult guardrail or strict off-goal block |
| `ch_chrome_shortlisted_trap_allow_001` | Gmail internship shortlist email | Research/docs only tonight | BLOCK (`study_aligned` inverted) | Narrow edu promise interpreted as “block everything except PDFs” |

**Pattern:** v01 says “BLOCK only when promise clearly forbids” but gives no guardrails against **over-interpreting** narrow goals. Model defaults to BLOCK when content is not literally a research paper.

### Cluster B — Over-block (WARN expected → BLOCK) — **P1**

| Case ID | Issue |
|---------|-------|
| `ch_yt_loading_incomplete_warn_001` | `…loading…` on YouTube → BLOCK (assumed vertical feed) |
| `ch_gpt_laugh_study_warn_001` | Comedy prompt during study → BLOCK (should be friction WARN) |
| `ch_chrome_compsci_meme_warn_001` | Meme sub when “memes no” → BLOCK (promise asks friction, not hard ban) |

**Pattern:** BLOCK used as “off-goal” hammer. v01 does not separate **clear violation** from **drift risk**.

### Cluster C — Over-lock (WARN expected → LOCK) — **P1**

| Case ID | Issue |
|---------|-------|
| `ch_set_a11y_list_warn_001` | Browsing accessibility list where PhoneCodex is listed → LOCK |

**Pattern:** v01 LOCK rule is one line; model treats **visibility of PhoneCodex** as tamper, not **active disable attempt**.

### Cluster D — Under-warn (WARN expected → ALLOW) — **P2**

| Case ID | Context |
|---------|---------|
| `ch_home_messy_icons_warn_001` | Distracting icons on launcher |
| `ch_set_wifi_normal_warn_001` | Wi‑Fi settings during study |
| `ch_wa_incomplete_warn_001` | `3 unread` preview |
| `ch_chrome_incomplete_tab_warn_001` | `about:blank` |
| `ch_wa_useful_monk_warn_001` | Academic WA under monk (should be friction) |
| `ch_ig_dm_project_allow_001` | Social DM with work context |

**Pattern:** Model ALLOWs neutral/system surfaces. Aligns with product goal (“do not over-block home/settings/WhatsApp/blank browser”). Some are label vs product tension — v02 should WARN on **drift risk** without BLOCKing.

---

## Exact prompt weaknesses in v01

1. **No decision ladder.** ALLOW, WARN, BLOCK, LOCK listed but not defined. Model fills gap with “strict = BLOCK”.
2. **Guardrail scope undefined.** `no_adult_content` conflated with “anything that feels adult-ish or non-educational”.
3. **No insufficient-evidence rule.** Missing/loading screen text → model guesses worst case (BLOCK).
4. **Edu-only promise unbounded.** “Research papers and docs only” read as veto on email, forums, career mail — no ALLOW carve-outs.
5. **LOCK under-specified.** “Tamper with PhoneCodex” without requiring **active disable/stop/confirm** language.
6. **No low-friction surfaces list.** Home launcher, settings browse, WhatsApp, blank tab not called out as BLOCK-forbidden unless clear violation.
7. **WARN underused.** Single line: “WARN when promise allows uncertainty” — too weak vs BLOCK bias.
8. **Short-form vs mention** not in v01 (Azure handles well already — keep explicit in v02).

---

## Proposed classifier_v02 rules (summary)

| # | Rule | Targets |
|---|------|---------|
| 1 | **Decision ladder** — ALLOW = aligned/neutral; WARN = uncertain/drift/friction; BLOCK = clear forbidden activity; LOCK = active PhoneCodex tamper only | Clusters A, B |
| 2 | **Insufficient evidence → WARN never BLOCK** — loading, blank tab, unread count, partial OCR | B (`ch_yt_loading_*`) |
| 3 | **`no_adult_content` narrow definition** — explicit porn, sexual age gates, dating/hookup apps; NOT free movies, news “adult learners”, “mature discussion” | A (`movie_guardrail`, `mature_discussion`) |
| 4 | **Guardrail-only promise** — user controls entertainment; only permanent guardrails can BLOCK | A (`movie_guardrail`) |
| 5 | **Edu/focus promise** — BLOCK streaming/social feeds/games; ALLOW study forums, career/academic email, SO/docs; WARN memes/off-topic | A (`shortlisted`), B (`meme`) |
| 6 | **Low-friction surfaces** — home launcher, settings (non-tamper), WhatsApp, blank browser → ALLOW or WARN, never BLOCK unless clear violation | C, D |
| 7 | **LOCK requires active tamper verbs** — disable/stop/turn off/confirm + PhoneCodex; listing service ≠ LOCK | C (`set_a11y_list`) |
| 8 | **Off-goal entertainment under study** → prefer WARN unless monk/zero-fun or explicit “no X” with short-form/install | B (`gpt_laugh_study`) |
| 9 | **Quota/time/attempt counters** — unchanged from v01 (working well) | Maintain 0 false allows |
| 10 | **When torn between WARN and BLOCK** → choose WARN | Reduces false blocks, preserves safety |

---

## Why each change reduces false blocks without increasing false allows

| Change | False blocks fixed | Why false allows stay 0 |
|--------|-------------------|-------------------------|
| Adult guardrail narrow definition | `movie_guardrail_allow` | Real adult cases (`ch_chrome_real_adult_block_001`, `ch_yt_adult_quota_*`) still have explicit 18+/explicit warnings — still BLOCK |
| “Mature” ≠ adult_content | `mature_discussion` | No loosening on `Verify 18+`, explicit content, Tinder/dating installs |
| Edu promise carve-outs (email, forums) | `shortlisted_trap` | Movie streaming, TikTok install, Reels player still clearly BLOCK under edu/monk promises |
| Insufficient evidence → WARN | `yt_loading` | Does not ALLOW active Shorts player, Reels feed, or explicit adult — only unknown state |
| BLOCK requires clear violation | `gpt_laugh_study`, `compsci_meme` | Monk roleplay, quota exceeded, tamper LOCK, adult gate remain BLOCK |
| LOCK only on active tamper | `set_a11y_list` | `ch_set_tamper_wording_lock_001` still has Stop/Confirm — stays LOCK |
| Low-friction surfaces never BLOCK | home/settings/WA/blank | BLOCK still applies inside YouTube Shorts player, Reels, install gates, adult sites |
| WARN when torn | general | WARN is stricter than ALLOW — does not open path for adult/tamper/short-form false allows |

**Safety invariant:** v02 pushes ambiguous cases **up** from BLOCK to WARN, not from BLOCK to ALLOW. Clear violations unchanged.

---

## How to run prompt versions

Default (v01):

```bash
python evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai
```

v02 (recommended after tuning):

```bash
python evals/runner/run_eval.py --dataset evals/datasets/v0_challenge.jsonl --adapter azure_openai --prompt evals/prompts/classifier_v02.txt
```

`--prompt` is ignored by the `baseline` adapter. Paths may be repo-relative or absolute.

**Verified v02 results (`v0_challenge`, 50 cases):**

| Metric | v01 | v02 |
|--------|-----|-----|
| Accuracy | 74% | **84%** |
| False allows | 0 | **0** |
| False blocks | 3 | **0** |

Re-check `v0_seed` after prompt changes to ensure no regression on teaching cases.

---

## Analysis checklist (post v02 run)

- [ ] All 3 prior false blocks resolved?
- [ ] `ch_chrome_real_adult_block_001` still BLOCK?
- [ ] `ch_ps_tinder_guardrail_block_001` still BLOCK?
- [ ] `ch_set_tamper_wording_lock_001` still LOCK?
- [ ] `ch_yt_shorts_ui_variant_block_001` still BLOCK?
- [ ] WARN→ALLOW count on home/settings — acceptable product tradeoff?

---

## What stays in PolicyEngine (not prompt)

- Counter math (`shortsWatched` / `shortsLimit`, `attemptCount` → LOCK)
- Guardrail catalog (known dating package IDs)
- Final decision merge: classifier advises, policy decides

Prompt should not be the only line of defense for quotas or tamper — but v02 must not fight policy on clear signals.
