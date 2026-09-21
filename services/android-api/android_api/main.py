"""android-api — Strlix in-phone backend.

Owns: chat, voice STT/TTS hooks, Accessibility agent tool protocol, health.
Does NOT own: ADB screencap, H.264 fan-out, web viewer taps (those are desktop-api).

Default port: 8788 (pilot monolith stays on 8787 until cutover).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]  # zevi-cloudphone/
load_dotenv(ROOT / ".env")

# Make packages/common importable without install during pilot
sys.path.insert(0, str(ROOT / "packages" / "common"))

from strlix_common.auth import AuthError, TokenService, bearer_from_header  # noqa: E402
from strlix_common.config import get_settings  # noqa: E402

from .agent_protocol import ChatTurnRequest, ChatTurnResponse, ToolResult  # noqa: E402
from .llm import AndroidLLM  # noqa: E402
from .rate_limit import RateLimiter  # noqa: E402

settings = get_settings()
tokens = TokenService(
    secret=settings.jwt_secret,
    issuer=settings.jwt_issuer,
    ttl_seconds=settings.jwt_ttl_seconds,
)
chat_limiter = RateLimiter(per_minute=settings.chat_rate_per_min)
_llm: Optional[AndroidLLM] = None
STARTED = time.time()

app = FastAPI(
    title="Strlix android-api",
    version="0.1.0",
    description="Phone-first chat/voice/Accessibility backend. No ADB stream.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_llm() -> AndroidLLM:
    global _llm
    if _llm is None:
        try:
            _llm = AndroidLLM()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"LLM init failed: {e}") from e
    return _llm


def optional_auth(authorization: Optional[str]) -> Optional[str]:
    """Phase-1: auth optional so existing APK (no JWT yet) keeps working.
    When STRLIX_REQUIRE_AUTH=1, Bearer token with aud=android-api is required.
    """
    require = os.environ.get("STRLIX_REQUIRE_AUTH", "0") == "1"
    if not authorization:
        if require:
            raise HTTPException(401, "Authorization required")
        return None
    try:
        raw = bearer_from_header(authorization)
        claims = tokens.verify(raw, expected_aud="android-api")
        return claims.sub
    except AuthError as e:
        raise HTTPException(e.status, e.message) from e


class MintRequest(BaseModel):
    device_id: str = Field(..., min_length=4, max_length=128)
    # Pilot: no real IdP yet — mint with shared secret after a simple device claim.
    # Replace with Azure AD B2C / Play Integrity attestation before public launch.


class SpeakHookRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    language: Optional[str] = None
    voice: Optional[str] = None


class SttHookRequest(BaseModel):
    """Phone does on-device STT; optionally upload transcript for logging / NLU."""
    transcript: str = Field(..., min_length=1, max_length=4000)
    language: Optional[str] = None
    confidence: Optional[float] = None


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "android-api",
        "version": "0.1.0",
        "uptime_s": round(time.time() - STARTED, 1),
        "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        "endpoint_set": bool(os.environ.get("AZURE_OPENAI_ENDPOINT")),
        "key_set": bool(os.environ.get("AZURE_OPENAI_API_KEY")),
        "speech_key_set": bool(os.environ.get("AZURE_SPEECH_KEY")),
        "auth_required": os.environ.get("STRLIX_REQUIRE_AUTH", "0") == "1",
        "note": "No ADB / no device stream — use desktop-api for viewer",
    }


@app.post("/v1/auth/device")
async def mint_device_token(req: MintRequest):
    """Mint a short-lived android-api JWT for the APK (keys never in APK)."""
    token = tokens.mint(
        sub=f"device:{req.device_id}",
        aud="android-api",
        scopes=["chat", "voice", "tools"],
        device_id=req.device_id,
    )
    return {
        "ok": True,
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": settings.jwt_ttl_seconds,
        "audience": "android-api",
    }


@app.post("/v1/chat", response_model=ChatTurnResponse)
@app.post("/chat", response_model=ChatTurnResponse)  # alias for current PilotClient
async def chat(
    req: ChatTurnRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    sub = optional_auth(authorization)
    key = sub or (request.client.host if request.client else "anon")
    if not chat_limiter.allow(key):
        raise HTTPException(429, "chat rate limit exceeded")
    try:
        return get_llm().chat(req)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"{type(e).__name__}: {e}") from e


@app.post("/v1/tools/result")
async def tool_result_ack(
    results: list[ToolResult],
    authorization: Optional[str] = Header(default=None),
):
    """Phone reports Accessibility outcomes (telemetry / future training)."""
    optional_auth(authorization)
    return {"ok": True, "accepted": len(results)}


@app.post("/v1/voice/speak")
async def voice_speak_hook(
    req: SpeakHookRequest,
    authorization: Optional[str] = Header(default=None),
):
    """TTS hook — synthesizes via host providers; phone plays locally.

    Phase-1: proxy to monolith voice if available, else return SSML/text for
    on-device TTS. Does not broadcast to desktop Live hub.
    """
    optional_auth(authorization)
    # Prefer returning text for on-device TTS; optional host synth URL later.
    return {
        "ok": True,
        "mode": "on_device_preferred",
        "text": req.text,
        "language": req.language or "en-US",
        "hint": "Prefer Android TextToSpeech / SpeechRecognizer on device; host TTS is for desktop Live.",
    }


@app.post("/v1/voice/stt")
async def voice_stt_hook(
    req: SttHookRequest,
    authorization: Optional[str] = Header(default=None),
):
    optional_auth(authorization)
    return {
        "ok": True,
        "transcript": req.transcript,
        "language": req.language,
        "next": "POST /v1/chat with transcript as message",
    }


@app.get("/v1/openapi-sketch")
async def openapi_sketch():
    """Compact API map for android clients (also see /docs)."""
    return {
        "service": "android-api",
        "base": "http://<host>:8788",
        "auth": "POST /v1/auth/device → Bearer for other routes (optional in phase-1)",
        "routes": {
            "GET /health": "liveness",
            "POST /v1/chat": "LLM turn + optional Accessibility tool proposals",
            "POST /chat": "alias of /v1/chat for existing APK",
            "POST /v1/tools/result": "report a11y tool outcomes",
            "POST /v1/voice/speak": "TTS hook (on-device preferred)",
            "POST /v1/voice/stt": "STT transcript ingest",
        },
        "not_here": [
            "/ws/h264",
            "/ws/stream",
            "/adb/*",
            "web viewer static",
        ],
    }
