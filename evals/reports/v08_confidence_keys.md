# v08 Confidence Keys — Ruthless Correctness Audit

**Date:** 2026-09-07 (updated: option rematerialize)  
**Scope:** Promise Compiler normalizer fail-closed gates + Android Start/confirm + surface/media-length enforcement  
**Rule:** Claim **100%** only where tests prove deterministic fail-closed behavior. Model intent is never 100%.

---

## Verdict (blunt)

| Layer | Certainty |
|-------|-----------|
| Deterministic normalizer Start/clarify/clock/leak/emergency gates | **Algorithmically certain** when these smokes/unit tests pass |
| Clarification option → enforceable scope rematerialize | **Algorithmically certain** for known Google-video / shorts-scope fingerprints + structured `internalPolicyPreview` |
| Model interpretation of messy language | **Probabilistic** — still needs evals + phone |
| Phone overlay / a11y / real YouTube/Chrome surfaces | **Not proven by this audit** — residual phone checklist below |

**Flag flip:** Safe to keep/use **v08 prompt + fail-closed normalizer** for confirm-before-start. **Not** safe to auto-wire compiler output straight into PolicyEngine without human confirm. Do **not** claim “works on phone” from this report alone.

---

## Confidence Keys

| ID | Statement | Proof location | Status |
|----|-----------|----------------|--------|
| **CK-CLARIFY-START** | `clarificationRequired ⇒ !canStartCommitment` | `backend/smoke_promise_compiler_v08.js` (staleStart, hi); `applyFailClosedStartGates` in `promiseCompilerService.js`; Android `computeCanStart` in `PromiseUnderstanding.kt` | **PASS** |
| **CK-HIGH-AMBIG** | `ambiguityLevel=high ⇒ clarificationRequired` | `smoke_promise_compiler_v08.js` (hi); normalizer forces flag | **PASS** |
| **CK-NO-PKG-LEAK** | No user-facing field matches package ID regex after normalize | `smoke_promise_compiler_v08.js` (leaky); `stripPackageLeaksFromDto`; `smoke_promise_compiler_normalize.js` `assertNoPackageLeak` | **PASS** |
| **CK-GOOGLE-VIDEO** | Ambiguous Google video ⇒ ≥2 options + `clarificationRequired` + `!canStart` | `smoke_promise_compiler_v08.js` (gv); `inferGoogleVideoClarification` | **PASS** |
| **CK-SHORTS-QUOTA** | “N shorts today” ⇒ daily quota shape; no invented 60-min session | `smoke_promise_compiler_v08.js` (shorts); normalize LIVE / tenShorts cases | **PASS** |
| **CK-MEDIA-VS-SESSION** | “videos under X for Y time” ⇒ media threshold X + session Y split; inverted min/max repaired | `smoke_promise_compiler_v08.js` (mediaSession BLOCK gt 30 + session 60); `repairMediaLengthItemQuotas` | **PASS** |
| **CK-NORMAL-EXCEPT** | “normal phone except porn” ⇒ not monk/study world | `smoke_promise_compiler_v08.js` (normalPhone); `repairNormalPhoneExceptSafety` | **PASS** |
| **CK-PERMANENT-PORN** | 1 year / permanent no porn ⇒ permanent + stronger confirm + `!canStart` soft-start | `smoke_promise_compiler_v08.js` (year); Android `CompiledPromiseMapperTest.permanentRequiresStrongerConfirmationBeforeStart` (checkbox unlock) | **PASS** |
| **CK-PASSIVE-SURFACE** | Passive surface never WARN/BLOCK/COUNT for media-length | `PassiveSurfaceEnforcementTest`, `ReliabilitySprintMatrixTest.matrix_passiveSurfaces_passMediaLength`, `SurfaceEnforcementGate` | **PASS** |
| **CK-PLAYER-DURATION** | Recommendation clocks never cause BLOCK | `VideoDurationParserTest`, `MediaLengthEnforcementTest`, `ReliabilitySprintMatrixTest.matrix_recommendationDurationsNeverBlock` | **PASS** |
| **CK-EMERGENCY** | Emergency exceptions never stripped by compiler normalize | `smoke_promise_compiler_v08.js` + normalize smoke; `normalizeEmergencyExceptions` → DTO field | **PASS** |
| **CK-OPTION-MAP** | Selecting clarification option rematerializes enforceable `contentRules` / `suggestedAppRules` / `scopePackages` / `internalPolicy` from `policyPreview`∪`internalPolicyPreview`; invalid id / missing usable preview never unlocks Start; user-facing copy stays package-free | `smoke_promise_compiler_v08.js` (afterPickChrome/All/Yt, missingPreview, shortsAll); `rematerializeDtoFromOptionPreview`; Android mapper + `MediaLengthEnforcement` scope gate | **PASS** |

---

## Bugs found + fixed

| Severity | Bug | Fix |
|----------|-----|-----|
| **P0** | Clarification option pick was preview-only — `contentRules` / scope unchanged after A/B/C | Server rematerialize on `selectedClarificationOptionId`: stamp packages, update `scopePackages` + `suggestedAppRules` + `internalPolicy`; fail-closed if no usable preview |
| **P0** | Permanent commitments could never Start after stronger-confirm checkbox: server always sent `canStartCommitment=false` and Android ANDed it forever | Android `computeCanStart`: after stronger ack, unlock locally even if server `canStart=false` (`PromiseUnderstanding.kt`) |
| **P0** | Invalid `selectedClarificationOptionId` still cleared clarify and unlocked Start | Only unlock when option id matches; else keep clarify + `!canStart` |
| **P0** | No final single-source Start seal — stale aliases / model `canStart=true` with clarify could theoretically diverge | `applyFailClosedStartGates()` always last in `normalizeCompiledPromise` |
| **P1** | `riskReview.requiresHumanConfirmation=true` alone did not force `!canStart` | Fail-closed: forces `!canStart` + stronger-confirm path |
| **P1** | Model `min_item_minutes` on “only allow video less than 30 min” inverted media law (BLOCK lt instead of BLOCK gt) | `repairMediaLengthItemQuotas` from raw text |
| **P1** | Package-ID strip not exhaustive on all nested user-facing fields | `stripPackageLeaksFromDto` final pass |
| **P1** | `emergencyExceptions` dropped from normalize DTO (CK-EMERGENCY hole) | Preserve via `normalizeEmergencyExceptions` on DTO |
| **P2** | Option pick did not prefer `policyPreview` for interpretation | Prefer `policyPreview` → `resultingPolicyPreview` → description |

