# Strlix Cloud Phone Pilot

**Touchable cloud Android phone** — AI lives *inside* the phone (home Ask / Live). The web UI is a phone-first window onto that device (full-bleed Pixel bezel, live screenshot preview), not a chat cockpit. Optional floating **Ask** drawer for rare host-side prompts; `/chat` still serves the in-phone agent.


**Client apps (Android, iOS, desktop):** [`clients/README.md`](clients/README.md). They open the soft-launch phone at `https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net`.

**Public demo URL (HTTPS):** https://dicke-materials-vendors-maritime.trycloudflare.com

> Quick tunnels rotate when restarted. Current URL is also in `demo/public-url.txt`. Restart with `./scripts/public-tunnel.sh`.

## Demo steps (startup pitch)

1. Open the public URL above (or `http://127.0.0.1:8787/` on the box).
2. Confirm header pills: **ADB connected** + model **gpt-5.6-sol**.
3. Watch the centered **live phone** preview (auto-refreshes when ADB is up).
4. Optional: tap **Ask** (floating) or **Live** for host-side voice — primary AI UX is on the phone.
5. Health check: `curl -s https://<public-host>/health | jq .`

## Layout

- `app/main.py` — FastAPI (`/chat`, `/health`, `/adb/screenshot`, `/ws/h264`, `/ws/stream`, web UI)
- `app/h264_stream.py` — **H.264 live video** producer (`screenrecord` → Annex-B → WS fan-out)
- `app/pilot.py` — Azure OpenAI tool loop (`adb_screenshot|tap|type|swipe|key`)
- `app/adb_client.py` — ADB helpers
- `static/index.html` — **phone-first** viewer (full-bleed bezel, H.264/WebCodecs video with JPEG fallback, minimal chrome, floating Ask) + **Live** voice
- `app/voice.py` — host TTS (edge-tts / optional Azure Speech) + live WS hub
- `demo/live-voice.md` — live voice architecture, API choice, routing diagram
- `scripts/adb-tunnel.sh` — SSH tunnel to VM ADB port 5555
- `scripts/run-pilot.sh` — start tunnel + uvicorn
- `scripts/public-tunnel.sh` — Cloudflare quick tunnel → HTTPS trycloudflare.com URL
- `scripts/demo_chat.py` — one-shot curl-style demo
- `scripts/h264_probe.py`, `scripts/h264_ws_probe.py` — headless H.264 pipeline probes
- `scripts/qa_h264_browser.py`, `scripts/qa_stream_load.py`, `scripts/qa_latency_ab.py` — browser / load / A-B QA
- `demo/overnight/H264.md` — H.264 architecture, tradeoffs vs scrcpy, measurements
- `scripts/fetch_openai_key.sh` — refresh `.env` key via `az`
- `.env` — secrets (chmod 600; never commit)

## Prerequisites

- Azure VM `20.115.117.71` with Android reachable on `127.0.0.1:5555` (emulator or Redroid)
- SSH key: `/home/box/Downloads/vm-zevi-cloudphone-key.pem`
- Azure OpenAI: `oai-zevi-phonepilot` / deployment `gpt-5.6-sol` in `rg-zevi-cloudphone`
- Optional public URL: `cloudflared` (installed system-wide)

## Run (local)

```bash
cd /workspace/zevi-cloudphone
./scripts/run-pilot.sh
```

Service: `http://127.0.0.1:8787/` (bound `0.0.0.0:8787`)

### Public HTTPS tunnel

```bash
./scripts/public-tunnel.sh
# prints https://….trycloudflare.com and writes demo/public-url.txt
# keep the cloudflared process running in the background
```

Force HTTP/2 if QUIC is flaky: `CLOUDFLARED_PROTOCOL=http2 ./scripts/public-tunnel.sh`

### Phone-first viewer

Open the public URL or `http://127.0.0.1:8787/`.

The page is a **window onto the phone**: near full-viewport Pixel-like bezel with live ADB screenshot refresh (~1.5s), slim top bar (Live voice, language, ADB status), and an optional floating **Ask** drawer — no big chat column. AI interaction is meant to happen on the Android Strlix app; the web keeps `/chat` for the agent and host Live voice. Before/after: `demo/ui-redesign/`. Design brief: `demo/ui-redesign-claude.md`.

### Desktop continuity

The phone viewport accepts host files and plain text: dropped files are pushed to the device's `/sdcard/Download` directory with a 50 MiB limit, sanitized names, and collision suffixes instead of overwrites. Plain text drop or `Ctrl/Cmd+V` sends text to the focused device field; `Ctrl/Cmd+Shift+C` requests a one-shot device→host clipboard copy when Android permits it. The browser never polls or reads the host clipboard automatically.

The clipboard path uses `ClipboardBridgeReceiver` from the Strlix agent APK because Android 10+ has no stable `adb shell` clipboard command. Device clipboard reads are available only while Strlix is foreground on ordinary Android builds; without the helper, text insertion falls back to focused `adb shell input text`.


### curl demo

```bash
curl -s http://127.0.0.1:8787/health | jq .
curl -s http://127.0.0.1:8787/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Take a screenshot and describe the home screen"}' | jq .
# or:
.venv/bin/python scripts/demo_chat.py
```

