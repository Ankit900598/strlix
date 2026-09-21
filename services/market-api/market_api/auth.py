"""JWT access + refresh with aud/iss checks. Sessions: sess:{user_id}:{jti}."""
from __future__ import annotations
import hashlib, time, uuid
from typing import Any, Optional

import jwt
from fastapi import Header, HTTPException

from .settings import settings
from . import redis_client

def mint_pair(user_id: str, email: str = "", *, is_anonymous: bool = False) -> dict[str, Any]:
    now = int(time.time())
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())
    access = jwt.encode(
        {"sub": user_id, "email": email, "anon": is_anonymous, "iss": settings.jwt_iss, "aud": settings.jwt_aud,
         "iat": now, "exp": now + settings.jwt_access_ttl_sec, "jti": access_jti, "typ": "access"},
        settings.jwt_secret, algorithm="HS256",
    )
    refresh = jwt.encode(
        {"sub": user_id, "email": email, "anon": is_anonymous, "iss": settings.jwt_iss, "aud": settings.jwt_aud,
         "iat": now, "exp": now + settings.jwt_refresh_ttl_sec, "jti": refresh_jti, "typ": "refresh"},
        settings.jwt_secret, algorithm="HS256",
    )
    redis_client.store_session(user_id, access_jti, settings.jwt_access_ttl_sec, kind="access")
    redis_client.store_session(user_id, refresh_jti, settings.jwt_refresh_ttl_sec, kind="refresh")
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_ttl_sec,
        "user_id": user_id,
        "is_anonymous": is_anonymous,
    }

def decode_token(token: str, *, expect_typ: Optional[str] = "access") -> dict:
    try:
        claims = jwt.decode(
            token, settings.jwt_secret, algorithms=["HS256"],
            audience=settings.jwt_aud, issuer=settings.jwt_iss,
            options={"require": ["exp", "iat", "sub", "aud", "iss", "jti"]},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(401, "invalid token") from e
    if expect_typ and claims.get("typ") != expect_typ:
        raise HTTPException(401, "wrong token type")
    if not redis_client.session_valid(claims["sub"], claims["jti"]):
        raise HTTPException(401, "session revoked or expired")
    return claims

def require_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Bearer token required")
    return decode_token(authorization.split(" ", 1)[1], expect_typ="access")

def hash_ua(ua: Optional[str]) -> Optional[str]:
    if not ua:
        return None
    return hashlib.sha256(ua.encode()).hexdigest()[:32]