---

## What is 100% guaranteed vs still needs phone

### Guaranteed (when tests green)

1. Clarification required ⇒ Start blocked (server + Android).
2. High ambiguity ⇒ clarification required.
3. User-facing copy after normalize has no `com.|org.|net.|io.` package IDs.
4. Ambiguous “Google video” injects ≥2 options and blocks Start.
5. “N shorts today” uses calendar-day window, not invented 60m session default caution.
6. Media length vs session length split + inverted min/max repair for clear under/over phrasing.
7. “Normal phone except porn” repaired out of monk/study lockdown shape.
8. Permanent / 1yr adult cannot soft-start without stronger confirmation UI.
9. Passive surfaces PASS for media-length; recommendation durations do not BLOCK.
10. Emergency exceptions array is not stripped by normalize.
11. Valid clarification option apply rematerializes enforceable scope (Chrome vs YouTube vs all-video; shorts all-surfaces vs YT-only); missing/invalid preview keeps Start blocked.

### Still probabilistic / phone-dependent

- Whether Azure/model emits correct quotas, clocks, and guardrails on messy Hinglish.
- Whether Accessibility text on real YouTube/Chrome/IG matches detector assumptions.
- Overlay flicker, PiP, tab switcher races, tamper disable.
- End-to-end: Speak → compile → confirm → Start → real BLOCK on device.
- Eval metrics (clarify recall ~60% strong on hard-core200) — **not** 100%.
- Unrecognized free-form option text without fingerprint / `internalPolicyPreview` still fail-closed (correct) but may feel stuck until rephrase.

---

## Residual risk (honest)

1. **Model still invents wrong intent** before normalizer — normalizer can only repair known shapes.
2. **Ambiguous phrases** (“don’t let me watch google video less than 30”) remain clarify-gated; after pick, scope is rematerialized for known Google A/B/C.
3. **Android still trusts server field shapes**; if API omits `clarificationRequired` but leaves options empty with a free-text question, Start stays blocked — good — but UX may feel stuck until re-understand.
4. **PolicyEngine auto-wire still OFF** by design — correct; flipping that without phone proof would be reckless.
5. **Default prompt env may still be v07** unless `PROMISE_COMPILER_PROMPT_VERSION=promise_compiler_v08` is set — set explicitly for product.

---

## Verification evidence (this audit)

```text
node backend/smoke_promise_compiler_normalize.js
→ ASSERTIONS_PASSED=142  ok=true

node backend/smoke_promise_compiler_v08.js
→ ASSERTIONS_PASSED=72   ok=true  (CK keys listed in JSON)

.\gradlew.bat testDebugUnitTest
  --tests com.phonecodex.app.domain.promise.*
  --tests com.phonecodex.app.ui.home.*
  --tests com.phonecodex.app.domain.enforcement.MediaLengthEnforcementTest
→ BUILD SUCCESSFUL
```

---

## Can Ankit flip the v08 flag safely?

**Yes for confirm-before-start lab/product path**, with:

```text
PROMISE_COMPILER_PROMPT_VERSION=promise_compiler_v08
```

**No for blind enforcement auto-start.** Fail-closed gates are airtight for the keys above; model + phone are not.

---

## Exact next phone verify checklist (residual only)

1. Set prompt to **v08**; compile “watch 10 shorts today” → calendar day, Start allowed, no 1h default caution.
2. Compile “block Google video less than 30 min for 1 hour” → must pick A/B/C; Start disabled until pick; after **Chrome only**, YouTube app short must **not** take the length law; Chrome player must.
3. Compile “normal phone except porn for 1 year” → permanent + checkbox; Start disabled until checkbox; not monk lockdown copy.
4. Compile “only allow video less than 30 min for 1 hour” → confirm card shows ~1 hour session + length rule (not 30m session).
5. On device with media-length promise: open YouTube **Home / Search / recommendations** → no BLOCK from thumbnail clocks.
6. Open active player over limit → BLOCK; under limit → ALLOW.
7. Permanent adult: confirm Start path; dialer / SOS still reachable (emergency not stripped).
8. Confirm package IDs never appear on confirmation card copy.

---

## Files touched this rematerialize fix

- `backend/promiseCompilerService.js` — `internalPolicyPreview`, rematerialize on option apply, shorts-scope options, fail-closed missing preview
- `backend/smoke_promise_compiler_v08.js` / `smoke_promise_compiler_normalize.js` — CK-OPTION-MAP rematerialize asserts
- `FocusPromise` / `CompiledPromiseMapper` / `StudyWorldSettings*` — `scopePackages` → enforcement scope
- `MediaLengthEnforcement` / `ShortFormQuotaGate` / Accessibility — respect rematerialized scope
- Android unit tests for mapper, understanding, media-length scope
- `evals/reports/v08_confidence_keys.md` / `v08_residual_risk_matrix.md`
