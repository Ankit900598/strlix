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
import gzip
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
INPUT_RATE_PER_SEC = float(os.environ.get("INPUT_RATE_PER_SEC", "90"))
WS_PING_INTERVAL_S = float(os.environ.get("WS_PING_INTERVAL_S", "15"))
WS_PING_TIMEOUT_S = float(os.environ.get("WS_PING_TIMEOUT_S", "40"))
_input_buckets: dict[str, list[float]] = {}

app = FastAPI(
    title="Strlix desktop-api",
    version="0.3.3",
    description="Viewer stream + input. Session-bound to one device from the pool.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def _warm_encoder() -> None:
    """perf1: start the H.264 encoder at boot (H264_KEEP_WARM_S>0) once adb sees the phone."""
    async def go() -> None:
        # Wait for a fully booted guest; starting scrcpy earlier only racks up
        # failed segments (the producer backs off and can mark itself unavailable).
        for _ in range(150):
            try:
                r = await adb.shell("getprop sys.boot_completed")
                if (r.get("stdout") or "").strip() == "1":
                    await asyncio.sleep(3)  # let the launcher settle
                    adb.h264.warm()
                    return
            except Exception:  # noqa: BLE001 - adb/phone still coming up
                pass
            await asyncio.sleep(2)
    asyncio.create_task(go())


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


# Touch playout pacing (normal-feel). Over AFD + the internet, WS motion events
# arrive bunched or with a late UP. scrcpy stamps each injected event with the
# *arrival* time, so Android's VelocityTracker sees a wrong finger speed and
# flings (Recents swipe-away, tab swipe, fast scroll) snap back. Replay MOVE/UP
# at the client's own spacing (msg "t") plus a small jitter buffer. DOWN is
# never delayed, so tap latency is unchanged.
MOTION_PLAYOUT_MS = float(os.getenv("MOTION_PLAYOUT_MS", "40"))
MOTION_PACE_MAX_MS = float(os.getenv("MOTION_PACE_MAX_MS", "250"))
# feel2: adaptive jitter buffer. A late MOVE used to be injected at once and so
# were all following events whose (old) targets had passed -> a burst of MOVEs
# a few ms apart right before UP, i.e. a wrong fling velocity. Now a late event
# re-anchors the timeline (later events keep the client's spacing relative to
# it) and the per-connection buffer grows toward the observed lateness
# (capped at MOTION_PACE_MAX_MS, default 250 ms), decaying 10% per gesture.
# On a clean link it stays at MOTION_PLAYOUT_MS (40 ms); DOWN is never delayed.
# A/B on 5 Oct (5+5 Recents dismissals via AFD each): adaptive 6/10, fixed 6/10.
# Cleaner injection traces but no measurable win, and it can delay DOWN (taps)
# on jittery links, so it ships OFF by default. Turn on with MOTION_PACE_ADAPT=1.
MOTION_PACE_ADAPT = os.getenv("MOTION_PACE_ADAPT", "0") in ("1", "true", "yes")
_PACE_STATS: dict[str, Any] = {"playout_ms": MOTION_PLAYOUT_MS, "adaptive": MOTION_PACE_ADAPT, "gestures": 0,
                               "paced": 0, "late": 0, "late_max_ms": 0.0, "buffer_ms": MOTION_PLAYOUT_MS, "last": []}


async def _pace_motion(pace: dict, action: str, client_t: Any) -> None:
    if MOTION_PLAYOUT_MS <= 0 or not isinstance(client_t, (int, float)):
        return
    now = time.monotonic()
    buf = pace.setdefault("buf", MOTION_PLAYOUT_MS)
    if action == "DOWN" or pace.get("srv") is None:
        if MOTION_PACE_ADAPT:
            pace["buf"] = buf = max(MOTION_PLAYOUT_MS, buf * 0.9)
        # Shift the whole gesture by the adaptive part of the buffer (DOWN too):
        # a DOWN injected at once followed by MOVEs 200+ ms later reads as
        # "press and hold, then drag" and the launcher refused the swipe.
        # On a clean link buf == MOTION_PLAYOUT_MS, so DOWN is not delayed.
        extra = max(0.0, buf - MOTION_PLAYOUT_MS)
        if extra > 0:
            await asyncio.sleep(extra / 1000.0)
            now = time.monotonic()
        pace["srv"], pace["cli"], pace["t0"] = now - extra / 1000.0, float(client_t), now
        pace["trace"] = [("D", 0, 0)]
        _PACE_STATS["gestures"] += 1
        _PACE_STATS["buffer_ms"] = round(buf, 1)
        return
    cli_ms = float(client_t) - pace["cli"]
    target = pace["srv"] + (cli_ms + buf) / 1000.0
    wait = target - now
    if wait > 0:
        _PACE_STATS["paced"] += 1
        await asyncio.sleep(min(wait, MOTION_PACE_MAX_MS / 1000.0))
    else:
        late_ms = -wait * 1000.0
        _PACE_STATS["late"] += 1
        _PACE_STATS["late_max_ms"] = round(max(_PACE_STATS["late_max_ms"], late_ms), 1)
        if MOTION_PACE_ADAPT:
            pace["srv"] += late_ms / 1000.0          # re-anchor: keep spacing after this event
            pace["buf"] = min(MOTION_PACE_MAX_MS, buf + late_ms + 10.0)
    tr = pace.get("trace")
    if tr is not None and len(tr) < 64:
        tr.append((action[0], round(cli_ms), round((time.monotonic() - pace["t0"]) * 1000)))
    if action in ("UP", "CANCEL"):
        pace["srv"] = None
        _PACE_STATS["last"] = tr or []


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


_INDEX_CACHE: dict[str, Any] = {}


@app.get("/")
async def index(request: Request):
    """Serve the phone-first viewer, gzip-compressed when the client allows it.

    perf1: the single-file viewer is ~180 KB. AFD forwards it uncompressed
    (route caching/compression is off for the stream endpoint), which costs
    several TCP round trips on a long path (~0.9 s from the US test box).
    gzip makes it ~45 KB. Bytes are cached per file mtime.
    """
    index_path = static_dir / "index.html"
    if not index_path.is_file():
        return HTMLResponse("<h1>desktop-api</h1><p>static/index.html missing</p>")
    mtime = index_path.stat().st_mtime
    if _INDEX_CACHE.get("mtime") != mtime:
        raw = index_path.read_bytes()
        _INDEX_CACHE.update(mtime=mtime, raw=raw, gz=gzip.compress(raw, compresslevel=9, mtime=0))
    headers = {"Cache-Control": "no-cache", "Vary": "Accept-Encoding"}
    if "gzip" in (request.headers.get("accept-encoding") or "").lower():
        headers["Content-Encoding"] = "gzip"
        return Response(_INDEX_CACHE["gz"], media_type="text/html; charset=utf-8", headers=headers)
    return Response(_INDEX_CACHE["raw"], media_type="text/html; charset=utf-8", headers=headers)


@app.get("/health")
async def health():
    info: dict[str, Any] = {
        "ok": True,
        "service": "desktop-api",
        "version": "0.3.3",
        "uptime_s": round(time.time() - STARTED, 1),
        "adb_serial": adb.serial,
        "stream": {**adb.frames.stats(), "max_clients": MAX_STREAM_CLIENTS},
        "h264": adb.h264.stats(),
        "audio": adb.audio.stats(),
        "touch": adb.touch.stats(),
        "touch_pacing": dict(_PACE_STATS),
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
    """Opus packets from scrcpy playback capture. Config frames have flags bit 0.

    Compatible with both AudioBroker (_WireQueue.get → bytes|dict) and
    DeviceAudioBroker (raw asyncio.Queue of wire bytes|dict). PR #9 switched
    AudioBroker.subscribe to yield _WireQueue; the old ``sub.queue.get`` +
    ``broker.wire(packet)`` path AttributeError'd and closed the socket in
    ~100ms — the live "opening scrcpy audio socket" toast hang.
    """
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
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    stop.set()
                    return
                if msg.get("type") == "websocket.receive" and msg.get("text"):
                    import json as _json
                    with contextlib.suppress(Exception):
                        data = _json.loads(msg["text"])
                        if (data or {}).get("type") == "stats":
                            await ws.send_json({"type": "stats", **broker.stats()})
        except Exception:  # noqa: BLE001
            stop.set()

    async def _queue_get(queue_obj):
        # AudioBroker: _WireQueue.get() → bytes|dict
        # DeviceAudioBroker: asyncio.Queue.get() → bytes|dict
        get = getattr(queue_obj, "get", None)
        if get is None and hasattr(queue_obj, "queue"):
            get = queue_obj.queue.get
        if get is None:
            raise AudioError("audio subscribe() yielded an unknown queue type")
        return await get()

    async def _send_item(item: object) -> None:
        if isinstance(item, dict):
            # Never forward sticky "opening…" as a hard error — client ignores it.
            src = str(item.get("source") or "")
            if src in ("starting", "idle"):
                return
            await ws.send_json(item)
            return
        if isinstance(item, (bytes, bytearray, memoryview)):
            await ws.send_bytes(bytes(item))
            return
        # Legacy AudioPacket object
        await ws.send_bytes(broker.wire(item))

    tasks = [asyncio.create_task(reader())]
    try:
        async with broker.subscribe(name=f"desktop-audio-{ws.client.host if ws.client else '?'}") as queue:
            hello = broker.hello() if hasattr(broker, "hello") else {"type": "hello", "service": "audio", **broker.stats()}
            hello["server_time"] = time.time()
            await ws.send_json(hello)
            while not stop.is_set():
                getter = asyncio.create_task(_queue_get(queue))
                stop_wait = asyncio.create_task(stop.wait())
                done, _ = await asyncio.wait(
                    {getter, stop_wait}, timeout=5.0, return_when=asyncio.FIRST_COMPLETED
                )
                if getter not in done:
                    getter.cancel()
                    stop_wait.cancel()
                    if stop.is_set():
                        break
                    # Soft keepalive — omit transient opening reason so the toast stays clear.
                    st = broker.stats()
                    if st.get("source") not in ("starting", "idle"):
                        await ws.send_json({"type": "audio", **{k: st.get(k) for k in ("source", "codec", "reason", "available", "packet_rate", "packet_age_ms")}})
                    continue
                stop_wait.cancel()
                item = getter.result()
                await _send_item(item)
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
    pace: dict = {}

    async def reader() -> None:
        nonlocal last_pong
        try:
            while not stop.is_set():
                msg = await ws.receive_json()
                typ = (msg or {}).get("type")
                if typ in ("pong", "ping"):
                    last_pong = time.time()
                    if typ == "ping":
                        await ws.send_json({"type": "pong", "t": msg.get("t"), "server_time": time.time()})
                elif typ == "keyframe":
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
                    broker.note_input()
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
                        # No forced IDR here: request_keyframe() kills and respawns
                        # scrcpy (~1 s of frozen video right when Back/Recents
                        # animates). The encoder already emits on screen change.
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
                    ip = ws.client.host if ws.client else "unknown"
                    client_t = msg.get("t")
                    action = str(msg.get("action") or "").upper()
                    try:
                        x = int(msg.get("x"))
                        y = int(msg.get("y"))
                    except (TypeError, ValueError):
                        await ws.send_json({"type": "motion_ack", "ok": False, "reason": "bad_xy", "t": client_t})
                        continue
                    # Never rate-limit DOWN/UP/CANCEL: a dropped UP leaves a
                    # finger stuck on the phone and breaks the next gesture.
                    if action == "MOVE" and not _allow_input(ip):
                        await ws.send_json({"type": "motion_ack", "ok": False, "reason": "rate", "t": client_t, "action": action})
                        continue
                    if action != "MOVE":
                        _allow_input(ip)
                    broker.note_input()
                    t_recv = time.time()
                    await _pace_motion(pace, action, client_t)
                    t0 = time.time()
                    try:
                        result = await adb.motion(action, x, y)
                        if action == "DOWN" and msg.get("trace"):
                            # Opt-in latency trace: reported after the first AU that follows the tap.
                            pace["taptrace"] = {"t": client_t, "recv": t_recv, "paced": t0, "inj": time.time(), "aus": []}
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
                tr = pace.get("taptrace")
                if tr is not None and au.wall >= tr["inj"]:
                    tr["aus"].append((au.wall, time.time(), au.size))
                    if len(tr["aus"]) >= 3:
                        pace.pop("taptrace", None)
                        r = lambda a, b: round((a - b) * 1000, 1)
                        await ws.send_json({
                            "type": "tap_trace", "t": tr["t"],
                            "pace_ms": r(tr["paced"], tr["recv"]),
                            "inject_ms": r(tr["inj"], tr["paced"]),
                            "inj_to_au_ms": [r(w, tr["inj"]) for w, _, _ in tr["aus"]],
                            "au_to_send_ms": [r(sd, w) for w, sd, _ in tr["aus"]],
                            "au_bytes": [n for _, _, n in tr["aus"]],
                            "server_recv": tr["recv"],
                        })
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


class AskIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: Optional[list[dict[str, Any]]] = None
    language: Optional[str] = None


@app.post("/chat")
async def viewer_ask(body: AskIn, request: Request):
    """Viewer Ask -> android-api (LLM) -> tools run on this phone via ADB."""
    from . import agent_bridge

    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "")
    if not agent_bridge.allow(ip):
        raise HTTPException(429, "Too many Ask requests — wait a minute and try again.")
    out = await agent_bridge.chat_turn(adb, body.message, body.history, body.language)
    if not out.get("ok"):
        raise HTTPException(int(out.get("status") or 502), out.get("error") or "Ask failed")
    return out


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
            "POST /chat": "viewer Ask: proxied to android-api, tools run on this phone",
        },
        "not_here": ["/v1/chat (android-api)", "Accessibility tool protocol"],
    }
