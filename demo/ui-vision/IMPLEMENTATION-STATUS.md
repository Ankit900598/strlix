# UI Vision — Implementation Status

**Updated:** 2026-09-21 19:45 IST (Asia/Calcutta)  
**Canonical vision:** `BILLION-USER-UI.md` (+ `CLAUDE-UI.md`)  
**Shipped screenshots:** `demo/ui-vision/shipped/`  
**Replay GIFs:** `demo/replay/`

---

## Shipped

### Pass A — Ask-in-bezel + Android chips + Azure primary
| Item | Status |
|---|---|
| Desktop ⌘K Ask **inside** bezel; narration strip; no side chat | **Shipped** |
| Android chips (Open Chrome / Go home / What’s on my screen?) | **Shipped** |
| Chat as launcher; Do-mode strip | **Shipped** |
| APK Azure primary + localhost fallbacks | **Shipped** (emulator falls back — no WAN) |

Screens: `desktop-ask-in-bezel.png`, `desktop-cmdk-hint.png`, `desktop-narration.png`, `android-chips.png`, `android-do-mode.png`.

### Pass B — Live barge-in + Replay/Share GIF (this pass)
| Item | Status |
|---|---|
| Desktop Live: VAD barge-in while TTS plays (AnalyserNode + AEC getUserMedia) | **Shipped** |
| Hard-stop TTS ≤120ms (measured **~1ms** pause/clear in Chromium) | **Shipped** |
| Talk-during-TTS = barge then listen (push-to-talk preserved when idle) | **Shipped** |
| `POST /voice/barge` + WS `barge` broadcast to all laptop clients | **Shipped** |
| Android LiveActivity: Talk / speech-start while “speaking” cue → `PilotClient.barge()` | **Shipped** (TTS still plays on laptop only) |
| Replay step log during Ask / Live turn (localStorage + in-memory) | **Shipped** |
| Capture live frames during Do; **Share** → animated GIF via `POST /replay/gif` | **Shipped** |
| GIF under `demo/replay/` with step captions + S watermark; toast + download link | **Shipped** |

Screens: `desktop-live-barge-ready.png`, `desktop-live-tts-playing.png`, `desktop-live-barge-in.png`, `desktop-narration-share.png`, `desktop-replay-share-toast.png`, `android-live-barge.png`, `replay-sample.gif`.

### Pass C — Live presence orb
| Item | Status |
|---|---|
| Desktop Live presence orb inside the phone bezel (no outside modal/chat) | **Shipped** |
| Desktop orb docks to a 48px top-left presence while a Live turn is acting | **Shipped** |
| Three presence controls (type, stop, mute); transcript drawer closed by default | **Shipped** |
| Android Live orb strip with listening/thinking/speaking states and the same three controls | **Shipped** |
| Azure Speech true duplex streaming STT | **Shipped** — Azure Speech SDK 1.51.2, `speech-zevi-strlix` / `eastus2`, `/ws/stt` accepts 16 kHz mono PCM and returns interim/final transcripts; browser Web Speech remains the fallback if Azure is unavailable |

### Pass D — APM-aware browser barge gate
| Item | Status |
|---|---|
| Adaptive VAD uses the existing browser WebRTC AEC/NS/AGC path, learns the TTS residual floor, and measures real elapsed time instead of assuming 60 Hz `requestAnimationFrame` | **Shipped** — no new audio dependency or server/Azure path; AEC settings are exposed through the dev hook for physical-mic verification |
| Azure duplex STT capture reuses the existing `MediaStreamAudioSourceNode`; TTS remains an HTML media element so browser AEC keeps its render reference | **Shipped** |

This is the smallest high-impact APM step recommended by Claude Code. It improves false-barge resistance and makes the voice gate display-rate independent without replacing the shipped Azure `/ws/stt` path. The 220 ms AEC convergence guard means the strict ≤120 ms barge measurement applies after the guard; loopback `RTCPeerConnection` AEC and AudioWorklet capture remain deferred until a physical-device test shows they are needed.

Screens: `desktop-live-orb-idle.png`, `desktop-live-orb-docked.png`, `desktop-live-transcript-open.png` (Android orb screenshot requires a connected device).

