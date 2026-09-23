"""FastAPI entrypoint for Zevi Cloud Phone Pilot + Live Voice."""
from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shlex
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

from .adb_client import STREAM_MAX_WIDTH, STREAM_QUALITY, AdbClient, AdbError  # noqa: E402
from .h264_stream import H264_MAX_CLIENTS, H264Error, pack_au  # noqa: E402
from .pilot import PhonePilot  # noqa: E402
from .languages import list_languages, resolve_language  # noqa: E402
from .voice import live_hub, provider_status, synthesize  # noqa: E402
from .stt import AzureSpeechSession, stt_status  # noqa: E402

app = FastAPI(title="Zevi Cloud Phone Pilot", version="0.2.0-live")
static_dir = ROOT / "static"
static_dir.mkdir(exist_ok=True)
(ROOT / "demo" / "voice-audio").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/demo", StaticFiles(directory=str(ROOT / "demo")), name="demo")

adb = AdbClient()
pilot: Optional[PhonePilot] = None

# Concurrency guard: every live viewer reads the SAME shared frame, so the
# cost per extra client is just the socket + JPEG bytes. The cap exists to
# protect memory/uplink, not the device.
MAX_STREAM_CLIENTS = int(os.environ.get("MAX_STREAM_CLIENTS", "12"))

INPUT_RATE_PER_SEC = float(os.environ.get("INPUT_RATE_PER_SEC", "90"))
CONTINUITY_MAX_FILE_BYTES = int(os.environ.get("CONTINUITY_MAX_FILE_BYTES", str(50 * 1024 * 1024)))
CONTINUITY_MAX_TEXT_CHARS = int(os.environ.get("CONTINUITY_MAX_TEXT_CHARS", "100000"))
_input_buckets: dict[str, list[float]] = {}

def _allow_input(ip: str) -> bool:
    """Return False when this IP exceeds INPUT_RATE_PER_SEC taps/swipes/keys."""
    now = time.time()
    key = ip or "unknown"
    bucket = [t for t in _input_buckets.get(key, []) if now - t < 1.0]
    if len(bucket) >= INPUT_RATE_PER_SEC:
        _input_buckets[key] = bucket
        return False
    bucket.append(now)
    _input_buckets[key] = bucket
    if len(_input_buckets) > 512:
        for stale in [k for k, v in _input_buckets.items() if not v or now - v[-1] > 300][:256]:
            _input_buckets.pop(stale, None)
    return True


# Application-level heartbeat. A backgrounded tab keeps its TCP socket open for
# a long time, so TCP liveness alone kept "ghost" viewers on the subscriber
# count (and, before H.264, kept the screencap producer awake for them).
WS_PING_INTERVAL_S = float(os.environ.get("WS_PING_INTERVAL_S", "15"))
WS_PING_TIMEOUT_S = float(os.environ.get("WS_PING_TIMEOUT_S", "40"))


def get_pilot() -> PhonePilot:
    global pilot
    if pilot is None:
        if not os.environ.get("AZURE_OPENAI_API_KEY"):
            raise HTTPException(500, "AZURE_OPENAI_API_KEY missing — put it in .env")
        pilot = PhonePilot(adb=adb)
    return pilot


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: Optional[list[dict[str, Any]]] = None


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1)
    voice: Optional[str] = None
    language: Optional[str] = None  # e.g. hi-IN, en-US
    broadcast: bool = True  # push to browser live clients


class VoiceTurnRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: Optional[list[dict[str, Any]]] = None
    speak: bool = True
    voice: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None  # browser | phone


class LiveStateRequest(BaseModel):
    active: bool
    source: Optional[str] = None
    language: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = static_dir / "index.html"
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health():
    info: dict[str, Any] = {
        "ok": True,
        "adb_serial": adb.serial,
        "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        "endpoint_set": bool(os.environ.get("AZURE_OPENAI_ENDPOINT")),
        "key_set": bool(os.environ.get("AZURE_OPENAI_API_KEY")),
        "voice": provider_status(),
        "stt": stt_status(),
        "live": {
            "active": live_hub.state.get("active"),
            "source": live_hub.state.get("source"),
            "browser_clients": live_hub.client_count(),
        },
        "stream": {**adb.frames.stats(), "max_clients": MAX_STREAM_CLIENTS},
        "h264": adb.h264.stats(),
        "audio": adb.audio.stats(),
        "input": adb.input_status(),
    }
    try:
        state = await adb.ensure_connected()
        info["adb_state"] = state
    except Exception as e:  # noqa: BLE001
        info["adb_state"] = f"error: {e}"
    return info


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        result = await get_pilot().chat(req.message, history=req.history)
        return result
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


class TapRequest(BaseModel):
    x: int
    y: int


class MotionRequest(BaseModel):
    action: str = Field(..., min_length=2, max_length=8)
    x: int
    y: int


class SwipeRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    duration_ms: int = 300


