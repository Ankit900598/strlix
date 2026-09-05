# Promise Compiler → Android integration notes

PhoneCodex confirmation UI does **not** call Azure yet. It uses an on-device preview compiler that already speaks the same product language as `evals/prompts/promise_compiler_v03.txt`.

## Layers

| Layer | Role |
|-------|------|
| `FocusPromiseParser` | Local compile: session duration ≠ content rules; asks clarification when intent is vague |
| `FocusPromise` + `ContentRule` | Domain shape the UI and (later) Azure both target |
| `buildPromiseUnderstanding` | Presentation only — never enforces |
| `HomeScreenState.startCommitment` | Refuses to start if `clarificationQuestion != null` |
| Accessibility / PolicyEngine / `/classify` | Real enforcement (unchanged by this slice) |

## Session vs content duration

- `for next 1 hour` / `for 7 days` / `for 1 year` → `sessionDurationMinutes`
- `videos longer than 40 min` / `> 20 min` → `contentRules` (`operator`, `value`, `unit`)
- Never let a content threshold become the session clock

## Clarification gate

If `FocusPromise.needsClarification`:

1. Confirmation card shows the question
2. **Start Commitment** is hidden
3. `startCommitment()` no-ops with a message if somehow invoked

Examples that must ask: `be strict today`, `use insta less`, allow-long-video without a shorter-video policy.

## Azure swap (next)

1. Keep `POST /draft-focus-promise` or add `POST /compile-promise` returning schema-compatible JSON (`evals/schemas/commitment_policy_schema.json`).
2. Add `PromiseCompilerClient` that maps JSON → `FocusPromise` (session duration from `duration`, content rules from `allowedContent`/`blockedContent`, `clarificationQuestion` from `followUpQuestion`).
3. In `HomeScreenState.understandPromise()`, call the network compiler first; on failure fall back to `FocusPromiseParser`.
4. Set `PromiseUnderstanding.source = PROMISE_COMPILER` when network wins.
5. Do **not** rewrite `PromiseUnderstandingCard` for the swap.

## Still local-only (honest gaps)

- Content length rules are confirmed in UI but not yet enforced frame-by-frame in AccessibilityService.
- Instagram “messages only” is a structured preview + `AI_DECIDE` app rule — true DM vs Reels classification still needs classifier/signals.
- Year-long commitments set session minutes; permanent guardrails remain the durable adult-content layer.

## Verify

```bat
.\gradlew.bat testDebugUnitTest --tests com.phonecodex.app.domain.promise.FocusPromiseParserTest --tests com.phonecodex.app.ui.home.PromiseUnderstandingTest
```