Duplex STT is live: the project venv and `requirements.txt` include `azure-cognitiveservices-speech`; `/ws/stt` streams browser PCM to `speech-zevi-strlix` using `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` (env values verified against `az` for `rg-zevi-cloudphone`).

**Verify:**
- Barge: open Live → play TTS → speak or tap Talk → meta shows `Barge-in Nms · listening`; audio stops.
- Share: Ask something → Share on narration strip → toast `Replay ready · N frames` → Open GIF.

---

### Pass E — Full Replay scrub + trust controls
| Item | Status |
|---|---|
| In-bezel Replay sheet with per-step scrubber, previous/next, play, and selected-screen preview | **Shipped** |
| Per-tap / per-swipe / navigation timeline events with the screenshot seen around each action | **Shipped** |
| Undo where a safe inverse exists (vertical scrolls); irreversible taps, typing, and navigation are clearly non-undoable | **Shipped** |
| One-tap **Turn off** revoke preserves unrelated accessibility services and disables Strlix control | **Shipped** |
| Existing Live orb, Azure STT, browser AEC/barge-in, and GIF Share path preserved | **Verified** |

Screens: `desktop-replay-scrub.png`, plus the existing `desktop-narration-share.png` and `desktop-replay-share-toast.png`.

### Pass F — Android Replay share sheet
| Item | Status |
|---|---|
| Android Ask captures bounded host-phone replay frames and exports through `POST /replay/gif` | **Shipped** |
| Android Live exports its settled replay without changing orb, STT, or barge behavior | **Shipped** |
| Android `ACTION_SEND` GIF share sheet via `FileProvider` content URI | **Shipped** — requires the host pilot/ADB frame path; Azure android-api-only sessions show a friendly fallback |

Implementation notes: the Android session polls `/adb/preview.json?quality=50&max_width=360` on a cancellable 700 ms loop, caps at 24 frames, and resolves the pilot's relative GIF URL against the endpoint that created it. The exported GIF is written to app cache and shared with URI read permission; no MediaProjection permission was added.

## Pass G — Golden-intent evaluation harness (2026-09-21 IST)

| Item | Status |
|---|---|
| Canonical list of 12 golden intents from the vision docs | **Shipped** — `demo/ui-vision/golden-intent-eval/intents.json` |
| Safe android-api contract/proposal runner | **Shipped** — `scripts/golden_intents_eval.py` |
| Legacy Pilot runner | **Shipped** — same runner with `--backend pilot`; explicit `--allow-device-actions` gate because Pilot executes real ADB tools |
| JSON + Markdown evidence | **Shipped** — `demo/ui-vision/golden-intent-eval/reports/android-api-latest.{json,md}` |
| Minimal fixture APK + provider | **Shipped** — `com.zevi.goldenfixture` installed on `127.0.0.1:5555`; `scripts/run_golden_fixture.py` verifies all 12 synthetic flows |
| Measured android-api run | **12/12 contract (100%)**, **12/12 plan (100%)**, **12/12 fixture-backed E2E (100%)** (2026-09-21 17:04 IST) |
| 95% golden-intent completion target | **Met for the offline synthetic fixture** — 100% (12/12); this is not a claim about real Gmail/Chrome/Photos accounts |

The runner keeps contract, plan, and completion scores separate. It is read-only by default: android-api proposals are not executed, and destructive intents stop at the fixture/confirmation gate. The connected emulator is `127.0.0.1:5555` at 1080×2400 with 225 packages and is reachable; `com.zevi.goldenfixture` is installed and the provider emitted strict evidence for every listed postcondition. The included fixture is an offline synthetic review-safe screen: it never opens real apps/accounts or performs irreversible actions. The Pilot HTTP path was not run against the live device because its ADB tool loop can mutate state. Live orb, STT, Replay, barge-in, and Android share paths were not changed.

