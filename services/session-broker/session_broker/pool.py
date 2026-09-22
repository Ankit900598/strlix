"""In-memory device pool (phase-1). Env selects which single device is seeded.

Capacity model:
  devices_available ≈ N physical/cloud Android instances
  concurrent_viewers_per_device ≈ 12 (shared H.264 fan-out)
  interactive_controller_per_device = 1 (tap owner)

Phase-1 honesty: DevicePool seeds **one** device from env (Azure emulator
default, or AWS Redroid when STRLIX_PILOT_DEVICE_ID / ADB_SERIAL point there).
It does **not** multi-lease Azure+AWS at once. Catalog SKUs ≠ broker seats.

100k concurrent *chat* users ≠ 100k phones. Chat scales on android-api.
Viewer sessions consume scarce devices via this broker.
"""
from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Device:
    device_id: str
    adb_serial: str
    region: str = "eastus2"
    capacity_viewers: int = 12
    status: str = "ready"  # ready | leased | draining | offline
    labels: dict = field(default_factory=dict)


@dataclass
class Session:
    sid: str
    user_id: str
    device_id: str
    adb_serial: str
    created_at: float
    expires_at: float
    controller: bool = True  # phase-1: lease holder is the tap owner


def _infer_pilot_kind(device_id: str, serial: str) -> str:
    explicit = os.environ.get("STRLIX_PILOT_KIND", "").strip().lower()
    if explicit:
        return explicit
    did = device_id.lower()
    if "redroid" in did or serial.endswith(":5556"):
        return "redroid"
    return "emulator"


def _infer_pilot_host(kind: str) -> str:
    explicit = os.environ.get("STRLIX_PILOT_HOST", "").strip()
    if explicit:
        return explicit
    if kind == "redroid":
        return "strlix-gpu-worker-1"
    return "vm-zevi-cloudphone"


def _infer_pilot_region(kind: str) -> str:
    explicit = os.environ.get("STRLIX_REGION", "").strip()
    if explicit:
        return explicit
    if kind == "redroid":
        return "us-east-1"
    return "eastus2"


class DevicePool:
    def __init__(self) -> None:
        self.devices: dict[str, Device] = {}
        self.sessions: dict[str, Session] = {}
        self._seed_pilot()

    def _seed_pilot(self) -> None:
        serial = os.environ.get("ADB_SERIAL", "127.0.0.1:5555")
        did = os.environ.get("STRLIX_PILOT_DEVICE_ID", "pilot-emulator-1")
        kind = _infer_pilot_kind(did, serial)
        host = _infer_pilot_host(kind)
        region = _infer_pilot_region(kind)
        self.devices[did] = Device(
            device_id=did,
            adb_serial=serial,
            region=region,
            capacity_viewers=int(os.environ.get("MAX_STREAM_CLIENTS", "12")),
            status="ready",
            labels={"tier": "pilot", "kind": kind, "host": host},
        )

    def list_devices(self) -> list[dict]:
        out = []
        for d in self.devices.values():
            active = sum(1 for s in self.sessions.values() if s.device_id == d.device_id)
            out.append({
                "device_id": d.device_id,
                "adb_serial": d.adb_serial,
                "region": d.region,
                "status": d.status,
                "capacity_viewers": d.capacity_viewers,
                "active_sessions": active,
                "labels": d.labels,
            })
        return out

    def acquire(
        self,
        user_id: str,
        *,
        ttl_s: int = 3600,
        prefer_device: Optional[str] = None,
    ) -> Session:
        now = time.time()
        self._expire(now)
        # Prefer sticky re-bind
        if prefer_device and prefer_device in self.devices:
            cand = [self.devices[prefer_device]]
        else:
            cand = [d for d in self.devices.values() if d.status in ("ready", "leased")]
        if not cand:
            raise RuntimeError("no devices in pool")
        # Pick least-loaded ready/leased device under viewer capacity
        def load(d: Device) -> int:
            return sum(1 for s in self.sessions.values() if s.device_id == d.device_id)

        cand.sort(key=load)
        chosen = None
        for d in cand:
            if load(d) < d.capacity_viewers:
                chosen = d
                break
        if chosen is None:
            raise RuntimeError("device pool at capacity")
        sid = uuid.uuid4().hex
        # First session on a device becomes controller; later are view-only in phase-2.
        is_controller = load(chosen) == 0
        sess = Session(
            sid=sid,
            user_id=user_id,
            device_id=chosen.device_id,
            adb_serial=chosen.adb_serial,
            created_at=now,
            expires_at=now + ttl_s,
            controller=is_controller,
        )
        self.sessions[sid] = sess
        chosen.status = "leased"
        return sess

    def release(self, sid: str) -> bool:
        sess = self.sessions.pop(sid, None)
        if not sess:
            return False
        remaining = [s for s in self.sessions.values() if s.device_id == sess.device_id]
        if not remaining:
            dev = self.devices.get(sess.device_id)
            if dev:
                dev.status = "ready"
        return True

    def get(self, sid: str) -> Optional[Session]:
        self._expire(time.time())
        return self.sessions.get(sid)

    def _expire(self, now: float) -> None:
        dead = [sid for sid, s in self.sessions.items() if s.expires_at <= now]
        for sid in dead:
            self.release(sid)

    def capacity_report(self) -> dict:
        total = len(self.devices)
        ready = sum(1 for d in self.devices.values() if d.status == "ready")
        leased = sum(1 for d in self.devices.values() if d.status == "leased")
        sessions = len(self.sessions)
        viewer_slots = sum(d.capacity_viewers for d in self.devices.values())
        seeded = next(iter(self.devices.values()), None)
        kind = (seeded.labels or {}).get("kind", "emulator") if seeded else "unknown"
        return {
            "devices_total": total,
            "devices_ready": ready,
            "devices_leased": leased,
            "active_sessions": sessions,
            "viewer_slots_total": viewer_slots,
            "seeded_device_id": seeded.device_id if seeded else None,
            "seeded_kind": kind,
            "honest_note": (
                f"Phase-1 pool seeds 1 device from env (kind={kind}). "
                "Azure emulator default; set STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1 "
                "and ADB_SERIAL=127.0.0.1:5556 for AWS Redroid. "
                "Not multi-lease Azure+AWS simultaneously. "
                "Billion-user chat scales on android-api; "
                "viewer concurrency scales only with device count × viewers/device."
            ),
        }


POOL = DevicePool()
