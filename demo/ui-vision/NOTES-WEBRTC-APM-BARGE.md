# WebRTC mic / APM barge polish (credit-burn sprint)

**Updated:** 2026-09-21 ~19:45 IST (Asia/Calcutta)  
**Surface:** desktop/web viewer `static/index.html` (phone-first Live orb — no outside chat UI)

## What shipped

| Piece | Path / flag | Notes |
|-------|-------------|-------|
| AudioWorklet VAD processor | `static/worklets/barge-vad-processor.js` | Runs off main thread; posts RMS / voiceMs / barge |
| Feature flag | `?bargeWorklet=1` **or** `localStorage.strlix_barge_worklet=1` **or** `window.__STRLIX_FLAGS.bargeWorklet=true` | Default **OFF** — preserves shipped AnalyserNode path |
| Fallback | Existing `ensureBargeMic` + `bargeLoop` (getUserMedia AEC/NS/AGC + AnalyserNode) | Always available |
| Azure Speech duplex STT | `/ws/stt` (unchanged) | Worklet is barge-gate only; STT still uses ScriptProcessor → PCM |

## Enable (dev)

```js
// In viewer console, or append ?bargeWorklet=1 to the URL
localStorage.setItem('strlix_barge_worklet', '1');
location.reload();
```

`window.__strlixLive.bargeStats` reports `{ path: 'worklet'|'analyser', ... }`.

## WebRTC APM path (documented)

Browser already requests:

```js
getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } })
```

That is the **browser WebRTC APM** (Chromium AEC3 / NS / AGC). TTS stays on an HTML `<audio>` element so the browser keeps a render reference for AEC. Do **not** route TTS through Web Audio if you want AEC to cancel speaker output.

Optional future (not shipped tonight): loopback `RTCPeerConnection` to force AEC graph when OS AEC is weak on a physical Android USB mic.

## Why feature-flagged

- AudioWorklet needs `audioWorklet.addModule` over **HTTPS or localhost**; some demo hosts are plain HTTP on LAN IP.
- Playwright fake devices do not exercise real AEC; physical-mic verification is the go/no-go for making worklet default.
- Avoid regressing the measured ≤120 ms hard-stop path (pause/clear TTS) that already ships.

## Verify

1. Flag off → Live → TTS → Talk / speak → meta `Barge-in Nms` (analyser path).
2. Flag on → same; `bargeStats.path === 'worklet'`.
3. If `addModule` fails → automatic fallback to analyser (caption may note it once).
