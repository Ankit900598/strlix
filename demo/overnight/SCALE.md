# Strlix cloud-phone — scale & capacity (overnight)

**Device model:** one Android emulator (or one physical device) behind one ADB
serial (`127.0.0.1:5555` via SSH tunnel to Azure VM). The phone is the bottleneck,
not the FastAPI process.

## Hard limits (by design)

| Resource | Limit | Why |
|----------|------:|-----|
| Devices / ADB serials | **1** | Single emulator on VM; screencap/screenrecord is exclusive |
| Live stream viewers | **12** (`MAX_STREAM_CLIENTS`) | Memory + uplink; each viewer is cheap once frames are shared |
| Frame producer | **1 per path** | `H264Broker` (`screenrecord`, primary) + `FrameBroker` (JPEG, fallback) |
| H.264 viewers | **12** (`H264_MAX_CLIENTS`) | Accepted then closed 1013 past the cap, so clients fall back |
| Live frame disk writes | **0** | Only pilot/chat screenshots hit `demo/`, pruned to `SCREENSHOT_RETENTION` (40) |
| Tap/swipe/key | Concurrent OK | Short `adb shell input …`; `INPUT_RATE_PER_SEC` (30/s per IP, 429 past it) on tap/swipe/key/type/nudge |

## Latency budget (local box → emulator)

| Path | Typical | Notes |
|------|--------:|-------|
| ADB `screencap -p` | 230–350 ms | Hard floor for JPEG path |
| Pillow JPEG encode 480px | 40–70 ms | |
| Shared JPEG `/ws/stream` | ~280–330 ms frame gap | One producer; N readers |
| Cached `/adb/preview` | 1–50 ms | Serves last FrameBroker JPEG |
| `screenrecord` first IDR | 218–356 ms | Measured, from subscribe |
| H.264 device change → AU on the wire | 16–50 ms | Measured, while frames flow |
| H.264 AU → painted pixels (WebCodecs) | 7–34 ms | Measured in Chromium |
| H.264 trailing frame (screen goes static) | ~2 × `flush_tick_ms` (60–130 ms) | Annex-B has no length prefix; see `H264.md` |
| H.264 input → pixels, paired vs JPEG | **1027 ms vs 1858 ms** median | Same events, same instant; H.264 faster on 14/18 |
| Cloudflare quick tunnel RTT | +50–200 ms | Extra hop; not LAN |

## Backpressure policy (implemented)

1. **H.264 WS:** the producer never blocks on a client. Per-client queue is
   180 AUs / 4 MB; overflow drops the AU and sets `needs_key`, so a viewer that
   fell behind resumes at the next IDR instead of decoding against frames it
   never received. A key AU drains the backlog rather than being dropped.
   Verified: 12 viewers, identical AU sequences, 0 drops.
2. **Late joiners:** replay the bounded GOP buffer (≤3 MB / ≤600 AUs) for an
   instant picture; if it is bigger than 1 MB and the joiner is alone, restart
   the encoder for a fresh IDR instead (a restart would freeze other viewers
   ~700 ms, so it is never done while others are watching).
3. **JPEG WS:** shared latest frame; consumers read the newest published frame,
   so a slow client simply skips versions (latest-wins).
4. **MJPEG HTTP:** same shared frames; HTTP 503 at capacity.
5. **Heartbeat:** both sockets ping every 15 s and close a viewer that has not
   ponged in 40 s, which is what reclaims ghost-tab slots.
6. **Input:** short `adb shell input …`, never behind the capture lock —
   71–172 ms measured with 12 viewers streaming. Per-IP budget of
   `INPUT_RATE_PER_SEC` (30/s) on tap/swipe/key/type/nudge returns **429**, so a
   client stuck in a retry loop cannot pin the ADB serial.

## Ops knobs (env)

```
# JPEG fallback path
MAX_STREAM_CLIENTS=12
STREAM_INTERVAL_MS=250
STREAM_QUALITY=50
STREAM_MAX_WIDTH=480
SCREENSHOT_RETENTION=40

# H.264 primary path (app/h264_stream.py)
H264_ENABLED=1                 # 0 falls every viewer back to JPEG
H264_WIDTH=540                 # encoder width; height keeps the device aspect
H264_BITRATE=1500000
H264_MAX_CLIENTS=12
H264_SEGMENT_S=60              # re-segment => fresh SPS/PPS + IDR
H264_IDLE_STOP_S=10
H264_GOP_MAX_BYTES=3145728     # replay buffer ceiling
H264_GOP_MAX_AUS=600
H264_GOP_REPLAY_MAX_BYTES=1048576
H264_QUEUE_MAX_AUS=180
H264_QUEUE_MAX_BYTES=4194304
H264_FLUSH_IDLE_MS=30          # base idle-flush tick (self-calibrating upward)
H264_MAX_INTRA_GAP_MS=120
H264_KEYFRAME_COOLDOWN_S=2.5

# Both sockets
WS_PING_INTERVAL_S=15
WS_PING_TIMEOUT_S=40
```

## Health

- `GET /health` — ADB + voice + `stream` (JPEG) + `h264` summary
- `GET /adb/stream/stats` — JPEG producer, subscribers, capture_ms
- `GET /adb/h264/stats` — video producer, viewers, fps/kbps, GOP state,
  `misflushes`, `flush_tick_ms`, per-client queue/drops
- `POST /adb/h264/keyframe` — force a fresh IDR (rate-limited 2.5 s)

## What does *not* scale yet

- Multiple phones / multi-tenant routing.
- **The device is now the floor, not the host.** Raw measurement with no app
  code in the path: after a discrete keypress, `screenrecord`'s first bytes
  appear 23–589 ms later depending on when SurfaceFlinger composes. Beating
  that needs an encoder-side change (scrcpy-server / MediaCodec with
  `KEY_REPEAT_PREVIOUS_FRAME_AFTER`), not a host-side one.
- Rotation costs a producer restart (~700 ms freeze).
- Audio mirroring (intentionally none; TTS plays in the laptop browser).

## Public access

Quick tunnel: see `demo/public-url.txt`. Origin is `http://127.0.0.1:8787`.
STREAM_INTERVAL_MS=250
STREAM_QUALITY=50
STREAM_MAX_WIDTH=480
SCREENSHOT_RETENTION=40
H264_ENABLED=1
H264_WIDTH=540
H264_BITRATE=1500000
H264_MAX_CLIENTS=12
```

## Health

- `GET /health` — ADB + voice + stream summary
- `GET /adb/stream/stats` — producer running, subscribers, dropped frames, capture_ms

## What does *not* scale yet

- Multiple phones / multi-tenant routing
- True &lt;50 ms interactive video without scrcpy-server / MediaCodec closer to device
- Audio mirroring (TTS plays in browser; scrcpy audio off)

## Public access

Quick tunnel: `demo/public-url.txt`. Origin: `http://127.0.0.1:8787`.


## Measured H.264 (overnight, local)

- Producer: `screenrecord --output-format=h264 --size 540x1200 --bit-rate 1.5M`
- Endpoint: `WS /ws/h264` (WebCodecs); stats: `GET /adb/h264/stats`
- Steady: ~**7–13 fps** (static UI lower; motion higher), first_frame_ms ~**300**
- A/B open_app median: H.264 **497ms** vs JPEG **2013ms**
- Cloudflare adds ~50–150ms RTT on top of local numbers
