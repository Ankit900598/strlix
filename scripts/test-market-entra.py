#!/usr/bin/env python3
"""Entra JWT validation is additive. Default anon mode rejects Entra tokens."""
from __future__ import annotations

import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [Path("/workspace/zevi-cloudphone"), ROOT]
REPO = next((p for p in CANDIDATES if (p / "services" / "market-api").is_dir()), ROOT)

TENANT = "11111111-1111-1111-1111-111111111111"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"
AUDIENCE = "api://strlix-market"


def _token(private_key, *, audience=AUDIENCE, email="entra-user@example.com"):
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "oid": str(uuid.uuid4()),
            "tid": TENANT,
            "email": email,
            "name": "Entra User",
            "iss": ISSUER,
            "aud": audience,
            "iat": now,
            "exp": now + 600,
        },
        private_key,
        algorithm="RS256",
    )


with tempfile.NamedTemporaryFile(prefix="strlix-entra-", suffix=".db") as db_file:
    os.environ["STRLIX_DATABASE_URL"] = ""
    os.environ["STRLIX_MARKET_DB"] = "sqlite:///" + db_file.name
    os.environ["STRLIX_AUTH_MODE"] = "anon"
    os.environ["STRLIX_ENTRA_TENANT_ID"] = TENANT
    os.environ["STRLIX_ENTRA_AUDIENCE"] = AUDIENCE
    os.environ["STRLIX_ENTRA_ISSUER"] = ISSUER
    os.environ["STRLIX_ENTRA_KIND"] = "workforce"
    sys.path.insert(0, str(REPO / "services" / "market-api"))

    from fastapi.testclient import TestClient
    import market_api.auth as auth
    from market_api.main import app

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    client = TestClient(app)
    entra_token = _token(private_key)

    blocked = client.get("/v1/me/orders", headers={"Authorization": "Bearer " + entra_token})
    assert blocked.status_code == 401, blocked.text

    anon = client.post("/v1/auth/anon")
    assert anon.status_code == 200, anon.text
    anon_headers = {"Authorization": "Bearer " + anon.json()["access_token"]}
    assert client.get("/v1/me/orders", headers=anon_headers).status_code == 200

    os.environ["STRLIX_AUTH_MODE"] = "entra"
    real_validate = auth.validate_entra_token

    def _validate(token, *, key=None):
        return real_validate(token, key=public_key)

    auth.validate_entra_token = _validate

    accepted = client.get("/v1/me/orders", headers={"Authorization": "Bearer " + entra_token})
    assert accepted.status_code == 200, accepted.text
    # Phone-first anon sessions keep working after Entra is enabled.
    assert client.get("/v1/me/orders", headers=anon_headers).status_code == 200
    assert client.post("/v1/auth/anon").status_code == 200

    wrong = client.get(
        "/v1/me/orders",
        headers={"Authorization": "Bearer " + _token(private_key, audience="api://other")},
    )
    assert wrong.status_code == 401, wrong.text

    os.environ["STRLIX_ENTRA_ISSUER"] = ""
    os.environ["STRLIX_ENTRA_TENANT_ID"] = ""
    os.environ["STRLIX_ENTRA_AUDIENCE"] = ""
    incomplete = client.get(
        "/v1/me/orders",
        headers={"Authorization": "Bearer " + _token(private_key, email="other@example.com")},
    )
    assert incomplete.status_code == 503, incomplete.text
    # Local anon bearer is still accepted while Entra config is incomplete.
    assert client.get("/v1/me/orders", headers=anon_headers).status_code == 200

    print("entra auth PASS")
