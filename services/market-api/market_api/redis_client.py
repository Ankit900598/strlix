"""Redis-backed sessions and rate limits; configured Redis never falls back in-process.

When STRLIX_REDIS_URL is set and Redis is down, rate_limit() returns False
(fail closed → HTTP 429). FREE_LAUNCH_MODE does not switch this to an
in-process bucket and does not raise the caller's limit.
"""
from __future__ import annotations
import time
from typing import Optional

from .settings import settings

_mem: dict[str, float] = {}
_rate: dict[str, list[float]] = {}
_client = None
_last_error: Optional[str] = None

def _get():
    global _client, _last_error
    if _client is False:
        return None
    if _client is not None:
        return _client
    if not settings.redis_url:
        return None
    try:
        import redis
        kwargs = {"decode_responses": True, "socket_connect_timeout": 5, "socket_timeout": 5, "retry_on_timeout": True, "health_check_interval": 30}
        if settings.redis_password:
            kwargs["password"] = settings.redis_password
        _client = redis.from_url(settings.redis_url, **kwargs)
        _client.ping()
        _last_error = None
        return _client
    except Exception as e:
        _last_error = type(e).__name__
        _client = False
        return None

def _require_redis() -> bool:
    return bool(settings.redis_url)

def store_session(user_id: str, jti: str, ttl: int, kind: str = "access") -> None:
    key = f"sess:{user_id}:{jti}"
    r = _get()
    if r:
        r.setex(key, ttl, kind)
        return
    if _require_redis():
        raise RuntimeError("configured Redis session store unavailable")
    _mem[key] = time.time() + ttl

def session_valid(user_id: str, jti: str) -> bool:
    key = f"sess:{user_id}:{jti}"
    r = _get()
    if r:
        return bool(r.exists(key))
    if _require_redis():
        return False
    exp = _mem.get(key)
    if exp is None:
        return True
    if exp < time.time():
        _mem.pop(key, None)
        return False
    return True

def revoke_session(user_id: str, jti: str) -> None:
    key = f"sess:{user_id}:{jti}"
    r = _get()
    if r:
        r.delete(key)
    _mem.pop(key, None)

def rate_limit(user_id: str, limit_per_min: int) -> bool:
    now = time.time()
    window = 60.0
    key = f"rl:{user_id}"
    r = _get()
    if r:
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(window) + 1)
        _, _, count, _ = pipe.execute()
        return int(count) <= limit_per_min
    if _require_redis():
        return False
    bucket = _rate.setdefault(key, [])
    bucket[:] = [t for t in bucket if t > now - window]
    bucket.append(now)
    return len(bucket) <= limit_per_min

def redis_ok() -> Optional[bool]:
    if not settings.redis_url:
        return None
    return bool(_get())

def redis_error() -> Optional[str]:
    return _last_error
