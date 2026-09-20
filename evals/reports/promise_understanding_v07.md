# Promise Understanding v07 — Eval Report

**Date:** 2026-09-07  
**Prompt:** `evals/prompts/promise_compiler_v07.txt`  
**Compare:** v06 vs v07 on `v7_assistant_promise_understanding_core200.jsonl` (200)  
**Strong probe:** `pc-lab-strong` + v07 limit 60  
**Design:** `docs/ai-promise-understanding-system.md`, `docs/promise-confirmation-ux-contract.md`  
**Routing:** `evals/reports/azure_model_routing_v07.md`

---

## What was built

Assistant interaction model: cleanup → candidates → multiple-choice clarification → human confirm → internal policy.  
Backend normalize (default prompt **v07**, flag `PROMISE_COMPILER_PROMPT_VERSION=v06|v07`): clarificationOptions, canStartCommitment, package-leak sanitizer, Google-video option engine.  
Dataset: **1516** gold + **102** red-team + **200** Azure core.

---

## Dataset size

| File | N |
|------|---|
| `v7_assistant_promise_understanding.jsonl` | 1516 |
| `v7_assistant_promise_understanding_core200.jsonl` | 200 |
| `v7_redteam_promise_breaks.jsonl` | 102 |

---

## Eval results

### Baseline (floor) — core200

| Metric | Value |
|--------|-------|
| Exact | 0.5% |
| Safety | 3.5% |
| Clock OK | 36.0% |
| Clarification agreement | 44.5% |
| Option quality | 44.0% |
| Package leak | **0.0%** |
| Unsafe auto-start proxy | 55.5% |

### Azure `pc-lab-cheap` — core200 (v07 vs v06)

| Metric | v07 | v06 | Winner |
|--------|-----|-----|--------|
| Exact | 0.0% | 1.0% | — (ignore) |
| Safety | 29.0% | 29.5% | tie |
| Safety violations | 63 | 57 | v06 slight |
| Clock OK | 81.5% | **83.5%** | v06 slight |
| Clarification agreement | **70.5%** | 70.5% | tie |
| **Option quality** | **72.0%** | 44.0% | **v07** |
| Package leak | **0.0%** | 0.0% | tie |
| Unsafe auto-start proxy | 28.5% | 27.0% | tie |
| Avg latency | 7.1s | 3.9s | v06 faster |

**Product takeaway:** v07 wins the assistant job (multiple-choice options). Clocks stay ≈v06. Exact match is the wrong KPI.

### Azure `pc-lab-strong` — v07 limit 60 (hard-first slice)

| Metric | Value |
|--------|-------|
| Safety | **51.7%** |
| Violations | **3** |
| Clock OK | 85.0% |
| Clarification agreement | **95.0%** |
| Option quality | **95.0%** |
| Package leak | **0.0%** |
| Unsafe auto-start proxy | **5.0%** |

Strong model is the right escalation for ambiguous/permanent subsets.

Reports:
- `..._v07_..._20260907_153750.csv`
- `..._v06_..._20260907_155042.csv`
- `..._strong_..._v07_..._limit60_20260907_155615.csv`

---

## Best examples

**Clear (LIVE):** 10 shorts today + no adult → quotas shorts=10/day, `no_adult_content`, interpretationNotes expand shorts to all short-form, package leak false.

**Ambiguous:** Google video + 30 min / 1 hour → must offer Chrome vs all video apps vs YouTube (normalize now **overrides** weak model options that only debate quota vs length).

---

## Worst failures

1. Model sometimes clarifies the wrong axis (time-role) for “Google video” — **patched in normalize**.  
2. `porn_1_year` cluster: missed stronger confirm / tamper on cheap.  
3. `media_length_vs_quota` option misses on cheap.  
4. Unsafe auto-start proxy ~28% on cheap — escalate strong when `ambiguityLevel` high.  
5. Exact match ~0% — expected; do not optimize.

