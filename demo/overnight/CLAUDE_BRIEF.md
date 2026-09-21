# OVERNIGHT SPRINT — Click/Touch + Performance Fix

## Critical complaint
Laptop viewer is SLOW; clicking does NOT work properly. User hates a broken viewer.

## Success criteria
1. Clicking Gmail / Chrome / Settings (or app drawer) on the live web viewer reliably opens the app.
2. Visual feedback latency feels under ~500ms after a tap (stream refresh / UI response).
3. Swipe and HOME button work.
4. No disk thrash under concurrent MJPEG viewers.
5. Document everything in demo/overnight/PROGRESS.md and demo/overnight/MISTAKES.md.

## Stack
- Project: /workspace/zevi-cloudphone/
- Frontend: static/index.html (phone-first, MJPEG via `<img src=/adb/mjpeg>`, pointer → `/adb/tap` `/adb/swipe`)
- Backend: app/main.py, app/adb_client.py
- ADB: 127.0.0.1:5555 (SSH tunnel), device 1080x2400 emulator
- Pilot: uvicorn on :8787 already running (restart after code changes)
- Constraints: no outside chat column; no phonecodex-* touch; no Azure/AWS sign-out; no user questions.

## Measured facts (do not re-debate)
- `adb exec-out screencap -p` ≈ 370ms
- `GET /adb/preview` ≈ 840ms (screencap + Pillow JPEG)
- `POST /adb/tap` ≈ 100–150ms when coords correct — **backend tap works**
- Direct ADB tap Gmail center (162,987) opens Gmail. Chrome hotseat (666,1970).
- Home icons: Gmail[57,851][267,1123], Photos, YouTube, Maps; hotseat Phone/Messages/Chrome/Camera; Settings not on home (app drawer).
- `AdbClient._preview_lock` serializes all previews → MJPEG ~1fps effective; concurrent users wait in line.
- Frontend `clientToDevice` uses `liveShot.naturalWidth/Height` + object-fit:contain. **Suspect**: MJPEG `<img>` may report naturalWidth=0 or wrong, causing taps to no-op (`return null`) or mis-map.
- After tap, if mjpegActive, no forced refresh nudge (only non-mjpeg path refreshes).

## Required approach
Diagnose root causes, then IMPLEMENT fixes in this repo:

### A. Click reliability (P0)
1. Fix coordinate mapping so it works with MJPEG streams even when naturalWidth is 0/stale. Prefer device aspect from `/adb/size` + displayed letterbox rect; cache last known image aspect from MJPEG headers or preview JSON.
2. Attach pointer listeners to a transparent overlay covering the screen (not only the img) so clicks always hit.
3. Fire tap on pointerup without waiting; optimistic UI (ripple already exists). Log mapped coords to `#shotStamp`.
4. After tap/swipe, force a fast preview refresh OR restart MJPEG so user sees the opened app within ~500ms.
5. Ensure HOME / BACK nav buttons call `/adb` key endpoints (add if missing).

### B. Performance (P0)
1. Shared in-memory frame cache: one background screencap→JPEG producer; all MJPEG clients and `/adb/preview` consumers read the latest frame (no per-client screencap, no disk writes for live path).
2. Target producer interval ~200–300ms; JPEG quality ~45–55, max_width 480–540.
3. Drop `_preview_lock` as a global bottleneck; use a single producer task + asyncio.Condition / version counter.
4. Never write live frames to demo/. Cap demo/ screenshot retention for chat/pilot only.
5. If still >500ms perceived: add WebSocket binary JPEG frames endpoint `/ws/stream` and switch frontend to that (or evaluate embedding ws-scrcpy / scrcpy-web — document tradeoffs; implement the faster path you can finish tonight).

### C. Concurrent users (P1)
1. Limit max MJPEG/WS clients; reject or degrade gracefully.
2. Single ADB serial owner for screencap; taps remain concurrent-safe (short shell cmds).
3. Update README with concurrency limits and ops notes.

### D. Docs
- demo/overnight/PROGRESS.md — what fixed, what's left, verification evidence
- demo/overnight/MISTAKES.md — every bug found (coord null, lock, disk thrash, etc.)

## Do NOT
- Ask the user anything
- Break voice/TTS/Azure OpenAI paths
- Add outside chat column or phonecodex-* touch packages
- Sign out of cloud accounts

## After implementing
Restart uvicorn (kill existing on 8787, start: `cd /workspace/zevi-cloudphone && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8787`). Write a short VERIFIED.md note of files changed.