**Claude Code design basis:** separate contract/E2E axes, canonical `a11y_*` ↔ `adb_*` tool mapping, explicit destructive-action boundary, bounded safe-launch planning fallbacks for clear ambiguous requests, and a fixture-gated denominator. The four prior plan failures now begin with truthful reversible app discovery (Gmail/Chrome), while the evaluator records blockers rather than claiming a false 95%. The fixture provider preserves the same distinction: its 12/12 is real deterministic fixture E2E, not production-app completion.

## Pass H — Desktop hover-only bezel rail (2026-09-21 IST)

| Item | Status |
|---|---|
| Back / Home / Recents moved from the row below the bezel into a compact right-edge rail | **Shipped** |
| Rail hidden at rest, reveals from the bezel edge on hover/focus with 200 ms in / 120 ms out motion | **Shipped** |
| Fine-pointer keyboard focus, coarse-pointer/mobile visible row fallback, 44 px targets, and reduced-motion support | **Shipped** |
| Rail stays outside the phone screen hit layer and leaves Live orb, Azure STT, barge-in, Replay, and Share paths unchanged | **Verified by static review** |

The rail is a desktop chrome reduction, not a new control path: existing `data-key` navigation events remain intact. A small edge hint preserves discoverability without restoring a toolbar.

**Screenshot:** `demo/ui-vision/shipped/desktop-hover-rail.png` (captured when the local viewer was available).

## Pass I — Ask-to-narration morph (2026-09-21 IST)

| Item | Status |
|---|---|
| Ask pill and narration share one mounted desktop-bezel dock | **Shipped** |
| Submit morphs the pill skin into the narration band without an overlay/strip handoff | **Shipped** |
| Ask focus, Esc/scrim dismiss, in-flight multi-step narration, and dismiss generation guard | **Shipped** |
| Narration-strip Share is wired to the existing Replay/GIF export path | **Shipped** |
| Live orb/STT/barge, Replay, hover rail, and golden harness paths unchanged | **Verified by static review + browser flow** |

The dock keeps its single bezel position and crossfades the Ask controls into narration while animating the border, radius, glow, and bottom offset. The narration stop action invalidates the active Ask generation so delayed tool ticks cannot reopen it. Existing Live, Replay, navigation rail, and replay capture layers retain their z-order and event paths.

**Screens:** `demo/ui-vision/shipped/desktop-ask-morph-ask.png`, `desktop-ask-morph-narration.png`.

## Pass J — Desktop continuity: drag/drop + clipboard (2026-09-21 IST)

| Item | Status |
|---|---|
| Drop files onto the phone-first bezel; push to `/sdcard/Download` without overwriting collisions | **Shipped** — multipart upload, 50 MiB cap, basename sanitization, `(1)`… collision suffixes |
| Drop text / paste while the phone surface is focused; send to the focused Android field | **Shipped** — real clipboard + paste through the Strlix helper when installed, explicit `adb input` fallback |
| Device → host clipboard action | **Shipped where Android permits** — `Ctrl/Cmd+Shift+C` requests one copy; browser writes only after that user gesture |
| Minimal in-bezel drag state and transfer feedback | **Shipped** — no tray/sidebar; Replay, Ask morph, hover rail, Live/orb layers stay separate |
| Android clipboard receiver | **Shipped** — `ClipboardBridgeReceiver` in debug APK; built, installed, and exercised on `127.0.0.1:5555` |

**Claude Code design basis:** the continuity target is the phone viewport, not desktop chrome; transfer state is `idle → dragging → transferring → done/error`; files are sequential and no-overwrite; clipboard is single-shot, not a live watcher. The browser never reads host clipboard on load and device clipboard is written back only after an explicit copy gesture.

**Screens:** `demo/ui-vision/shipped/desktop-continuity-idle.png`, `desktop-continuity-drop.png`.

**Verification:** `./gradlew :app:assembleDebug` passed; the receiver APK installed; ADB set/get round-trip passed while Strlix is foreground; `/adb/push` and `/adb/clipboard` smoke tests passed; a Playwright browser drop reached `/sdcard/Download` and was cleaned up; browser text bridge round-tripped through the device clipboard; a background clipboard read returns truthful HTTP 501 because Android blocks ordinary apps from reading clipboard while not foreground. Live orb/STT, barge-in, Replay/GIF Share, hover rail, Ask morph, and golden-intent files were not changed.