### ADB tunnel only

```bash
./scripts/adb-tunnel.sh
platform-tools/adb devices -l
```

## Scope / safety

- Only touch resource group `rg-zevi-cloudphone`
- Never touch `phonecodex-*`
- Never sign out of Azure
- Do not print API keys

## Notes

Redroid on this Azure kernel (`6.8.0-*-azure`) can panic `binder_linux` and reboot the VM.
Prefer the KVM Android emulator on the VM, publishing ADB on port 5555.

## Phone backend on the VM

**Preferred (current):** KVM Android emulator AVD `zevi` (API 30 google_apis x86_64).

```bash
ssh -i /home/box/Downloads/vm-zevi-cloudphone-key.pem azureuser@20.115.117.71
export ANDROID_HOME=/opt/android-sdk JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH:$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools
# Do not pass -no-audio — scrcpy playback capture needs the guest audio HAL.
emulator -avd zevi -no-window -no-boot-anim -gpu swiftshader_indirect -port 5554 &
adb wait-for-device
adb shell getprop sys.boot_completed   # expect 1
```

## Service command

```bash
cd /workspace/zevi-cloudphone && ./scripts/run-pilot.sh
# or:
set -a; source .env; set +a
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8787
```

Health: `curl -s http://127.0.0.1:8787/health`

## Demo evidence

- Polished UI: `demo/ui-polished.png` (mobile: `demo/ui-polished-mobile.png`)
- Phone screenshot: `demo/screen-20260920-123807.png`
- Response JSON: `demo/last-demo.json`
- Public URL file: `demo/public-url.txt`
- Tunnel log: `demo/cloudflared.log`


## Live video (H.264) and the JPEG fallback

The viewer's primary path is **H.264**: one `adb exec-out screenrecord
--output-format=h264 -` producer on the host, Annex-B access units fanned out
over `/ws/h264`, decoded in the browser with **WebCodecs**. Typical: 13–28 fps
at 0.6–1.2 Mbps, 7–34 ms to decode and paint a frame.

`screenrecord` was chosen over scrcpy deliberately: nothing to push to the
device, no server jar to keep version-matched, one subprocess to supervise.
Full rationale, wire format and measurements: `demo/overnight/H264.md`.

The JPEG `FrameBroker` is **kept as the fallback** and is unchanged in
behaviour. The browser walks the ladder automatically:

**H.264/WebCodecs → JPEG WebSocket (`/ws/stream`) → MJPEG (`/adb/mjpeg`) → polled `/adb/preview`.**

The JPEG socket stays connected until the first decoded video frame paints, so
a browser without WebCodecs — or a device where `screenrecord` is unavailable
(`H264_ENABLED=0`) — sees no interruption. The footer readout shows which
transport is live, its fps/bitrate, and the last tap-to-pixels time.

Paired measurement (both transports watching the same device events at the same
instant): H.264 was faster on **14 of 18** events, median **1027 ms vs 1858 ms**
input-to-pixels. It wins clearly on animated transitions; a discrete keypress
onto a static screen can still favour JPEG, because that path force-captures
instead of waiting for the device encoder. For those, the viewer paints a
single catch-up JPEG if no video frame arrives within ~420 ms.

### Concurrency

- One producer per path; every viewer reads the same frames/access units.
- Caps: `H264_MAX_CLIENTS` (12) and `MAX_STREAM_CLIENTS` (12). Viewers past the
  cap are accepted, told why, then closed with **1013** so they fall back
  instead of retrying blind.
- Per-client H.264 queues (180 AUs / 4 MB) drop under pressure and wait for the
  next IDR rather than shipping frames that reference what was dropped.
- Both sockets run an application-level heartbeat (`WS_PING_INTERVAL_S` 15 s,
  `WS_PING_TIMEOUT_S` 40 s) so a backgrounded ghost tab releases its slot.
- Both producers stop when nobody is watching (10 s / 12 s idle) and restart on
  demand; `screencap` for the pilot/chat agent keeps working during video.
- Taps/swipes/keys are never serialized behind capture: 71–172 ms with 12
  viewers streaming.

### Ops

```bash
curl -s localhost:8787/adb/h264/stats | jq .     # producer, viewers, fps/kbps, GOP, misflushes
curl -s -X POST localhost:8787/adb/h264/keyframe # force a fresh IDR
curl -s localhost:8787/adb/stream/stats | jq .   # JPEG broker
curl -s localhost:8787/health | jq '.h264, .stream'
```

Env knobs: `H264_ENABLED`, `H264_WIDTH`, `H264_BITRATE`, `H264_MAX_CLIENTS`,
`H264_SEGMENT_S`, `H264_GOP_MAX_BYTES`, `H264_FLUSH_IDLE_MS`,
`MAX_STREAM_CLIENTS`, `STREAM_INTERVAL_MS`, `STREAM_QUALITY`,
`STREAM_MAX_WIDTH`, `WS_PING_INTERVAL_S`, `WS_PING_TIMEOUT_S`
(full list in `demo/overnight/H264.md` and `demo/overnight/SCALE.md`).
