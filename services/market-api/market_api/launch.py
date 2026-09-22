"""Free-first-month launch: waitlist + phone grant without a card.

Stripe stays test-gated in payments.py. This module never calls Stripe and
never reads live secret keys. FREE_LAUNCH_MODE does not relax rate limits.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Optional

from fastapi import HTTPException

from . import db
from .settings import settings


COPY = "Free for your first month — no card required."


def _truthy(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


def billing_mode() -> str:
    """BILLING_MODE (unprefixed) wins, then STRLIX_BILLING_MODE, then settings."""
    raw = os.getenv("BILLING_MODE")
    if raw is None:
        raw = os.getenv("STRLIX_BILLING_MODE", settings.billing_mode)
    mode = (raw or "free_month").strip().lower()
    if mode == "free":
        return "free_month"
    return mode


def free_launch_flag() -> bool:
    if os.getenv("FREE_LAUNCH_MODE") is not None:
        return _truthy(os.getenv("FREE_LAUNCH_MODE", ""))
    if os.getenv("STRLIX_FREE_LAUNCH_MODE") is not None:
        return _truthy(os.getenv("STRLIX_FREE_LAUNCH_MODE", ""))
    return bool(settings.free_launch_mode)


def free_month_active() -> bool:
    """On when billing mode is free_month OR the free-launch flag is on.

    Turning the free month off requires both signals off
    (BILLING_MODE=test|live AND FREE_LAUNCH_MODE=false). A single leftover
    flag keeps the no-card path so a soft launch cannot start charging.
    """
    if billing_mode() == "free_month":
        return True
    return free_launch_flag()


def free_month_days() -> int:
    raw = os.getenv("STRLIX_FREE_MONTH_DAYS")
    if raw is None:
        return max(1, int(settings.free_month_days))
    try:
        return max(1, int(raw))
    except ValueError:
        return max(1, int(settings.free_month_days))


def support_email() -> str:
    return (
        os.getenv("SUPPORT_EMAIL")
        or os.getenv("STRLIX_SUPPORT_EMAIL")
        or settings.support_email
        or "support@strlix.app"
    ).strip()


def support_email_is_placeholder() -> bool:
    raw = os.getenv("STRLIX_SUPPORT_EMAIL_PLACEHOLDER")
    if raw is None:
        return bool(settings.support_email_placeholder)
    return _truthy(raw)


def configured_invite_codes() -> set[str]:
    raw = os.getenv("STRLIX_INVITE_CODES")
    if raw is None:
        raw = settings.invite_codes or ""
    return {part.strip().upper() for part in raw.split(",") if part.strip()}


def invite_required() -> bool:
    return bool(configured_invite_codes())


def require_invite(code: Optional[str]) -> None:
    """No-op when signup is open. Rejects a missing or unknown code otherwise."""
    allowed = configured_invite_codes()
    if not allowed:
        return
    presented = (code or "").strip().upper()
    if not presented:
        raise HTTPException(403, "invite code required")
    # Compare against each allowed code in constant time per candidate.
    ok = False
    for candidate in allowed:
        ok = hmac.compare_digest(presented, candidate) or ok
    if not ok:
        raise HTTPException(403, "invite code not recognized")


def _code_hash(code: Optional[str]) -> Optional[str]:
    if not code or not code.strip():
        return None
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def public_status() -> dict[str, Any]:
    active = free_month_active()
    email = support_email()
    placeholder = support_email_is_placeholder()
    return {
        "billing_mode": billing_mode(),
        "free_launch_mode": free_launch_flag(),
        "free_month_active": active,
        "free_month_days": free_month_days(),
        "card_required": not active,
        "pay_required_for_session": False,
        "copy": COPY if active else "Free month is off. Checkout stays test-gated until live gates are enabled.",
        "support_email": email,
        "support_email_placeholder": placeholder,
        "support_note": (
            "Placeholder address until a custom domain is attached."
            if placeholder
            else "Configured support address."
        ),
        "invite_required": invite_required(),
        "legal": {
            "terms": "/market/legal/terms.html",
            "privacy": "/market/legal/privacy.html",
            "support": "/market/legal/support.html",
            "capabilities": "/market/legal/capabilities.html",
        },
    }


def join_waitlist(email: str, invite_code: Optional[str] = None) -> dict[str, Any]:
    """Store email + created_at. Open signup unless invite codes are configured."""
    require_invite(invite_code)
    email = email.strip().lower()
    code_hash = _code_hash(invite_code)
    now = time.time()
    row_id = db.new_id()
    try:
        with db.session() as con:
            if con.kind == "pg":
                con.execute(
                    """INSERT INTO market.waitlist(id, email, created_at, invite_code_hash)
                       VALUES (%s::uuid, %s::citext, to_timestamp(%s), %s)""",
                    (row_id, email, now, code_hash),
                )
            else:
                existing = db.fetchone(
                    con.execute("SELECT id, created_at FROM waitlist WHERE email=%s", (email,))
                )
                if existing:
                    return {
                        "status": "already_registered",
                        "email": email,
                        "created_at": existing["created_at"],
                        "card_required": False,
                    }
                con.execute(
                    "INSERT INTO waitlist(id, email, created_at, invite_code_hash) VALUES (%s,%s,%s,%s)",
                    (row_id, email, now, code_hash),
                )
            db.audit(con, None, "waitlist_join", "waitlist", row_id, {"invite": bool(code_hash)})
    except HTTPException:
        raise
    except Exception as exc:
        message = str(exc).lower()
        if "waitlist" in message and ("does not exist" in message or "undefined" in message or "no such table" in message):
            raise HTTPException(
                503,
                "waitlist table missing — apply services/market-api/migrations/006_free_month.sql",
            ) from exc
        if "duplicate" in message or "unique" in message:
            return {"status": "already_registered", "email": email, "card_required": False}
        raise
    return {
        "status": "joined",
        "email": email,
        "created_at": now,
        "card_required": False,
        "copy": COPY,
    }


def _insert_free_order(con: db.Conn, *, order_id: str, user_id: str, device_id: str) -> str:
    """Insert a $0 order. Plan column is free_month when the schema allows it.

    Postgres deployments that have not applied migration 006 still have
    plan IN ('hour','day'). A failed check falls back to plan='day' inside
    a savepoint so the free grant still works. provider stays free_month.
    """
    amount = 0
    provider = "free_month"
    status = "granted_free"
    now = time.time()

    def _write(plan: str) -> None:
        if con.kind == "pg":
            con.execute(
                """INSERT INTO market.orders
                   (id,user_id,device_id,plan,amount_cents,currency,provider,status,provider_ref)
                   VALUES (%s::uuid,%s::uuid,%s,%s,%s,'USD',%s,%s,%s)""",
                (order_id, user_id, device_id, plan, amount, provider, status, "free_month"),
            )
        else:
            con.execute(
                """INSERT INTO orders
                   (id,user_id,device_id,plan,amount_cents,currency,provider,status,provider_ref,created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (order_id, user_id, device_id, plan, amount, "USD", provider, status, "free_month", now),
            )

    if con.kind != "pg":
        _write("free_month")
        return "free_month"
    try:
        con.execute("SAVEPOINT free_plan")
        _write("free_month")
        con.execute("RELEASE SAVEPOINT free_plan")
        return "free_month"
    except Exception as exc:
        con.execute("ROLLBACK TO SAVEPOINT free_plan")
        if "check" not in str(exc).lower():
            raise
        _write("day")
        return "day"


