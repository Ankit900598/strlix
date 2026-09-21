"""Host-side TTS / live-voice helpers with multi-language support.

Providers (in preference order when VOICE_TTS_PROVIDER=auto):
  1. Azure Speech REST (AZURE_SPEECH_KEY + region/endpoint)
  2. AWS Polly neural (boto3 / env AWS credentials)
  3. edge-tts Microsoft neural (offline-key fallback)

Playback: synthesize on host → URL for laptop browser WebAudio.
Never play assistant TTS on the phone speaker / scrcpy.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx

from .languages import list_languages, resolve_language

log = logging.getLogger("strlix.voice")

ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "demo" / "voice-audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

TTS_PROVIDER = os.environ.get("VOICE_TTS_PROVIDER", "auto").lower()  # auto|azure|polly|edge


def _azure_ready() -> bool:
    return bool(os.environ.get("AZURE_SPEECH_KEY")) and bool(
        os.environ.get("AZURE_SPEECH_ENDPOINT") or os.environ.get("AZURE_SPEECH_REGION")
    )


def _polly_ready() -> bool:
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_PROFILE")
        or os.path.exists(os.path.expanduser("~/.aws/credentials"))
    )


def pick_provider() -> str:
    pref = TTS_PROVIDER
    if pref in ("azure", "polly", "edge"):
        if pref == "azure" and not _azure_ready():
            return "edge" if not _polly_ready() else "polly"
        if pref == "polly" and not _polly_ready():
            return "azure" if _azure_ready() else "edge"
        return pref
    # auto
    if _azure_ready():
        return "azure"
    if _polly_ready():
        return "polly"
    return "edge"


def provider_status() -> dict[str, Any]:
    active = pick_provider()
    return {
        "provider": active,
        "configured_preference": TTS_PROVIDER,
        "azure_configured": _azure_ready(),
        "polly_configured": _polly_ready(),
        "edge_available": True,
        "languages": list_languages(),
        "audio_dir": str(AUDIO_DIR),
        "local_playback": False,
        "note": (
            "Assistant audio is synthesized on host and played on the laptop browser "
            "(WebAudio). Phone speaker stays silent; scrcpy stays --no-audio."
        ),
    }


def _escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


async def synthesize_edge(text: str, voice: str) -> Path:
    import edge_tts

    uid = uuid.uuid4().hex[:12]
    out = AUDIO_DIR / f"tts-{uid}.mp3"
    await edge_tts.Communicate(text, voice).save(str(out))
    return out


async def synthesize_azure(text: str, voice: str, lang_id: str) -> Path:
    key = os.environ["AZURE_SPEECH_KEY"]
    endpoint = os.environ.get("AZURE_SPEECH_ENDPOINT", "").rstrip("/")
    region = os.environ.get("AZURE_SPEECH_REGION", "")
    # Prefer regional TTS host — cognitive.microsoft.com/.../cognitiveservices/v1 returns 404.
    if region:
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    elif endpoint and "tts.speech.microsoft.com" in endpoint:
        url = f"{endpoint}/cognitiveservices/v1"
    elif endpoint:
        # Last resort: try endpoint as-is (may 404 on api.cognitive.microsoft.com)
        url = f"{endpoint}/cognitiveservices/v1"
    else:
        raise RuntimeError("AZURE_SPEECH_ENDPOINT or AZURE_SPEECH_REGION required")

    parts = voice.split("-")
    xml_lang = f"{parts[0]}-{parts[1]}" if len(parts) >= 2 else lang_id
    ssml = (
        f"<speak version='1.0' xml:lang='{xml_lang}'>"
        f"<voice name='{voice}'>{_escape_xml(text)}</voice></speak>"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "StrlixLiveVoice",
    }
    uid = uuid.uuid4().hex[:12]
    out = AUDIO_DIR / f"tts-{uid}.mp3"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, content=ssml.encode("utf-8"), headers=headers)
        if r.status_code != 200:
            raise RuntimeError(f"Azure Speech TTS HTTP {r.status_code}: {r.text[:300]}")
        out.write_bytes(r.content)
    return out


async def synthesize_polly(text: str, voice_id: str, engine: str, lang_code: str) -> Path:
    def _sync() -> Path:
        import boto3

        client = boto3.client(
            "polly",
            region_name=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")),
        )
        kwargs: dict[str, Any] = {
            "Text": text,
            "OutputFormat": "mp3",
            "VoiceId": voice_id,
            "Engine": engine or "neural",
        }
        if lang_code:
            kwargs["LanguageCode"] = lang_code
        resp = client.synthesize_speech(**kwargs)
        uid = uuid.uuid4().hex[:12]
        out = AUDIO_DIR / f"tts-{uid}.mp3"
        out.write_bytes(resp["AudioStream"].read())
        return out

    return await asyncio.to_thread(_sync)


async def synthesize(
    text: str,
    *,
    language: Optional[str] = None,
    voice: Optional[str] = None,
) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("empty text")
    if len(text) > 2500:
        text = text[:2500] + "…"

    lang = resolve_language(language)
    t0 = time.time()
    provider = pick_provider()
    used_voice = voice
    path: Path
    errors: list[str] = []

    async def _try_azure() -> Path:
        v = voice or lang["azure_voice"]
        return await synthesize_azure(text, v, lang["id"])

    async def _try_polly() -> Path:
        v = voice or lang["polly_voice"]
        return await synthesize_polly(text, v, lang.get("polly_engine") or "neural", lang.get("polly_lang") or "")

    async def _try_edge() -> Path:
        v = voice or lang["edge_voice"]
        return await synthesize_edge(text, v)

    # Preference chain: Azure → Polly → edge (last resort), regardless of which is active first.
    if provider == "azure":
        order = [_try_azure]
        if _polly_ready():
            order.append(_try_polly)
        order.append(_try_edge)
    elif provider == "polly":
        order = [_try_polly, _try_edge]
    else:
        order = [_try_edge]

    path = None  # type: ignore
    used_provider = provider
    for attempt in order:
        try:
            path = await attempt()
            used_provider = {
                _try_azure: "azure",
                _try_polly: "polly",
                _try_edge: "edge",
            }[attempt]
            if used_provider == "azure":
                used_voice = voice or lang["azure_voice"]
            elif used_provider == "polly":
                used_voice = voice or lang["polly_voice"]
            else:
                used_voice = voice or lang["edge_voice"]
            break
        except Exception as e:  # noqa: BLE001
            errors.append(f"{attempt.__name__}: {type(e).__name__}: {e}")
            log.warning("TTS attempt failed: %s", errors[-1])

    if path is None:
        raise RuntimeError("All TTS providers failed: " + " | ".join(errors))

    rel = path.name
    return {
        "ok": True,
        "provider": used_provider,
        "language": lang["id"],
        "language_name": lang["name"],
        "path": str(path),
        "url": f"/demo/voice-audio/{rel}",
        "bytes": path.stat().st_size,
        "voice": used_voice,
        "stt_locale": lang["stt_locale"],
        "ms": int((time.time() - t0) * 1000),
        "text_hash": hashlib.sha256(text.encode()).hexdigest()[:12],
        "fallback_errors": errors or None,
    }


class LiveHub:
    """Fan-out live session events to browser WebSocket clients (audio surface)."""

    def __init__(self) -> None:
        self._clients: set[Any] = set()
        self._lock = asyncio.Lock()
        self.state: dict[str, Any] = {
            "active": False,
            "source": None,
            "language": "en-US",
            "started_at": None,
        }

    async def register(self, ws: Any) -> None:
        async with self._lock:
            self._clients.add(ws)

    async def unregister(self, ws: Any) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast(self, event: dict[str, Any]) -> int:
        dead = []
        n = 0
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_json(event)
                n += 1
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.unregister(ws)
        return n

    def client_count(self) -> int:
        return len(self._clients)


live_hub = LiveHub()
