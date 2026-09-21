# scrcpy-server as the H.264 producer (`H264_SOURCE=scrcpy`)

**Date:** Mon Sep 21, 2026 · **Status:** **shipped + tuned** (`H264_SOURCE=auto|scrcpy`, low-lat knobs; glass-to-glass &lt;100 ms still blocked by emu encode floor)

Same wire, same client. `scrcpy-server` replaces `adb exec-out screenrecord` as
the *byte source* behind `app/h264_stream.py`; the Annex-B parser, the AU
framing (`pack_au`), `/ws/h264`, and the WebCodecs client in
`static/index.html` are all untouched. The JPEG `/ws/stream` ladder and the
`adb shell input tap` control path are untouched too — scrcpy runs with
`control=false`, so it never competes for input.

```
scrcpy-server (device, app_process, AVC, raw_stream=true)
  → localabstract:scrcpy_<scid>
    → adb forward tcp:<port>          (local adb server, over the SSH tunnel)
      → H264Broker._segment_scrcpy: Annex-B → AUs → GOP buffer + fan-out
        → /ws/h264 → VideoDecoder → <canvas>      [unchanged from H264.md]
```

## Why bother — what scrcpy buys over `screenrecord`

| | `screenrecord` | `scrcpy-server` |
|---|---|---|
| Frame pacing | encoder default, no knob | `max_fps=60` |
| Encoder latency tuning | none exposed | `video_bit_rate`, `max_size`, codec opts |
| Recording time limit | `--time-limit 0` needed | none |
| Geometry | `--size WxH` (exact) | `max_size` (caps the long edge, rounds to /8) |
| Framing | Annex-B, no length prefixes | Annex-B raw, **or** 12-byte PTS+length headers if `raw_stream=false` |
| Deploy | nothing | push 717 KB jar, version-pinned to the client (`4.1`) |
| IDR on demand | restart only | restart only (no client-facing sync-frame request) |

