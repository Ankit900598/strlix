# Promise Confirmation UX Contract

**Audience:** Android + backend owners  
**Pairs with:** `docs/ai-promise-understanding-system.md`, `docs/android-promise-semantics-contract.md`  
**Compiler:** Promise Understanding **v08** (`evals/prompts/promise_compiler_v08.txt`, schema `evals/schemas/promise_understanding_v08.schema.json`)

---

## Pattern: Claude-like confirm sheet

Think Codex/Claude confirm — not a settings dump.

```text
I understood: …
  → Allowed / Blocked / Time / Applies to
  → Check this (soft notes)
  → If unsure: one question + 2–3 option cards (one Recommended)
  → Start Commitment (or disabled until option / permanent confirm)
```

User never sees package IDs, raw JSON, or model names in the primary sheet.

---

## Screen: “I understood”

### Always show (human copy only)

| Field (v08) | UI label | Notes |
|-------------|----------|--------|
| `userFacingConfirmation.understood` | I understood | Also accept v07 `understoodSummary` |
| `userFacingConfirmation.allowed[]` | I will allow | v07: `allowedBullets` |
| `userFacingConfirmation.blocked[]` | I will block | v07: `blockedBullets` |
| `userFacingConfirmation.time` | When this applies | Never invent hidden 60m for calendar-day quotas |
| `userFacingConfirmation.appliesTo` | Applies to | Categories only |
| `userFacingConfirmation.checkThis[]` | Check this | Shorts expansion, voice uncertainty, soft questions |
| `userFacingConfirmation.safetyNotes[]` | Safety | Adult / emergency / permanent |
| quoted `rawText` | Your promise | Editable before Start |
| status | AI preview ready / Needs clarification / Offline | |

### Show when `clarificationRequired`

- Question text (`clarificationQuestion`) — **one** focused question
- **Option cards A/B/C** from `clarificationOptions[]` (2–3 options)
  - `label` (short)
  - `description` (one sentence)
  - **Recommended** badge if `recommended === true`
  - Preview: `policyPreview` (v08) or `resultingPolicyPreview` (v07)
- Selecting an option sets `selectedClarificationOptionId` and recompiles **or** applies that option’s preview → `internalPolicy`
- **Start Commitment disabled** until option selected OR user edits promise and re-runs Understand

### Mobile examples (copy tone)

**Clear quota (no options):**
> I understood: Up to 10 short videos today, no adult content.  
> Allowed: first 10 short-form plays today; long educational videos  
> Blocked: adult/sexual videos always; short-form after 10  
> Check this: I treated “shorts” as all short-form video apps (change?)

**Ambiguous Google video (options required):**
> When you said “Google video,” what did you mean?  
> ○ Recommended — Videos inside Chrome / browser  
> ○ All video apps on my phone  
> ○ YouTube only

**Permanent (stronger confirm):**
> I understood: No porn for 1 year; rest of phone stays normal.  
> ☐ I understand this lasts **1 year** and is harder to remove  
> Start stays disabled until the checkbox is checked.

**Voice uncertain:**
> Check this: Voice transcript looked uncertain — please re-read before locking a long commitment.

---

## Never show in primary UI

- Package IDs (`com.google…`, `org.schabi…`)
- Raw JSON, `BLOCK ->`, classifier names, “AI model”, deployment names
- Full `hiddenInternalScope` / `internalPolicy.appRules` package lists (Advanced / debug only)

---

## Start Commitment enablement

| Condition | Start |
|-----------|-------|
| Offline local preview only | Allowed with caution (existing) |
| Compiler returned `clarificationRequired=true` and no option selected | **Disabled** |
| `ambiguityLevel=high` | Treated as clarification required |
| Permanent / 1 year / forever (`requiresStrongerConfirmation` / `riskReview.requiresHumanConfirmation`) | Allowed only after explicit confirm checkbox (“I understand this lasts …”) |
| Low `transcriptConfidence` on permanent | Stronger confirm + show uncertainty in Check this |
| `rejectedUnsafeParts` non-empty for whole-promise reject | Disabled; show rejection |
| Ambiguity none/low and confirm sheet reviewed | Enabled |

---

## Option → policy mapping (Android)

1. User taps option `id` (A/B/C).  
2. Client sends `{ userPromise, selectedClarificationOptionId }` to `/compile-promise` **or** applies server-provided policy for that option.  
3. Confirm sheet refreshes from normalized DTO:
   - Human: `userFacingConfirmation.*` + `clarificationOptions`
   - Law: `internalPolicy` (+ flat `contentRules` / `suggestedAppRules` for PolicyEngine)
4. On Start, persist **`internalPolicy` + flat CommitmentPolicy fields only** — not option labels.  
5. Map preview → enforcement:
   - `internalPolicy.timeWindow` → session / calendar / permanent minutes  
   - `internalPolicy.surfaceRules` / `contentRules` → surface + content gates  
   - `internalPolicy.appRules` → package allow/block (internal)  
   - `internalPolicy.quotaRules` → shorts/reels/minutes quotas (`allow_first_n`)  
   - `internalPolicy.recoveryRules` → unlock / tamper hardness  
   - `internalPolicy.guardrails` → permanent guardrail flags  

Example: option **A** “Videos inside Chrome / browser” → appRules emphasize Chrome + browser video surfaces; options **B/C** expand or narrow video apps — still no packages in the card labels.

---

## “Change interpretation”

- Link/button re-opens option list or “Understand Promise” again  
- Does not wipe typed promise  
- Voice transcript: same pipeline — show transcript as quoted promise, allow edit before Understand  
- Soft defaults (shorts → all short-form) live in **Check this**, not a forced dialog

---

## Voice flow

```text
mic → Azure Speech (or on-device) transcript
  → same Understand Promise path
  → cleanup + candidates + clarify + confirm
  → if transcriptConfidence < ~0.7: show uncertainty in Check this / safetyNotes
```

No separate enforcement path for voice.

---

## Copy sanitizer (required)

Any user-facing string must run through package-ID strip:

- Backend: `sanitizeUserFacingCopy` / `userFacingHasPackageLeak`
- Android: `ConfirmationUserCopy`

Eval metric: **packageLeakRate = 0** on confirm fields, options, questions, and notes.

---

## v08 envelope checklist (Android bind)

Required on compiler DTO for confirm UI:

- `cleanedPromiseText`, `userIntentSummary`, `ambiguityLevel`
- `clarificationRequired`, `clarificationQuestion`, `clarificationOptions[]`
- `recommendedInterpretation`, `alternativeInterpretations[]`
- `userFacingConfirmation` (understood / allowed / blocked / time / appliesTo / checkThis / safetyNotes)
- `internalPolicy`, `riskReview`, `hiddenInternalScope`
- `transcriptConfidence` (nullable), `detectedLanguage`
- `canStartCommitment`, `requiresStrongerConfirmation` / `isPermanentCommitment`