class KeyRequest(BaseModel):
    keycode: str = Field(..., min_length=1)  # HOME | BACK | APP_SWITCH | 3 | ...


class TypeRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ClipboardRequest(BaseModel):
    text: str = Field(..., max_length=CONTINUITY_MAX_TEXT_CHARS)
    paste: bool = True


@app.post("/adb/screenshot")
async def adb_screenshot(save: bool = Query(True, description="Write PNG under demo/")):
    """Full PNG. Default still saves for pilot/chat; set save=false to skip disk."""
    try:
        shot = await adb.screenshot(save=save)
        url = None
        if shot.get("path"):
            url = f"/demo/{Path(shot['path']).name}"
        return {
            "ok": True,
            "path": shot.get("path") or None,
            "bytes": shot["bytes"],
            "url": url,
            "mime": shot.get("mime"),
            "base64": shot.get("base64") if not save else None,
        }
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.get("/adb/preview")
async def adb_preview(
    quality: int = Query(STREAM_QUALITY, ge=20, le=90),
    max_width: int = Query(STREAM_MAX_WIDTH, ge=240, le=1080),
):
    """Fast JPEG preview (in-memory, no demo/ write)."""
    try:
        prev = await adb.preview_jpeg(quality=quality, max_width=max_width)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e
    return Response(
        content=prev["bytes"],
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store",
            "X-Device-Width": str(prev["device_width"]),
            "X-Device-Height": str(prev["device_height"]),
            "X-Image-Width": str(prev["image_width"]),
            "X-Image-Height": str(prev["image_height"]),
        },
    )


@app.get("/adb/preview.json")
async def adb_preview_json(
    quality: int = Query(STREAM_QUALITY, ge=20, le=90),
    max_width: int = Query(STREAM_MAX_WIDTH, ge=240, le=1080),
):
    """Same as /adb/preview but base64 JSON (for clients that prefer fetch+blob)."""
    try:
        prev = await adb.preview_jpeg(quality=quality, max_width=max_width)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e
    return {
        "ok": True,
        "mime": prev["mime"],
        "bytes": prev["size"],
        "base64": prev["base64"],
        "device_width": prev["device_width"],
        "device_height": prev["device_height"],
        "image_width": prev["image_width"],
        "image_height": prev["image_height"],
    }


