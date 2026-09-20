# Azure model routing — Promise Understanding v08

**Date:** 2026-09-07  
**Account:** `ay186mnc-1561-resource` (westus3, kind AIServices)  
**Also present:** `phonecodex-ai-dev` (OpenAI, eastus2) — no deployments listed via CLI; `phonecodex-speech-dev` (SpeechServices, eastus2)  
**CLI:** `az cognitiveservices account deployment list --name ay186mnc-1561-resource --resource-group phonecodex-dev` succeeded (no MFA/payment blocker this run).

## Deployments (names only — no secrets)

| Deployment | Family (lab map) | Role |
|------------|------------------|------|
| `pc-lab-cheap` | gpt-4.1-mini | Default cleanup + compiler evals |
| `pc-lab-strong` | gpt-4.1 | Ambiguity / safety / hard-subset escalation |
| `pc-lab-vision` | gpt-4o | OCR/screenshot only — **not** promise compiler primary |

**Prompt used:** `evals/prompts/promise_compiler_v08.txt` (present; no v07 fallback needed).

---

## Hard-subset eval (200 cases)

**Dataset:** `evals/datasets/v8_hard_core200.jsonl`  
**Composition:** 100 red-team + 100 hard assistant (clarification / adult / dating / channel / girls_chatting priority).  
**Source pools:** `v8_assistant_promise_understanding.jsonl` (1776) + `v8_redteam_promise_breaks.jsonl` (228).  
**Also built:** `v8_hard_core280.jsonl` (all 228 redteam + 52 assistant) — used for early baseline only.

### Metrics (same scorer)

| Run | Exact | Safety | Clock OK | Clarify agree | Clarify P / R | Option qual | Package leak | Unsafe auto-start | Avg lat | Parse fail | CF blocks |
|-----|-------|--------|----------|---------------|---------------|-------------|--------------|-------------------|---------|------------|-----------|
| baseline | 0.0% | 0.0% | 23.5% | 5.5% | 0 / 0.0 | 5.5% | **0.0%** | 94.5% | ~0ms | 0 | 0 |
| azure `pc-lab-cheap` + v08 | 0.0% | 2.0% | 63.0% | 40.0% | **0.937 / 0.392** | 42.5% | **0.5%** | 64.5% | **11761ms** | 9 | 3 |
| azure `pc-lab-strong` + v08 | 0.0% | 2.5% | **70.0%** | **57.5%** | **0.913 / 0.608** | **63.0%** | **0.0%** | **35.5%** | **6697ms** | 0 | 3 |

**CSV evidence:**

- `evals/reports/promise_compiler_baseline_v8_hard_core200_20260907_163228.csv`
- `evals/reports/promise_compiler_azure_openai_pc-lab-cheap_promise_compiler_v08_v8_hard_core200_20260907_171545.csv`
- `evals/reports/promise_compiler_azure_openai_pc-lab-strong_promise_compiler_v08_v8_hard_core200_20260907_173835.csv`

### Approx cost / latency notes

- Cheap: ~40 min wall for 200 sequential calls (~11.8s/case). Rough token ballpark ~3k in + ~0.8k out/case → order-of-magnitude **~$0.5–1** for the cheap sweep (list prices move; treat as spend discipline signal only).
- Strong: ~22 min wall (~6.7s/case — shorter completions). Order-of-magnitude **~$2–4** for the strong sweep.
- Vision **not** run for text promises (correct per ladder).

---

## Recommended production ladder (v08)

```text
1. Fast cleanup / compile     → pc-lab-cheap + promise_compiler_v08
2. If ambiguity high OR permanent/adult/dating OR parse/content_filter
                             → re-run pc-lab-strong (same prompt)
3. Deterministic normalizer  → always (sanitize, clocks, aliases, options,
                                force canStartCommitment=false when clarificationRequired)
4. User confirms             → Start enabled only if canStartCommitment
5. PolicyEngine              → law
```

**Do not:**

- Full-corpus sweeps on `pc-lab-strong`
- Vision for text promises
- Blind auto-start from compiler confidence
- Replace v07 default until Android option cards + Start gating ship

---

## Routing decision from this sprint

| Question | Answer |
|----------|--------|
| Prefer cheap or strong for day-to-day? | **Cheap default** |
| Escalate when? | Clarify miss risk, permanent/adult/dating, parse fail, content filter |
| Ship v08 as default backend prompt? | **Not yet** — allowlist yes; default stays v07; enable via `PROMISE_COMPILER_PROMPT_VERSION=promise_compiler_v08` / `v08` |
| Why? | Hard-subset unsafe-auto-start still **35.5%** on strong; clarify recall only **60.8%**; dating/porn permanent clusters still dominate followup misses |

---

## Azure blockers

**None for inference this run.** Account Enabled; deployments listed; single-call probe HTTP 200 in ~1.5s.  
Earlier 280-case job looked “hung” but was sequential latency (~12s×280 ≈ 56m) with no progress logs — use progress wrapper for future sweeps.

---

## Speech path (unchanged)

```text
mic → Azure Speech STT → cleaned transcript → Promise Compiler (v08 when flagged) → confirm UX
```

Smoke: `backend/smoke_transcribe_promise.js` PASS (mock + client_transcript + 400).
