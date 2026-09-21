#!/usr/bin/env python3
"""Demonstrate per-user RLS isolation against Azure Postgres."""
import os, sys
sys.path.insert(0, "/workspace/zevi-cloudphone/services/market-api")
from fastapi.testclient import TestClient
from market_api.main import app

assert os.environ.get("STRLIX_DATABASE_URL"), "STRLIX_DATABASE_URL required"
client = TestClient(app)

r = client.get("/health")
print("health", r.status_code, r.json())

a = client.post("/v1/auth/login", json={"email": "alice-rls@example.com", "display_name": "Alice"})
b = client.post("/v1/auth/login", json={"email": "bob-rls@example.com", "display_name": "Bob"})
assert a.status_code == 200, a.text
assert b.status_code == 200, b.text
ta, tb = a.json()["access_token"], b.json()["access_token"]
print("login ok", a.json()["user_id"], b.json()["user_id"])

# list devices
devs = client.get("/v1/devices").json()["devices"]
device_id = devs[0]["id"]
print("device", device_id)

ca = client.post(
    "/v1/checkout/session",
    json={"device_id": device_id, "plan": "hour", "provider": "stub"},
    headers={"Authorization": f"Bearer {ta}"},
)
assert ca.status_code == 200, ca.text
oid = ca.json()["order_id"]
print("alice order", oid)

oa = client.get("/v1/me/orders", headers={"Authorization": f"Bearer {ta}"})
ob = client.get("/v1/me/orders", headers={"Authorization": f"Bearer {tb}"})
assert oa.status_code == 200 and ob.status_code == 200
alice_ids = {o["id"] for o in oa.json()["orders"]}
bob_ids = {o["id"] for o in ob.json()["orders"]}
print("alice orders", len(alice_ids), "bob orders", len(bob_ids))
assert oid in alice_ids, "alice should see her order"
assert oid not in bob_ids, "RLS FAIL: bob must not see alice order"
print("RLS PASS: bob cannot see alice order")

conf = client.post(f"/v1/checkout/confirm?order_id={oid}", headers={"Authorization": f"Bearer {ta}"})
assert conf.status_code == 200, conf.text
print("confirm", conf.json()["status"])
print("SUCCESS")
