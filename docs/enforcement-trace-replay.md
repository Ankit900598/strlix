# Phone Surface Trace Replay

**Why this exists:** Phone testing kept finding the same class of bug — one Accessibility dump, one wrong ALLOW/WAIT/BLOCK. That is firefighter mode. This harness replays realistic `packageName + screenText + stored settings` through the same deterministic laws Accessibility uses, without the phone and without AI.

```text
Accessibility snapshot
  → EnforcementTraceEvaluator
      safe apps → adult guardrail → session lock
      → PromiseEnforcementCoordinator (scope / blank tree / entertainment / media / shorts)
      → ShortFormQuotaGate
  → assert decision + reasonCode + surface/activity/durationSource
```

AI is not in this path. PolicyEngine / domain law is final.

## How to add a new phone bug

1. Copy the Logcat screen text (first 200–400 chars is enough if it has the player clock / URL).
2. Add one `EnforcementTrace` in `PhoneSurfaceTraceCatalog` with:
   - `id` — unique, snake_case
   - `packageName`, `screenText`, `goal`
   - `settings` already compiled (min/max/quota/brands/packages)
   - `expectedDecisions` / `expectedReasonCodes` / `forbiddenReasonCodes`
3. Run the replay test. It should **fail** on the unfixed bug.
4. Fix the domain law (parser, surface, scope, lock). Do not special-case one package.
5. Re-run. Commit the trace with the fix.

Example ids that encode the last three phone bugs:

- `chrome_yt_spoken_31m33_blocks_min40` — spoken `Time duration 31 minutes, 33 seconds` must BLOCK, not WAIT
- `chrome_shorts_locked_never_unrelated` — Chrome Shorts while LOCKED must not be `SESSION_LOCK_ALLOW_UNRELATED`
- `scope_content_chrome_not_official_only` — “YouTube video” is a brand, not `com.google.android.youtube` alone

## How to run

From repo root (set `JAVA_HOME` to Android Studio JBR on Windows):

```text
gradlew :app:testDebugUnitTest --tests com.phonecodex.app.domain.enforcement.trace.PhoneSurfaceTraceReplayTest
```

Full Android unit tests:

```text
gradlew :app:testDebugUnitTest
```

A failure prints: trace id, package, goal, first 200 chars of screenText, expected vs actual decision / reasonCode / surface / durationSource.

## Known gaps (still need the phone)

- Overlay flicker, own-package hide loops, MIUI freeform
- Accessibility service bind / heartbeat / Xiaomi 20s grace
- Real URL missing from some Chrome events until the next dump
- PiP / floating window / multi-window focus
- Install-time Play Store flows on a live device
- Tamper: user turns Accessibility off
- Vision counsel JPEG path (opt-in, not law)
- Backend compile of messy language (this harness assumes settings are already bound)
- English “longer than 40” vs stored min=40: law blocks when `seconds < 40*60`, so **40:00 allows**. A true `gt 40` floor would block 40:00; that is not changed here.
- Recommendation clocks after `More videos` (including `2:14 8:10`) must never become Clock B. The parser stops chrome-adjacent fallback once a rec section is split.

The harness proves **decision law** on frozen traces. It does not prove the service is bound or the overlay is visible.
