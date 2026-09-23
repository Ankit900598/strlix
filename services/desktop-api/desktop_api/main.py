"""desktop-api — web phone mirror backend.

Owns: H.264/WS + JPEG stream, tap/swipe/key, session binding to ONE device.
Does NOT own: in-phone chat LLM loop, Accessibility tool protocol (android-api).

Phase-1: reuses zevi-cloudphone/app ADB + H264 modules against the pilot
emulator serial. Session broker (:8791) issues desktop JWTs with sid+device_id.

Default port: 8789 (monolith pilot remains :8787).
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(ROOT / "packages" / "common"))
sys.path.insert(0, str(ROOT))  # import app.adb_client, app.h264_stream

from strlix_common.auth import AuthError, TokenService, bearer_from_header  # noqa: E402
from strlix_common.config import get_settings  # noqa: E402

from app.adb_client import STREAM_MAX_WIDTH, STREAM_QUALITY, AdbClient, AdbError  # noqa: E402
from app.audio_stream import AUDIO_MAX_CLIENTS, AudioError  # noqa: E402
from app.client_debug import record as record_client_debug  # noqa: E402
from app.client_debug import snapshot as client_debug_snapshot  # noqa: E402
from app.h264_stream import H264_MAX_CLIENTS, pack_au  # noqa: E402

settings = get_settings()
tokens = TokenService(secret=settings.jwt_secret, issuer=settings.jwt_issuer)
adb = AdbClient()
STARTED = time.time()
BROKER_URL = os.environ.get("SESSION_BROKER_URL", "http://127.0.0.1:8791")
MAX_STREAM_CLIENTS = int(os.environ.get("MAX_STREAM_CLIENTS", "12"))
INPUT_RATE_PER_SEC = float(os.environ.get("INPUT_RATE_PER_SEC", "60"))
WS_PING_INTERVAL_S = float(os.environ.get("WS_PING_INTERVAL_S", "15"))
WS_PING_TIMEOUT_S = float(os.environ.get("WS_PING_TIMEOUT_S", "40"))
_input_buckets: dict[str, list[float]] = {}

app = FastAPI(
    title="Strlix desktop-api",
    version="0.3.1",
    description="Viewer stream + input. Session-bound to one device from the pool.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = ROOT / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def _allow_input(ip: str) -> bool:
    now = time.time()
    key = ip or "unknown"
    bucket = [t for t in _input_buckets.get(key, []) if now - t < 1.0]
    if len(bucket) >= INPUT_RATE_PER_SEC:
        _input_buckets[key] = bucket
        return False
    bucket.append(now)
    _input_buckets[key] = bucket
    return True


def optional_desktop_auth(authorization: Optional[str]) -> Optional[dict]:
    require = os.environ.get("STRLIX_REQUIRE_AUTH", "0") == "1"
    if not authorization:
        if require:
            raise HTTPException(401, "Authorization required")
        return None
    try:
        raw = bearer_from_header(authorization)
        claims = tokens.verify(raw, expected_aud="desktop-api")
        return {
            "sub": claims.sub,
            "sid": claims.sid,
            "device_id": claims.device_id,
            "scopes": claims.scopes,
        }
    except AuthError as e:
        raise HTTPException(e.status, e.message) from e


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
    keycode: str = Field(..., min_length=1)


class TypeRequest(BaseModel):
    text: str = Field(..., min_length=1)


class BindRequest(BaseModel):
    user_id: str = Field(default="viewer-anon", min_length=1)
    ttl_s: int = Field(default=3600, ge=60, le=86400)


@app.get("/")
async def index():
    """Serve the existing phone-first viewer (same static UI as pilot)."""
    index_path = static_dir / "index.html"
    if not index_path.is_file():
        return HTMLResponse("<h1>desktop-api</h1><p>static/index.html missing</p>")
    # Inject a small banner comment — page still talks to same-origin paths.
    html = index_path.read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/health")
async def health():
    info: dict[str, Any] = {
        "ok": True,
        "service": "desktop-api",
        "version": "0.3.1",
        "uptime_s": round(time.time() - STARTED, 1),
        "adb_serial": adb.serial,
        "stream": {**adb.frames.stats(), "max_clients": MAX_STREAM_CLIENTS},
        "h264": adb.h264.stats(),
        "audio": adb.audio.stats(),
        "client_debug": client_debug_snapshot(),
        "input": adb.input_status(),
        "broker_url": BROKER_URL,
        "auth_required": os.environ.get("STRLIX_REQUIRE_AUTH", "0") == "1",
        "note": "Viewer only — chat/voice LLM lives on android-api :8788",
    }
    try:
        state = await adb.ensure_connected()
        info["adb_state"] = state
    except Exception as e:  # noqa: BLE001
        info["adb_state"] = f"error: {e}"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{BROKER_URL}/health")
            info["broker"] = r.json() if r.status_code == 200 else {"ok": False, "status": r.status_code}
    except Exception as e:  # noqa: BLE001
        info["broker"] = {"ok": False, "error": str(e)}
    return info


@app.post("/v1/sessions/bind")
async def bind_session(req: BindRequest):
    """Acquire a device session from the broker and return a desktop JWT."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(
                f"{BROKER_URL}/v1/sessions",
                json={"user_id": req.user_id, "ttl_s": req.ttl_s},
            )
            if r.status_code >= 400:
                raise HTTPException(r.status_code, r.text)
            return r.json()
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"broker unavailable: {e}") from e


