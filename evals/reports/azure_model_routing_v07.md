# Azure model routing — Promise Understanding v07

**Date:** 2026-09-07  
**Account:** ay186mnc-1561-resource (westus3)  
**Known deployments (no secrets):**

| Deployment | Family | Role |
|------------|--------|------|
| `pc-lab-cheap` | gpt-4.1-mini | Default cleanup + compiler evals |
| `pc-lab-strong` | gpt-4.1 | Ambiguity / safety / hard-subset escalation |
| `pc-lab-vision` | gpt-4o | OCR/screenshot only — **not** promise compiler primary |

Speech: `backend/speechTranscriptionService.js` exists — use Azure Speech for transcript → same `/compile-promise` path. Do not invent a second policy path.

---

## Recommended production ladder

```text
1. Fast cleanup / compile     → pc-lab-cheap + promise_compiler_v07
2. If ambiguity high OR permanent/adult/dating OR parse fail
                             → re-run pc-lab-strong (same prompt)
3. Deterministic normalizer  → always (sanitize, clocks, aliases, options)
4. User confirms             → Start enabled only if canStartCommitment
5. PolicyEngine              → law
```

**Do not:**

- Full-corpus sweeps on `pc-lab-strong`
- Vision for text promises
- Fine-tune before ≥1k reviewed gold + failure clusters are stable
- Spend Azure on every Accessibility event

---

## Spend priorities (credits expiring)

1. **Do:** 200–1000 case v07 evals on cheap; hard-subset (ambiguous + permanent) on strong  
2. **Do:** Measure packageLeakRate, clarification recall, unsafe auto-start (`canStart` when clarify required)  
3. **Do:** Speech smoke: 5–10 Hinglish voice clips → transcript → v07  
4. **Don’t:** Idle GPU, unused new resources, training from scratch  
5. **Don’t:** Create deployments without documenting region/model if portal blocks — fall back to existing three

---

## Metrics to log per Azure run

- exactMatch / safetyMatch / clockOk (existing)
- clarificationRequired agreement
- optionCount ≥ 2 when required
- packageLeakRate on userFacingConfirmation + options + clarificationQuestion
- canStartCommitment false when clarificationRequired
- latencyMs p50/p95
- approximate token cost (from Azure metrics)

---

## If new deployment cannot be created

Continue with `pc-lab-cheap` + `pc-lab-strong`. Document blocker (quota/MFA/region). Propose: one additional mini deployment in westus3 only if latency/capacity fails.

---

## Speech path (lab)

```text
mic → Azure Speech STT → cleaned transcript → Promise Compiler v07 → confirm UX
```

Same clarification/options rules. Eval with messy ASR errors in `v7` voice-transcript cluster.
