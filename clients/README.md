# Strlix clients

Three apps, one phone. You open the app and you are on the cloud Android phone — video, sound, and touch. There is no chat column and no setup maze.

| App | How you control it | Where it runs |
| --- | --- | --- |
| Android | Fingers. Each finger becomes its own tap or swipe. | Capacitor WebView |
| iOS | Same as Android | Capacitor project. Signing is a Mac step. |
| Desktop | Mouse click and drag, scroll wheel, keyboard | Electron window |

They share `@strlix/stream-client` (the protocol) and `@strlix/player` (the screen).

## Soft launch

The apps open this stream host. It is the phone, not the market page.

- Stream: `https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net`
- Market (browser, separate): `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/`

`···` in the corner changes the host and remembers it. You do not need that on a normal launch.

## Build

Node 22+. From this `clients/` directory:

```bash
npm install
npm test          # protocol, coordinates, gestures, keyboard, sockets
npm start         # builds the player and opens the desktop window
```

Desktop window is a tall phone, not a maximized browser. F11 or the fullscreen button fills the display. Escape is Android Back. Arrows are the d-pad. Letters go to the focused field. Right-click is Back. The scroll wheel is a short swipe.

### Android

The native project is `mobile/android` (package `com.strlix.phone`). Linux can sync it. A device or emulator plus the Android SDK is what produces an APK.

```bash
npm run build
npm run android:sync
cd mobile
npx cap open android
```

In Android Studio: Run. Or, with a device attached and `ANDROID_HOME` set:

```bash
cd mobile
npx cap run android
```

The activity keeps the screen on and hides the system bars. The first tap anywhere on the picture starts the speakers. That is the browser autoplay rule: sound cannot start at process launch.

Back, Home, and Recents call `POST /adb/key`. Volume − / + call `VOLUME_DOWN` / `VOLUME_UP` on the phone, which is the volume that gets encoded into Opus.

### iOS

The Xcode project is already in `mobile/ios` (bundle id `com.strlix.phone`). CocoaPods is not installed on Linux, so `Pods/` is not in the repo. Signing still happens on a Mac.

On a Mac, Xcode 16 or newer:

```bash
cd clients
npm install
npm run build
npm run ios:sync
cd mobile/ios/App
pod install
open App.xcworkspace
```

Then:

1. Select the `App` target → Signing & Capabilities → your Team.
2. Bundle id is `com.strlix.phone`. Change it if that id is taken on your team.
3. Pick an iPhone and Run.
4. For TestFlight: Product → Archive → Distribute App → App Store Connect → Upload. In App Store Connect, add the build to TestFlight. The first upload needs an Apple Developer account ($99/year). No store listing is required for internal TestFlight.

iOS plays video through WebCodecs (`VideoDecoder`), which Safari has had since 16.4. Opus uses `AudioDecoder`. That API is in the Android WebView and in Electron. It is not in every iOS WebKit. If the status line says the WebView cannot decode Opus, video and touch still work; sound needs a newer WebKit or the Android/desktop app. Do not ship a silent iOS build to TestFlight without checking that line on a real phone.

## What the library understands

`/ws/h264` and `/ws/audio` use the same 16-byte little-endian header (`struct <BBHId` in `app/h264_stream.py` and `app/device_audio.py`):

```
u8 version (1) | u8 flags | u16 reserved | u32 sequence | f64 pts_us | payload
```

Bit 0 does not mean the same thing on both sockets:

- Video: bit 0 = keyframe. Payload is Annex-B H.264.
- Audio: bit 0 = codec config. Payload is Opus (or PCM if the server says so).

**OpusHead / OpusTags are config even when flags = 0.** Production has sent those headers with the flag clear. Feeding them to the decoder errors it, and every later packet goes silent. `routeAudioPacket` sniffs the 8-byte magic first. The server-side fix can land separately; the clients already tolerate the bug.

Taps use the **device** size from the hello message (1080×2400 on the soft-launch emulator), not the encoder picture (often ~480×1080). `input tap` is in device pixels. Mapping through the encoder size puts every tap in the corner.

Two fingers are two contacts. Each one becomes a tap or a swipe when that finger lifts, because the public API is `POST /adb/tap` and `POST /adb/swipe`. There is no touch-down/move/up stream, so a pinch is not a real two-pointer gesture on Android. The contact book already tracks pointer ids for a future channel that can.

WebRTC is named (`StreamTransport`) and not implemented. A later peer should emit the same `WireHeader` values. The player would not grow a second decoder.

## Latency, honestly

Nothing here beats the network plus the encoder. A tap is:

1. The HTTP POST to the stream host (one RTT, plus ADB).
2. Android `input` injecting the event.
3. The encoder emitting an access unit when the screen changes.
4. Decode and paint on the device in your hand.

Measured from this workspace on 22 Sep 2026:

| What | Number | What it is not |
| --- | --- | --- |
| `GET /health` on the stream host | 0.66 s for one sample. Earlier the same day the spread was 157–986 ms (`demo/launch/PHONE-TOUCH-AUDIO.md`). | Not tap latency. Not glass-to-glass. |
| On-screen `tap x,y · Nms` in the web viewer | The HTTP round trip only | Does not include encode or decode |
| Decoder in headless Chrome against the live stream, 22 Sep 2026 | About 1 ms to decode a frame, about 13 fps once the join burst settled. Picture was 486×1080. A center tap mapped to device pixel 540,1200 on the 1080×2400 phone. | One machine, one sample. Open the app with `?debug=1` and read your own number. The join burst drops late deltas on purpose; that counter is not steady-state loss. |

The player drops non-key frames when `decodeQueueSize > 1`, draws inside the decoder callback (it does not wait for the next animation frame), and keeps audio about 50 ms ahead, snapping back if it drifts past 350 ms. Those are latency choices. They are not a measured end-to-end budget. Add `?debug=1` on a run and read the decode number instead of guessing.

If `/health` says audio `source: error` or the status line repeats the server `reason`, the emulator has no guest audio (often it was started with `-no-audio`). The client cannot invent that sound. Restart the emulator without `-no-audio`.

## Where to read first

1. `stream-client/src/protocol.ts` — header, OpusHead defense, Annex-B → avcC.
2. `stream-client/src/coords.ts` — why taps use device pixels.
3. `player/src/main.ts` — wires sockets, fingers, and the keyboard to those two.

`npm test` in `clients/` is the check that the header still matches the Python struct and that a flags=0 OpusHead is config.

## Three questions for the morning

1. The live picture is 486×1080. Why is a tap in the middle of it `540,1200` and not `243,540`?
2. An audio packet starts with the bytes `OpusHead` and flags is 0. Why must the decoder not be given that packet as a sound frame?
3. Why is the phone visible before the first tap, but silent until that tap?