@app.get("/adb/mjpeg")
async def adb_mjpeg(
    quality: int = Query(50, ge=20, le=80),
    max_width: int = Query(480, ge=240, le=720),
    interval_ms: int = Query(0, ge=0, le=2000),
):
    """Multipart MJPEG stream, fed from the shared frame cache.

    `quality`/`max_width`/`interval_ms` are accepted for backwards
    compatibility but the live path always serves the producer's frames —
    one screencap feeds every viewer. Set STREAM_QUALITY / STREAM_MAX_WIDTH /
    STREAM_INTERVAL_MS in the environment to retune the producer.
    """
    if adb.frames.subscribers >= MAX_STREAM_CLIENTS:
        raise HTTPException(503, f"stream at capacity ({MAX_STREAM_CLIENTS} viewers)")

    boundary = b"frame"

    async def gen():
        async with adb.frames.subscribe():
            last = 0
            while True:
                frame = await adb.frames.next_frame(after_version=last, timeout=10.0)
                if frame is None:
                    # Keep the connection warm across ADB blips rather than
                    # dropping the viewer back to the reconnect path.
                    continue
                last = frame.version
                data = frame.jpeg
                header = (
                    b"--" + boundary + b"\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(data)).encode() + b"\r\n"
                    b"X-Device-Width: " + str(frame.device_width).encode() + b"\r\n"
                    b"X-Device-Height: " + str(frame.device_height).encode() + b"\r\n"
                    b"X-Frame-Version: " + str(frame.version).encode() + b"\r\n"
                    b"\r\n"
                )
                yield header + data + b"\r\n"

    return StreamingResponse(
        gen(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary.decode()}",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


# ═══════════════════════════════════════════════════════════════════════════
#  H.264 live video (preferred path)
#
#  One `adb exec-out screenrecord --output-format=h264 -` producer feeds every
#  viewer; the browser decodes with WebCodecs. The JPEG socket below stays as
#  the fallback for browsers without WebCodecs and for devices where
#  screenrecord is unavailable.
# ═══════════════════════════════════════════════════════════════════════════
@app.websocket("/ws/h264")
async def ws_h264(ws: WebSocket):
    """Binary H.264 access units.

    Wire format: one binary message per access unit, 16-byte little-endian
    header (see ``h264_stream.pack_au``) + Annex-B payload. Text messages carry
    control/telemetry JSON (`hello`, `ping`, `stall`, `bye`).

    Client → server JSON: ``{"type":"pong"}``, ``{"type":"keyframe"}``,
    ``{"type":"ping"}``, ``{"type":"stats"}``,
    ``{"type":"motion","action":"DOWN|MOVE|UP|CANCEL","x":int,"y":int,"t":?}``.
    """
    broker = adb.h264
    # A viewer means someone is about to touch. Rebuild a dead input shell
    # and finish the jar push off this socket, not on the first tap.
    asyncio.create_task(adb.warm_input())
    # Refuse *after* accepting: closing during the handshake surfaces in the
    # browser as an opaque HTTP 403 / code 1006, which is indistinguishable
    # from "server is down" and sends the client into pointless retries.
    # Accept, say why, then close 1013 so the viewer falls back immediately.
    await ws.accept()
    if not broker.enabled:
        await ws.send_json({"type": "bye", "reason": "h264 disabled", "fallback": "/ws/stream"})
        await ws.close(code=1013, reason="h264 disabled")
        return
    if broker.subscribers >= H264_MAX_CLIENTS:
        await ws.send_json({
            "type": "bye",
            "reason": f"h264 at capacity ({H264_MAX_CLIENTS} viewers)",
            "viewers": broker.subscribers,
            "fallback": "/ws/stream",
        })
        await ws.close(code=1013, reason="h264 at capacity")
        return

    stop = asyncio.Event()
    last_pong = time.time()

    async def reader() -> None:
        nonlocal last_pong
        try:
            while not stop.is_set():
                msg = await ws.receive_json()
                typ = (msg or {}).get("type")
                if typ in ("pong", "ping"):
                    last_pong = time.time()
                    if typ == "ping":
                        # Echo client `t` so the viewer can measure WS RTT.
                        await ws.send_json({"type": "pong", "t": msg.get("t"), "server_time": time.time()})
                elif typ == "keyframe":
                    # Viewer's decoder lost sync (tab restore, dropped AUs).
                    broker.request_keyframe("client")
                elif typ == "key":
                    # Nav keys over the open H.264 socket — same RTT win as motion.
                    ip = ws.client.host if ws.client else "unknown"
                    client_t = msg.get("t")
                    keycode = str(msg.get("keycode") or msg.get("key") or "").strip()
                    if not keycode:
                        await ws.send_json({"type": "key_ack", "ok": False, "reason": "bad_key", "t": client_t})
                        continue
                    if not _allow_input(ip):
                        await ws.send_json({"type": "key_ack", "ok": False, "reason": "rate", "t": client_t, "keycode": keycode})
                        continue
                    t0 = time.time()
                    try:
                        result = await adb.key(keycode)
                        await ws.send_json({
                            "type": "key_ack",
                            "ok": True,
                            "keycode": keycode,
                            "t": client_t,
                            "server_ms": round((time.time() - t0) * 1000, 1),
                            "result": result if isinstance(result, dict) else {"ok": True},
                        })
                        try:
                            broker.request_keyframe("key")
                        except Exception:
                            pass
                    except AdbError as e:
                        await ws.send_json({
                            "type": "key_ack",
                            "ok": False,
                            "keycode": keycode,
                            "t": client_t,
                            "reason": str(e)[:120],
                        })
                elif typ == "stats":
                    await ws.send_json({"type": "stats", **broker.stats()})
                elif typ == "motion":
                    # Touch over the open H.264 socket — skips AFD HTTP POST RTT
                    # (often 500–1300ms) for ~one WS frame + ADB pump (~20–50ms).
                    ip = ws.client.host if ws.client else "unknown"
                    client_t = msg.get("t")
                    action = str(msg.get("action") or "").upper()
                    try:
                        x = int(msg.get("x"))
                        y = int(msg.get("y"))
                    except (TypeError, ValueError):
                        await ws.send_json({"type": "motion_ack", "ok": False, "reason": "bad_xy", "t": client_t})
                        continue
                    if not _allow_input(ip):
                        await ws.send_json({"type": "motion_ack", "ok": False, "reason": "rate", "t": client_t, "action": action})
                        continue
                    t0 = time.time()
                    try:
                        result = await adb.motion(action, x, y)
                        await ws.send_json({
                            "type": "motion_ack",
                            "ok": True,
                            "action": result.get("action", action),
                            "x": x,
                            "y": y,
                            "t": client_t,
                            "server_ms": round((time.time() - t0) * 1000, 1),
                            "via": result.get("via"),
                            "acked": result.get("acked"),
                        })
                    except AdbError as e:
                        await ws.send_json({
                            "type": "motion_ack",
                            "ok": False,
                            "action": action,
                            "t": client_t,
                            "reason": str(e)[:120],
                        })
        except Exception:  # noqa: BLE001 — disconnect or malformed frame
            stop.set()

    async def heartbeat() -> None:
        try:
            while not stop.is_set():
                await asyncio.sleep(WS_PING_INTERVAL_S)
                if time.time() - last_pong > WS_PING_TIMEOUT_S:
                    stop.set()      # ghost tab: reclaim the viewer slot
                    return
                await ws.send_json({"type": "ping", "t": time.time()})
        except Exception:  # noqa: BLE001
            stop.set()

    tasks: list[asyncio.Task] = []
    try:
        async with broker.subscribe(name=f"{ws.client.host if ws.client else '?'}") as sub:
            # hello carries the codec string the decoder is configured with, so
            # it has to wait for this segment's SPS rather than guess.
            await broker.wait_ready(timeout=3.0)
            await ws.send_json({**broker.hello(), "server_time": time.time()})
            tasks = [
                asyncio.create_task(reader(), name="h264-reader"),
                asyncio.create_task(heartbeat(), name="h264-heartbeat"),
            ]
            stop_wait = asyncio.create_task(stop.wait(), name="h264-stop")
            while not stop.is_set():
                getter = asyncio.create_task(sub.queue.get(), name="h264-get")
                done, _ = await asyncio.wait(
                    {getter, stop_wait}, timeout=20.0, return_when=asyncio.FIRST_COMPLETED
                )
                if getter not in done:
                    getter.cancel()
                    if stop.is_set():
                        break
                    # A silent stream is normal (static screen emits nothing),
                    # so say so rather than tearing the socket down.
                    await ws.send_json({
                        "type": "stall",
                        "running": broker.running,
                        "frame_age_ms": broker.stats().get("frame_age_ms"),
                        "error": broker.stats().get("last_error"),
                    })
                    continue
                au = getter.result()
                sub.took(au)
                await ws.send_bytes(pack_au(au))
            stop_wait.cancel()
    except WebSocketDisconnect:
        pass
    except H264Error as e:
        with contextlib.suppress(Exception):
            await ws.close(code=1013, reason=str(e)[:100])
    except Exception:  # noqa: BLE001
        pass
    finally:
        stop.set()
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await ws.close()


@app.get("/adb/h264/stats")
async def adb_h264_stats():
    """H.264 pipeline telemetry: producer, viewers, fps/kbps, GOP state."""
    return {"ok": True, **adb.h264.stats()}


@app.post("/adb/h264/keyframe")
async def adb_h264_keyframe():
    """Force a fresh IDR (restarts the encoder; rate-limited server side)."""
    fired = adb.h264.request_keyframe("api")
    return {"ok": True, "requested": fired, "reason": None if fired else "cooldown"}


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    """Binary JPEG frame stream — the fast live path.

    Protocol: a JSON `hello` with device geometry, then alternating
    JSON metadata / binary JPEG pairs. Clients may send {"type":"nudge"} to
    force an immediate capture, or {"type":"ping"}.
    """
    await ws.accept()
    if adb.frames.subscribers >= MAX_STREAM_CLIENTS:
        await ws.send_json({
            "type": "bye",
            "reason": f"stream at capacity ({MAX_STREAM_CLIENTS} viewers)",
        })
        await ws.close(code=1013, reason="stream at capacity")
        return

    stop = asyncio.Event()
    last_pong = time.time()

    async def reader():
        nonlocal last_pong
        try:
            while True:
                msg = await ws.receive_json()
                typ = (msg or {}).get("type")
                if typ == "nudge":
                    adb.frames.nudge()
                elif typ == "pong":
                    last_pong = time.time()
                elif typ == "ping":
                    last_pong = time.time()
                    await ws.send_json({"type": "pong", "t": time.time()})
        except Exception:  # noqa: BLE001
            stop.set()

    async def heartbeat():
        # Ghost tabs used to sit on a subscriber slot (and keep the screencap
        # producer awake) until the TCP socket finally died.
        try:
            while not stop.is_set():
                await asyncio.sleep(WS_PING_INTERVAL_S)
                if time.time() - last_pong > WS_PING_TIMEOUT_S:
                    stop.set()
                    return
                await ws.send_json({"type": "ping", "t": time.time()})
        except Exception:  # noqa: BLE001
            stop.set()

    reader_task = asyncio.create_task(reader(), name="ws-stream-reader")
    beat_task = asyncio.create_task(heartbeat(), name="ws-stream-heartbeat")
    try:
        async with adb.frames.subscribe():
            size = adb.frames.latest
            await ws.send_json({
                "type": "hello",
                "device_width": size.device_width if size else None,
                "device_height": size.device_height if size else None,
                "interval_ms": round(adb.frames.interval * 1000),
                "viewers": adb.frames.subscribers,
                "h264": {
                    "available": adb.h264.available,
                    "path": "/ws/h264",
                },
            })
            last = 0
            while not stop.is_set():
                frame = await adb.frames.next_frame(after_version=last, timeout=10.0)
                if frame is None:
                    await ws.send_json({"type": "stall", "error": adb.frames.stats()["last_error"]})
                    continue
                last = frame.version
                await ws.send_json({
                    "type": "frame",
                    "version": frame.version,
                    "ts": frame.ts,
                    "bytes": len(frame.jpeg),
                    "image_width": frame.image_width,
                    "image_height": frame.image_height,
                    "device_width": frame.device_width,
                    "device_height": frame.device_height,
                    "capture_ms": round(frame.capture_ms),
                })
                await ws.send_bytes(frame.jpeg)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        stop.set()
        reader_task.cancel()
        beat_task.cancel()
        with contextlib.suppress(Exception):
            await ws.close()


@app.get("/adb/stream/stats")
async def adb_stream_stats():
    """Live-pipeline telemetry: producer health, viewers, frame age."""
    return {"ok": True, "max_clients": MAX_STREAM_CLIENTS, **adb.frames.stats()}


@app.post("/adb/stream/nudge")
async def adb_stream_nudge(request: Request):
    """Force an immediate capture (used after out-of-band device changes)."""
    # A nudge costs a screencap, so it shares the input budget.
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    adb.frames.nudge_soon()
    return {"ok": True}


@app.post("/adb/motion")
async def adb_motion(req: MotionRequest, request: Request):
    """Streaming finger. The viewer coalesces MOVE so this stays under the input budget."""
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    try:
        return await adb.motion(req.action, req.x, req.y)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/tap")
async def adb_tap(req: TapRequest, request: Request):
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    try:
        return await adb.tap(req.x, req.y)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/swipe")
async def adb_swipe(req: SwipeRequest, request: Request):
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    try:
        return await adb.swipe(req.x1, req.y1, req.x2, req.y2, req.duration_ms)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/key")
async def adb_key(req: KeyRequest, request: Request):
    """Hardware/navigation keys: HOME, BACK, APP_SWITCH, ENTER, DEL, ..."""
    # Same budget as tap/swipe: nav keys are the same `adb shell input` work.
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    try:
        return await adb.key(req.keycode)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/type")
async def adb_type(req: TypeRequest, request: Request):
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    try:
        return await adb.type_text(req.text)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/push")
async def adb_push(request: Request, file: UploadFile = File(...)):
    """Drop one host file into the device's shared Downloads directory."""
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    if not file.filename:
        raise HTTPException(400, "file name is required")
    total = 0
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(prefix="strlix-drop-", delete=False) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > CONTINUITY_MAX_FILE_BYTES:
                    raise HTTPException(413, f"file exceeds {CONTINUITY_MAX_FILE_BYTES // (1024 * 1024)} MiB limit")
                tmp.write(chunk)
        try:
            result = await adb.push_file(tmp_path, file.filename)
        except AdbError as e:
            raise HTTPException(503, str(e)) from e
        result.update({"bytes": total, "mime": file.content_type or "application/octet-stream"})
        return result
    finally:
        await file.close()
        if tmp_path:
            with contextlib.suppress(OSError):
                Path(tmp_path).unlink()


@app.post("/adb/clipboard")
async def adb_clipboard_set(req: ClipboardRequest, request: Request):
    """Bridge text into Android; paste into the focused field when requested."""
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    try:
        return await adb.clipboard_set(req.text, paste=req.paste)
    except AdbError as e:
        # A device without the Strlix helper can still receive ASCII-ish text
        # through the focused ADB input field. Do not pretend this is a global
        # clipboard bridge; return the fallback explicitly for the UI.
        if req.paste:
            try:
                typed = await adb.type_text(req.text)
                typed.update({"clipboard": False, "fallback": "typed", "detail": str(e)})
                return typed
            except AdbError:
                pass
        raise HTTPException(501, str(e)) from e


@app.get("/adb/clipboard")
async def adb_clipboard_get(request: Request):
    """Read Android clipboard when the Strlix helper APK is installed."""
    if not _allow_input(request.client.host if request.client else ""):
        raise HTTPException(429, "input rate limited")
    try:
        return await adb.clipboard_get()
    except AdbError as e:
        raise HTTPException(501, str(e)) from e


@app.get("/adb/size")
async def adb_size():
    try:
        return await adb.wm_size()
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.get("/voice/languages")
async def voice_languages():
    return {"ok": True, "languages": list_languages(), "default": "en-US"}


@app.get("/voice/status")
async def voice_status():
    return {
        "ok": True,
        **provider_status(),
        "stt": stt_status(),
        "live": live_hub.state,
        "browser_clients": live_hub.client_count(),
    }


@app.post("/voice/speak")
async def voice_speak(req: SpeakRequest):
    """Synthesize text on host; return audio URL for laptop browser playback."""
    try:
        audio = await synthesize(req.text, language=req.language or live_hub.state.get("language"), voice=req.voice)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"TTS failed: {type(e).__name__}: {e}") from e
    n = 0
    if req.broadcast:
        n = await live_hub.broadcast(
            {
                "type": "speak",
                "text": req.text,
                "audio_url": audio["url"],
                "provider": audio["provider"],
                "language": audio.get("language"),
                "voice": audio.get("voice"),
                "ms": audio["ms"],
            }
        )
    return {**audio, "broadcast_clients": n}


