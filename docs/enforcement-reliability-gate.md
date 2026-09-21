# Promise Enforcement Reliability Gate

**Date:** 2026-09-13
**Goal:** one user promise must never randomly block passive screens, wrong apps,
home pages, recommendations, or ambiguous contexts.

Law recap:

```text
natural-language promise -> structured policy -> deterministic enforcement -> log/feedback
AI is counsel. PolicyEngine is law. Overlay is hand. Logs are witness.
```

---

## 1. Enforcement pipeline (exact path)

```text
Promise text (typed/voice)
  │  backend POST /compile-promise  (promiseCompilerService.js, prompt v07/v08)
  ▼
Compiled DTO + normalizeCompiledPromise  (fail-closed gates, leak strip, clocks)
  │  clarificationRequired=true  →  Start stays blocked (canStartCommitment=false)
  ▼
Confirmation UI (HomeScreen / PromiseUnderstandingCard)
  │  user picks option → server rematerialize → re-normalize → confirm → Start
  ▼
StudyWorldSettingsStore (stored policy: quotas, scope packages, thresholds, goal text)
  │
  ▼
PhoneCodexAccessibilityService.onAccessibilityEvent
  │  EnforcementEventGate: debounce CONTENT_CHANGED, skip blank/stale text,
  │  throttle + cache backend classification
  ▼
collectScreenText → EnforcementContext (single snapshot object)
  │  SurfaceDetector.detect → surface family + activity + duration evidence
  │  VideoDurationParser  → CURRENT_PLAYER vs RECOMMENDATION_IGNORED vs NONE
  ▼
Gate chain (deterministic, ordered):
  1. Emergency/safe apps          → always ALLOW
  2. PermanentGuardrailEvaluator  → adult/tamper law (strong signals only)
  3. SurfaceEnforcementGate       → passive video/system surface = hard PASS
  4. MediaLengthEnforcement       → active player only; WAIT without player clock
  5. ShortFormQuotaGate           → counts active short PLAYS only
  6. PolicyEngine app rules       → world/app allow/block
  7. Backend AI (counsel)         → only if gate CONTINUE; PASS may not be overridden
  ▼
OverlayLifecycleGate → show/keep/clear overlay
  ▼
EnforcementDecisionLog → pkg / surface / activity / rule / durationSource /
                         decision / reasonCode / count
```

## 2. Where false blocks can enter (audit result)

| # | Entry point | Guard |
|---|-------------|-------|
| 1 | Recommendation/thumbnail durations parsed as player clock | `VideoDurationParser` sources; media gate WAITs without `CURRENT_PLAYER` |
| 2 | Passive Home/Search/shelf text (“Shorts”, “Videos”) treated as behavior | `SurfaceDetector` strong-evidence rules + `SurfaceEnforcementGate` PASS |
| 3 | Backend AI WARN/BLOCK on passive screens | `aiMayWarnOrBlock(gate)=false` after PASS — service enforces both on sync and async callback paths |
| 4 | Launcher/system shade/tab switcher classified as violation | surface families `LAUNCHER` / `SYSTEM_SHADE` / `BROWSER_TAB_SWITCHER` → PASS |
| 5 | One-off app handling (NewPipe special-case) | `VideoPlatformRegistry` category (official YT, clones, browsers, social) |
| 6 | Length promise mutating into quota / study-mode | normalizer clock separation + `repairMediaLengthItemQuotas` |
| 7 | Ambiguous promise auto-starting | `clarificationRequired` ⇒ `canStartCommitment=false` (fail-closed seal) |
| 8 | Own-package a11y events hiding overlay | `OverlayLifecycleGate` own-package rules |
| 9 | Blank/stale a11y text triggering re-classification | `EnforcementEventGate.shouldSkipContentAndAi` |
| 10 | Neutral apps (WhatsApp/Drive) hit by permanent adult rule | guardrail requires strong adult signal, not app identity |

## 3. EnforcementContext (Phase 2)

One immutable object per screen snapshot answering:

- `packageName`, `surfaceFamily` (launcher/browser/youtube/video_client/social_feed/messaging/settings/play_store/unknown)
- `activityState` (passive / active_player / active_short_player / active_long_player / install_flow / settings_tamper / messaging_thread / unknown)
- `durationSource` (current_player / recommendation / none / ambiguous) + seconds
- `ruleBeingEvaluated` (rule id)
- `decisionSource` (deterministic / local_heuristic / backend_ai)

Invariant: a media-length BLOCK is constructible **only** with
`activityState ∈ {active_player, active_short_player, active_long_player}`
**and** `durationSource == current_player`.

## 4. Reason codes (Phase 4)

Every decision log carries machine-readable `reasonCode`, e.g.
`SURFACE_PASS_PASSIVE`, `MEDIA_WAIT_NO_PLAYER_CLOCK`, `MEDIA_BLOCK_UNDER_MIN`,
`QUOTA_ALLOW_COUNT`, `QUOTA_BLOCK_EXCEEDED`, `ADULT_BLOCK_GUARDRAIL`,
`AI_SUPPRESSED_BY_SURFACE_GATE`, `OVERLAY_CLEAR_CONTEXT_EXIT`.

## 5. Length polarity (2026-09-13)

`"allow only videos longer than 40 min"` is a **floor** (block shorts / under-40).
`"do not allow / except / block videos longer than 40"` is a **ceiling**.
`PromiseIntentRules` must not treat allow-only-longer as a max-length ban.

## 6. Ship gate

Reliability suite (`ReliabilityGateInvariantsTest`, 15 families) must stay green
before enforcement changes ship. Cross-app quota counting still requires the
phone harness pass (YT + NewPipe + IG + Chrome) per
`docs/android-promise-semantics-contract.md`.

**Phone installed:** `installDebug` succeeded on Redmi `2312DRAABI` (2026-09-13).
Offline unit tests are green. Phone checklist below is still required before
claiming live reliability.

## 7. Protection Reliability Gate (Home preflight, 2026-09-20)

Different from this document’s Surface/media-length gate. Home now proves the
enforcement *loop* is alive before any commitment test:

- Accessibility service enabled + (`RuntimeDiagStore` alive **or** heartbeat ≤45s)
- Active commitment **or** enabled permanent guardrail
- Backend kind is informational (does not override Protected)
- `Run protection check` refreshes those signals and logs; it does not Start

See `ProtectionReliabilityGate` + Home **Protection status** card.

## 8. Phone Surface Trace Replay (2026-09-21)

Offline replay of frozen Accessibility dumps through the same law chain
(safe → adult → lock → coordinator → quota). Add a failing trace before the
next phone fix. See `docs/enforcement-trace-replay.md`. This does not prove
overlay flicker or Accessibility bind.
