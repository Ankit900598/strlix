"""Sign in with Microsoft for the market (OpenID Connect auth-code + PKCE).

Server-side confidential client: the browser goes to
  GET /v1/auth/entra/login     -> 302 to login.microsoftonline.com (authorize)
  GET /v1/auth/entra/callback  <- code; exchanged here with the client secret
The ID token is validated (signature via JWKS, aud, iss pattern, nonce, exp),
the email is mapped to a market user (same find-or-create as /v1/auth/login),
and the usual market session pair is minted. The browser is sent back to
/market/ with the pair in the URL *fragment* (never sent to any server or
logged by AFD); market.js stores it and clears the fragment.

Env (all optional; the feature is off until client id + secret are set):
  STRLIX_ENTRA_LOGIN_CLIENT_ID   app (client) id   (falls back to STRLIX_ENTRA_CLIENT_ID)
  STRLIX_ENTRA_CLIENT_SECRET     client secret (Key Vault: entra-market-web-client-secret)
  STRLIX_ENTRA_LOGIN_AUTHORITY   "common" (work/school + personal, default), "consumers",
                                 "organizations" or a tenant id
  STRLIX_PUBLIC_BASE_URL         e.g. https://strlix-edge-....azurefd.net (else X-Forwarded-Host)
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from .settings import settings
from . import auth

router = APIRouter()

LOGIN_HOST = "https://login.microsoftonline.com"
COOKIE = "strlix_entra_oidc"
COOKIE_PATH = "/v1/auth/entra"
STATE_TTL = 600
_ISS_RE = re.compile(r"^https://login\.microsoftonline\.com/([0-9a-f-]{36})/v2\.0$")
_jwks: dict[str, Any] = {}


def client_id() -> str:
    return (os.getenv("STRLIX_ENTRA_LOGIN_CLIENT_ID") or os.getenv("STRLIX_ENTRA_CLIENT_ID")
            or settings.entra_client_id or "").strip()


def client_secret() -> str:
    return (os.getenv("STRLIX_ENTRA_CLIENT_SECRET") or "").strip()


def authority() -> str:
    a = (os.getenv("STRLIX_ENTRA_LOGIN_AUTHORITY") or "common").strip().strip("/")
    return a or "common"


def enabled() -> bool:
    return bool(client_id() and client_secret())


def public_base(request: Request) -> str:
    explicit = (os.getenv("STRLIX_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    host = host.split(",")[0].strip()
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
    return f"{proto}://{host}"


def redirect_uri(request: Request) -> str:
    return public_base(request) + COOKIE_PATH + "/callback"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _safe_return(ret: Optional[str]) -> str:
    # Only same-site market paths: blocks open redirects (//evil, https://evil).
    if ret and ret.startswith("/market/") and not ret.startswith("//") and "\\" not in ret:
        return ret.split("#", 1)[0][:300]
    return "/market/"


def _fail(ret: str, code: str) -> RedirectResponse:
    sep = "&" if "?" in ret else "?"
    r = RedirectResponse(f"{ret}{sep}signin_error={code}", status_code=302)
    r.delete_cookie(COOKIE, path=COOKIE_PATH)
    return r


@router.get("/v1/auth/entra/status")
def entra_status(request: Request):
    """Public: tells market.js whether to show the Microsoft button (no secrets)."""
    return {
        "enabled": enabled(),
        "authority": authority(),
        "client_id": client_id() or None,
        "redirect_uri": redirect_uri(request) if enabled() else None,
    }


@router.get("/v1/auth/entra/login")
def entra_login(request: Request, ret: Optional[str] = None, prompt: Optional[str] = "select_account"):
    if not enabled():
        raise HTTPException(503, "Sign in with Microsoft is not configured on this server")
    state = _b64url(secrets.token_bytes(24))
    nonce = _b64url(secrets.token_bytes(24))
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    now = int(time.time())
    cookie = jwt.encode(
        {"st": state, "no": nonce, "cv": verifier, "ret": _safe_return(ret),
         "iat": now, "exp": now + STATE_TTL, "aud": "strlix-entra-oidc"},
        settings.jwt_secret, algorithm="HS256",
    )
    q = {
        "client_id": client_id(),
        "response_type": "code",
        "redirect_uri": redirect_uri(request),
        "response_mode": "query",
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if prompt in ("select_account", "login", "consent"):
        q["prompt"] = prompt
    url = f"{LOGIN_HOST}/{authority()}/oauth2/v2.0/authorize?{urlencode(q)}"
    r = RedirectResponse(url, status_code=302)
    r.set_cookie(COOKIE, cookie, max_age=STATE_TTL, path=COOKIE_PATH,
                 secure=True, httponly=True, samesite="lax")
    r.headers["Cache-Control"] = "no-store"
    return r


def _jwks_client(uri: str):
    c = _jwks.get(uri)
    if c is None:
        c = jwt.PyJWKClient(uri, cache_keys=True, lifespan=3600)
        _jwks[uri] = c
    return c


def validate_id_token(id_token: str, nonce: str, *, key=None) -> dict:
    """Validate a v2.0 ID token from the common/consumers/organizations or tenant authority."""
    if key is None:
        key = _jwks_client(f"{LOGIN_HOST}/{authority()}/discovery/v2.0/keys").get_signing_key_from_jwt(id_token).key
    claims = jwt.decode(
        id_token, key, algorithms=["RS256"], audience=client_id(),
        options={"require": ["exp", "iat", "aud", "iss", "sub"], "verify_iss": False},
        leeway=120,
    )
    m = _ISS_RE.match(str(claims.get("iss", "")))
    if not m or m.group(1) != str(claims.get("tid", "")):
        raise jwt.InvalidIssuerError("issuer does not match tenant")
    a = authority()
    if re.fullmatch(r"[0-9a-f-]{36}", a) and a != m.group(1):
        raise jwt.InvalidIssuerError("token from another tenant")
    if not nonce or claims.get("nonce") != nonce:
        raise jwt.InvalidTokenError("nonce mismatch")
    return claims


@router.get("/v1/auth/entra/callback")
def entra_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None,
                   error: Optional[str] = None, error_description: Optional[str] = None):
    raw = request.cookies.get(COOKIE)
    try:
        st = jwt.decode(raw or "", settings.jwt_secret, algorithms=["HS256"], audience="strlix-entra-oidc")
    except jwt.PyJWTError:
        return _fail("/market/", "expired")
    ret = _safe_return(st.get("ret"))
    if error:
        return _fail(ret, "cancelled" if error == "access_denied" else "provider")
    if not code or not state or not secrets.compare_digest(state, str(st.get("st", ""))):
        return _fail(ret, "state")
    try:
        tok = httpx.post(
            f"{LOGIN_HOST}/{authority()}/oauth2/v2.0/token",
            data={
                "client_id": client_id(),
                "client_secret": client_secret(),
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri(request),
                "code_verifier": st.get("cv", ""),
                "scope": "openid profile email",
            },
            timeout=15,
        )
    except httpx.HTTPError:
        return _fail(ret, "network")
    if tok.status_code != 200 or "id_token" not in tok.json():
        return _fail(ret, "token")
    try:
        claims = validate_id_token(tok.json()["id_token"], str(st.get("no", "")))
    except jwt.PyJWTError:
        return _fail(ret, "id_token")
    if not (claims.get("email") or claims.get("preferred_username")):
        return _fail(ret, "no_email")
    try:
        user = auth.bind_entra_user(claims)
    except HTTPException:
        return _fail(ret, "no_email")
    pair = auth.mint_pair(user["sub"], user["email"], is_anonymous=False)
    frag = urlencode({
        "strlix_auth": "entra",
        "access_token": pair["access_token"],
        "refresh_token": pair["refresh_token"],
        "email": user["email"],
    })
    r = RedirectResponse(f"{ret}#{frag}", status_code=302)
    r.delete_cookie(COOKIE, path=COOKIE_PATH)
    r.headers["Cache-Control"] = "no-store"
    r.headers["Referrer-Policy"] = "no-referrer"
    return r
