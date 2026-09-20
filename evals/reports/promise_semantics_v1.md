# Promise Semantics v1 — Report

**Date:** 2026-09-07  
**Status:** Lab foundation shipped — **not** auto-wire into PolicyEngine  
**Prompt:** `evals/prompts/promise_compiler_v06.txt`  
**Schema:** optional `userFacingConfirmation`, `interpretationNotes`  
**Normalize:** `backend/promiseCompilerService.js` (PROMPT_VERSION = v06)  
**Dataset:** `evals/datasets/v6_promise_semantics.jsonl` (122 gold)  
**Smoke:** `node backend/smoke_promise_compiler_normalize.js` (20 invariants)

---

## Problem (live failure)

User promise:

> I want to watch at most 10 shorts today, but never adult/sexual shorts. After 10 shorts, block shorts for the rest of the day. Long educational YouTube should still be allowed.

Broken assumptions observed:

| # | Failure | Semantics v1 fix |
|---|---------|------------------|
| 1 | “shorts” = YouTube-only | Category expand → YT, IG Reels, FB Reels, TikTok, Snap Spotlight, NewPipe, Chrome |
| 2 | “today” invented as 60m session | `timeWindowKind=calendar_day`, `sessionDurationMinutes=1440`, no “defaulted to 60” caution |
| 3 | First Short blocked | Quota boundary **`allow_first_n`**: events 1..N ALLOW, N+1 BLOCK |
| 4 | NewPipe silent allow | Always in `scopePackages` / suggested apps for short-form category |
| 5 | No multi-platform scope | Alias table `SHORT_FORM_PLATFORM_PACKAGES` |
| 6 | No clarification path | Vague bare “shorts” / “study only” → follow-up; clear quota → default+preview |
| 7 | Quota mixed with entertainment ban | Count rules separate from `entertainment_minutes` / hard `no_short_form_video` |
| 8 | Unknown clone harmless | NewPipe registered as video platform (Android registry already); compiler includes it |
| 9 | No confirm preview | `confirmationPreview[]` lines for UI |
| 10 | Concepts collapsed | TIME / SCOPE / ACTION / QUOTA / GUARDRAIL kept separate in normalize DTO |

---

## Quota boundary (documented law)

```text
allow_first_n
  count matching short-form PLAY events only
  (not app open, homepage, search, comments)
  events 1..N  → ALLOW
  events N+1+  → BLOCK until period ends
adult/sexual   → BLOCK immediately (never consumes friendly quota)
```

---

## Failure classes FIXED (normalize + contract)

1. **Invented 1-hour session** on daily short-form quotas  
2. **WARN-then-feel-blocked** under quota (now ALLOW under limit + BLOCK over)  
3. **YouTube-only shorts** for bare “shorts” category language  
4. **Missing NewPipe / IG / FB / TikTok / Chrome** in scope for category shorts  
5. **Missing confirm-sheet bullets** (`confirmationPreview`)  
6. **Adult missing as always-block** when guardrail present (normalize ensures adult content rule)  
7. **Media-length → entertainment budget** still repaired (prior clocks work kept)  
8. **Prompt path** upgraded lab default to v06 (backend)

Verified offline:

```text
node backend/smoke_promise_compiler_normalize.js
→ ok, promptVersion promise_compiler_v06, liveExample calendar_day 1440, scopePackages 7, 20 invariants
```

---

## Failure classes REMAINING

1. **Model exact-match still low** on 122-case gold without Azure (baseline ~6% exact) — expected; measure semantics not strings.  
2. **Playlist/channel identity** (Neso Academy OS) still needs follow-up; enforcement of specific playlist IDs not on-device yet.  
3. **Counting PLAY events** on IG/FB/TikTok/NewPipe/Chrome — Android must implement detectors per surface; compiler only emits policy.  
4. **Unknown future clones** beyond alias table still need WARN/registry updates.  
5. **Trusted recovery UX** for year-long guardrails — recommended in contract, not fully productized.  
6. **Multilingual full native script** — romanized Tamil/Hindi covered lightly; not complete language support.  
7. **Azure v06 quality** — run report below; do not ship on exactMatch alone.

---

## Eval commands

```powershell
node backend/smoke_promise_compiler_normalize.js
py -3.12 evals/datasets/_build_v6_promise_semantics.py
py -3.12 evals/runner/run_promise_eval.py --adapter baseline --dataset evals/datasets/v6_promise_semantics.jsonl --prompt evals/prompts/promise_compiler_v06.txt
py -3.12 evals/runner/run_promise_eval.py --adapter azure_openai --deployment pc-lab-cheap --prompt evals/prompts/promise_compiler_v06.txt --dataset evals/datasets/v6_promise_semantics.jsonl
```

### Baseline (no model) — floor only

| Metric | Value |
|--------|-------|
| Cases | 122 |
| Exact | 5.7% |
| Safety | 16.4% |
| Clock OK | 42.6% |
| Parse fail | 0 |

Baseline cannot invent adult guardrails / quotas — floor is not the ship bar.

### Azure `pc-lab-cheap` + v06

| Metric | Value |
|--------|-------|
| Cases | 122 |
| Exact | 9.0% (11/122) |
| Safety-critical | 45.1% (55/122) |
| Safety violations | **3** (all missed follow-ups) |
| Temporal clock OK | **91.8% (112/122)** |
| Quotas field match | **94%** |
| Parse / content-filter | 0 / 0 |
| Avg latency | ~5.4s |

**LIVE example (`v6_quota_live_001`):** clock OK; `shorts=10`/`day`; `no_adult_content`; confirm copy present. Exact/safety string-match still False mainly on duration encoding (`none` vs `fixed 1 day`) and soft content prose — both map to calendar-day in normalize. **Do not ship on exactMatch.**

Cluster clock OK highlights: short_form_daily_quota **18/18**, media_max contrast **8/8**, newpipe/chrome **8/8**, neso **6/6**. Weakest: install_gate clock 3/7.

Failure cluster MD: `evals/reports/promise_semantics_v1_failure_clusters.md`

---

## Android contract

See `docs/android-promise-semantics-contract.md`.

---

## What is safe to ship vs lab-only

| Asset | Ship? |
|-------|-------|
| Normalize repairs + confirmationPreview + calendar_day + allow_first_n | Yes to backend (counsel path) |
| Confirm-sheet showing preview before Start | Yes (UI) |
| Auto-enforce compiled policy without confirm | **No** |
| Short-form count across IG/FB/TikTok/NewPipe | Only after Android detectors exist |
| v06 as sole production brain | Lab until Azure metrics + phone harness pass |

---

## Next 100 real-phone cases to collect

1. Shorts quota mid-day after N plays  
2. NewPipe short vs long  
3. Chrome youtube.com/shorts embed  
4. IG Reels after quota exhausted  
5. FB Reels / TikTok same quota  
6. Adult Short that must not count as friendly quota  
7. Lecture + Shorts shelf visible  
8. “40 min youtube” clarification accept paths  
9. Neso playlist drift to Home  
10. Install flirt APK during year guardrail  
… (log package, surface, decision, expected)
