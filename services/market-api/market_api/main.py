"""Strlix market-api — catalog, JWT auth, gated checkout, per-user Postgres RLS."""
from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from .settings import settings
from . import db, auth, launch, redis_client, payments
from .jobs import create as create_job, get as get_job

def _repo_root() -> Path:
    """Prefer the historical /workspace/zevi-cloudphone checkout, else this repo."""
    here = Path(__file__).resolve()
    candidates = [Path("/workspace/zevi-cloudphone"), here.parents[3]]
    for candidate in candidates:
        if (candidate / "web-market" / "devices.json").is_file():
            return candidate
    return candidates[-1]

ROOT = _repo_root()
DEVICES = ROOT / "web-market" / "devices.json"

app = FastAPI(title="Strlix market-api", version="0.6.9")
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if origins == ["*"] else origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginIn(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None

class ClaimIn(BaseModel):
    email: EmailStr
    display_name: Optional[str] = Field(default=None, max_length=120)

class RefreshIn(BaseModel):
    refresh_token: str

class CheckoutIn(BaseModel):
    device_id: str
    plan: str = Field(pattern="^(hour|day)$")
    provider: Optional[str] = None

class JobCreateIn(BaseModel):
    """Create a status-only job; task content never crosses this boundary."""
    kind: Literal["phone_task", "device_wake", "replay_export"] = "phone_task"

class WaitlistIn(BaseModel):
    email: EmailStr
    invite_code: Optional[str] = Field(default=None, max_length=64)

class GrantIn(BaseModel):
    device_id: Optional[str] = None
    invite_code: Optional[str] = Field(default=None, max_length=64)

def _devices_payload() -> dict[str, Any]:
    if DEVICES.is_file():
        return json.loads(DEVICES.read_text())
    return {"devices": []}

def _client_key(request: Request, prefix: str) -> str:
    # Only a short hash is sent to the limiter. Do not put raw client
    # addresses or emails in Redis keys.
    client_host = request.client.host if request.client else "unknown"
    return prefix + auth.hash_ua(client_host)[:32]

def _rate(claims: dict) -> None:
    if not redis_client.rate_limit(claims["sub"], settings.rate_limit_per_min):
        raise HTTPException(429, "rate limit exceeded")

def _limited(key: str, limit: int, detail: str) -> None:
    if not redis_client.rate_limit(key, limit):
        raise HTTPException(429, detail)

def _anonymous_rate(request: Request) -> None:
    _limited(
        _client_key(request, "anon_create:"),
        settings.anon_rate_per_min,
        "anonymous session rate limit exceeded",
    )

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

@app.get("/health")
def health():
    gates = payments.gate_status()
    return {
        "ok": True,
        "service": "market-api",
        "version": "0.6.9",
        "pay_mode": gates["effective_mode"],
        "pay_gates": gates,
        "billing_mode": launch.billing_mode(),
        "free_month_active": launch.free_month_active(),
        "card_required": not launch.free_month_active(),
        "auth_mode": auth.current_auth_mode(),
        "db": "postgres" if settings.use_postgres else "sqlite",
        "redis": redis_client.redis_ok(),
        "redis_error": redis_client.redis_error(),
        "jwt_access_ttl_sec": settings.jwt_access_ttl_sec,
    }

@app.get("/ready")
def ready():
    if settings.use_postgres:
        try:
            with db.session() as con:
                con.execute("SELECT 1")
        except Exception as e:
            raise HTTPException(503, f"db not ready: {type(e).__name__}") from e
    return {"ready": True}

@app.post("/v1/jobs", status_code=202)
def create_async_job(body: JobCreateIn, claims: dict = Depends(auth.require_user)):
    """Start a minimal pollable job state machine: queued → running → done.

    This shell is deliberately process-local and accepts no prompt, chat text,
    device content, URL, or outbound destination. It is suitable for wiring the
    phone UI before a durable worker is selected.
    """
    job = create_job(claims["sub"], body.kind)
    return {**job, "poll_after_ms": 250}


@app.get("/v1/jobs/{job_id}")
def read_async_job(job_id: str, claims: dict = Depends(auth.require_user)):
    # A missing job and another user's job are intentionally indistinguishable.
    job = get_job(job_id, claims["sub"])
    if not job:
        raise HTTPException(404, "job not found")
    return job


@app.get("/v1/devices")
def list_devices():
    return _devices_payload()

@app.get("/v1/devices/{device_id}")
def get_device(device_id: str):
    for d in _devices_payload().get("devices", []):
        if d["id"] == device_id:
            return d
    raise HTTPException(404, "device not found")

@app.get("/v1/launch")
def launch_status():
    """Public free-month flags. No secrets, no Stripe calls."""
    status = launch.public_status()
    status["auth_mode"] = auth.current_auth_mode()
    status["pay_gates"] = payments.gate_status()
    return status

@app.post("/v1/waitlist")
def waitlist(body: WaitlistIn, request: Request):
    """Open signup (or invite-coded) email capture. Does not charge a card."""
    _limited(
        _client_key(request, "waitlist:"),
        settings.waitlist_rate_per_min,
        "waitlist rate limit exceeded",
    )
    return launch.join_waitlist(str(body.email), body.invite_code)

@app.post("/v1/access/grant")
def grant_access(body: GrantIn, claims: dict = Depends(auth.require_user)):
    """Phone lease for the free month. Payment endpoints are not required."""
    _rate(claims)
    if not launch.free_month_active():
        raise HTTPException(
            409,
            "free month is not active — checkout remains available and test-gated",
        )
    launch.require_invite(body.invite_code)
    devices = {d["id"]: d for d in _devices_payload().get("devices", [])}
    device_id = body.device_id
    if not device_id:
        for device in _devices_payload().get("devices", []):
            if device.get("available", True):
                device_id = device["id"]
                break
    if not device_id or device_id not in devices:
        raise HTTPException(404, "device not found")
    if not devices[device_id].get("available", True):
        raise HTTPException(409, "device unavailable")
    granted = launch.grant_free_month(user_id=claims["sub"], device_id=device_id)
    granted["stream_url"] = settings.stream_url
    granted["stream_fallback"] = settings.stream_fallback
    return granted

@app.post("/v1/auth/login")
def login(body: LoginIn, request: Request):
    _limited(
        _client_key(request, "login:") + ":" + auth.hash_ua(body.email.lower())[:16],
        settings.login_rate_per_min,
        "login rate limit exceeded",
    )
    email = body.email.lower()
    with db.session() as con:
        if settings.use_postgres:
            cur = con.execute(
                "SELECT market.find_or_create_user(%s::citext, %s) AS id",
                (email, body.display_name),
            )
            uid = str(db.fetchone(cur)["id"])
            con.set_user(uid)
            db.audit(con, uid, "login", "user", uid, {"ua_hash": auth.hash_ua(request.headers.get("user-agent"))})
        else:
            cur = con.execute("SELECT * FROM users WHERE email=%s AND deleted_at IS NULL", (email,))
            row = db.fetchone(cur)
            if not row:
                uid = db.new_id()
                con.execute(
                    "INSERT INTO users(id,email,display_name,created_at) VALUES (%s,%s,%s,%s)",
                    (uid, email, body.display_name or email.split("@")[0], time.time()),
                )
            else:
                uid = row["id"]
            db.audit(con, uid, "login", "user", uid, {})
    return auth.mint_pair(uid, email, is_anonymous=False)

@app.post("/v1/auth/anon")
def anonymous_session(request: Request):
    """Create a PII-free session only when the visitor starts a rental."""
    _anonymous_rate(request)
    with db.session() as con:
        if settings.use_postgres:
            cur = con.execute("SELECT market.create_anon_user() AS id")
            uid = str(db.fetchone(cur)["id"])
            con.set_user(uid)
            db.audit(con, uid, "anon_create", "user", uid, {})
        else:
            uid = db.new_id()
            con.execute(
                "INSERT INTO users(id,email,display_name,is_anonymous,created_at) VALUES (%s,NULL,NULL,1,%s)",
                (uid, time.time()),
            )
            db.audit(con, uid, "anon_create", "user", uid, {})
    return auth.mint_pair(uid, "", is_anonymous=True)

@app.post("/v1/auth/claim")
def claim_anonymous(body: ClaimIn, claims: dict = Depends(auth.require_user)):
    """Attach an email to the existing anonymous identity without changing its id."""
    if not claims.get("anon", False):
        raise HTTPException(409, "session is already claimed")
    email = body.email.lower()
    uid = claims["sub"]
    try:
        with db.session(user_id=uid) as con:
            if settings.use_postgres:
                cur = con.execute(
                    "SELECT market.claim_anon_user(%s::uuid,%s::citext,%s) AS id",
                    (uid, email, body.display_name),
                )
                row = db.fetchone(cur)
                if not row or row["id"] is None:
                    raise HTTPException(409, "session is already claimed or unavailable")
            else:
                existing = db.fetchone(
                    con.execute("SELECT id FROM users WHERE email=%s AND deleted_at IS NULL", (email,))
                )
                if existing and existing["id"] != uid:
                    raise HTTPException(409, "email already belongs to another account")
                current = db.fetchone(con.execute("SELECT is_anonymous FROM users WHERE id=%s", (uid,)))
                if not current or not current["is_anonymous"]:
                    raise HTTPException(409, "session is already claimed or unavailable")
                con.execute(
                    "UPDATE users SET email=%s, display_name=%s, is_anonymous=0 WHERE id=%s",
                    (email, body.display_name or email.split("@", 1)[0], uid),
                )
            db.audit(con, uid, "claim", "user", uid, {})
    except HTTPException:
        raise
    except Exception as exc:
        # The SECURITY DEFINER function turns the cross-tenant duplicate check
        # into a stable application error while preserving RLS boundaries.
        if "email already belongs" in str(exc) or "duplicate key" in str(exc).lower() or "unique" in str(exc).lower():
            raise HTTPException(409, "email already belongs to another account") from exc
        raise
    return auth.mint_pair(uid, email, is_anonymous=False)

@app.post("/v1/auth/refresh")
def refresh(body: RefreshIn):
    claims = auth.decode_token(body.refresh_token, expect_typ="refresh")
    redis_client.revoke_session(claims["sub"], claims["jti"])
    is_anonymous = bool(claims.get("anon", False))
    # The claim can happen in another tab. Read the authoritative flag so a
    # stale refresh token cannot resurrect the anonymous UX after claiming.
    with db.session(user_id=claims["sub"]) as con:
        cur = con.execute(
            "SELECT is_anonymous FROM market.users WHERE id=%s::uuid AND deleted_at IS NULL"
            if settings.use_postgres else
            "SELECT is_anonymous FROM users WHERE id=%s AND deleted_at IS NULL",
            (claims["sub"],),
        )
        row = db.fetchone(cur)
        if row is not None:
            is_anonymous = bool(row["is_anonymous"])
    return auth.mint_pair(claims["sub"], claims.get("email", ""), is_anonymous=is_anonymous)

@app.post("/v1/auth/logout")
def logout(claims: dict = Depends(auth.require_user)):
    jti = claims.get("jti")
    if jti:
        redis_client.revoke_session(claims["sub"], jti)
    return {"ok": True, "auth": claims.get("auth", "local")}

@app.post("/v1/checkout/session")
def checkout(body: CheckoutIn, claims: dict = Depends(auth.require_user)):
    """Create checkout + payment_intent row. Default TEST; live is triple-gated."""
    _rate(claims)
    devices = {d["id"]: d for d in _devices_payload().get("devices", [])}
    if body.device_id not in devices:
        raise HTTPException(404, "device not found")
    d = devices[body.device_id]
    if not d.get("available", True):
        raise HTTPException(409, "device unavailable")
    # Refuse half-enabled live configs early with a clear 503 (no charges).
    if settings.pay_mode == "live" and not payments.live_charges_allowed():
        raise HTTPException(
            503,
            "live charges disabled — set PAYMENTS_LIVE=true AND STRLIX_ALLOW_LIVE_CHARGES=true "
            "AND STRLIX_PAY_MODE=live (and load live keys from Key Vault). Default remains TEST.",
        )
    amount = d["price_hour_cents"] if body.plan == "hour" else d["price_day_cents"]
    provider = body.provider or settings.pay_provider
    oid = db.new_id()
    with db.session(user_id=claims["sub"]) as con:
        if settings.use_postgres:
            con.execute(
                """INSERT INTO market.orders(id,user_id,device_id,plan,amount_cents,currency,provider,status,provider_ref)
                   VALUES (%s::uuid,%s::uuid,%s,%s,%s,'USD',%s,'checkout',%s)""",
                (oid, claims["sub"], body.device_id, body.plan, amount, provider, ""),
            )
        else:
            con.execute(
                "INSERT INTO orders(id,user_id,device_id,plan,amount_cents,currency,provider,status,provider_ref,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (oid, claims["sub"], body.device_id, body.plan, amount, "USD", provider, "checkout", "", time.time()),
            )
        db.audit(con, claims["sub"], "checkout", "order", oid, {"plan": body.plan, "provider": provider})
    try:
        result = payments.create_checkout_session(
            user_id=claims["sub"],
            order_id=oid,
            device_id=body.device_id,
            plan=body.plan,
            amount_cents=amount,
            provider=provider,
            success_url=settings.checkout_success_url,
            cancel_url=settings.checkout_cancel_url,
        )
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    return {
        "order_id": result.order_id,
        "payment_intent_id": result.payment_intent_id,
        "mode": result.mode,
        "provider": result.provider,
        "amount_cents": result.amount_cents,
        "currency": result.currency,
        "status": result.status,
        "publishable_key": result.publishable_key,
        "checkout_url": result.checkout_url,
        "client_secret": result.client_secret,
        "provider_ref": result.provider_ref,
        "message": result.message,
        "card_required": not launch.free_month_active(),
        "free_month_grant": "/v1/access/grant" if launch.free_month_active() else None,
        "device": d,
        "stream_after_pay": settings.stream_url,
        "pay_gates": payments.gate_status(),
    }

@app.post("/v1/checkout/confirm")
def confirm(order_id: str, claims: dict = Depends(auth.require_user)):
    """TEST-only confirm. Live path must complete via signed Stripe webhook."""
    _rate(claims)
    try:
        out = payments.confirm_test_payment(user_id=claims["sub"], order_id=order_id)
    except PermissionError as e:
        raise HTTPException(503, str(e)) from e
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    return {
        **out,
        "viewer_url": f"/phone?device={out['device_id']}&lease={out['lease_id']}",
        "stream_url": settings.stream_url,
        "stream_fallback": settings.stream_fallback,
    }

@app.get("/v1/me/orders")
def my_orders(claims: dict = Depends(auth.require_user)):
    with db.session(user_id=claims["sub"]) as con:
        if settings.use_postgres:
            cur = con.execute(
                "SELECT id::text, device_id, plan, amount_cents, status, created_at FROM market.orders WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 50"
            )
        else:
            cur = con.execute(
                "SELECT id, device_id, plan, amount_cents, status, created_at FROM orders WHERE user_id=%s AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 50",
                (claims["sub"],),
            )
        return {"orders": db.fetchall(cur)}

@app.post("/v1/privacy/soft-delete")
def soft_delete(claims: dict = Depends(auth.require_user)):
    with db.session(user_id=claims["sub"]) as con:
        if settings.use_postgres:
            con.execute("UPDATE market.users SET deleted_at=now() WHERE id=%s::uuid", (claims["sub"],))
            con.execute("UPDATE market.orders SET deleted_at=now() WHERE user_id=%s::uuid", (claims["sub"],))
            con.execute("UPDATE market.leases SET deleted_at=now() WHERE user_id=%s::uuid", (claims["sub"],))
        else:
            now = time.time()
            con.execute("UPDATE users SET deleted_at=%s WHERE id=%s", (now, claims["sub"]))
            con.execute("UPDATE orders SET deleted_at=%s WHERE user_id=%s", (now, claims["sub"]))
            con.execute("UPDATE leases SET deleted_at=%s WHERE user_id=%s", (now, claims["sub"]))
        db.audit(con, claims["sub"], "soft_delete", "user", claims["sub"], {})
    jti = claims.get("jti")
    if jti:
        redis_client.revoke_session(claims["sub"], jti)
    return {"status": "soft_deleted", "user_id": claims["sub"]}

@app.post("/v1/privacy/hard-delete")
def hard_delete_stub(claims: dict = Depends(auth.require_user)):
    with db.session(user_id=claims["sub"]) as con:
        db.audit(con, claims["sub"], "hard_delete_requested", "user", claims["sub"], {})
    return {"status": "accepted", "note": "Hard-delete job stubbed (phase-2).", "user_id": claims["sub"]}

@app.post("/v1/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Stripe webhook stub (test) / signature-verified handler (live gated).

    Stores only intent id + status. Never logs secrets or raw card data.
    """
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        return payments.handle_stripe_webhook(payload, sig)
    except PermissionError as e:
        raise HTTPException(400, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

@app.post("/v1/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    """Razorpay webhook stub — parity endpoint; signature verify TBD when INR live."""
    _ = await request.body()
    return {"received": True, "mode": payments.effective_mode(), "provider": "razorpay", "note": "stub"}

@app.get("/v1/payments/status")
def payments_status():
    """Public gate status for web-market PAY: TEST/LIVE pill (no secrets)."""
    return payments.gate_status()

@app.get("/")
def root():
    return {"service": "market-api", "docs": "/docs", "health": "/health", "ready": "/ready", "market_ui": "/market/"}

_LEGAL = ROOT / "static" / "legal"
if _LEGAL.is_dir():
    app.mount("/legal", StaticFiles(directory=str(_LEGAL), html=True), name="legal")

_WM = ROOT / "web-market"
if _WM.is_dir():
    app.mount("/market", StaticFiles(directory=str(_WM), html=True), name="web_market")
