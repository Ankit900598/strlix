#!/usr/bin/env python3
"""Smoke-test the privacy-safe queued/running/done job shell against SQLite."""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [Path("/workspace/zevi-cloudphone"), ROOT]
REPO = next((p for p in CANDIDATES if (p / "services" / "market-api").is_dir()), ROOT)

with tempfile.NamedTemporaryFile(prefix="strlix-jobs-", suffix=".db") as db_file:
    os.environ["STRLIX_DATABASE_URL"] = ""
    os.environ["STRLIX_MARKET_DB"] = "sqlite:///" + db_file.name
    sys.path.insert(0, str(REPO / "services" / "market-api"))

    from fastapi.testclient import TestClient
    from market_api.main import app

    client = TestClient(app)
    anon = client.post("/v1/auth/anon")
    assert anon.status_code == 200, anon.text
    headers = {"Authorization": "Bearer " + anon.json()["access_token"]}

    created = client.post("/v1/jobs", json={"kind": "phone_task"}, headers=headers)
    assert created.status_code == 202, created.text
    job = created.json()
    assert job["status"] in {"queued", "running", "done"}
    assert set(job) >= {"job_id", "status", "kind", "poll_after_ms"}

    deadline = time.time() + 3
    states = {job["status"]}
    while time.time() < deadline:
        current = client.get("/v1/jobs/" + job["job_id"], headers=headers)
        assert current.status_code == 200, current.text
        state = current.json()
        states.add(state["status"])
        if state["status"] == "done":
            assert state["result"] == {"ok": True}
            break
        time.sleep(0.1)
    else:
        raise AssertionError("job did not reach done")

    assert states <= {"queued", "running", "done"}

    other = client.post("/v1/auth/anon")
    assert other.status_code == 200, other.text
    other_headers = {"Authorization": "Bearer " + other.json()["access_token"]}
    assert client.get("/v1/jobs/" + job["job_id"], headers=other_headers).status_code == 404
    assert client.post("/v1/jobs", json={"kind": "free_form_chat"}, headers=headers).status_code == 422
    print("async market job flow PASS", sorted(states))