## Pass L — Needs-you handoff (2026-09-21 IST)

| Item | Status |
|---|---|
| In-bezel Needs-you pill with countdown, frozen phone stage, and pulsing target ring | **Shipped** |
| Login, CAPTCHA, permission, and payment copy with exact-screen / trust framing | **Shipped** |
| Deep-link acknowledgement, explicit Not now path, and task-plane auto-resume events | **Shipped** — `needs_you` / `needs_you_resolved` WebSocket messages plus `/chat` `needs_you` payload |
| QA hook for deterministic review variants | **Shipped** — `window.__strlixNeedsYou.demo('login'|'captcha'|'permission')` or `?needs-you=...` |

The handoff stays inside the phone bezel: no side panel, no guessing, and no background action while the user is deciding. The highlighted target accepts normalized `target.x` / `target.y`; the primary action emits `strlix:needs-you:ack` and the task plane closes the surface on completion. Verified with `node --check` and the local viewer serving the updated HTML.

## Pass N — Scheduled Ask + notification triage (2026-09-21 IST)

|| Item | Status |
|---|---|
| Phone-first notification triage strip with honest, user-controlled actions | **Shipped** | In-phone strip offers **Open notifications** and **Ask Strlix to triage**; it never reads or auto-acts on notification content without the user's choice. |
| Simple recurring Ask | **Shipped** | Daily/weekly cadence, local time picker, persisted schedule, edit/pause summary, and visible Android reminder with **Open Ask**. |
| Scheduled Ask safety boundary | **Shipped** | A reminder opens the Ask with the request prefilled; it does not run a hidden background agent (async tasks remain later). |
| Accessibility / phone-first continuity | **Verified** | Existing Ask, Do strip, Replay/share, Live, and accessibility paths remain in the same phone surface. |

Design basis: Claude Code timed out during this pass, so implementation follows the accepted `BILLION-USER-UI.md` rules: AI stays inside the phone, one compact daily-loop surface, point-of-need control, and no outside chat cockpit.

**Evidence:** `demo/ui-vision/shipped/android-scheduled-triage.png`; debug APK built and installed on emulator `127.0.0.1:5555`.

## Pass O — iOS viewer stub + async task status (2026-09-21 IST)

| Item | Status |
|---|---|
| iOS phone-first viewer shell | **Shipped** — `wrappers/ios/StrlixShell.xcodeproj` opens in Xcode and loads the shared HTTPS `web-market` surface through SwiftUI/WKWebView. |
| iOS security boundary | **Shipped** — ATS remains strict and the navigation delegate rejects non-HTTPS schemes; host, signing, Store capabilities, and production metadata remain explicit setup work. |
| Minimal async task status API | **Shipped** — market-api `POST /v1/jobs` creates an authenticated, process-local job and `GET /v1/jobs/{job_id}` exposes `queued → running → done`. |
| Phone-first UI polling bridge | **Shipped** — `window.StrlixJobs.create/get/poll` in `web-market/js/market.js`; only allow-listed kinds cross the boundary, with no prompt/chat/device payloads or outside chat. |

The iOS project is a developer-openable scaffold, not an App Store artifact. Async status is intentionally a small privacy-safe seam for UI polling; durable queues, retries, cancellation, and worker execution remain later work.

## Pass P — On-device model + `ROLE_ASSISTANT` honest seams (2026-09-21 IST)

|| Item | Status |
||---|---|
|| On-device model architecture, constraints, privacy, and rollout path | **Shipped** — `demo/ui-vision/ON-DEVICE-AND-ASSISTANT.md`; no model is bundled or implied |
|| Android on-device model interface and unavailable provider stub | **Shipped** — `OnDeviceModel` + `UnavailableOnDeviceModel`; checked-in build flag is `false` and the stub never fabricates output |
|| `ROLE_ASSISTANT` inspection/request seam | **Shipped as a disabled hook** — `AssistantRoleHook` can be reviewed later, but it does not launch consent, claim the role, or add a qualifying service/filter |
|| Play-safe Android surface | **Verified by static review** — no new permissions, model downloader, `VoiceInteractionService`, `ACTION_ASSIST`, or background listener |