@app.post("/voice/turn")
async def voice_turn(req: VoiceTurnRequest):
    """Full live turn: LLM chat → host TTS → broadcast audio URL to laptop browsers."""
    await live_hub.broadcast({"type": "agent", "state": "acting", "line": "Working…", "source": req.source or "unknown"})
    try:
        result = await get_pilot().chat(req.message, history=req.history)
    except Exception as e:  # noqa: BLE001
        await live_hub.broadcast({"type": "agent", "state": "done", "line": "Ready", "source": req.source or "unknown"})
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e

    reply = result.get("reply") or ""
    audio: Optional[dict[str, Any]] = None
    if req.speak and reply.strip():
        try:
            audio = await synthesize(reply, language=req.language or live_hub.state.get("language"), voice=req.voice)
            await live_hub.broadcast(
                {
                    "type": "speak",
                    "text": reply,
                    "audio_url": audio["url"],
                    "provider": audio["provider"],
                    "language": audio.get("language"),
                    "voice": audio.get("voice"),
                    "user": req.message,
                    "source": req.source or "unknown",
                    "ms": audio["ms"],
                }
            )
        except Exception as e:  # noqa: BLE001
            # Chat succeeded; TTS optional failure shouldn't kill the turn
            audio = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    await live_hub.broadcast(
        {
            "type": "turn",
            "user": req.message,
            "reply": reply,
            "source": req.source or "unknown",
        }
    )
    await live_hub.broadcast({"type": "agent", "state": "done", "line": "Ready", "source": req.source or "unknown"})
    return {
        **result,
        "audio": audio,
        "routing": {
            "playback": "host_browser_webaudio",
            "phone_speaker": "device audio is /ws/audio (separate from assistant TTS)",
            "scrcpy_audio": "opus on /ws/audio when the emulator is not -no-audio",
        },
    }


