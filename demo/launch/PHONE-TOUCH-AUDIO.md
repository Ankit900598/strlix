# Phone touch, audio, and latency (soft launch)

Verified against the live stream on 2026-09-22 by reading
`wss://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/ws/audio` and `/ws/h264`.

## What was actually broken

**Sound.** scrcpy sends one Opus identification header (`OpusHead…`, 19 bytes,
48 kHz stereo) and then raw Opus packets (not Ogg). The browser wire left
flags bit 0 clear on that header, so WebCodecs `AudioDecoder.decode()` was
handed `OpusHead` as if it were audio. Chrome reports that as
`Opus decoder: Decoding error` and closes the decoder, so later valid packets
never play and the speaker stays red. A 3-byte packet `fc ff fe` is a real
(tiny) Opus frame — libopus decodes it to 960 samples. It was not the bug.

The emulator start script also passed `-no-audio`. That removes the guest
audio HAL, so playback capture stays silent even after framing is fixed.
Restart the AVD **without** `-no-audio` (a Pulse null sink is enough; the VM
does not need speakers).

**Picture.** A captured `/ws/h264` GOP decoded in ffmpeg with zero warnings
(home screen, 486×1080). The severe YouTube blocking matches the viewer
dropping P-frames whenever `decodeQueueSize > 1` and then **continuing to
decode the next P-frame**. That breaks the reference chain until the next
IDR. The fix waits for a keyframe instead of painting garbage, and asks the
encoder for an IDR only if none arrives within 1.5 s. Annex-B is normalized
to 4-byte start codes. scrcpy is no longer sticky-disabled after one error
(screenrecord IDRs are rare and look like a stuck glitch).

On `emulator-*`, requested fps above 30 and bitrate above 1.8 Mbps are
clamped. `SCRCPY_MAX_FPS=90` and `H264_BITRATE=2500000` on the swiftshader
AVD make the encoder miss deadlines; the browser then drops references.
GPU / Redroid serials are not clamped.

**Touch.** Taps use the painted video rectangle, plus
`visualViewport` offset when the mobile URL bar shifts the viewport. Finger
slop is 28px so a slightly moving tap is not sent as a swipe. The market
keeps the phone in an iframe (Close stays available). The “Waking” layer
does not receive pointer events and hides on iframe load or
`strlix-first-frame`.

## How to verify after deploy

```bash
curl -sS https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/health | jq '{version,audio,h264:.h264|{source,fps,kbps,frame_age_ms,misflushes,scrcpy_disabled,bitrate,scrcpy_max_fps},client_debug}'
```

1. Open the market, tap **Open phone**. The bezel should show the stream
   without a stuck Waking card. Tap an icon; the corner should read
   `tap x,y · Nms` and the icon should hit.
2. Tap the speaker. The banner must not stay on `Opus decoder: Decoding error`.
   With the emulator restarted without `-no-audio`, YouTube audio should come
   out of this device. `/health` → `audio.codec=opus`, `audio.config_packets≥1`,
   `audio.packet_rate` moving, `client_debug.audio_error` empty.
3. Play a YouTube video for 20 seconds. Picture should not freeze into
   macroblocks. `h264.source` stays `scrcpy`, `misflushes` stays near 0,
   `client_debug.h264_error` empty.

`POST /debug/client` is what the viewer uses to fill `client_debug`. It does
not change the stream.

## Latency: what this PR can and cannot do

Soft-launch physics, Azure VM `vm-zevi-cloudphone` in `rg-zevi-cloudphone`,
one emulator, swiftshader, viewers on the public internet via Front Door:

| Hop | Typical | Why it does not hit “10× a real phone” |
| --- | --- | --- |
| Encoder | 30–80 ms | CPU MediaCodec. `latency:int=1` and `priority:int=0` are on. They do not make swiftshader a GPU. |
| ADB + WebSocket + AFD | 40–150 ms+ | RTT from the phone to Azure, then a TCP forward. Not UDP. |
| Decode + paint | 15–40 ms | WebCodecs. We no longer add a second buffer of late P-frames. |
| Audio | ~30–80 ms | 20 ms Opus frames, ~30 ms jitter cap in the viewer. |

A handset on the same Wi-Fi drawing its own screen has none of those hops.
**This path will not feel like a local phone, and it will not feel like a
10× cloud gaming rig.** Browsing and YouTube should feel continuous (about
the cadence of a video call), not like a game.

What still needs the AWS GPU Redroid worker (or a real device on a low-RTT
link), not more websocket tuning:

- Glass-to-glass under ~50 ms (game-feel). That wants a hardware encoder,
  WebRTC (UDP, FEC, no AFD TCP buffering), and a region close to the user.
- Stable 60 fps while YouTube or a game is in motion.
- Many phones at once. This VM is one emulator.

WebRTC is the right next transport. It is not in this change: standing up an
SFU / encoder pipeline is a different service, and claiming it here would be
false. The wins that do ship are a correct Opus header, no corrupt P-frame
chain, scrcpy not stuck on screenrecord, emulator fps/bitrate caps, and taps
that land on the painted frame.