Top option-fail clusters (v07 cheap): porn_1_year, media_length_vs_quota, dating_flirt, channel_playlist, ambiguous_google_video.

---

## Integration verdict

| Decision | Verdict |
|----------|---------|
| Backend default v07 (flag) | **YES** — already default `PROMISE_COMPILER_PROMPT_VERSION=promise_compiler_v07` |
| Keep v06 pin available | YES |
| Auto-wire PolicyEngine | **NO** |
| Android option cards | **Shipped (Home UI)** — A/B/C + stronger-confirm + recompile with option id; phone verify still required |
| Strong on every request | **NO** — escalate ambiguous/permanent only |
| `/compile-promise` + `selectedClarificationOptionId` | **YES** (backend + Android client) |

---

## Self-audit (2026-09-07) — unfinished + own mistakes fixed

### Not done (honest)

| Gap | Status |
|-----|--------|
| Android A/B/C option cards + Start gating | **Shipped** (unit-tested; phone verify next) |
| Permanent “I understand this lasts…” checkbox in UI | **Shipped** (Home card) |
| Full 1516 Azure sweep / critic model / fine-tune | **Not run** |
| Speech/ASR batch evals | **Not run** (service exists) |
| Re-run core200 Azure after normalize patches | **Not re-run** (scores above are pre-patch) |
| `internalPolicy` on Start / PolicyEngine auto-wire | **Not done** (auto-wire stays NO) |

### Mistakes we shipped, then corrected in normalize/API

1. **Wrong clarify axis for “Google video”** — model debated quota vs length; normalize now **overrides** to Chrome / all video apps / YouTube.  
2. **Shorts quota + `no_short_form_video` hard ban** — contradictory; normalize **strips** hard shorts guardrail when shorts quota present.  
3. **API ignored selected option** — Start could never unlock after A/B/C; `server.js` + `compilePromise` + normalize now accept `selectedClarificationOptionId`.  
4. **`canStartCommitment` stayed false after pick** — because `requiresStrongerConfirmation` wrongly included “needs clarify”; fixed: stronger confirm = permanent/low-transcript only; after pick, Start unlocks unless permanent/transcript gate.

Smoke: `node backend/smoke_promise_compiler_normalize.js` → **130 assertions** (includes pick-unlock + quota strip).

### Android gap (audit 2026-09-07) — **wired**

Home confirmation now consumes v07 fields (mapper + client + card + `HomeScreenState`):

- `clarificationOptions[]` as A/B/C cards with Recommended
- Start gated by server `canStartCommitment` + option pick + stronger-confirm checkbox
- Recompile POST includes `selectedClarificationOptionId`
- Unit tests: mapper / PromiseUnderstanding / ConfirmationUserCopy (package-leak) green

**Still open after wire:** phone verify; `internalPolicy` blob persistence on Start; PolicyEngine auto-wire (by design NO); voice transcriptConfidence surface; Compose UI tests.

### What to do next

1. **Phone verify** A/B/C + permanent checkbox + no package IDs in copy.  
2. Optional: re-run core200 Azure to refresh metrics after normalize patches.  
3. Do **not** auto-wire PolicyEngine; later: persist `internalPolicy` if Start needs full blob.

---

## Remaining research

- ASR/Hinglish speech batch evals (path exists: Azure Speech `en-IN`)  
- Critic model pass for permanent promises  
- Reduce cheap unsafe-auto-start without killing latency  
- Expand red-team reviewed gold beyond templates  

---

## Next prompt for Backend/Android

```text
Read docs/promise-confirmation-ux-contract.md and evals/reports/promise_understanding_v07.md.
Wire Home confirmation UI to clarificationOptions[] + canStartCommitment from /compile-promise (v07).
Disable Start until an option is selected when clarificationRequired.
POST selectedClarificationOptionId on recompile after user picks A/B/C.
Do not change Accessibility overlay enforcement in this task.
Verify ConfirmationUserCopyTest still blocks package IDs.
```
