"""Live-voice language catalog for Strlix.

Each entry maps BCP-47 locale → Azure Speech / Polly / edge-tts / WebSpeech locales.
"""
from __future__ import annotations

from typing import Any, Optional

# Major languages well-supported by Azure Speech neural + Polly neural + edge-tts
LANGUAGES: list[dict[str, Any]] = [
    {
        "id": "en-US",
        "name": "English",
        "native": "English",
        "azure_voice": "en-US-JennyNeural",
        "polly_voice": "Joanna",
        "polly_engine": "neural",
        "polly_lang": "en-US",
        "edge_voice": "en-US-JennyNeural",
        "stt_locale": "en-US",
        "web_speech": "en-US",
    },
    {
        "id": "hi-IN",
        "name": "Hindi",
        "native": "हिन्दी",
        "azure_voice": "hi-IN-SwaraNeural",
        "polly_voice": "Kajal",
        "polly_engine": "neural",
        "polly_lang": "hi-IN",
        "edge_voice": "hi-IN-SwaraNeural",
        "stt_locale": "hi-IN",
        "web_speech": "hi-IN",
    },
    {
        "id": "es-ES",
        "name": "Spanish",
        "native": "Español",
        "azure_voice": "es-ES-ElviraNeural",
        "polly_voice": "Lucia",
        "polly_engine": "neural",
        "polly_lang": "es-ES",
        "edge_voice": "es-ES-ElviraNeural",
        "stt_locale": "es-ES",
        "web_speech": "es-ES",
    },
    {
        "id": "fr-FR",
        "name": "French",
        "native": "Français",
        "azure_voice": "fr-FR-DeniseNeural",
        "polly_voice": "Lea",
        "polly_engine": "neural",
        "polly_lang": "fr-FR",
        "edge_voice": "fr-FR-DeniseNeural",
        "stt_locale": "fr-FR",
        "web_speech": "fr-FR",
    },
    {
        "id": "zh-CN",
        "name": "Mandarin",
        "native": "中文",
        "azure_voice": "zh-CN-XiaoxiaoNeural",
        "polly_voice": "Zhiyu",
        "polly_engine": "neural",
        "polly_lang": "cmn-CN",
        "edge_voice": "zh-CN-XiaoxiaoNeural",
        "stt_locale": "zh-CN",
        "web_speech": "zh-CN",
    },
    {
        "id": "ar-SA",
        "name": "Arabic",
        "native": "العربية",
        "azure_voice": "ar-SA-ZariyahNeural",
        "polly_voice": "Hala",
        "polly_engine": "neural",
        "polly_lang": "ar-AE",
        "edge_voice": "ar-SA-ZariyahNeural",
        "stt_locale": "ar-SA",
        "web_speech": "ar-SA",
    },
    {
        "id": "pt-BR",
        "name": "Portuguese",
        "native": "Português",
        "azure_voice": "pt-BR-FranciscaNeural",
        "polly_voice": "Camila",
        "polly_engine": "neural",
        "polly_lang": "pt-BR",
        "edge_voice": "pt-BR-FranciscaNeural",
        "stt_locale": "pt-BR",
        "web_speech": "pt-BR",
    },
    {
        "id": "ja-JP",
        "name": "Japanese",
        "native": "日本語",
        "azure_voice": "ja-JP-NanamiNeural",
        "polly_voice": "Kazuha",
        "polly_engine": "neural",
        "polly_lang": "ja-JP",
        "edge_voice": "ja-JP-NanamiNeural",
        "stt_locale": "ja-JP",
        "web_speech": "ja-JP",
    },
]

_BY_ID = {x["id"]: x for x in LANGUAGES}


def list_languages() -> list[dict[str, Any]]:
    return [
        {
            "id": x["id"],
            "name": x["name"],
            "native": x["native"],
            "azure_voice": x["azure_voice"],
            "polly_voice": x["polly_voice"],
            "edge_voice": x["edge_voice"],
            "stt_locale": x["stt_locale"],
        }
        for x in LANGUAGES
    ]


def resolve_language(lang: Optional[str], fallback: str = "en-US") -> dict[str, Any]:
    """Resolve user/browser/device locale to a catalog entry."""
    if not lang:
        return _BY_ID[fallback]
    raw = lang.strip().replace("_", "-")
    if raw in _BY_ID:
        return _BY_ID[raw]
    # prefix match: hi → hi-IN, en-GB → en-US, zh-Hans-CN → zh-CN
    lower = raw.lower()
    primary = lower.split("-")[0]
    aliases = {
        "en": "en-US",
        "hi": "hi-IN",
        "es": "es-ES",
        "fr": "fr-FR",
        "zh": "zh-CN",
        "cmn": "zh-CN",
        "ar": "ar-SA",
        "pt": "pt-BR",
        "ja": "ja-JP",
    }
    if primary in aliases:
        return _BY_ID[aliases[primary]]
    for item in LANGUAGES:
        if item["id"].lower().startswith(primary + "-"):
            return item
    return _BY_ID[fallback]
