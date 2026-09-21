"""Payment intents — Stripe Checkout (test default; live dual-gated).

Gates for any real Stripe network call (ALL required):
  1. STRLIX_PAY_MODE=live
  2. PAYMENTS_LIVE=true  (or STRLIX_PAYMENTS_LIVE=true)
  3. STRLIX_ALLOW_LIVE_CHARGES=true

Default build never charges. We store only provider intent / session ids +
status per tenant (RLS via market.payment_intents / SQLite mirror). Card PANs
and full charge payloads are never persisted.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from . import db
from .settings import settings

STRIPE_API = "https://api.stripe.com/v1"


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def payments_live_flag() -> bool:
    """Unprefixed PAYMENTS_LIVE wins; STRLIX_PAYMENTS_LIVE also accepted."""
    if os.getenv("PAYMENTS_LIVE") is not None:
        return _env_truthy("PAYMENTS_LIVE")
    return bool(settings.payments_live) or _env_truthy("STRLIX_PAYMENTS_LIVE")


def live_charges_allowed() -> bool:
    """Triple gate — all must be true before live Stripe API is used."""
    return (
        settings.pay_mode == "live"
        and payments_live_flag()
        and bool(settings.allow_live_charges)
    )


def effective_mode() -> str:
    return "live" if live_charges_allowed() else "test"


@dataclass
class CheckoutResult:
    order_id: str
    payment_intent_id: str
    provider_ref: str
    mode: str
    provider: str
    amount_cents: int
    currency: str
    status: str
    publishable_key: str
    checkout_url: str
    client_secret: Optional[str]
    message: str
    raw: dict[str, Any]


def _store_intent(
    con: db.Conn,
    *,
    intent_row_id: str,
    user_id: str,
    order_id: str,
    provider: str,
    provider_intent_id: str,
    status: str,
    amount_cents: int,
    currency: str = "USD",
) -> None:
    now = time.time()
    if con.kind == "pg":
        con.execute(
            """INSERT INTO market.payment_intents
               (id, user_id, order_id, provider, provider_intent_id, status, amount_cents, currency)
               VALUES (%s::uuid, %s::uuid, %s::uuid, %s, %s, %s, %s, %s)
               ON CONFLICT (provider, provider_intent_id) DO UPDATE
                 SET status = EXCLUDED.status, updated_at = now()""",
            (intent_row_id, user_id, order_id, provider, provider_intent_id, status, amount_cents, currency),
        )
    else:
        # SQLite: upsert by unique provider+provider_intent_id
        existing = db.fetchone(
            con.execute(
                "SELECT id FROM payment_intents WHERE provider=? AND provider_intent_id=?",
                (provider, provider_intent_id),
            )
        )
        if existing:
            con.execute(
                "UPDATE payment_intents SET status=?, updated_at=? WHERE id=?",
                (status, now, existing["id"]),
            )
        else:
            con.execute(
                """INSERT INTO payment_intents
                   (id, user_id, order_id, provider, provider_intent_id, status, amount_cents, currency, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (intent_row_id, user_id, order_id, provider, provider_intent_id, status, amount_cents, currency, now, now),
            )


def update_intent_status(con: db.Conn, provider: str, provider_intent_id: str, status: str) -> None:
    now = time.time()
    if con.kind == "pg":
        con.execute(
            """UPDATE market.payment_intents SET status=%s, updated_at=now()
               WHERE provider=%s AND provider_intent_id=%s""",
            (status, provider, provider_intent_id),
        )
    else:
        con.execute(
            "UPDATE payment_intents SET status=?, updated_at=? WHERE provider=? AND provider_intent_id=?",
            (status, now, provider, provider_intent_id),
        )


def create_checkout_session(
    *,
    user_id: str,
    order_id: str,
    device_id: str,
    plan: str,
    amount_cents: int,
    provider: str,
    success_url: str,
    cancel_url: str,
) -> CheckoutResult:
    """Create a Checkout session (test stub or gated live Stripe)."""
    mode = effective_mode()
    provider = (provider or settings.pay_provider or "stripe").lower()
    intent_row_id = db.new_id()

    if provider == "stripe" and mode == "live":
        return _stripe_live_checkout(
            user_id=user_id,
            order_id=order_id,
            device_id=device_id,
            plan=plan,
            amount_cents=amount_cents,
            intent_row_id=intent_row_id,
            success_url=success_url,
            cancel_url=cancel_url,
        )

    # ---- TEST / stub path (default) ----
    pref = f"test_{provider}_{order_id[:8]}"
    status = "requires_confirmation"
    with db.session(user_id=user_id) as con:
        _store_intent(
            con,
            intent_row_id=intent_row_id,
            user_id=user_id,
            order_id=order_id,
            provider=provider,
            provider_intent_id=pref,
            status=status,
            amount_cents=amount_cents,
        )
        if con.kind == "pg":
            con.execute(
                "UPDATE market.orders SET provider_ref=%s, status=%s WHERE id=%s::uuid",
                (pref, "checkout", order_id),
            )
        else:
            con.execute(
                "UPDATE orders SET provider_ref=?, status=? WHERE id=?",
                (pref, "checkout", order_id),
            )
        db.audit(con, user_id, "checkout", "payment_intent", intent_row_id, {
            "mode": mode, "provider": provider, "order_id": order_id,
        })

    pub = settings.stripe_publishable_key if provider == "stripe" else settings.razorpay_key_id
    return CheckoutResult(
        order_id=order_id,
        payment_intent_id=intent_row_id,
        provider_ref=pref,
        mode=mode,
        provider=provider,
        amount_cents=amount_cents,
        currency="USD",
        status=status,
        publishable_key=pub,
        checkout_url=f"/pay/stub?order={order_id}",
        client_secret=f"stub_secret_{order_id}",
        message="TEST MODE — no real charge. Confirm via POST /v1/checkout/confirm",
        raw={"stub": True},
    )


