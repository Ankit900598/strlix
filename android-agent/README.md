# Strlix In-Phone AI Agent (`com.zevi.agent`)

**Vision:** Strlix replaces Google Search / Assistant on the home screen. People say or type anything; the agent can touch-control the screen when needed; the rest of the time the phone is normally touchable.

Package: `com.zevi.agent` · minSdk 30 · targetSdk 34 · version **0.3.0-live**

**Azure OpenAI keys never ship in the APK.** Chat goes to **android-api** (`POST /v1/chat` on port **8788**), with fallback to the pilot monolith (`POST /chat` on 8787).

## What’s in 0.2

| Feature | Status |
|---------|--------|
| Home App Widget — Google-style search pill (S + colored dots instead of G / Assistant) | Done |
| Tap widget → Strlix voice+text assistant (`ChatActivity`) | Done |
| `ZeviAccessibilityService`: tap, swipe, type, scroll, launch apps, Home/Back/Recents | Done |
| Enable a11y via `adb shell settings put secure` (emulator, no UI friction) | Done |
| Text chat solid; voice via `SpeechRecognizer` (graceful stub if no mic) | Done |
| Local commands preferred on-device; else host `gpt-5.6-sol` + ADB tools | Done |
| Floating overlay bubble | Done |
| Network probe: adb reverse → `10.0.2.2` → public HTTPS | Done |

## Requirements

- JDK 17+ (`JAVA_HOME`)
- Android SDK (`ANDROID_HOME`, build-tools 34, platform 30+)
- Emulator/device API 30+ (this env: AVD on `127.0.0.1:5555`)
- Host pilot: `cd /workspace/zevi-cloudphone && ./scripts/run-pilot.sh`

## Build

```bash
cd /workspace/zevi-cloudphone/android-agent
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
export ANDROID_HOME=/home/box/Android
./gradlew :app:assembleDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`

## Install, Accessibility, widget

```bash
./scripts/install-and-launch.sh
```

Manual:

```bash
ADB=/workspace/zevi-cloudphone/platform-tools/adb
SERIAL=127.0.0.1:5555
PKG=com.zevi.agent

$ADB -s $SERIAL reverse tcp:8787 tcp:8787
$ADB -s $SERIAL install -r app/build/outputs/apk/debug/app-debug.apk
$ADB -s $SERIAL shell appops set $PKG SYSTEM_ALERT_WINDOW allow
$ADB -s $SERIAL shell pm grant $PKG android.permission.RECORD_AUDIO

# Accessibility without Settings UI (emulator / userdebug)
$ADB -s $SERIAL shell settings put secure enabled_accessibility_services \
  $PKG/$PKG.ZeviAccessibilityService
$ADB -s $SERIAL shell settings put secure accessibility_enabled 1

# Open hub (requests pin widget) + assistant
$ADB -s $SERIAL shell am start -n $PKG/.MainActivity --ez pin_widget true
$ADB -s $SERIAL shell am start -n $PKG/.ChatActivity --ez from_widget true
```

**Add the search pill to Home:** In the app tap **Add search bar to Home**, confirm **Add automatically**, or long-press Home → Widgets → **Ask Strlix or type**. Place it at the bottom like the Google pill.

## On-device commands (Accessibility preferred)

Handled inside the phone before calling the host:

- `Go home` / `Back` / `Recents`
- `Open Settings` / `Open Chrome` / `Open <app name|package>`
- `tap <label>` / `type <text>` / `swipe up|down|left|right` / `scroll down`

Gesture commands (`tap` / `type` / `swipe`) move the Strlix task to the background so the target app stays focused, run via Accessibility, then reopen the assistant with the result.

Anything else → host `POST /chat` (Azure on host; ADB tools for complex UI).

## Desktop continuity bridge

The debug APK includes `ClipboardBridgeReceiver`, used by the desktop bezel over ADB for host→device clipboard and one-shot device→host export. Android only permits ordinary apps to read clipboard contents while Strlix is foreground; the desktop reports that limitation instead of returning a misleading empty value. Host files use ADB push directly to `/sdcard/Download`.

