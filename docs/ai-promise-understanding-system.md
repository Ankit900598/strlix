# Strlix AI Promise Understanding System

**Date:** 2026-09-07  
**Status:** Active design — Promise Compiler **v08**  
**Law:** AI is counsel. PolicyEngine is law. User confirms before Start.

---

## North star UX

User says something messy. Strlix answers like Claude/ChatGPT:

> I think you mean **A**. Or maybe **B** / **C**. Pick one.

Then it compiles safe policy. **Internal policy may be technical. User-facing copy must be human.**  
Never: `Allowed: com.google.android.youtube -> ALLOW`.

---

## Architecture (14 layers)

```text
 1 Raw user promise          typed / voice / messy language
 2 Speech transcript cleanup OCR-ish cleanup, confidence
 3 Cleaned intent            cleanedPromiseText + userIntentSummary
 4 Meaning candidates        1–3 interpretations + recommended
 5 Clarification options     one question + 2–3 choices if needed
 6 Policy compiler           CommitmentPolicy JSON (counsel)
 7 Deterministic normalizer  clocks / scope / package sanitizer
 8 User confirmation copy    understood / allow / block / time / appliesTo
 9 Safety critic             falseAllow / falseBlock / permanent risk
10 Model router              cheap vs strong by ambiguity/safety
11 Eval feedback loop        datasets → failure clusters → prompt bumps
12 Personal memory (later)   prior promises / corrections (not v08 ship)
13 Multilingual roadmap      Hinglish → Indic scripts → more locales
14 Cost/latency at scale     cache, debounce, confirm-before-cloud
```

### 1. Raw user promise

- Typed text, voice transcript, broken English, Hinglish, typo storms
- Emotional / contradictory / safety-sensitive long-term wording

### 2. Speech transcript cleanup

- Fix obvious ASR errors without inventing rules
- Expose `transcriptConfidence` when input was voice
- Never auto-start enforcement from transcript alone

### 3. Cleaned intent

- `cleanedPromiseText`, `userIntentSummary`, `detectedLanguage`
- Preserve ambiguity; do not silently invent duration or bans

### 4. Meaning candidate generation

- 1–3 candidates; mark `recommendedInterpretation`
- `ambiguityLevel`: none | low | medium | high
- `alternativeInterpretations[]`

### 5. Clarification option generation

When behavior would change on the phone:

- One focused `clarificationQuestion`
- 2–3 `clarificationOptions` (id, label, description, recommended, policyPreview)
- Start blocked until option selected or promise edited

Safe default + editable note (no force-click):

- Clear “10 shorts today” → all short-form surfaces + interpretation note

Must ask:

- Ambiguous “Google video”
- “bad apps” / “normal phone” without mechanism
- Number + app with no role (“40 min youtube”)
- Permanent / 1-year adult or dating (stronger confirm)

### 6. Policy compiler

- Azure/OpenAI (or baseline) produces structured CommitmentPolicy
- Packages allowed **only** in internal fields
- Five clocks never mixed: session / media length / usage quota / lock / permanent

### 7. Deterministic normalizer (`promiseCompilerService.normalizeCompiledPromise`)

- Repair media-length vs budget confusion
- Expand short-form `scopePackages` internally
- Force package-leak strip on all user-facing strings
- Force Google-video options when ambiguous
- Set `clarificationRequired` / `canStartCommitment`

### 8. User confirmation copy

Show: understood, allow, block, when, appliesTo (categories), checkThis, safetyNotes.  
Hide: package IDs, deployment names, raw JSON.

### 9. Safety critic

- `riskReview`: falseAllowRisk, falseBlockRisk, safetyRisk, requiresHumanConfirmation
- Permanent / LOCKED / preventDisable → stronger confirm
- Emergency paths never removed by model

### 10. Model router (billion-user cost)

| Situation | Model |
|-----------|--------|
| ambiguity none/low, short promise | cheap / fast |
| ambiguity medium/high, permanent, adult/dating | stronger |
| offline / Azure down | local parser + caution |

Never call cloud AI on every accessibility event.

### 11. Eval feedback loop

```text
messy cases → eval run → failure clusters → prompt/normalizer patch → re-eval
```

Moat = labeled promise behavior corpus, not a single model.

### 12. Personal memory (later)

- Prior clarifications, user corrections, recurring worlds
- Not required for v08 ship; schema reserved

### 13. Multilingual roadmap

1. English + Hinglish + roman Hindi (now)  
2. Tamil-English / other code-mix  
3. Native scripts with same confirmation UX  
4. Locale-specific short-form app categories

### 14. Cost / latency strategy

- Confirm-before-cloud: Understand once per edit, not per keystroke  
- Cache compile by (normalized text + option id)  
- Debounce voice finalize  
- Eval in Azure; phone enforcement stays local/deterministic

---

## Integration rule

```text
Understand → Confirm → Start → PolicyEngine → Overlay → Log
```

Do **not** auto-wire compiler JSON into enforcement without confirmation.  
Do **not** let cloud AI override permanent guardrails or emergency exceptions.
