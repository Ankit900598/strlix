"""JWT access + refresh with aud/iss checks. Sessions: sess:{user_id}:{jti}.

STRLIX_AUTH_MODE=anon (default) accepts only these HS256 session tokens.
STRLIX_AUTH_MODE=entra additionally accepts Entra External ID / workforce
RS256 access tokens. Anonymous /v1/auth/anon keeps working in both modes.
"""
from __future__ import annotations
import hashlib, os, time, uuid
from typing import Any, Optional

import jwt
from fastapi import Header, HTTPException

from .settings import settings
from . import db, redis_client

_jwks_clients: dict[str, Any] = {}

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

def current_auth_mode() -> str:
    raw = os.getenv("STRLIX_AUTH_MODE", settings.auth_mode)
    mode = (raw or "anon").strip().lower()
    return mode if mode in ("anon", "entra") else "anon"


def entra_tenant_id() -> str:
    return os.getenv("STRLIX_ENTRA_TENANT_ID", settings.entra_tenant_id).strip()


def entra_client_id() -> str:
    return os.getenv("STRLIX_ENTRA_CLIENT_ID", settings.entra_client_id).strip()


def entra_audience() -> str:
    return (os.getenv("STRLIX_ENTRA_AUDIENCE", settings.entra_audience) or "").strip()


def entra_kind() -> str:
    kind = os.getenv("STRLIX_ENTRA_KIND", settings.entra_kind).strip().lower()
    return kind if kind in ("workforce", "ciam") else "workforce"


def entra_issuer() -> str:
    explicit = os.getenv("STRLIX_ENTRA_ISSUER", settings.entra_issuer).strip().rstrip("/")
    if explicit:
        return explicit
    tid = entra_tenant_id()
    if not tid:
        return ""
    if entra_kind() == "ciam":
        return f"https://{tid}.ciamlogin.com/{tid}/v2.0"
    return f"https://login.microsoftonline.com/{tid}/v2.0"


def entra_jwks_uri() -> str:
    explicit = os.getenv("STRLIX_ENTRA_JWKS_URI", settings.entra_jwks_uri).strip()
    if explicit:
        return explicit
    issuer = entra_issuer()
    if issuer.endswith("/v2.0"):
        return issuer[: -len("/v2.0")] + "/discovery/v2.0/keys"
    return ""


def _jwks_client():
    uri = entra_jwks_uri()
    if not uri:
        raise HTTPException(
            503,
            "Entra mode needs STRLIX_ENTRA_JWKS_URI or STRLIX_ENTRA_TENANT_ID. "
            "Anonymous /v1/auth/anon still works.",
        )
    client = _jwks_clients.get(uri)
    if client is None:
        client = jwt.PyJWKClient(uri, cache_keys=True, lifespan=3600)
        _jwks_clients[uri] = client
    return client


def validate_entra_token(token: str, *, key=None) -> dict:
    """Validate an Entra access token. `key` is a test hook (no network)."""
    if current_auth_mode() != "entra":
        raise HTTPException(401, "entra auth is disabled")
    issuer = entra_issuer()
    audience = entra_audience()
    if not issuer or not audience or (key is None and not entra_jwks_uri()):
        raise HTTPException(
            503,
            "Entra mode is on but STRLIX_ENTRA_ISSUER / STRLIX_ENTRA_AUDIENCE / "
            "STRLIX_ENTRA_TENANT_ID are incomplete. Anonymous /v1/auth/anon still works.",
        )
    if key is None:
        try:
            key = _jwks_client().get_signing_key_from_jwt(token).key
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(401, "entra signing key lookup failed") from exc
    audiences = [audience]
    client_id = entra_client_id()
    if client_id and client_id not in audiences:
        audiences.append(client_id)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=audiences,
            issuer=issuer,
            leeway=60,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "invalid entra token") from exc
    tid = entra_tenant_id()
    token_tid = str(claims.get("tid") or "")
    if tid and token_tid and token_tid != tid:
        raise HTTPException(401, "entra tenant mismatch")
    return claims


def _entra_email(claims: dict) -> str:
    raw = claims.get("email") or claims.get("preferred_username") or ""
    email = str(raw).strip().lower()
    if "@" not in email:
        return ""
    return email


def bind_entra_user(claims: dict) -> dict:
    """Map a validated Entra token onto a local market user. No session mint."""
    email = _entra_email(claims)
    if not email:
        raise HTTPException(
            401,
            "entra token has no email claim — add email or preferred_username "
            "in the app registration token configuration",
        )
    name = str(claims.get("name") or email.split("@", 1)[0])[:120]
    with db.session() as con:
        if settings.use_postgres:
            cur = con.execute(
                "SELECT market.find_or_create_user(%s::citext, %s) AS id",
                (email, name),
            )
            uid = str(db.fetchone(cur)["id"])
            con.set_user(uid)
        else:
            row = db.fetchone(
                con.execute("SELECT id FROM users WHERE email=%s AND deleted_at IS NULL", (email,))
            )
            if row:
                uid = row["id"]
            else:
                uid = db.new_id()
                con.execute(
                    "INSERT INTO users(id,email,display_name,is_anonymous,created_at) VALUES (%s,%s,%s,0,%s)",
                    (uid, email, name, time.time()),
                )
        db.audit(con, uid, "entra_login", "user", uid, {})
    return {
        "sub": uid,
        "email": email,
        "anon": False,
        "auth": "entra",
        "typ": "access",
        "jti": claims.get("jti") or "",
    }


def require_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    # Local HS256 first so anon and claimed sessions work even when Entra is on.
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_aud,
            issuer=settings.jwt_iss,
            options={"require": ["exp", "iat", "sub", "aud", "iss", "jti"]},
        )
    except jwt.PyJWTError:
        claims = None
    if claims is not None:
        if claims.get("typ") != "access":
            raise HTTPException(401, "wrong token type")
        if not redis_client.session_valid(claims["sub"], claims["jti"]):
            raise HTTPException(401, "session revoked or expired")
        claims.setdefault("auth", "local")
        return claims
    if current_auth_mode() != "entra":
        raise HTTPException(401, "invalid token")
    return bind_entra_user(validate_entra_token(token))

def hash_ua(ua: Optional[str]) -> Optional[str]:
    if not ua:
        return None
    return hashlib.sha256(ua.encode()).hexdigest()[:32]
