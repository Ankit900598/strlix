# Android Alpha Readiness — Strlix / PhoneCodex

Date: 2026-09-06. Scope: local Android commitment OS (messy promise → confirm → enforce).

## Works (ship-ready enough for internal alpha)

- Promise confirmation card with **Time / Allowed / Blocked / Conditional / Need clarification / Cautions**
- Session duration vs content-duration separation in local parser
- Clarification gate blocks Start
- Only-allow long YouTube → ALLOW long + BLOCK shorter
- Instagram messages vs Reels surfaces (local rules)
- Commitment start resets app-rule overrides (no poison from previous promise)
- Instagram default is AI_DECIDE (not hard BLOCK)
- Broad Chrome allow → Chrome app rule ALLOW
- Drive / Docs / Gmail treated as safe / productivity (no false WARN on “no porn rest normal”)
- Shorts shelf ≠ Shorts player (content signals)
- Chrome YouTube duration over/under limit detection
- Advanced engineering collapsed; inspector lazy + viewport-gated poll
- Unit tests covering confirmation, intent rules, edge battery

## Fails / weak (do not trust yet)

- Azure Promise Compiler not wired — local regex parser is a preview, not production understanding
- Intra-app Instagram enforcement still thin (rules exist; live surface detection incomplete)
- YouTube “only Neso playlist” is a content rule hint, not real playlist identity matching
- Backend AI classify path still WARNs when offline (safe fallback) — feels naggy on unknown apps
- Permanent guardrails + year-long sessions are preview, not MDM-grade locks
- Overlay / Accessibility can be defeated by power users (Android platform limit)
- Custom app rules UI still manual; compiler→enforcement mapping incomplete for many apps
- Hinglish coverage is heuristic, not bilingual NLU

## Trust bugs found & status

| Bug | Status |
| --- | --- |
| Chrome “allowed” but WARN via policy/AI_DECIDE | Mitigated: broad allow → ALLOW; docs no longer imply Chrome |
| Only block YT>20 but Shorts wrongly blocked | Mitigated: length rules → AI_DECIDE app rule; `blocksShortForm` ignores pure length limits; rule reset on start |
| Drive/Docs WARN on unrelated promise | Mitigated: safe catalog + productivity allow + policy world allow list |
| Old Instagram BLOCK poisons new promise | Mitigated: `applyCommitmentSuggestions` clears overrides |

## Manual phone checklist

1. Enable Accessibility for PhoneCodex; confirm Home shows protection on.
2. Promise: `only allow YouTube videos longer than 40 min for next 2 hours` → Start enabled; Time=2 hours; Allowed/Blocked both mention 40.
3. Promise: `allow YouTube videos greater than 40 min for next 1 hour` → Need clarification; Start disabled.
4. Promise: `make me strict today` → clarification; Start disabled.
5. Promise: `kal OS exam hai only Neso Academy playlist 3 hours` → Start; Time=3 hours; YouTube conditional.
6. Promise: `no porn for 1 year rest normal` → Start; open Drive/Docs → ALLOW (no warn); adult site → block/guardrail.
7. Promise: `Instagram only for messages for 7 days. no reels` → Start; check Instagram rule AI_DECIDE.
8. Promise: `block YouTube videos longer than 20 min for next 1 hour` → Shorts player still not hard-blocked by “long video” rule alone; long video on Chrome YouTube over 20 → block when duration visible.
9. Open Advanced → engineering tools stay hidden until “Show engineering tools”.
10. With session active, open inspector → Current app, Promise, Decision, Source, Why, Signals, Backend status.
11. Start commitment A with Instagram blocked manually, end, start “no porn rest normal” → Instagram must not stay hard BLOCK from A.
12. Browse Accessibility settings during commitment → tamper/safe path does not brick Settings permanently.

## Android limits (honest)

- Accessibility is best-effort; OEMs differ; content tree text is incomplete.
- Cannot truly prevent uninstall / Safe Mode / second user without Device Owner.
- Chrome in-page YouTube duration depends on visible accessibility text.
- Background classification needs network; offline = soft WARN, not silent ALLOW forever.

## Azure Promise Compiler needs

1. Structured JSON → `FocusPromise` (session vs content rules, clarification, summaries)
2. Confidence + alternative interpretations for confirmation UI
3. Surface ontology: messages / reels / shorts / playlist / chrome_youtube
4. Hinglish + broken English same schema
5. Eval harness against PRODUCT_MEMORY examples before cutting over

## What NOT to ship to paying strangers yet

- “Permanent 1-year lock” marketing language
- Claims of 100% porn / Shorts blocking
- Unsupervised backend BLOCK without local confirmation
- Whole-device lockdown narrative

## Next 10 tasks (impact order)

1. Wire Azure Promise Compiler → `FocusPromise` behind feature flag
2. Live Instagram surface detector (messages vs Reels vs feed)
3. YouTube playlist / channel allowlist matching (Neso)
4. Silent ALLOW for unknown productivity when promise is narrow (reduce WARN spam)
5. PRODUCT_MEMORY golden tests in CI
6. Session end clears temporary app-rule overrides explicitly in UI copy
7. Chrome YouTube Shorts vs long-form on web
8. On-device telemetry of confirmation edit→start funnel (no PII)
9. One-tap “I meant: …” clarification chips
10. Device Owner / MDM path research for real hard locks (later)

## Build gate

`.\gradlew.bat testDebugUnitTest assembleDebug` must stay green before any alpha APK.