@app.post("/voice/live")
async def voice_live_state(req: LiveStateRequest):
    lang = resolve_language(req.language or live_hub.state.get("language")).get("id")
    live_hub.state = {
        "active": req.active,
        "source": req.source,
        "language": lang,
        "started_at": live_hub.state.get("started_at") if req.active else None,
    }
    if req.active and not live_hub.state.get("started_at"):
        import time

        live_hub.state["started_at"] = time.time()
    await live_hub.broadcast({"type": "live_state", **live_hub.state})
    return {"ok": True, **live_hub.state, "browser_clients": live_hub.client_count()}


class BargeRequest(BaseModel):
    source: Optional[str] = "browser"
    reason: Optional[str] = "user_speech"


@app.post("/voice/barge")
async def voice_barge(req: BargeRequest):
    """Hard-stop assistant TTS on all laptop browsers (≤120ms client cancel)."""
    import time
    payload = {
        "type": "barge",
        "source": req.source or "unknown",
        "reason": req.reason or "user_speech",
        "ts": time.time(),
    }
    n = await live_hub.broadcast(payload)
    return {"ok": True, "broadcast_clients": n, **payload}


class ReplayUndoRequest(BaseModel):
    """Only reversible desktop-pilot action today: a vertical scroll gesture."""
    kind: str = Field(..., min_length=1)
    x1: int = Field(..., ge=0, le=10000)
    y1: int = Field(..., ge=0, le=10000)
    x2: int = Field(..., ge=0, le=10000)
    y2: int = Field(..., ge=0, le=10000)
    duration_ms: int = Field(default=300, ge=80, le=1200)