def grant_free_month(*, user_id: str, device_id: str) -> dict[str, Any]:
    """Activate a phone lease without checkout. No Stripe call."""
    if not free_month_active():
        raise HTTPException(409, "free month is not active")
    days = free_month_days()
    now = time.time()
    ends = now + days * 86400
    with db.session(user_id=user_id) as con:
        if con.kind == "pg":
            cur = con.execute(
                """SELECT l.id::text AS id, l.device_id, EXTRACT(EPOCH FROM l.ends_at) AS ends_at
                   FROM market.leases l
                   JOIN market.orders o ON o.id = l.order_id
                   WHERE l.user_id=%s::uuid AND l.device_id=%s AND l.status='active'
                     AND l.deleted_at IS NULL AND o.provider='free_month'
                     AND l.ends_at > now()
                   ORDER BY l.ends_at DESC LIMIT 1""",
                (user_id, device_id),
            )
        else:
            cur = con.execute(
                """SELECT l.id AS id, l.device_id AS device_id, l.ends_at AS ends_at
                   FROM leases l
                   JOIN orders o ON o.id = l.order_id
                   WHERE l.user_id=%s AND l.device_id=%s AND l.status='active'
                     AND l.deleted_at IS NULL AND o.provider='free_month'
                     AND l.ends_at > %s
                   ORDER BY l.ends_at DESC LIMIT 1""",
                (user_id, device_id, now),
            )
        existing = db.fetchone(cur)
        if existing:
            return {
                "status": "already_granted",
                "lease_id": existing["id"],
                "device_id": existing["device_id"],
                "ends_at": existing["ends_at"],
                "plan": "free_month",
                "amount_cents": 0,
                "card_required": False,
                "mode": "free_month",
                "copy": COPY,
            }
        order_id = db.new_id()
        lease_id = db.new_id()
        stored_plan = _insert_free_order(
            con, order_id=order_id, user_id=user_id, device_id=device_id
        )
        if con.kind == "pg":
            con.execute(
                """INSERT INTO market.leases
                   (id,user_id,order_id,device_id,broker_sid,starts_at,ends_at,status)
                   VALUES (%s::uuid,%s::uuid,%s::uuid,%s,NULL,to_timestamp(%s),to_timestamp(%s),'active')""",
                (lease_id, user_id, order_id, device_id, now, ends),
            )
        else:
            con.execute(
                """INSERT INTO leases
                   (id,user_id,order_id,device_id,broker_sid,starts_at,ends_at,status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (lease_id, user_id, order_id, device_id, None, now, ends, "active"),
            )
        db.audit(con, user_id, "free_month_grant", "lease", lease_id, {"days": days, "stored_plan": stored_plan})
    return {
        "status": "granted_free",
        "order_id": order_id,
        "lease_id": lease_id,
        "device_id": device_id,
        "plan": "free_month",
        "stored_plan": stored_plan,
        "amount_cents": 0,
        "currency": "USD",
        "days": days,
        "ends_at": ends,
        "card_required": False,
        "mode": "free_month",
        "pay_mode": "test",
        "copy": COPY,
        "viewer_url": f"/phone?device={device_id}&lease={lease_id}",
    }