## Live voice (0.3)

- Chip **Live** on chat → `LiveActivity` (waveform session UI).
- Phone may capture mic (fallback); assistant TTS is synthesized on the **host** and played on the **laptop browser** (`POST /voice/turn`, `WS /ws/live`). Never phone `AudioTrack` / scrcpy audio.
- See `/workspace/zevi-cloudphone/demo/live-voice.md`.

## Voice

Mic button uses `SpeechRecognizer`. Emulators often lack a mic / recognition service — the app toasts and keeps the **text path** fully working.

## Network (no secrets in APK)

`PilotClient` probes in order (`app/build.gradle.kts`, v0.3.1-split):

1. `ANDROID_API_URL` = `http://127.0.0.1:8788` — needs `adb reverse tcp:8788 tcp:8788` (**preferred**)
2. `ANDROID_API_EMULATOR_URL` = `http://10.0.2.2:8788`
3. `PILOT_BASE_URL` = `http://127.0.0.1:8787` — fallback monolith (`adb reverse tcp:8787`)
4. `PILOT_EMULATOR_URL` = `http://10.0.2.2:8787`
5. `PILOT_FALLBACK_URL` — public HTTPS (keys stay on host)

Chat path: `:8788` → `POST /v1/chat`; `:8787` → `POST /chat`. Live voice falls back to pilot if android-api has no `/voice/turn`.


Do **not** embed `AZURE_OPENAI_*` in the APK.

## Screenshots

- `demo/strlix-widget-home.png` — single Strlix search bar on home
- `demo/strlix-assistant-open.png` / `zevi-assistant-open.png` — assistant open
- `demo/zevi-a11y-enabled.png` — Accessibility settings
- `demo/zevi-demo-chrome.png` / `zevi-demo-settings.png` / `zevi-demo-a11y-tap.png` — demos

Also copied under `/workspace/zevi-cloudphone/demo/`.

## Layout

```
app/src/main/java/com/zevi/agent/
  MainActivity.java              # hub, pin widget, permissions
  ChatActivity.java              # text + voice assistant
  ZeviSearchWidget.java          # home search pill provider
  ZeviAccessibilityService.java  # tap/swipe/type/scroll/launch
  LocalActions.java              # on-device command parser
  PilotClient.java               # host /health + /chat
  OverlayService.java            # floating bubble
  MessageAdapter.java
```

## Pass P boundaries

The Android project now contains an honest, disabled seam for a future
on-device model (`OnDeviceModel` / `UnavailableOnDeviceModel`) and a disabled
`RoleManager.ROLE_ASSISTANT` inspection seam (`AssistantRoleHook`). No model is
bundled, no model output is fabricated, no assistant role is requested or
claimed, and the APK does not declare `VoiceInteractionService` or
`ACTION_ASSIST`. The architecture, privacy constraints, and enablement gates
are documented in `../demo/ui-vision/ON-DEVICE-AND-ASSISTANT.md`.

## Gaps / next

- Emulator mic often unavailable — text is the solid path
- Widget pin: install script uninstalls first and pins at most ONE; app refuses a second pin
- Place widget at bottom of home manually for Google-pill parity (auto-pin lands mid-screen)
- Richer host↔a11y action protocol (structured tool calls back to device)
- Do not touch `phonecodex-*`; do not put Azure keys in APK; do not sign out Azure

## Dual-backend cutover (2026-09-21)

Prefer **android-api** for chat (no ADB stream on this path):

| Env | Base URL |
|-----|----------|
| Emulator → host android-api | `http://10.0.2.2:8788` (+ `adb reverse tcp:8788 tcp:8788`) |
| Emulator → legacy pilot | `http://10.0.2.2:8787` (still works) |

`POST /chat` and `POST /v1/chat` both work on android-api. Desktop viewers should use **desktop-api :8789**, not the phone chat API.
