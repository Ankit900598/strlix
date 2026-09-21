#!/usr/bin/env python3
"""Smoke-test the privacy-first anonymous rental flow against SQLite."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [Path("/workspace/zevi-cloudphone"), ROOT]
REPO = next((p for p in CANDIDATES if (p / "services" / "market-api").is_dir()), ROOT)

with tempfile.NamedTemporaryFile(prefix="strlix-anon-", suffix=".db") as db_file:
    os.environ["STRLIX_DATABASE_URL"] = ""
    os.environ["STRLIX_MARKET_DB"] = "sqlite:///" + db_file.name
    sys.path.insert(0, str(REPO / "services" / "market-api"))

    from fastapi.testclient import TestClient
    from market_api.main import app

    client = TestClient(app)
    devices = client.get("/v1/devices").json()["devices"]
    anon = client.post("/v1/auth/anon")
    assert anon.status_code == 200, anon.text
    anon_json = anon.json()
    assert anon_json["is_anonymous"] is True
    headers = {"Authorization": "Bearer " + anon_json["access_token"]}

    session = client.post(
        "/v1/checkout/session",
        json={"device_id": devices[0]["id"], "plan": "hour"},
        headers=headers,
    )
    assert session.status_code == 200, session.text
    order_id = session.json()["order_id"]
    confirmed = client.post(
        "/v1/checkout/confirm",
        params={"order_id": order_id},
        headers=headers,
    )
    assert confirmed.status_code == 200, confirmed.text

    claim = client.post(
        "/v1/auth/claim",
        json={"email": "anonymous-smoke@example.com"},
        headers=headers,
    )
    assert claim.status_code == 200, claim.text
    claim_json = claim.json()
    assert claim_json["is_anonymous"] is False
    assert claim_json["user_id"] == anon_json["user_id"]

    orders = client.get(
        "/v1/me/orders",
        headers={"Authorization": "Bearer " + claim_json["access_token"]},
    )
    assert order_id in {row["id"] for row in orders.json()["orders"]}
    print("anonymous market flow PASS")
