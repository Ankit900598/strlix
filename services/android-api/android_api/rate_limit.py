"""Simple in-process token bucket (phase-1). Replace with Redis for multi-replica."""
from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    def __init__(self, per_minute: int = 60):
        self.per_minute = per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        window = [t for t in self._hits[key] if now - t < 60.0]
        if len(window) >= self.per_minute:
            self._hits[key] = window
            return False
        window.append(now)
        self._hits[key] = window
        if len(self._hits) > 10_000:
            # opportunistic prune
            stale = [k for k, v in self._hits.items() if not v or now - v[-1] > 300][:2000]
            for k in stale:
                self._hits.pop(k, None)
        return True
