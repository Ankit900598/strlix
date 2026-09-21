# VERIFIED — H.264 live video (A + B + C)

**Date:** Sun Sep 20, 2026 · **Service:** `uvicorn app.main:app --host 0.0.0.0 --port 8787` (restarted with this code)

## What shipped

**A — H.264 capture path.** `adb exec-out screenrecord --output-format=h264 -`
→ Annex-B parser → access units → WebSocket fan-out → browser WebCodecs.
Chosen over scrcpy: nothing to push to the device, no server jar to keep
version-matched, one subprocess to supervise. Rationale, wire format and the
three problems `screenrecord` creates (no length prefixes, rare IDRs, time
limit) are written up in `H264.md`.

**B — Viewer.** Transport ladder **H.264/WebCodecs → JPEG WS → MJPEG → poll**.
The JPEG socket stays connected until the first decoded video frame paints, so
there is never a blank phone; the badge flips to *Live · H.264* and the footer
shows transport · fps · kbps · tap-to-pixels. A one-shot JPEG catch-up covers
the single case JPEG used to win (a keypress with no animation behind it).

**C — Concurrency, backpressure, ops.** Per-client AU queues that wait for an
IDR rather than ship frames referencing dropped ones; bounded GOP replay for
joiners; capacity refusal that the browser can actually act on (accept → reason
→ 1013); heartbeat GC on both sockets; idle stop; per-IP input rate limit
extended to key/type/nudge; `/adb/h264/stats`, `/adb/h264/keyframe`, and an
`h264` block in `/health`.

## Files changed

| File | Change |
|------|--------|
| `app/h264_stream.py` | **new** — `H264Broker`, Annex-B parser, GOP buffer, fan-out, telemetry |
| `app/main.py` | `/ws/h264`, `/adb/h264/stats`, `/adb/h264/keyframe`, `h264` in `/health`, heartbeat GC on both sockets, capacity refusal after accept, rate limit on key/type/nudge |
| `app/adb_client.py` | owns `self.h264` alongside `self.frames` (JPEG fallback untouched) |
| `static/index.html` | WebCodecs transport + ladder + telemetry readout + JPEG catch-up (backup: `index.html.pre-h264.bak`) |
| `scripts/h264_probe.py` | **new** — broker-only probe |
| `scripts/h264_ws_probe.py` | **new** — `/ws/h264` end-to-end probe |
| `scripts/qa_h264_browser.py` | **new** — real Chromium QA (`--no-webcodecs` for the fallback) |
| `scripts/qa_stream_load.py` | **new** — cap / fan-out / backpressure / GC |
| `scripts/qa_latency_ab.py` | **new** — paired H.264-vs-JPEG measurement |
| `demo/overnight/H264.md` | **new** — architecture, tradeoffs, measurements |
| `README.md`, `SCALE.md`, `PROGRESS.md`, `MISTAKES.md` | updated |

## Evidence

Run against `http://127.0.0.1:8787/` with the emulator on `127.0.0.1:5555`.

| Check | Result |
|-------|--------|
| Stream decodes | `ffmpeg -f null -` on captured `/ws/h264`: **0 warnings**, frames-in = frames-out |
| Parser mis-flushes | **0** (`flush_tick_ms` self-calibrates to 30–65 ms) |
| Chromium upgrade JPEG → H.264 | 513 ms after load; badge *Live · H.264*, canvas 540×1200 |
| Steady state | 19 fps, ~1.0 Mbps, decode+paint 7–34 ms |
| Tap → painted pixels | 568 ms (tap POST itself 73 ms) |
| HOME → painted pixels | 533 ms |
| Swipe → painted pixels | 1 ms (frames already flowing) |
| Tab hide → restore → input → pixels | 564 ms |
| Paired A/B vs JPEG (same events, same instant) | H.264 faster on **14/18**, median **1027 ms vs 1858 ms** |
| 12 viewers / one producer | identical AU sequences, **0 drops**, 247 KB each per 12 s |
| 13th viewer | accepted, told why, closed **1013** |
| Taps with 12 viewers streaming | 71–172 ms |
| Ghost tab (ignores heartbeat) | slot reclaimed after the ping timeout |
| Input flood | 80 concurrent nudges → 30×200, 50×429, refills |
| `H264_ENABLED=0` | viewer falls back to JPEG WS, HUD reads *JPEG fallback*, inputs work |
| Browser without WebCodecs | same fallback, canvas 480×1067, inputs work |
| Pilot/chat agent during a live stream | `/chat` answered correctly with a screenshot tool step; `/adb/preview` 515 ms, `/adb/screenshot` 945 ms |
| Voice/TTS | untouched; `/health` reports provider `azure` |

Screenshots: `demo/overnight/qa/h264-0*.png`, `ab-h264.png`, `ab-jpeg.png`.
Raw report: `demo/overnight/qa/h264-report.json`, `latency-ab.json`.

## Reproduce

```bash
cd /workspace/zevi-cloudphone
set -a; source .env; set +a
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8787

.venv/bin/python scripts/h264_ws_probe.py --clients 3
.venv/bin/python scripts/qa_h264_browser.py
.venv/bin/python scripts/qa_stream_load.py --n 13
.venv/bin/python scripts/qa_latency_ab.py --rounds 3
ffmpeg -v warning -i /tmp/ws.h264 -f null -
```

## Known limits

* The **device** is the remaining floor: after a discrete keypress the encoder's
  first bytes take 23–589 ms depending on when SurfaceFlinger composes. Measured
  raw, with no app code in the path.
* A keypress onto a static screen can still be quicker on JPEG (it force
  captures); the catch-up poke covers it, but the video path does not *win*
  there.
* Rotation is handled by a producer restart (~700 ms freeze) — not exercised
  against a real rotation on this AVD.
* H.264 over the Cloudflare quick tunnel was not re-measured; all numbers above
  are `127.0.0.1` → tunnelled ADB.
* One device, one ADB serial. Nothing here makes the service multi-tenant.

## Note for whoever picks this up

`app/main.py` gained a per-IP input rate limiter (`_allow_input`) from outside
this session while the work was in progress. It was kept and extended to
`key`/`type`/`nudge` for consistency rather than reverted.