def _stripe_live_checkout(
    *,
    user_id: str,
    order_id: str,
    device_id: str,
    plan: str,
    amount_cents: int,
    intent_row_id: str,
    success_url: str,
    cancel_url: str,
) -> CheckoutResult:
    """Honest live path: calls Stripe Checkout Sessions API when triple-gated.

    Still refuses if secret key looks like a placeholder or test key while
    gates claim live (safety). Never logs the secret.
    """
    secret = (settings.stripe_secret_key or "").strip()
    if not secret or "REPLACE" in secret or secret.startswith("sk_test_"):
        raise RuntimeError(
            "live gates are on but STRLIX_STRIPE_SECRET_KEY is missing/test/placeholder; "
            "load sk_live_* from Key Vault (see infra/hardening/PAYMENTS-KEYVAULT.md)"
        )

    data = {
        "mode": "payment",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": order_id,
        "metadata[order_id]": order_id,
        "metadata[device_id]": device_id,
        "metadata[plan]": plan,
        "metadata[user_id]": user_id,
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": str(amount_cents),
        "line_items[0][price_data][product_data][name]": f"Strlix cloud phone ({plan})",
        "line_items[0][quantity]": "1",
    }
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            f"{STRIPE_API}/checkout/sessions",
            data=data,
            auth=(secret, ""),
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"Stripe Checkout Session failed: HTTP {resp.status_code}")
    body = resp.json()
    session_id = body.get("id") or ""
    pi = body.get("payment_intent") or session_id
    status = body.get("status") or "open"
    checkout_url = body.get("url") or ""

    with db.session(user_id=user_id) as con:
        _store_intent(
            con,
            intent_row_id=intent_row_id,
            user_id=user_id,
            order_id=order_id,
            provider="stripe",
            provider_intent_id=str(pi),
            status=status,
            amount_cents=amount_cents,
        )
        con.execute(
            "UPDATE market.orders SET provider_ref=%s, status=%s WHERE id=%s::uuid"
            if con.kind == "pg" else
            "UPDATE orders SET provider_ref=?, status=? WHERE id=?",
            (session_id, "checkout", order_id),
        )
        db.audit(con, user_id, "checkout_live", "payment_intent", intent_row_id, {
            "provider": "stripe", "session_id": session_id, "order_id": order_id,
        })

    return CheckoutResult(
        order_id=order_id,
        payment_intent_id=intent_row_id,
        provider_ref=session_id,
        mode="live",
        provider="stripe",
        amount_cents=amount_cents,
        currency="USD",
        status=status,
        publishable_key=settings.stripe_publishable_key,
        checkout_url=checkout_url,
        client_secret=None,
        message="LIVE Checkout Session created — complete payment on Stripe hosted page",
        raw={"id": session_id, "payment_intent": pi},
    )