Pass P is an architecture handoff, not production on-device inference and not an
Android assistant-role claim. `ROLE_ASSISTANT` remains ungranted until a future
build qualifies, obtains explicit system consent, and verifies
`RoleManager.isRoleHeld()` on a real device. See
`ON-DEVICE-AND-ASSISTANT.md` for the constraints, privacy checklist, and staged
path.


## Pass Q — Credit-burn: payments + barge worklet + hardening + latency (2026-09-21 IST)

| Item | Status |
|---|---|
| market-api payments module (Stripe Checkout + webhook stub, intent id storage, RLS migration) | **Shipped** — `services/market-api/market_api/payments.py`, `migrations/005_payment_intents.sql`; default TEST; live triple-gated (`PAY_MODE` + `PAYMENTS_LIVE` + `ALLOW_LIVE_CHARGES`) |
| Key Vault flip runbook (no secrets in git) | **Shipped** — `infra/hardening/PAYMENTS-KEYVAULT.md` |
| web-market PAY pill refreshes from `/v1/payments/status` | **Shipped** |
| AudioWorklet barge VAD (feature-flagged) + WebRTC APM notes | **Shipped** — `static/worklets/barge-vad-processor.js`, flag `?bargeWorklet=1` / `localStorage.strlix_barge_worklet`; falls back to AnalyserNode + Azure `/ws/stt` unchanged |
| Front Door + WAF / Redis / PE / Entra hardening scripts | **Shipped (IaC/docs)** — `infra/hardening/*`; dry-run default; not applied to Azure tonight |
| Real-device &lt;100ms path doc | **Shipped** — `demo/latency/REAL-DEVICE-SUB-100MS.md` |
| GPU worker | **NO-GO** — quota unchanged |

Phone-first constraint preserved: no outside chat UI. Live charges remain impossible until Ankit flips all three gates and loads live keys from Key Vault.

## Deferred (still backlog vs vision)

### Wow-now remainder
- Loopback `RTCPeerConnection` AEC (deferred). AudioWorklet **barge VAD** is now flag-gated (Pass Q); STT capture still ScriptProcessor until physical-device evidence favors worklet for PCM too
- APNG option
- 12 golden intents @ ≥95% E2E completion in real apps (offline synthetic fixture now 12/12; production-app provider remains deferred)

### Next / later
- Production iOS hardening (Sign in with Apple when gated, deep links, TestFlight/App Store metadata)
- Durable async workers, retries/cancellation, and the later “While you were out” digest
- Bring Strlix home (a11y rehearsal)
- Production on-device model: runtime/model selection, signed delivery, evaluation, performance, and privacy gates remain later; Pass P is only the disabled seam
- `ROLE_ASSISTANT`: qualifying component, current Play/policy review, explicit system consent, real-device verification, and revocation UX remain later; it is **not granted**

### Explicitly not building
- Outside web chat column / cockpit side panel
- Chat threads / New chat / model picker in main UI
- Engineer token/latency/JSON bubbles in product UI

---

## Notes for next agent
1. Pilot `:8787` owns `/voice/*` and `/replay/gif`. Restart uvicorn after `app/main.py` changes (no `--reload`).
2. Emulator has **no external network** — Azure chat primary fails DNS → localhost reverse.
3. Barge mic needs browser permission; Playwright uses fake device. Real barge VAD needs a physical mic + AEC.
4. Test hooks: `window.__strlixLive.playHostAudio / doBargeIn / stopTtsImmediate / bargeStats` (dev only). `bargeStats` reports `path` (`analyser`|`worklet`), RMS, floor, threshold, voiceMs, APM. Enable worklet via `?bargeWorklet=1`.
5. Keep TTS on the HTML `Audio` element; do not route it through Web Audio, because browser AEC may lose the render reference.
6. Claude judgment (prior): pointer-events Ask transitions and 17sp input remain; the hover rail is shipped in Pass H with focus/mobile fallbacks.
