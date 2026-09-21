"""Privacy-safe, process-local async job status shell.

Jobs intentionally carry only an allow-listed kind and a pseudonymous owner id
from the authenticated session. No prompt, chat text, device content, or outside
messages are accepted or persisted. Replace this executor with a durable worker
only when the product has a retention policy and queue boundary.
"""
from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock, Thread
import time
import uuid

_TERMINAL_TTL_SECONDS = 15 * 60
_MAX_JOBS = 1000
_jobs: dict[str, dict] = {}
_lock = Lock()


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _prune_locked() -> None:
    cutoff = time.time() - _TERMINAL_TTL_SECONDS
    stale = [
        job_id for job_id, job in _jobs.items()
        if job["status"] == "done" and job["completed_at_epoch"] < cutoff
    ]
    for job_id in stale:
        _jobs.pop(job_id, None)
    if len(_jobs) > _MAX_JOBS:
        done = sorted(
            (job for job in _jobs.values() if job["status"] == "done"),
            key=lambda job: job["completed_at_epoch"],
        )
        for job in done[: max(0, len(_jobs) - _MAX_JOBS)]:
            _jobs.pop(job["id"], None)


def _public(job: dict) -> dict:
    return {
        "job_id": job["id"],
        "kind": job["kind"],
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
        "result": job["result"],
    }


def _run(job_id: str) -> None:
    # The small delay makes queued/running observable to a polling client while
    # keeping this a deterministic status shell rather than a fake chat loop.
    time.sleep(0.10)
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = _timestamp()

    time.sleep(0.40)
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "done"
        job["completed_at"] = _timestamp()
        job["completed_at_epoch"] = time.time()
        job["result"] = {"ok": True}


def create(owner_id: str, kind: str) -> dict:
    now = _timestamp()
    job = {
        "id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "kind": kind,
        "status": "queued",
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "completed_at_epoch": 0.0,
        "result": None,
    }
    with _lock:
        _prune_locked()
        _jobs[job["id"]] = job
    Thread(target=_run, args=(job["id"],), name="strlix-job", daemon=True).start()
    return _public(job)


def get(job_id: str, owner_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job or job["owner_id"] != owner_id:
            return None
        return _public(job)