def confirm_test_payment(*, user_id: str, order_id: str) -> dict[str, Any]:
    """Mark a test checkout paid and activate a lease. Live mode must use webhooks."""
    if live_charges_allowed():
        raise PermissionError("live mode: confirm via Stripe webhook, not /confirm")

    with db.session(user_id=user_id) as con:
        if con.kind == "pg":
            cur = con.execute(
                "SELECT * FROM market.orders WHERE id=%s::uuid AND deleted_at IS NULL", (order_id,)
            )
        else:
            cur = con.execute(
                "SELECT * FROM orders WHERE id=%s AND deleted_at IS NULL", (order_id,)
            )
        row = db.fetchone(cur)
        if not row:
            raise LookupError("order not found")
        pref = row.get("provider_ref") or ""
        if pref:
            update_intent_status(con, row.get("provider") or "stripe", pref, "succeeded_test")
        lid = db.new_id()
        now = time.time()
        hours = 1 if row["plan"] == "hour" else 24
        if con.kind == "pg":
            con.execute("UPDATE market.orders SET status=%s WHERE id=%s::uuid", ("paid_test", order_id))
            con.execute(
                """INSERT INTO market.leases(id,user_id,order_id,device_id,broker_sid,starts_at,ends_at,status)
                   VALUES (%s::uuid,%s::uuid,%s::uuid,%s,NULL,to_timestamp(%s),to_timestamp(%s),'active')""",
                (lid, user_id, order_id, row["device_id"], now, now + hours * 3600),
            )
        else:
            con.execute("UPDATE orders SET status=%s WHERE id=%s", ("paid_test", order_id))
            con.execute(
                "INSERT INTO leases(id,user_id,order_id,device_id,broker_sid,starts_at,ends_at,status) VALUES (?,?,?,?,?,?,?,?)",
                (lid, user_id, order_id, row["device_id"], None, now, now + hours * 3600, "active"),
            )
        db.audit(con, user_id, "paid_test", "order", order_id, {})
    return {
        "status": "paid_test",
        "lease_id": lid,
        "device_id": row["device_id"],
        "mode": "test",
    }


def verify_stripe_signature(payload: bytes, sig_header: str | None) -> bool:
    """Verify Stripe-Signature (t=...,v1=...) when webhook secret is configured.

    In test mode with placeholder secret, accept stub posts so local demos work.
    """
    secret = (settings.stripe_webhook_secret or "").strip()
    mode = effective_mode()
    if mode != "live" or not secret or "REPLACE" in secret or secret.startswith("whsec_test"):
        return True  # test / stub path
    if not sig_header:
        return False
    # Parse t= and v1=
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    ts = parts.get("t")
    v1 = parts.get("v1")
    if not ts or not v1:
        return False
    try:
        if abs(time.time() - int(ts)) > 300:
            return False
    except ValueError:
        return False
    signed = f"{ts}.".encode() + payload
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def handle_stripe_webhook(payload: bytes, sig_header: str | None) -> dict[str, Any]:
    if not verify_stripe_signature(payload, sig_header):
        raise PermissionError("invalid stripe signature")
    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise ValueError("invalid json") from e

    etype = event.get("type") or "stub.test"
    data_obj = (event.get("data") or {}).get("object") or {}
    # Prefer payment_intent id; fall back to checkout session id
    provider_intent_id = (
        data_obj.get("payment_intent")
        or data_obj.get("id")
        or event.get("id")
        or "stub"
    )
    status_map = {
        "checkout.session.completed": "succeeded",
        "payment_intent.succeeded": "succeeded",
        "payment_intent.payment_failed": "failed",
        "checkout.session.expired": "canceled",
    }
    new_status = status_map.get(etype, "received")
    mode = effective_mode()

    # Webhooks are system-scoped; update by provider_intent_id without user RLS.
    with db.session(user_id=None) as con:
        if con.kind == "pg":
            # Bypass RLS for webhook worker via set_config empty + SECURITY — we only
            # update by opaque provider id. Prefer matching rows.
            con.execute("SELECT set_config('app.user_id', %s, true)", ("",))
            con.execute(
                """UPDATE market.payment_intents SET status=%s, updated_at=now()
                   WHERE provider='stripe' AND provider_intent_id=%s""",
                (new_status, str(provider_intent_id)),
            )
            if new_status == "succeeded":
                # Mark related order paid if metadata carries order_id
                order_id = (data_obj.get("metadata") or {}).get("order_id") or data_obj.get("client_reference_id")
                if order_id:
                    con.execute(
                        "UPDATE market.orders SET status=%s WHERE id=%s::uuid AND deleted_at IS NULL",
                        ("paid" if mode == "live" else "paid_test", order_id),
                    )
        else:
            update_intent_status(con, "stripe", str(provider_intent_id), new_status)
            order_id = (data_obj.get("metadata") or {}).get("order_id") or data_obj.get("client_reference_id")
            if order_id and new_status == "succeeded":
                con.execute(
                    "UPDATE orders SET status=? WHERE id=? AND deleted_at IS NULL",
                    ("paid" if mode == "live" else "paid_test", order_id),
                )
        db.audit(con, None, "webhook_stripe", "payment_intent", str(provider_intent_id), {
            "type": etype, "status": new_status, "mode": mode,
        })

    return {"received": True, "mode": mode, "type": etype, "status": new_status}


def gate_status() -> dict[str, Any]:
    return {
        "pay_mode_setting": settings.pay_mode,
        "payments_live": payments_live_flag(),
        "allow_live_charges": bool(settings.allow_live_charges),
        "effective_mode": effective_mode(),
        "live_charges_allowed": live_charges_allowed(),
        "provider": settings.pay_provider,
        "publishable_key_prefix": (settings.stripe_publishable_key or "")[:12],
    }
