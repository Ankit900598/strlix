"""JWT device/session tokens for android-api and desktop-api.

Phase-1: HS256 with shared secret (STRLIX_JWT_SECRET).
Phase-2: swap to Azure AD B2C / Entra External ID + JWKS without changing claim shape.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Literal, Optional

import jwt

from .errors import ApiError

Audience = Literal["android-api", "desktop-api"]


class AuthError(ApiError):
    def __init__(self, message: str = "unauthorized"):
        super().__init__(401, "unauthorized", message)


@dataclass
class TokenClaims:
    sub: str                 # user or device id
    aud: Audience
    sid: Optional[str] = None  # session id (desktop ↔ device bind)
    device_id: Optional[str] = None
    scopes: tuple[str, ...] = ()
    iat: int = 0
    exp: int = 0
    jti: str = ""

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "*" in self.scopes


class TokenService:
    def __init__(
        self,
        secret: str,
        issuer: str = "strlix",
        ttl_seconds: int = 86400,
    ):
        self.secret = secret
        self.issuer = issuer
        self.ttl_seconds = ttl_seconds
        self.alg = "HS256"

    def mint(
        self,
        *,
        sub: str,
        aud: Audience,
        scopes: list[str] | tuple[str, ...] = (),
        sid: Optional[str] = None,
        device_id: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> str:
        now = int(time.time())
        ttl = ttl if ttl is not None else self.ttl_seconds
        payload: dict[str, Any] = {
            "sub": sub,
            "aud": aud,
            "iss": self.issuer,
            "iat": now,
            "exp": now + ttl,
            "jti": uuid.uuid4().hex,
            "scopes": list(scopes),
        }
        if sid:
            payload["sid"] = sid
        if device_id:
            payload["device_id"] = device_id
        return jwt.encode(payload, self.secret, algorithm=self.alg)

    def verify(self, token: str, *, expected_aud: Audience) -> TokenClaims:
        try:
            data = jwt.decode(
                token,
                self.secret,
                algorithms=[self.alg],
                audience=expected_aud,
                issuer=self.issuer,
            )
        except jwt.ExpiredSignatureError as e:
            raise AuthError("token expired") from e
        except jwt.InvalidTokenError as e:
            raise AuthError(f"invalid token: {e}") from e
        return TokenClaims(
            sub=str(data["sub"]),
            aud=data["aud"],  # type: ignore[arg-type]
            sid=data.get("sid"),
            device_id=data.get("device_id"),
            scopes=tuple(data.get("scopes") or ()),
            iat=int(data.get("iat") or 0),
            exp=int(data.get("exp") or 0),
            jti=str(data.get("jti") or ""),
        )


def bearer_from_header(authorization: Optional[str]) -> str:
    if not authorization:
        raise AuthError("missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise AuthError("expected Bearer <token>")
    return parts[1].strip()
