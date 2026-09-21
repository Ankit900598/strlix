# Overnight sprint — PROGRESS

**Date:** Mon Sep 21, 2026 00:49 IST (2026-09-20 19:19 UTC)  
**Goal:** Fix broken/slow cloud-phone viewer clicks; perceived feedback under ~500ms.

## Verified (API + Playwright browser → http://127.0.0.1:8787/)

| Action | Result | Evidence |
|--------|--------|----------|
| Open viewer | Live WS canvas paints (device 1080×2400 → ~480 JPEG) | `qa/60-browser-viewer.png`, `qa/20-live-home.png` |
| **Browser click Gmail** | Opens Gmail WelcomeTour | map `162,987`; stamp `tap 162,987 · 55ms`; app ~**446ms** (`qa/61-browser-after-gmail-click.png`) |
| **Browser click Chrome** | Opens Chrome FirstRun | map `666,1970`; app ~**1622ms** cold (`qa/63-browser-chrome.png`) |
| API tap Gmail / Chrome | Opens apps | `qa/11-after-gmail-tap.png`, `qa/13-after-chrome-tap.png`, `qa/RESULTS.json` |
| Settings via drawer | swipe up + tap | `qa/40-drawer.png`, `qa/41-settings.png` |
| HOME / BACK nav | Works via `/adb/key` | navbar + API |
| Swipe | `/adb/swipe` OK | drawer |

## Performance

| Metric | Before | After |
|--------|--------|-------|
| Preview under MJPEG load | ~840ms–2.5s (`_preview_lock`) | shared FrameBroker ~1–50ms cached |
| WS frame age (subscribed) | producer often `running:false` / stale 20s+ | **~9–400ms** while clients connected |
| Tap HTTP | ~100–150ms | **~55–220ms** |
| Browser tap → Gmail activity | unreliable / no-op | **~446ms** |
| Producer with viewers | could die and stay dead | **auto-restarts** (`restarts` in `/adb/stream/stats`) |

## What changed

1. **`app/adb_client.py`** — `FrameBroker` single producer; in-memory JPEG; `nudge`/`nudge_soon`; **auto-restart if producer dies while subscribers > 0**; `_ensure_task` on nudge/next_frame; screenshot retention prune.
2. **`app/main.py`** — `/ws/stream` binary JPEG; shared `/adb/mjpeg` + `/adb/preview`; `/adb/key`; `/adb/stream/stats` + `/adb/stream/nudge`; `MAX_STREAM_CLIENTS=12`.
3. **`static/index.html`** — phone-first canvas; device-aspect `#touchLayer` mapping (no `naturalWidth=0` trap); WS→MJPEG→poll; optimistic `nudgeStream` on every input; HOME/BACK.
4. **`README.md`** — concurrency / ops notes.
5. Backups: `*.pre-overnight.bak`.

## Concurrent users

- One ADB screencap owner; N viewers share frames.
- Cap **12** (`MAX_STREAM_CLIENTS`). Extra: HTTP 503 / WS 1013.
- Live frames never write `demo/`.

## Left / morning blockers

- Sub-100ms video still blocked by `screencap` (~250–350ms). Next: ws-scrcpy / H.264.
- Occasional capture spikes (~1s) when nudge aborts in-flight screencap under load — monitor `aborted_captures`.
- Stale WS tabs can keep `subscribers>0` until disconnect; heartbeat GC nice-to-have.
- Public Cloudflare tunnel latency not re-measured tonight (local verified).
- Voice/Ask: not full STT E2E overnight.

## How to run

```bash
cd /workspace/zevi-cloudphone
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8787
# ADB: scripts/adb-tunnel.sh --watch
```

---

## Milestone 2 — H.264 / WebCodecs low-latency (2026-09-21 01:21 IST)

### Approach chosen
- **Not full scrcpy-web** for overnight: would need jar push, control protocol, SDL.
- **Implemented:** single `adb exec-out screenrecord --output-format=h264 -` producer
  (`app/h264_stream.py`) → Annex-B AUs over **`/ws/h264`** → browser **WebCodecs `VideoDecoder`**.
- JPEG `FrameBroker` + `/ws/stream` kept as automatic fallback.

### Verified (this box, Chromium)
| Check | Result |
|-------|--------|
| Badge | `Live · H.264` |
| Steady HUD | ~**11–13 fps**, ~165–900 kbps |
| First frame | ~**261–322 ms** to decode path |
| Gmail tap (viewer) | opens in **~625 ms**; stamp `tap 162,987 · 235ms` (`qa/71-h264-gmail.png`) |
| HOME | returns to launcher (`qa/72-h264-home-btn.png`) |
| Cloudflare | `demo/public-url.txt` health + `/adb/h264/stats` OK |

