"""Azure Speech continuous PCM streaming STT for Strlix Live."""
from __future__ import annotations

import asyncio
import importlib
import importlib.util
import os
import re
from typing import Any, Optional

from .languages import resolve_language

SPEECH_RESOURCE = os.environ.get("AZURE_SPEECH_RESOURCE", "speech-zevi-strlix")
SAMPLE_RATE = 16_000
CHANNELS = 1
BITS_PER_SAMPLE = 16


def _first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _speech_region() -> str:
    region = _first_env("AZURE_SPEECH_REGION", "SPEECH_REGION")
    if region:
        return region
    endpoint = _first_env("AZURE_SPEECH_ENDPOINT", "SPEECH_ENDPOINT")
    # Cognitive Services endpoints are normally https://{region}.api.cognitive...
    match = re.match(r"https?://([a-z0-9-]+)\.api\.cognitive\.microsoft\.com", endpoint, re.I)
    return match.group(1) if match else ""


def _speech_key() -> str:
    return _first_env("AZURE_SPEECH_KEY", "SPEECH_KEY")


def _sdk_version() -> Optional[str]:
    try:
        sdk = importlib.import_module("azure.cognitiveservices.speech")
        return getattr(sdk, "__version__", None) or "installed"
    except Exception:  # noqa: BLE001
        return None


def stt_status() -> dict[str, Any]:
    provider = os.environ.get("VOICE_STT_PROVIDER", "auto").lower()
    key = bool(_speech_key())
    region = bool(_speech_region())
    try:
        sdk = importlib.util.find_spec("azure.cognitiveservices.speech") is not None
    except Exception:  # noqa: BLE001
        sdk = False
    if provider == "off":
        reason = "disabled"
    elif provider == "browser":
        reason = "browser_forced"
    elif not key:
        reason = "no_key"
    elif not region:
        reason = "no_region"
    elif not sdk:
        reason = "sdk_missing"
    else:
        reason = None
    return {
        "provider": "azure" if reason is None else "browser",
        "configured_preference": provider,
        "available": reason is None,
        "reason": reason,
        "sdk_version": _sdk_version() if sdk else None,
        "resource": SPEECH_RESOURCE,
        "region": _speech_region() or None,
        "locale_source": "languages.stt_locale",
        "transport": "websocket_pcm_s16le_16khz_mono" if reason is None else "webspeech",
        "note": (
            "Azure Speech continuous recognition is active over the duplex PCM WebSocket."
            if reason is None else
            "Using browser Web Speech fallback; Azure Speech duplex is not active."
        ),
    }


def stt_is_available() -> bool:
    return bool(stt_status()["available"])


class AzureSpeechSession:
    """One Azure continuous-recognition session backed by a push PCM stream.

    Azure SDK callbacks run on SDK worker threads. They are copied to an asyncio
    queue so the FastAPI WebSocket remains the only writer to the client.
    """

    def __init__(self, locale: str, loop: asyncio.AbstractEventLoop) -> None:
        self.locale = resolve_language(locale).get("stt_locale", "en-US")
        self.loop = loop
        self.events: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=64)
        self._sdk: Any = None
        self._push_stream: Any = None
        self._recognizer: Any = None
        self._started = False
        self._closed = False

    def _queue(self, event: dict[str, Any]) -> None:
        if self._closed:
            return

        def put() -> None:
            if self._closed:
                return
            try:
                self.events.put_nowait(event)
            except asyncio.QueueFull:
                # Interim results are disposable; retain final/error events.
                if event.get("final") or event.get("type") == "error":
                    try:
                        self.events.get_nowait()
                        self.events.put_nowait(event)
                    except asyncio.QueueEmpty:
                        pass

        self.loop.call_soon_threadsafe(put)

    def _on_recognizing(self, event: Any) -> None:
        text = getattr(event.result, "text", "") or ""
        if text:
            self._queue({"type": "transcript", "text": text, "final": False})

    def _on_recognized(self, event: Any) -> None:
        result = event.result
        reason = getattr(result, "reason", None)
        text = getattr(result, "text", "") or ""
        # ResultReason.RecognizedSpeech is 3 in the Speech SDK; use the name when
        # available so this remains compatible across SDK versions.
        recognized = getattr(self._sdk, "ResultReason", None)
        recognized_reason = getattr(recognized, "RecognizedSpeech", None) if recognized else None
        if text and (recognized_reason is None or reason == recognized_reason):
            self._queue({"type": "transcript", "text": text, "final": True})
        elif recognized_reason is not None and reason not in (recognized_reason, getattr(recognized, "NoMatch", None)):
            self._queue({"type": "error", "reason": str(reason), "message": "Azure Speech recognition failed"})

    def _on_canceled(self, event: Any) -> None:
        details = getattr(event, "cancellation_details", None)
        message = getattr(details, "error_details", "Azure Speech recognition canceled") if details else "Azure Speech recognition canceled"
        self._queue({"type": "error", "reason": "canceled", "message": message})

    async def start(self) -> None:
        if self._started:
            return
        try:
            self._sdk = importlib.import_module("azure.cognitiveservices.speech")
            key = _speech_key()
            region = _speech_region()
            speech_config = self._sdk.SpeechConfig(subscription=key, region=region)
            speech_config.speech_recognition_language = self.locale
            audio_format = self._sdk.audio.AudioStreamFormat(
                samples_per_second=SAMPLE_RATE,
                bits_per_sample=BITS_PER_SAMPLE,
                channels=CHANNELS,
            )
            self._push_stream = self._sdk.audio.PushAudioInputStream(stream_format=audio_format)
            audio_config = self._sdk.audio.AudioConfig(stream=self._push_stream)
            self._recognizer = self._sdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
            self._recognizer.recognizing.connect(self._on_recognizing)
            self._recognizer.recognized.connect(self._on_recognized)
            self._recognizer.canceled.connect(self._on_canceled)
            await asyncio.to_thread(self._recognizer.start_continuous_recognition_async().get)
            self._started = True
        except Exception:
            self.close()
            raise

    def write(self, pcm: bytes) -> None:
        if self._started and not self._closed and pcm:
            self._push_stream.write(pcm)

    async def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._push_stream is not None:
            try:
                self._push_stream.close()
            except Exception:  # noqa: BLE001
                pass
        if self._recognizer is not None and self._started:
            try:
                await asyncio.to_thread(self._recognizer.stop_continuous_recognition_async().get)
            except Exception:  # noqa: BLE001
                pass
        self._started = False

    def close(self) -> None:
        self._closed = True
        if self._push_stream is not None:
            try:
                self._push_stream.close()
            except Exception:  # noqa: BLE001
                pass