class ReplayGifRequest(BaseModel):
    title: Optional[str] = "Strlix replay"
    steps: list[str] = []
    # data-URL or raw base64 JPEG/PNG frames (max ~24)
    frames: list[str] = []
    duration_ms: int = 450  # per frame


@app.post("/replay/undo")
async def replay_undo(req: ReplayUndoRequest):
    """Reverse a safe, reversible Replay action without guessing at app state.

    The pilot currently marks vertical scrolls undoable. Taps, typing, payment,
    and navigation actions deliberately stay non-undoable until an app-level
    inverse exists.
    """
    if req.kind != "swipe":
        raise HTTPException(400, "this Replay action is not undoable")
    if abs(req.y2 - req.y1) <= abs(req.x2 - req.x1):
        raise HTTPException(400, "only vertical scrolls are undoable")
    try:
        result = await adb.swipe(req.x1, req.y1, req.x2, req.y2, req.duration_ms)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e
    return {"ok": True, "action": "undo", "inverse": result}


@app.post("/replay/revoke")
async def replay_revoke():
    """Turn off Strlix Accessibility control while preserving other services."""
    try:
        current = await adb.shell("settings get secure enabled_accessibility_services")
        raw = (current.get("stdout") or "").strip()
        services = [part for part in raw.split(":") if part and part.lower() not in {"null", "none"}]
        kept = [part for part in services if not part.startswith("com.zevi.agent/")]
        value = ":".join(kept)
        write_services = await adb.shell(
            "settings put secure enabled_accessibility_services " + shlex.quote(value)
        )
        if not write_services.get("ok"):
            raise HTTPException(503, write_services.get("stderr") or "could not update accessibility services")
        enabled = "1" if kept else "0"
        write_enabled = await adb.shell("settings put secure accessibility_enabled " + enabled)
        if not write_enabled.get("ok"):
            raise HTTPException(503, write_enabled.get("stderr") or "could not disable accessibility")
        adb.frames.nudge_soon()
        return {
            "ok": True,
            "revoked": len(kept) != len(services),
            "enabled_services": kept,
            "message": "Strlix control is off",
        }
    except HTTPException:
        raise
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/replay/gif")
async def replay_gif(req: ReplayGifRequest):
    """Minimal shareable Replay GIF from recent live frames + step captions."""
    import base64
    import json
    import time
    import uuid
    from io import BytesIO

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise HTTPException(500, f"Pillow required for GIF export: {e}") from e

    if not req.frames:
        raise HTTPException(400, "frames required")

    out_dir = ROOT / "demo" / "replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    rid = uuid.uuid4().hex[:10]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    gif_name = f"replay-{stamp}-{rid}.gif"
    json_name = f"replay-{stamp}-{rid}.json"
    gif_path = out_dir / gif_name
    json_path = out_dir / json_name

    pil_frames = []
    max_frames = min(len(req.frames), 24)
    for i, raw in enumerate(req.frames[:max_frames]):
        b64 = raw
        if "," in b64 and b64.strip().startswith("data:"):
            b64 = b64.split(",", 1)[1]
        try:
            data = base64.b64decode(b64)
            im = Image.open(BytesIO(data)).convert("RGB")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"bad frame {i}: {e}") from e
        # Downscale for small shareable GIF
        w, h = im.size
        max_w = 360
        if w > max_w:
            nh = int(h * (max_w / w))
            im = im.resize((max_w, nh), Image.Resampling.LANCZOS)
        # Burn-in step caption if available
        caption = ""
        if req.steps:
            caption = req.steps[min(i, len(req.steps) - 1)]
        if caption:
            draw = ImageDraw.Draw(im)
            pad = 6
            text = caption[:64]
            # dark bar
            bar_h = 28
            draw.rectangle([0, im.height - bar_h, im.width, im.height], fill=(18, 21, 28))
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            draw.text((pad, im.height - bar_h + 8), text, fill=(155, 163, 180), font=font)
        # tiny S watermark
        draw = ImageDraw.Draw(im)
        draw.text((im.width - 14, im.height - 22), "S", fill=(91, 140, 255))
        pil_frames.append(im)

    duration = max(120, min(int(req.duration_ms or 450), 1200))
    pil_frames[0].save(
        gif_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration,
        loop=0,
        optimize=True,
    )
    meta = {
        "ok": True,
        "id": rid,
        "title": req.title or "Strlix replay",
        "steps": req.steps,
        "frame_count": len(pil_frames),
        "gif": f"/demo/replay/{gif_name}",
        "json": f"/demo/replay/{json_name}",
        "created_at": stamp,
    }
    json_path.write_text(json.dumps(meta, indent=2))
    return meta