### A/B latency (Playwright, `qa/latency-ab.json`)
| Action | H.264 median | JPEG median |
|--------|-------------:|------------:|
| open_app | **497 ms** | 2013 ms |
| home | 310 ms | 92 ms |
| drawer | 539 ms | 614 ms |

H.264 wins hard on app-open visual feedback (~4×). Home can still look “instant” on JPEG when the frame happens to already match.

### Scale
See `demo/overnight/SCALE.md` (updated). Caps: 12 JPEG + 12 H.264 viewers; latest-wins backpressure; no live disk writes.

### Still blocked / next
- True &lt;100 ms glass-to-glass needs scrcpy-server / MediaCodec with frequent IDRs; `screenrecord` keyframes are rare (segment restart helps late joiners).
- Input rate-limit polish if missing.
- Claude session may still be finishing extra QA scripts; core path is live on **:8787**.

---

## Milestone 3 — scrcpy-server raw H.264 (2026-09-21 ~13:30 IST)

### Approach
- **Not** full scrcpy GUI / ws-scrcpy (SDL + XDG_RUNTIME_DIR still blocked).
- **Shipped:** `app/scrcpy_source.py` + `H264Broker` source switch
  (`H264_SOURCE=auto|scrcpy|screenrecord`). scrcpy-server `raw_stream=true`
  over `adb forward` → existing Annex-B `/ws/h264` → WebCodecs.
- Sticky fallback to `screenrecord` on hard scrcpy failure. JPEG ladder + taps unchanged.
- Defaults: segment **15s** (more IDRs), bitrate **1.2 Mbps**.

### Measured (host AU probe)
| | Before (screenrecord) | After (scrcpy) |
|--|--:|--:|
| Swipe → next AU | 576 ms | **~254 ms** |
| Warm join → first AU | (GOP) | **~4 ms** |
| Cold first frame | ~500–800 ms | ~1744 ms (server spawn) |

### Docs
- `demo/overnight/SCRCPY.md` — blockers, recipe, before/after
- QA: `demo/overnight/qa/latency-before-scrcpy.json`, `latency-after-scrcpy.json`, `latency-scrcpy-joins.json`

### Still open toward &lt;100 ms glass-to-glass
- Emulator encode + SSH/ADB RTT floor
- IDR-on-demand without restart (emu ignores i-frame-interval)
- Optional: `raw_stream=false` length-prefixed frames to drop idle-flush heuristics
- Ephemeral `adb forward` port / scid if multiple brokers share one device

---

## Milestone 4 — scrcpy low-lat tune (2026-09-21 ~13:45 IST)

### Tries (in order)
1. **Tunnel hops:** VM-local ADB floor ~165 ms median input→bytes (shell RTT ~10 ms).
   Box SSH ADB RTT ~53 ms. **Tunnel is not the &lt;100 ms unlock.**
2. **Encode knobs:** `max_size=800`, bitrate 800k, `video_codec_options=i-frame-interval:int=1,latency:int=1`,
   flush idle 12 ms, ephemeral scid + `tcp:0`.
3. **XDG stub:** `XDG_RUNTIME_DIR=/tmp/runtime-$UID` — headless scrcpy past XDG abort;
   SDL interactive / ws-scrcpy still non-goal.
4. **Client:** `decodeQueueSize` backpressure + separate `paintMs` (rAF). Decode+paint ~1–10 ms.

### Measured (host AU)
| | Median | Min |
|--|--:|--:|
| Pass 1 warm swipe→AU | 253 ms | 242 ms |
| Tuned swipe 30 ms → AU | **127.5 ms** | 121 ms |
| Tuned tap→AU | **105 ms** | **52.8 ms** |

### Verdict
**Glass-to-glass &lt;100 ms: not feasible on this ranchu emulator.** Best host median
~105 ms (tap→AU); G2G adds decode/paint. Need a real device or non-AVC path.

### Artifacts
- `demo/overnight/qa/latency-scrcpy-tuned.json`
- `demo/overnight/qa/latency-scrcpy-tuned-swipe30.json`
- `demo/overnight/qa/latency-scrcpy-ceiling.json`
- `demo/overnight/qa/latency-scrcpy-tuned-summary.json`
- `demo/overnight/SCRCPY.md` (Pass 2 section)
- Code: `app/scrcpy_source.py`, `app/h264_stream.py`, `static/index.html`, `scripts/qa_scrcpy_latency.py`

### Phone path
Tap / swipe / JPEG preview / H.264 stream verified up on **:8787** after restart.
