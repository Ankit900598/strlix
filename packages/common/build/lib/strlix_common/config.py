"""Shared settings loaded from env / .env (never bake secrets into APK)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env() -> str:
    # Prefer monorepo root .env so pilot + split services share one secret file.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file() and (parent / "services").is_dir():
            return str(candidate)
        if candidate.is_file() and (parent / "app").is_dir() and (parent / "static").is_dir():
            return str(candidate)
    # Fallback: walk up for any .env
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return str(candidate)
    return ".env"


class CommonSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Auth
    jwt_secret: str = Field(default="dev-only-change-me-strlix-2026-ok32b", alias="STRLIX_JWT_SECRET")
    jwt_issuer: str = Field(default="strlix", alias="STRLIX_JWT_ISSUER")
    jwt_audience_android: str = Field(default="android-api", alias="STRLIX_JWT_AUD_ANDROID")
    jwt_audience_desktop: str = Field(default="desktop-api", alias="STRLIX_JWT_AUD_DESKTOP")
    jwt_ttl_seconds: int = Field(default=86400, alias="STRLIX_JWT_TTL_S")

    # Azure OpenAI (rg-zevi-cloudphone)
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: Optional[str] = Field(default=None, alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-12-01-preview", alias="AZURE_OPENAI_API_VERSION")

    # Speech
    azure_speech_key: Optional[str] = Field(default=None, alias="AZURE_SPEECH_KEY")
    azure_speech_region: Optional[str] = Field(default=None, alias="AZURE_SPEECH_REGION")
    azure_speech_endpoint: Optional[str] = Field(default=None, alias="AZURE_SPEECH_ENDPOINT")
    voice_tts_provider: str = Field(default="auto", alias="VOICE_TTS_PROVIDER")

    # Device / ADB (pilot + desktop-api)
    adb_serial: str = Field(default="127.0.0.1:5555", alias="ADB_SERIAL")
    session_broker_url: str = Field(default="http://127.0.0.1:8791", alias="SESSION_BROKER_URL")

    # Rate limits (phase-1 defaults)
    chat_rate_per_min: int = Field(default=60, alias="CHAT_RATE_PER_MIN")
    input_rate_per_sec: float = Field(default=30.0, alias="INPUT_RATE_PER_SEC")
    max_stream_clients_per_device: int = Field(default=12, alias="MAX_STREAM_CLIENTS")


@lru_cache
def get_settings() -> CommonSettings:
    return CommonSettings()
