# Tap / swipe control + faster preview

**When:** Sun Sep 20, 2026 ~18:23 IST (Asia/Calcutta)  
**Verified:** ADB tap on **Settings** (177,1827) opened Settings → Network & internet, Battery 100%, etc.  
**After shot:** `after-tap-settings.png` / `.jpg` in this folder.

## What was slow

1. **Disk thrash on every poll** — `POST /adb/screenshot` wrote a full PNG under `demo/screen-*.png` every ~1.5s. ~80–100 files piled up (~100KB each). Browser then fetched `/demo/...` with cache-bust query → extra round trip + static file I/O.
2. **Heavy PNG over the wire** — full-res PNG (~100–150KB) vs scaled JPEG (~20–35KB).
3. **1.5s poll cadence** — felt laggy after taps; no interactive boost.
4. **No input path** — UI was view-only; no `/adb/tap` or `/adb/swipe` HTTP endpoints wired to the phone image.
5. **Tunnel** — SSH forward was up with keepalive, but no reconnect watcher if port dropped.

Emulator/VM CPU was fine for a single screencap (~300–400ms); the bottleneck was write+transfer+interval, not ADB itself.

## What we fixed

### Backend (`app/adb_client.py`, `app/main.py`)
- **`POST /adb/tap`** `{x,y}` and **`POST /adb/swipe`** `{x1,y1,x2,y2,duration_ms}`
- **`GET /adb/preview`** — in-memory JPEG (Pillow), scaled to max-width 540, quality ~55, **no demo/ write**. Headers: `X-Device-Width/Height`, `X-Image-Width/Height`
- **`GET /adb/preview.json`** — same as base64 JSON
- **`GET /adb/mjpeg`** — multipart MJPEG stream (~400ms frames)
- **`GET /adb/size`** — cached `wm size`
- Screenshot `save=` query (default true for pilot/chat; preview path never saves)
- ADB reconnect backoff on ensure_connected + screencap retry

### Frontend (`static/index.html`)
- Pointer events on `#liveShot` (mouse **and** touch): `pointerdown` / `pointerup`
- Coord map via `getBoundingClientRect` + `naturalWidth/Height` with **object-fit: contain** letterboxing
- Short drag → swipe; tap otherwise
- Press ripple feedback (`#pressRipple`)
- Prefer **MJPEG stream**; fallback to `/adb/preview` poll (~500ms when interactive, ~800ms idle); pause when tab hidden
- `touch-action: none` so mobile doesn’t scroll the page while dragging

### Ops
- `scripts/adb-tunnel.sh` — stronger SSH keepalive (`ServerAliveInterval=20`, `ExitOnForwardFailure`) + **`--watch`** reconnect loop
- Cleared accumulated `demo/screen-2026*.png` poll junk

## Perf snapshot (this box → tunnel → Azure emulator)

| Path | Size | Wall time |
|------|------|-----------|
| Old PNG save+URL | ~100KB disk | ~340ms + disk + 2nd fetch |
| New JPEG preview | ~21KB RAM | ~400ms (screencap-bound), no disk |
| MJPEG | ~2 frames / 2s smoke | continuous |

## Manual check

1. Open UI → phone image streams / refreshes quickly.
2. Tap Settings (or any icon) on the image → device responds; ripple shows.
3. Drag to swipe app drawer.
4. Confirm ADB pill stays green; tunnel watch log if flaky: `/tmp/adb-tunnel-watch.log`.