@app.get("/adb/preview")
async def adb_preview(
    quality: int = 50,
    max_width: int = STREAM_MAX_WIDTH,
    authorization: Optional[str] = Header(default=None),
):
    optional_desktop_auth(authorization)
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
        },
    )


@app.get("/adb/size")
async def adb_size(authorization: Optional[str] = Header(default=None)):
    optional_desktop_auth(authorization)
    try:
        size = await adb.wm_size()
        return {"ok": True, **size}
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/motion")
async def adb_motion(
    req: MotionRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    claims = optional_desktop_auth(authorization)
    if claims and "input" not in claims["scopes"] and "*" not in claims["scopes"]:
        raise HTTPException(403, "session is view-only (no input scope)")
    ip = request.client.host if request.client else "unknown"
    if not _allow_input(ip):
        raise HTTPException(429, "input rate limit")
    try:
        return await adb.motion(req.action, req.x, req.y)
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/tap")
async def adb_tap(
    req: TapRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    claims = optional_desktop_auth(authorization)
    if claims and "input" not in claims["scopes"] and "*" not in claims["scopes"]:
        # view-only session
        raise HTTPException(403, "session is view-only (no input scope)")
    ip = request.client.host if request.client else "unknown"
    if not _allow_input(ip):
        raise HTTPException(429, "input rate limit")
    try:
        await adb.tap(req.x, req.y)
        return {"ok": True, "x": req.x, "y": req.y}
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/swipe")
async def adb_swipe(
    req: SwipeRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    claims = optional_desktop_auth(authorization)
    if claims and "input" not in claims["scopes"] and "*" not in claims["scopes"]:
        raise HTTPException(403, "session is view-only")
    ip = request.client.host if request.client else "unknown"
    if not _allow_input(ip):
        raise HTTPException(429, "input rate limit")
    try:
        await adb.swipe(req.x1, req.y1, req.x2, req.y2, req.duration_ms)
        return {"ok": True}
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/key")
async def adb_key(
    req: KeyRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    claims = optional_desktop_auth(authorization)
    if claims and "input" not in claims["scopes"] and "*" not in claims["scopes"]:
        raise HTTPException(403, "session is view-only")
    ip = request.client.host if request.client else "unknown"
    if not _allow_input(ip):
        raise HTTPException(429, "input rate limit")
    try:
        await adb.key(req.keycode)
        return {"ok": True, "keycode": req.keycode}
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


@app.post("/adb/type")
async def adb_type(
    req: TypeRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    claims = optional_desktop_auth(authorization)
    if claims and "input" not in claims["scopes"] and "*" not in claims["scopes"]:
        raise HTTPException(403, "session is view-only")
    ip = request.client.host if request.client else "unknown"
    if not _allow_input(ip):
        raise HTTPException(429, "input rate limit")
    try:
        await adb.type_text(req.text)
        return {"ok": True}
    except AdbError as e:
        raise HTTPException(503, str(e)) from e


class ClientDebugReport(BaseModel):
    audio_error: Optional[str] = None
    audio_packets: int = 0
    audio_played: int = 0
    audio_codec: Optional[str] = None
    h264_error: Optional[str] = None
    h264_frames: int = 0
    h264_dropped: int = 0
    h264_source: Optional[str] = None
    ua: Optional[str] = None


@app.post("/debug/client")
async def debug_client(req: ClientDebugReport):
    """Viewer decode counters. Does not affect the stream."""
    return record_client_debug(req.model_dump())


@app.websocket("/ws/audio")
async def ws_audio(ws: WebSocket):
    """Opus packets from scrcpy playback capture. Config frames have flags bit 0."""
    broker = adb.audio
    await ws.accept()
    if not broker.enabled:
        await ws.send_json({"type": "audio", "source": "error", "codec": "opus", "reason": "audio disabled"})
        await ws.close(code=1013)
        return
    if broker.subscribers >= AUDIO_MAX_CLIENTS:
        await ws.send_json({"type": "audio", "source": "error", "reason": "audio at capacity"})
        await ws.close(code=1013)
        return
    stop = asyncio.Event()

    async def reader() -> None:
        try:
            while not stop.is_set():
                msg = await ws.receive_json()
                if (msg or {}).get("type") == "stats":
                    await ws.send_json({"type": "stats", **broker.stats()})
        except Exception:  # noqa: BLE001
            stop.set()

    tasks = [asyncio.create_task(reader())]
    try:
        async with broker.subscribe(name=f"desktop-audio-{ws.client.host if ws.client else '?'}") as sub:
            hello = broker.hello()
            hello["server_time"] = time.time()
            await ws.send_json(hello)
            # Push a status line once the producer has had a moment to open scrcpy.
            await asyncio.sleep(0.05)
            await ws.send_json({"type": "audio", **{k: broker.stats()[k] for k in ("source", "codec", "reason", "available")}})
            while not stop.is_set():
                getter = asyncio.create_task(sub.queue.get())
                stop_wait = asyncio.create_task(stop.wait())
                done, _ = await asyncio.wait(
                    {getter, stop_wait}, timeout=5.0, return_when=asyncio.FIRST_COMPLETED
                )
                if getter not in done:
                    getter.cancel()
                    stop_wait.cancel()
                    if stop.is_set():
                        break
                    await ws.send_json({"type": "audio", **{k: broker.stats()[k] for k in ("source", "codec", "reason", "available", "packet_rate", "packet_age_ms")}})
                    continue
                stop_wait.cancel()
                packet = getter.result()
                await ws.send_bytes(broker.wire(packet))
    except WebSocketDisconnect:
        pass
    except AudioError as e:
        with contextlib.suppress(Exception):
            await ws.send_json({"type": "audio", "source": "error", "reason": str(e)})
            await ws.close(code=1013, reason=str(e)[:100])
    except Exception:  # noqa: BLE001
        pass
    finally:
        stop.set()
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await ws.close()


@app.websocket("/ws/h264")
async def ws_h264(ws: WebSocket):
    """Binary H.264 AU stream — same wire format as pilot monolith."""
    from app.h264_stream import H264Error  # local import keeps module load light

    broker = adb.h264
    await ws.accept()
    asyncio.create_task(adb.warm_input())
    if not broker.enabled:
        await ws.send_json({"type": "bye", "reason": "h264 disabled", "fallback": "/ws/stream"})
        await ws.close(code=1013)
        return
    if broker.subscribers >= H264_MAX_CLIENTS:
        await ws.send_json({"type": "bye", "reason": "h264 at capacity", "fallback": "/ws/stream"})
        await ws.close(code=1013)
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
                        await ws.send_json({"type": "pong", "t": time.time()})
                elif typ == "keyframe":
                    broker.request_keyframe("client")
                elif typ == "stats":
                    await ws.send_json({"type": "stats", **broker.stats()})
        except Exception:  # noqa: BLE001
            stop.set()

    async def heartbeat() -> None:
        try:
            while not stop.is_set():
                await asyncio.sleep(WS_PING_INTERVAL_S)
                if time.time() - last_pong > WS_PING_TIMEOUT_S:
                    stop.set()
                    return
                await ws.send_json({"type": "ping", "t": time.time()})
        except Exception:  # noqa: BLE001
            stop.set()

    tasks: list[asyncio.Task] = []
    try:
        async with broker.subscribe(name=f"desktop-{ws.client.host if ws.client else '?'}") as sub:
            await broker.wait_ready(timeout=3.0)
            hello = broker.hello()
            hello["service"] = "desktop-api"
            hello["server_time"] = time.time()
            await ws.send_json(hello)
            tasks = [
                asyncio.create_task(reader()),
                asyncio.create_task(heartbeat()),
            ]
            stop_wait = asyncio.create_task(stop.wait())
            while not stop.is_set():
                getter = asyncio.create_task(sub.queue.get())
                done, _ = await asyncio.wait(
                    {getter, stop_wait}, timeout=20.0, return_when=asyncio.FIRST_COMPLETED
                )
                if getter not in done:
                    getter.cancel()
                    if stop.is_set():
                        break
                    await ws.send_json({
                        "type": "stall",
                        "running": broker.running,
                        "frame_age_ms": broker.stats().get("frame_age_ms"),
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


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    """Binary JPEG frames (fallback)."""
    await ws.accept()
    if adb.frames.subscribers >= MAX_STREAM_CLIENTS:
        await ws.send_json({"type": "bye", "reason": "stream at capacity"})
        await ws.close(code=1013)
        return
    stop = asyncio.Event()
    last_pong = time.time()

    async def reader() -> None:
        nonlocal last_pong
        try:
            while not stop.is_set():
                msg = await ws.receive_json()
                if (msg or {}).get("type") in ("pong", "ping"):
                    last_pong = time.time()
        except Exception:  # noqa: BLE001
            stop.set()

    tasks = [asyncio.create_task(reader())]
    try:
        await ws.send_json({"type": "hello", "service": "desktop-api", "codec": "jpeg"})
        async with adb.frames.subscribe():
            last = 0
            while not stop.is_set():
                if time.time() - last_pong > WS_PING_TIMEOUT_S:
                    break
                frame = await adb.frames.next_frame(after_version=last, timeout=10.0)
                if frame is None:
                    continue
                last = frame.version
                await ws.send_bytes(frame.jpeg)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        stop.set()
        for t in tasks:
            t.cancel()
        with contextlib.suppress(Exception):
            await ws.close()


@app.get("/v1/openapi-sketch")
async def openapi_sketch():
    return {
        "service": "desktop-api",
        "base": "http://<host>:8789",
        "auth": "POST /v1/sessions/bind → Bearer (aud=desktop-api, sid+device_id)",
        "routes": {
            "GET /": "phone-first viewer HTML",
            "GET /health": "ADB + stream + broker",
            "POST /v1/sessions/bind": "lease device via session-broker",
            "WS /ws/h264": "H.264 Annex-B AUs (4-byte start codes)",
            "WS /ws/audio": "Opus packets; flags bit0 = OpusHead config",
            "POST /debug/client": "viewer decode error / frame counters",
            "WS /ws/stream": "JPEG fallback",
            "GET /adb/preview": "latest JPEG",
            "POST /adb/tap|swipe|key|type": "input (controller scope)",
        },
        "not_here": ["/chat", "/v1/chat", "Accessibility tool protocol"],
    }
