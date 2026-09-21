"""session-broker HTTP API — :8790

Binds desktop viewer sessions to one device from the pool.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "packages" / "common"))

from strlix_common.auth import TokenService  # noqa: E402
from strlix_common.config import get_settings  # noqa: E402

from .pool import POOL  # noqa: E402

settings = get_settings()
tokens = TokenService(secret=settings.jwt_secret, issuer=settings.jwt_issuer)
STARTED = time.time()

app = FastAPI(title="Strlix session-broker", version="0.1.0")


class AcquireRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    ttl_s: int = Field(default=3600, ge=60, le=86400)
    prefer_device: Optional[str] = None


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "session-broker",
        "uptime_s": round(time.time() - STARTED, 1),
        "capacity": POOL.capacity_report(),
    }


@app.get("/v1/devices")
async def list_devices():
    return {"ok": True, "devices": POOL.list_devices(), "capacity": POOL.capacity_report()}


@app.post("/v1/sessions")
async def acquire(req: AcquireRequest):
    try:
        sess = POOL.acquire(req.user_id, ttl_s=req.ttl_s, prefer_device=req.prefer_device)
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    # Mint desktop-api token bound to this session + device
    access = tokens.mint(
        sub=req.user_id,
        aud="desktop-api",
        scopes=["stream", "input"] if sess.controller else ["stream"],
        sid=sess.sid,
        device_id=sess.device_id,
        ttl=req.ttl_s,
    )
    return {
        "ok": True,
        "session": {
            "sid": sess.sid,
            "device_id": sess.device_id,
            "adb_serial": sess.adb_serial,
            "controller": sess.controller,
            "expires_at": sess.expires_at,
        },
        "access_token": access,
        "token_type": "Bearer",
        "desktop_api_hint": "http://127.0.0.1:8789",
    }


@app.get("/v1/sessions/{sid}")
async def get_session(sid: str):
    sess = POOL.get(sid)
    if not sess:
        raise HTTPException(404, "session not found")
    return {
        "ok": True,
        "session": {
            "sid": sess.sid,
            "user_id": sess.user_id,
            "device_id": sess.device_id,
            "adb_serial": sess.adb_serial,
            "controller": sess.controller,
            "expires_at": sess.expires_at,
        },
    }


@app.delete("/v1/sessions/{sid}")
async def release(sid: str):
    ok = POOL.release(sid)
    if not ok:
        raise HTTPException(404, "session not found")
    return {"ok": True, "released": sid}
