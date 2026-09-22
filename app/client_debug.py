"""Last viewer-reported decode stats, surfaced on ``GET /health``.

The browser is the only place an Opus/H.264 decode error is observable.
Viewers POST a small JSON blob; ops read it next to server packet counters.
"""
from __future__ import annotations

import time
from typing import Any

_last: dict[str, Any] = {}
_last_at = 0.0


def record(payload: dict[str, Any]) -> dict[str, Any]:
    global _last_at
    clean = {k: payload.get(k) for k in (
        "audio_error",
        "audio_packets",
        "audio_played",
        "audio_codec",
        "h264_error",
        "h264_frames",
        "h264_dropped",
        "h264_source",
        "ua",
    ) if k in payload}
    clean["at"] = time.time()
    _last.clear()
    _last.update(clean)
    _last_at = clean["at"]
    return dict(_last)


def snapshot() -> dict[str, Any]:
    if not _last:
        return {"reports": 0}
    age_ms = round((time.time() - _last_at) * 1000) if _last_at else None
    return {"reports": 1, "age_ms": age_ms, **_last}
