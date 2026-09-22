#!/usr/bin/env python3
"""Free-month launch: waitlist + phone grant without Stripe, anon still works."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [Path("/workspace/zevi-cloudphone"), ROOT]
REPO = next((p for p in CANDIDATES if (p / "services" / "market-api").is_dir()), ROOT)

with tempfile.NamedTemporaryFile(prefix="strlix-free-", suffix=".db") as db_file:
    os.environ["STRLIX_DATABASE_URL"] = ""
    os.environ["STRLIX_MARKET_DB"] = "sqlite:///" + db_file.name
    os.environ["STRLIX_PAY_MODE"] = "test"
    os.environ["PAYMENTS_LIVE"] = "false"
    os.environ["STRLIX_ALLOW_LIVE_CHARGES"] = "false"
    os.environ["STRLIX_BILLING_MODE"] = "free_month"
    os.environ["STRLIX_FREE_LAUNCH_MODE"] = "true"
    os.environ["STRLIX_AUTH_MODE"] = "anon"
    os.environ.pop("STRLIX_INVITE_CODES", None)
    sys.path.insert(0, str(REPO / "services" / "market-api"))

    from fastapi.testclient import TestClient
    from market_api.main import app
    from market_api import redis_client
    from market_api.settings import settings

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200, health.text
    body = health.json()
    assert body["pay_mode"] == "test"
    assert body["free_month_active"] is True
    assert body["card_required"] is False
    assert body["pay_gates"]["live_charges_allowed"] is False
    assert body["auth_mode"] == "anon"

    launch = client.get("/v1/launch").json()
    assert "no card required" in launch["copy"].lower()
    assert launch["pay_required_for_session"] is False
    assert launch["support_email_placeholder"] is True
    assert "mailbox is being set up" in launch["support_note"].lower()
    assert launch["invite_required"] is False
    assert launch["legal"] == {
        "terms": "/market/legal/terms.html",
        "privacy": "/market/legal/privacy.html",
        "support": "/market/legal/support.html",
        "capabilities": "/market/legal/capabilities.html",
    }

    static_legal = REPO / "static" / "legal"
    market_legal = REPO / "web-market" / "legal"
    for name in ("terms.html", "privacy.html", "support.html", "capabilities.html", "legal.css"):
        assert (static_legal / name).read_bytes() == (market_legal / name).read_bytes(), name

    banner = "Soft-launch terms — not a substitute for independent legal advice."
    for name in ("terms.html", "privacy.html", "support.html", "capabilities.html"):
        for prefix in ("/market/legal/", "/legal/"):
            page = client.get(prefix + name)
            assert page.status_code == 200, (prefix + name, page.status_code)
            assert banner in page.text
        text = (static_legal / name).read_text()
        assert "counsel passed" not in text.lower()
        assert "registered office" not in text.lower() or "do not name a registered" in text.lower()
    terms = (static_legal / "terms.html").read_text()
    privacy = (static_legal / "privacy.html").read_text()
    support = (static_legal / "support.html").read_text()
    caps = (static_legal / "capabilities.html").read_text()
    assert "not a device reserved for you alone" in terms
    assert "about one hour" in terms
    assert "not a warranty that any particular use is legal" in terms
    assert "can be wrong" in terms.lower() or "can be mistaken" in terms
    assert "POST /v1/privacy/soft-delete" in privacy
    assert "POST /v1/privacy/hard-delete" in privacy
    assert "Redis" in privacy and "Postgres" in privacy and "Azure" in privacy
    assert "mailbox is being set up" in support
    assert "SUPPORT_EMAIL" in support
    assert "ROLE_ASSISTANT" in caps and "not claimed" in caps
    assert "Sub-100" in caps
    assert "No illegal-use warranty" in caps

    joined = client.post("/v1/waitlist", json={"email": "launch@example.com"})
    assert joined.status_code == 200, joined.text
    assert joined.json()["status"] == "joined"
    assert joined.json()["created_at"]
    again = client.post("/v1/waitlist", json={"email": "launch@example.com"})
    assert again.status_code == 200, again.text
    assert again.json()["status"] == "already_registered"

    anon = client.post("/v1/auth/anon")
    assert anon.status_code == 200, anon.text
    anon_json = anon.json()
    assert anon_json["is_anonymous"] is True
    headers = {"Authorization": "Bearer " + anon_json["access_token"]}

    granted = client.post("/v1/access/grant", json={}, headers=headers)
    assert granted.status_code == 200, granted.text
    grant_body = granted.json()
    assert grant_body["status"] == "granted_free"
    assert grant_body["amount_cents"] == 0
    assert grant_body["card_required"] is False
    assert grant_body["plan"] == "free_month"
    assert grant_body["mode"] == "free_month"

    repeat = client.post(
        "/v1/access/grant",
        json={"device_id": grant_body["device_id"]},
        headers=headers,
    )
    assert repeat.status_code == 200, repeat.text
    assert repeat.json()["status"] == "already_granted"
    assert repeat.json()["lease_id"] == grant_body["lease_id"]

    claim = client.post(
        "/v1/auth/claim",
        json={"email": "launch-claim@example.com"},
        headers=headers,
    )
    assert claim.status_code == 200, claim.text
    assert claim.json()["is_anonymous"] is False
    assert claim.json()["user_id"] == anon_json["user_id"]

    orders = client.get(
        "/v1/me/orders",
        headers={"Authorization": "Bearer " + claim.json()["access_token"]},
    )
    assert orders.status_code == 200, orders.text
    match = [row for row in orders.json()["orders"] if row["id"] == grant_body["order_id"]]
    assert match and match[0]["amount_cents"] == 0
    assert match[0]["status"] == "granted_free"

    os.environ["STRLIX_INVITE_CODES"] = "BETA1,beta2"
    denied = client.post("/v1/waitlist", json={"email": "needs-code@example.com"})
    assert denied.status_code == 403, denied.text
    allowed = client.post(
        "/v1/waitlist",
        json={"email": "needs-code@example.com", "invite_code": "beta2"},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "joined"
    os.environ.pop("STRLIX_INVITE_CODES", None)

    settings.anon_rate_per_min = 2
    redis_client._rate.clear()
    assert client.post("/v1/auth/anon").status_code == 200
    assert client.post("/v1/auth/anon").status_code == 200
    limited = client.post("/v1/auth/anon")
    assert limited.status_code == 429, limited.text

    print("free-month launch PASS")