The framing row is the real prize and we are **not** taking it yet:
`send_frame_meta` (i.e. `raw_stream=false`) would give per-frame length +
device PTS, which deletes the whole idle-flush / mis-flush machinery described
in `H264.md` §1 and replaces guessed timestamps with real ones. Deliberately
deferred — reusing the proven parser is what makes this patch small. See
[Next steps](#next-steps).

## Proven invocation (this box, 2026-09-21)

```bash
adb push /home/box/.local/scrcpy/scrcpy-server /data/local/tmp/scrcpy-server.jar
adb forward tcp:27183 localabstract:scrcpy
adb shell CLASSPATH=/data/local/tmp/scrcpy-server.jar \
  app_process / com.genymobile.scrcpy.Server 4.1 \
    tunnel_forward=true audio=false control=false cleanup=false raw_stream=true \
    max_size=1200 video_bit_rate=1500000 max_fps=60
# TCP connect → pure Annex-B H.264. No dummy byte, no device-meta header
# (raw_stream implies send_dummy_byte=0 / send_device_meta=0 / send_codec_meta=0).
# 540x1200. TTFB ~600 ms cold, then frames only when the screen changes.
```

Facts that shape the implementation:

- **`raw_stream=true` sends no dummy byte.** The parser must not skip a byte.
- **`i-frame-interval=1` is ignored by the emulator encoder.** IDRs stay rare,
  so the GOP-replay + restart-for-IDR logic from `H264.md` §2 still carries the
  whole late-joiner story. scrcpy does not make keyframes cheaper.
- **Version string must be exactly `4.1`** — it is checked against the jar's
  `BuildConfig`. Host binary confirms: `scrcpy 4.1`.
- **The jar is already on the device** and byte-identical to the host copy, so
  the push is skippable when `ls -l` size matches.

## Blockers

| # | Blocker | Impact | Status | Resolution |
|---|---|---|---|---|
| 1 | scrcpy GUI needs SDL + XDG_RUNTIME_DIR | no interactive mirror on this box | **open, out of scope** | not needed — we consume the server socket directly, no client binary |
| 2 | ws-scrcpy browser protocol | would replace our wire + client | **rejected** | non-goal; keep `/ws/h264` + `pack_au` |
| 3 | Three processes share one device (`app.main` :8787, `desktop-api` :8789, and a duplicate :8787 uvicorn) — each builds its own `H264Broker` | second server dies on `localabstract:scrcpy` already in use; `tcp:27183` forward collides | **must fix in patch** | per-process random `scid`, `adb forward tcp:0` (kernel picks the port) |
| 4 | Killing local `adb shell` does not reliably kill the device-side `app_process` | leftover Server holds the abstract socket → every later segment fails | **must fix in patch** | `pkill -f com.genymobile.scrcpy.Server` on segment teardown *and* in `aclose()`; `/system/bin/pkill` confirmed present |
| 5 | No client-facing IDR request in the scrcpy protocol | `keyframe-on-tap` costs a full server restart (~600 ms) instead of `screenrecord`'s ~250 ms | **open** | longer cooldown for scrcpy; serve the cached key AU to the asking viewer instead of restarting (see Next steps) |
| 6 | `max_size` caps the *long* edge and rounds to /8; `screenrecord` takes exact `WxH` | `H264_WIDTH=540` must be converted; reported `size` in stats is an estimate until SPS is parsed | **handled** | `max_size = round(width * long/short)`; cosmetic only — the client renders from `device_width/height` + SPS, not from `hello.width` |
| 7 | Browser drops to JPEG if no frame lands in 9 s (`static/index.html` watchdog) | a slow scrcpy→screenrecord fallback loses the H.264 path for that page load | **must respect in patch** | bound scrcpy startup at ~3.5 s and fall back on the *first* failed segment, not after N |
| 8 | Video and taps share one SSH-tunneled adb transport | a fat GOP can head-of-line block `input tap` | pre-existing, unchanged | same as `screenrecord`; watch it in the A/B |

## Measurements (this box, 2026-09-21 IST)

Method: WebSocket `/ws/h264` probe (AU header arrival) + `POST /adb/swipe` as the
device-side event. Not full glass-to-glass (no display-photodiode), but the same
host-side clock used for the overnight H.264 A/B.

### Before (live `screenrecord`, segment=60s, bitrate=1.5 Mbps)

| Metric | Value | Evidence |
|--------|------:|----------|
| Hello `source` | `screenrecord` | `qa/latency-before-scrcpy.json` |
| Swipe → next AU | **576.5 ms** | same |
| Steady fps under motion | ~18 | same |
| First frame (cold producer) | 479–792 ms | `/adb/h264/stats` |

### After (`scrcpy-server` raw_stream, segment=15s, bitrate=1.2 Mbps)

| Metric | Value | Evidence |
|--------|------:|----------|
| Hello `source` | `scrcpy` | `qa/latency-after-scrcpy.json`, `qa/latency-scrcpy-joins.json` |
| Swipe → next AU | **242–275 ms** (median ~254) | joins.json ×3 |
| Warm join → first AU (GOP replay) | **4.2–4.4 ms** | joins.json |
| Cold producer first frame | ~1744 ms (jar+server spawn) | after.json |
| Steady fps under motion | ~11–14 | stats |
| Tap control | intact (`POST /adb/tap` 200) | curl |
| JPEG `/adb/preview` | intact (28 KB JPEG) | curl |

### Verdict vs &lt;100 ms glass-to-glass

Host swipe→AU improved **~2.3×** (576 → ~250 ms) but **still above 100 ms**.
Remaining floor on this path:

1. Emulator MediaCodec + SurfaceFlinger composition (tens–hundreds of ms).
2. ADB TCP tunnel over SSH to the Azure VM (serialisation with taps).
3. No on-demand IDR without restart (`i-frame-interval` ignored by emu encoder).
4. Full scrcpy GUI / ws-scrcpy still blocked by SDL + XDG_RUNTIME_DIR on this box
   — we never needed them; server-socket path is what shipped.


## Ops

| Env | Default | Meaning |
|---|---|---|
| `H264_SOURCE` | `auto` | `scrcpy` \| `screenrecord` \| `auto` (try scrcpy, fall back) |
| `SCRCPY_SERVER_JAR` | `/home/box/.local/scrcpy/scrcpy-server` | host path pushed to the device |
| `SCRCPY_SERVER_VERSION` | `4.1` | must match the jar's `BuildConfig` |
| `SCRCPY_MAX_FPS` | `60` | server-side frame cap |
| `SCRCPY_START_TIMEOUT_S` | `3.5` | connect deadline before falling back (< the browser's 9 s watchdog) |

`/adb/h264/stats` and the `/ws/h264` `hello` both carry `source`, so which
producer is live is never a guess.

Rollback: `H264_SOURCE=screenrecord` restores the shipped path exactly;
`H264_ENABLED=0` drops the whole page to the JPEG ladder.



---

## Pass 2 — low-lat tune (2026-09-21 ~13:40 IST)

Goal: push host swipe→AU / glass-to-glass as close to &lt;100 ms as this ranchu
emulator allows. Same host AU probe style as Pass 1.

### What we changed

| Knob | Before | After |
|---|---|---|
| `SCRCPY_MAX_SIZE` | ~1200 (from width 540) | **800** → 360×800 |
| `H264_BITRATE` | 1.2 Mbps | **800 kbps** |
| `video_codec_options` | (none) | `i-frame-interval:int=1,latency:int=1` |
| `H264_FLUSH_IDLE_MS` | 30 | **12** |
| forward / scid | fixed `tcp:27183` / bare `scrcpy` | **ephemeral `tcp:0` + `scid=<8 hex>`** |
| client | `optimizeForLatency` only | + `decodeQueueSize` drop + **paintMs** via rAF |
| `XDG_RUNTIME_DIR` | unset (SDL abort) | stub `/tmp/runtime-$UID` (headless scrcpy past XDG; SDL window still N/A) |

### Tunnel-hop experiment (ordered try #1)

Measured **on the Azure VM with local ADB** (no SSH hop):

| | Box→SSH→ADB | VM-local ADB |
|---|---:|---:|
| `adb shell echo` RTT median | ~53 ms | ~10 ms |
| input→TCP bytes median (best cfg) | — | **~165 ms** |

**Conclusion:** moving the producer onto the VM does **not** unlock &lt;100 ms.
The emulator MediaCodec + SurfaceFlinger path is the floor. Tunnel RTT is real
but secondary once encode knobs are lowered.

### Host AU measurements (this box)

| Probe | Median | Min | Evidence |
|---|---:|---:|---|
| Pass 1 warm swipe→AU (legacy) | 253 ms | 242 ms | `qa/latency-scrcpy-joins.json` |
| Tuned swipe 80 ms → AU | 270 ms | 260 ms | `qa/latency-scrcpy-tuned.json` |
| Tuned swipe 30 ms → AU | **127.5 ms** | 121 ms | `qa/latency-scrcpy-tuned-swipe30.json` |
| Tuned **tap→AU** | **105 ms** | **52.8 ms** | `qa/latency-scrcpy-ceiling.json` |
| Tuned swipe 160 ms → AU | 357 ms | 288 ms | same (duration dominates) |

Swipe duration is a large fraction of swipe→AU. Tap→AU is the fairest encode
floor signal on this path.

### Client

WebCodecs already used `optimizeForLatency: true`. Pass 2 adds:

- drop non-key AUs when `decoder.decodeQueueSize > 1` (no decoder backlog)
- `paintMs` = rAF time after `drawImage` (separate from `decodeMs` in HUD title)

Decode+paint on this box is typically **1–10 ms** — not the budget eater.

### Honest ceiling vs &lt;100 ms glass-to-glass

**Not reachable on this ranchu emulator**, even with VM-local ADB and aggressive
encode knobs. Best host median is **~105 ms tap→AU**; glass-to-glass adds
decode+paint+display, so realistic G2G sits ~110–150 ms on a good sample and
higher under motion.

To actually break 100 ms G2G would need at least one of:

1. A **real device** with a low-latency MediaCodec path (or vendor low-lat mode
   that this emulator ignores), or
2. Producer + broker **on the same machine as a hardware encoder** with
   sub-frame capture (not ranchu software codec), or
3. Accepting a non-AVC path (e.g. raw frames / lower-quality JPEG at &gt;30 fps)
   — which regresses bandwidth and multi-viewer scale.

`i-frame-interval` remains ignored by the emulator encoder; IDRs still come from
segment restart / cold spawn only.

### Ops knobs added

| Env | Default | Meaning |
|---|---|---|
| `SCRCPY_MAX_SIZE` | `800` | long-edge cap passed to scrcpy-server |
| `SCRCPY_CODEC_OPTIONS` | `i-frame-interval:int=1,latency:int=1` | MediaCodec extras |
| `SCRCPY_PORT` | `0` | `adb forward tcp:0` → ephemeral local port |
| `H264_WIDTH` | `360` | used when max_size unset / screenrecord |
| `H264_BITRATE` | `800000` | both producers |
| `H264_FLUSH_IDLE_MS` | `12` | Annex-B idle flush |

Live example (2026-09-21):

```
scid=72940b43 tunnel_forward=true … raw_stream=true max_size=800
video_bit_rate=800000 max_fps=60
video_codec_options=i-frame-interval:int=1,latency:int=1
→ adb forward tcp:43019 localabstract:scrcpy_72940b43
```

### Next (only if hardware changes)

1. Re-measure on a physical device with the same probe suite.
2. Optional `raw_stream=false` length-prefixed frames (correctness / PTS; small
   latency win by killing idle-flush).
3. Keep ws-scrcpy / SDL interactive mirror as non-goal on this box.

## Next steps

1. Re-run the Pass 2 probe suite on a **physical device** — the ranchu ceiling
   is the blocker, not the wire.
2. `raw_stream=false` → 12-byte frame headers: real PTS/lengths; deletes idle-flush
   heuristics (`H264.md` §1). Correctness win; small latency win.
3. Serve the cached key AU + GOP to a viewer that asks for a keyframe instead of
   restarting the encoder (removes tap-stall from IDR-via-restart).
4. scrcpy `control=true` for input — still an explicit non-goal (would replace
   `adb shell input`, risk fighting the JPEG/tap path).
