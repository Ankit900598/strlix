# Promise Compiler v04 — Design

**Date:** 2026-09-05  
**Status:** Active lab design (quality-first; supersedes junk-heavy v3 fill)  
**Prompt:** `evals/prompts/promise_compiler_v04.txt`  
**Dataset:** `evals/datasets/v3_commitment_messy_global.jsonl` (rebuilt, no synthetic_fill)  
**Schema:** existing `commitment_policy_schema.json` — **no new required fields**

---

## 1. Problem

Raw messy human promise → structured `CommitmentPolicy` → clarify when uncertain → (later) user confirms → PolicyEngine enforces.

Hard failure modes are **meaning collisions**, not missing synonyms:

| Collision | Wrong compile |
|-----------|---------------|
| “40 min YouTube” | Session 40m **or** video ≤40m **or** daily quota — must ask |
| “block videos >20 min for 1h session” | Session=`duration`; content cap=`quotas.entertainment_minutes` |
| IG messages vs Reels | Surface split, not whole-app ban |
| Neso / playlist only | Scope on allowedApps + block Shorts/other |
| “be stricter” | Follow-up, never invent rules |

---

## 2. Meaning taxonomy (10 distinction classes)

Every case’s `notes` / `cluster` maps to one primary class:

| # | Class | `duration` | `quotas` / content | Follow-up? |
|---|-------|------------|--------------------|------------|
| 1 | **session_duration** | Commitment length | empty unless also stated | No if explicit |
| 2 | **content_duration** | none / separate | `entertainment_minutes` = max media length/budget | No if explicit |
| 3 | **session_and_content** | Both stated | Both populated | No |
| 4 | **duration_ambiguous** | defaults | defaults | **Yes — required** |
| 5 | **app_surface** | as stated | allowed/blockedContent by surface | No if concrete |
| 6 | **quota_count** | often 1 day / none | shorts/reels/social_minutes | No |
| 7 | **permanent_guardrail** | fixed/indefinite | adult/dating/gambling/… | No |
| 8 | **strict_locked_tamper** | as stated | strike/lock/tamper | No |
| 9 | **exception_safe** | as stated | emergencyExceptions | No |
| 10 | **ambiguous_or_unsafe** | defaults | reject or ask | Yes / reject |

Multilingual (Hinglish, Hindi/Tamil romanized, Tamil script, mixed) is a **cross-cutting dimension**, not a separate policy type — same class, messier string.

---

## 3. Schema decision

**No new fields.** Encode:

- Session length → `duration`
- Max video/episode length or media-minute budget → `quotas` with `entertainment_minutes` (+ `allowedContent` description)
- Ambiguity → `followUpQuestionRequired` + `followUpQuestion` (question may be in user’s language)
- Confirmation UX later can reuse `followUpQuestion` / app copy — not a schema blocker for v04

Adding `contentDuration` now would break Android/PolicyEngine without buying clarity the quotas field already provides.

---

## 4. Dataset policy (quality bar)

- **≥200 excellent cases**, zero `synthetic_fill` spam.
- Each case tests **one primary distinction** (stated in `notes`).
- Required fixtures include: Neso playlist, IG DM vs Reels, porn 1yr, video>40min, block video>20min during 1h session, 40 Shorts no adult, monk except calls, install gate, vague strict, unsafe emergency block, multilingual variants.
- Gold must not contradict promise text (lesson from v02/v03 debug).

---

## 5. Prompt v04 load-bearing rules

1. Session vs content vs lock timer — never conflate.  
2. Ambiguous number+app → ask; never guess.  
3. Multilingual = compile if concrete; ask if vague.  
4. Unsafe emergency/surveillance → reject shape.  
5. Follow-up question should match user language when input is clearly non-English.

---

## 6. Eval plan

Compare **v03 vs v04** on the quality rebuilt dataset with `pc-lab-cheap` (`py -3.12`).

Primary metrics: exactMatch, safetyMatch, parseFailures, safetyViolations.  
Extra lens: clarification precision on `duration_ambiguous` + `ambiguous_*` clusters (followUp required when gold says so; not when concrete).

**App-ready bar:** safetyMatch ≥80% on this set, 0 missed adult/tamper/unsafe, clarification recall high on ambiguous duration — else research-only.

---

## 7. Explicit non-goals

- Android integration this track  
- Quantity padding  
- Claiming production-ready without numbers
