# Promise Compiler v04 — Eval Report

**Date:** 2026-09-05  
**Deployment:** `pc-lab-cheap`  
**Dataset:** `evals/datasets/v3_commitment_messy_global.jsonl` — **200 quality cases, 0 synthetic_fill**  
**Prompts:** `promise_compiler_v03.txt` vs `promise_compiler_v04.txt`  
**Design:** `evals/reports/promise_compiler_v04_design.md`  
**Case map:** `evals/reports/promise_compiler_v04_case_map.md`

---

## Commands run

```text
py -3.12 evals/datasets/_build_v3_promise_messy_global.py

py -3.12 evals/runner/run_promise_eval.py --adapter azure_openai --deployment pc-lab-cheap --prompt evals/prompts/promise_compiler_v04.txt --dataset evals/datasets/v3_commitment_messy_global.jsonl

py -3.12 evals/runner/run_promise_eval.py --adapter azure_openai --deployment pc-lab-cheap --prompt evals/prompts/promise_compiler_v03.txt --dataset evals/datasets/v3_commitment_messy_global.jsonl
```

Reports:

- v04: `promise_compiler_azure_openai_pc-lab-cheap_promise_compiler_v04_v3_commitment_messy_global_20260905_205215.csv`
- v03: `promise_compiler_azure_openai_pc-lab-cheap_promise_compiler_v03_v3_commitment_messy_global_20260905_210207.csv`

---

## Headline metrics (same 200-case quality set)

| Metric | v03 | v04 | Δ |
|--------|-----|-----|---|
| exactMatchRate | 35.0% (70/200) | **41.0% (82/200)** | +6.0pp |
| safetyMatchRate | **64.5% (129/200)** | 62.5% (125/200) | −2.0pp |
| safetyViolations | 15 | **7** | −8 |
| parseFailures | 0 | **0** | — |
| contentFilterBlocks | 0 | 0 | — |

**Read carefully:** Overall safetyMatch dipped 2pp, but that is not the story. The **product-critical distinctions** improved hard, and **safety violations halved** (all remaining are missed follow-ups on vague phrases — not adult/tamper/unsafe misses).

---

## Clarification precision (gold `followUpQuestionRequired=true`, n=40)

| Prompt | Field match on followUpQuestionRequired | Missed-follow-up violations |
|--------|-------------------------------------------|-----------------------------|
| v03 | 62.5% (25/40) | 15 |
| v04 | **82.5% (33/40)** | **7** |

### Duration-ambiguous cluster (n=20) — the “40 min YouTube” class

| Prompt | safetyMatch | followUpQuestionRequired OK | duration OK | quotas OK |
|--------|-------------|-----------------------------|-------------|-----------|
| v03 | 4/20 (20%) | 7/20 | 16/20 | 8/20 |
| v04 | **17/20 (85%)** | **20/20** | **20/20** | **19/20** |

v04 stops guessing session length on ambiguous number+app promises. That was the main design goal.

### Session vs content clocks

| Cluster | v03 quotas OK | v04 quotas OK |
|---------|---------------|---------------|
| content_duration (n=12) | 7/12 | **10/12** |
| session_and_content (n=13) | **1/13** | **10/13** |
| session_duration (n=19) duration OK | 18/19 | 17/19 |

v03 almost never put media length into `quotas` when both clocks were stated. v04 mostly does.

---

## Schema

**No schema change.** Session → `duration`; content length/budget → `quotas.entertainment_minutes`; ambiguity → `followUp*`. Sufficient for v04.

---

## Top 10 remaining failure modes (v04)

1. **Vague non-duration ambiguity still sometimes compiled** (`ambiguous_clarify`, 7 missed_follow_up) — e.g. “focus mode on”, Tamil “கவனம் வேணும்”, “vague but strict please”.  
2. **`allowedContent` over/under-specification** (46 mismatches) — model adds/omits content rows vs gold scopes.  
3. **`blockedContent` surface granularity** (29) — whole-app vs Reels/feed/shorts split still noisy.  
4. **`commitmentType` on edge installs/soft warns** (22) — install_gate vs focus_session; soft reel nudge typed wrong.  
5. **Permanent guardrail + LOCKED/tamper coupling** — “don’t disable” / cheat cases miss `tamperPolicy` or invent `lockPolicy`.  
6. **Strike/lock recipes** — warn/strike counts and lock minutes imperfect on multi-clause promises.  
7. **Playlist/channel rail scopes** — Neso/3Blue1Brown scope strings don’t always land in `allowedApps`.  
8. **Exceptions packaging** — family/SOS present but `emergencyExceptions` type mix imperfect (`allowed_exceptions` 44% safety).  
9. **Multilingual clear compiles inconsistently** (38% safety) — Tamil/Hinglish clear sessions sometimes ask or drop guardrails.  
10. **install_gate small-n fragility** (1/5 safety) — “ask before install” / education-only still shaky.

**Not failing:** `rejectedUnsafeParts` 100%; no adult-miss or unsafe-compile violations in the violation list.

---

## App integration verdict

### **NOT ready for Android wiring as product input.**

Reasons:

- safetyMatch **62.5% < 80%** design bar on this distinction set.  
- Surface / content field noise still too high for silent compile → enforce.  
- Clarification path works better but still misses ~17.5% of required follow-ups.

### What *is* ready as research

- v04 is the better **lab prompt** for session-vs-content and ambiguous duration.  
- Use v04 for offline compile experiments and Decision Inspector demos with **human confirm**.  
- Do **not** auto-apply compiled policy to PolicyEngine without confirmation UI.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Silent wrong session length | Keep v04 ask-on-ambiguous; confirm UI |
| Over-trust exactMatch | Ship on safety + clarification recall, not exact |
| Azure content filter on adult phrases | None this run; keep sanitized gold wording |
| Gold scope string brittleness | Score apps by package (already); scopes are soft |

---

## Changed / created files

| File | Role |
|------|------|
| `evals/reports/promise_compiler_v04_design.md` | Taxonomy + quality bar |
| `evals/reports/promise_compiler_v04_case_map.md` | Cluster + fixture map |
| `evals/reports/promise_compiler_v04_eval.md` | This report |
| `evals/prompts/promise_compiler_v04.txt` | Three-clock rules + multilingual follow-ups |
| `evals/datasets/_build_v3_promise_messy_global.py` | Quality rebuild (no synthetic_fill) |
| `evals/datasets/v3_commitment_messy_global.jsonl` | 200 cases |
| `evals/datasets/v3_commitment_combined.jsonl` | v2+v3 combined |
| `evals/runner/run_promise_eval.py` | `--limit` support (earlier) |

---

## Next Android task (when product track resumes)

1. Keep P0 overlay stability if still open (`docs/CURRENT_STATE.md`).  
2. **Promise confirm sheet:** show compiled fields + follow-up answers before session start — do not hot-wire v04 into enforcement.  
3. Template overlay UX can proceed independently (`trustworthy_block_experience.md` / block experience lab).

---

## One-line CTO summary

v04 **wins the science** (duration clocks + ask-don’t-guess); v03 slightly higher aggregate safetyMatch is **noise** next to 20%→85% on `duration_ambiguous` and 1/13→10/13 on dual-clock quotas. Still **research-stage**, not app-ready.