@app.get("/replay/latest")
async def replay_latest():
    out_dir = ROOT / "demo" / "replay"
    if not out_dir.exists():
        return {"ok": False, "gif": None}
    gifs = sorted(out_dir.glob("replay-*.gif"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not gifs:
        return {"ok": False, "gif": None}
    return {"ok": True, "gif": f"/demo/replay/{gifs[0].name}"}


@app.websocket("/ws/stt")
async def ws_stt(ws: WebSocket):
    """Duplex Azure Speech stream: browser sends 16 kHz mono PCM, server sends results."""
    await ws.accept()
    status = stt_status()
    if not status["available"]:
        await ws.send_json({"type": "unavailable", "reason": status["reason"], "fallback": "webspeech"})
        await ws.close(code=1013, reason="Azure Speech streaming STT unavailable")
        return

    # The browser sends a small start envelope before PCM so the locale can be
    # selected without exposing Speech credentials to the client.
    first: Optional[dict[str, Any]] = None
    try:
        first = await asyncio.wait_for(ws.receive(), timeout=3.0)
    except asyncio.TimeoutError:
        first = None
    except WebSocketDisconnect:
        return
    if first and first.get("type") == "websocket.disconnect":
        return

    locale = "en-US"
    if first and first.get("text"):
        try:
            hello = json.loads(first["text"])
            if hello.get("type") == "start":
                locale = resolve_language(hello.get("language") or locale).get("stt_locale", locale)
        except Exception:  # noqa: BLE001
            await ws.send_json({"type": "error", "reason": "bad_start", "message": "Invalid STT start message"})
            await ws.close(code=1003, reason="Invalid STT start message")
            return

    session = AzureSpeechSession(locale, asyncio.get_running_loop())
    try:
        await session.start()
    except Exception as exc:  # noqa: BLE001
        await ws.send_json({"type": "error", "reason": "azure_start_failed", "message": f"{type(exc).__name__}: {exc}"})
        await ws.close(code=1011, reason="Azure Speech session failed to start")
        return

    await ws.send_json({
        "type": "ready",
        "provider": "azure",
        "resource": status.get("resource"),
        "region": status.get("region"),
        "language": locale,
        "sample_rate": 16000,
        "channels": 1,
        "format": "s16le",
    })

    async def forward_results() -> None:
        while True:
            event = await session.events.get()
            await ws.send_json(event)

    forwarder = asyncio.create_task(forward_results())
    try:
        if first and first.get("bytes"):
            session.write(first["bytes"])
        while True:
            packet = await ws.receive()
            packet_type = packet.get("type")
            if packet_type == "websocket.disconnect":
                break
            if packet.get("bytes"):
                session.write(packet["bytes"])
                continue
            text = packet.get("text")
            if not text:
                continue
            try:
                message = json.loads(text)
            except Exception:  # noqa: BLE001
                await ws.send_json({"type": "error", "reason": "bad_message", "message": "Expected JSON control message"})
                continue
            typ = message.get("type")
            if typ == "ping":
                await ws.send_json({"type": "pong"})
            elif typ == "stop":
                break
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await session.stop()
        forwarder.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await forwarder
        with contextlib.suppress(Exception):
            await ws.close()


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    """Laptop browser connects here to receive speak events + play TTS locally."""
    await ws.accept()
    await live_hub.register(ws)
    await ws.send_json(
        {
            "type": "hello",
            "voice": provider_status(),
            "live": live_hub.state,
            "clients": live_hub.client_count(),
        }
    )
    try:
        while True:
            data = await ws.receive_json()
            typ = (data or {}).get("type")
            if typ == "ping":
                await ws.send_json({"type": "pong"})
            elif typ == "live_state":
                live_hub.state = {
                    "active": bool(data.get("active")),
                    "source": data.get("source") or "browser",
                    "language": resolve_language(data.get("language") or live_hub.state.get("language")).get("id"),
                    "started_at": live_hub.state.get("started_at"),
                }
                await live_hub.broadcast({"type": "live_state", **live_hub.state})
            elif typ == "transcript":
                # Browser may publish partial transcripts for phone UI sync
                await live_hub.broadcast(
                    {
                        "type": "transcript",
                        "text": data.get("text"),
                        "final": bool(data.get("final")),
                        "source": data.get("source") or "browser",
                    }
                )
            elif typ == "barge":
                await live_hub.broadcast(
                    {
                        "type": "barge",
                        "source": data.get("source") or "browser",
                        "reason": data.get("reason") or "user_speech",
                    }
                )
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        await live_hub.unregister(ws)


@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    """Cloud-phone audio for the laptop/phone speakers. Video stays on /ws/h264."""
    await ws.accept()
    broker = adb.audio
    if not broker.enabled:
        await ws.send_json({"type": "audio", "available": False, "reason": "DEVICE_AUDIO=0"})
        await ws.close(code=1013, reason="audio disabled")
        return
    stop = asyncio.Event()

    async def reader() -> None:
        try:
            while not stop.is_set():
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    stop.set()
        except Exception:  # noqa: BLE001
            stop.set()

    tasks = [asyncio.create_task(reader())]
    try:
        async with broker.subscribe() as queue:
            await ws.send_json({"type": "hello", "service": "audio", **broker.stats()})
            while not stop.is_set():
                getter = asyncio.create_task(queue.get())
                stop_wait = asyncio.create_task(stop.wait())
                done, _ = await asyncio.wait(
                    {getter, stop_wait}, timeout=20.0, return_when=asyncio.FIRST_COMPLETED
                )
                if getter not in done:
                    getter.cancel()
                    stop_wait.cancel()
                    if stop.is_set():
                        break
                    await ws.send_json({"type": "ping", "t": time.time(), **broker.stats()})
                    continue
                stop_wait.cancel()
                item = getter.result()
                if isinstance(item, dict):
                    await ws.send_json(item)
                else:
                    await ws.send_bytes(item)
    except RuntimeError as exc:
        with contextlib.suppress(Exception):
            await ws.send_json({"type": "audio", "available": False, "reason": str(exc)})
            await ws.close(code=1013, reason=str(exc)[:100])
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        stop.set()
        for task in tasks:
            task.cancel()
        with contextlib.suppress(Exception):
            await ws.close()


@app.on_event("startup")
async def _warm_input() -> None:
    asyncio.create_task(adb.warm_input())


@app.on_event("shutdown")
async def _shutdown() -> None:
    await adb.frames.aclose()
    await adb.h264.aclose()


@app.get("/favicon.ico")
async def favicon():
    return HTMLResponse("")
