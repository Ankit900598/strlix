# Promise Confirmation (Android) — notes

Local on-device Promise Compiler preview for Strlix / PhoneCodex.

## What confirmation is

1. User writes a messy promise.
2. `FocusPromiseParser.parse` builds a `FocusPromise`.
3. `buildPromiseUnderstanding` maps it to human labels on `PromiseUnderstandingCard`.
4. If `needsClarification` → **Start Commitment is disabled**.
5. On Start → session duration + `AppRulesStore.applyCommitmentSuggestions` + session start.

## Session vs content duration

| Field | Meaning |
| --- | --- |
| `sessionDurationMinutes` | How long the commitment runs |
| `contentRules` with `operator`/`value` | Intra-app length (e.g. video longer than 40 min) |

Never map "longer than 40 min" into session length.

## Only-allow long video

`"only allow YouTube videos longer than 40 min"` →

- ALLOW `gt 40`
- BLOCK `lte 40`
- **No** clarification

`"allow … greater than 40"` without a shorter policy → clarification question.

## Vague promises → clarification

- `make me strict today` / `be strict today`
- `focus mode`
- `use insta less`

## Lean Advanced

Advanced opens session/permanent/recovery only. **Engineering tools** (app rules, safe apps, events, inspector, diagnostics, feedback) stay behind a second expand so Home stays light.

## Azure swap

Map Promise Compiler JSON → `FocusPromise` (including summary lists + clarification). Keep confirmation UI unchanged.
