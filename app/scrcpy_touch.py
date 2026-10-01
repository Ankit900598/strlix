"""Touch injection over a control-only scrcpy-server session.

Why (normal-feel, 2026-10): ``input motionevent DOWN|MOVE|UP`` gives every
injected event its *own* downTime (Android's InputShellCommand stamps
``downTime = now`` per invocation). Most views tolerate that, but Launcher3's
Recents swipe-to-dismiss and other fling detectors do not: a card dragged with
``input motionevent`` snaps back, while the same path via ``input swipe`` (one
process, one downTime) dismisses. scrcpy's control socket injects a real,
consistent gesture (one downTime per pointer, proper pressure), with no process
spawn per event.

Protocol (scrcpy ≥ 2.x, used here with 4.1): video=false audio=false
control=true tunnel_forward=true → the control socket is the first socket, so
the server sends one dummy byte on it. INJECT_TOUCH_EVENT is 32 bytes:
u8 type=2 | u8 action | i64 pointer_id | i32 x | i32 y | u16 w | u16 h |
u16 pressure | u32 action_button | u32 buttons. w/h must equal the device
display size (control-only sessions map positions against the display).
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import secrets
import struct
import time
from typing import TYPE_CHECKING, Optional

from app.scrcpy_source import SCRCPY_SERVER_PATH, SCRCPY_VERSION, _REMOTE_JAR

if TYPE_CHECKING:  # pragma: no cover
    from app.adb_client import AdbClient

SCRCPY_TOUCH = os.environ.get("SCRCPY_TOUCH", "1") not in ("0", "false", "no")
_ACTIONS = {"DOWN": 0, "UP": 1, "MOVE": 2, "CANCEL": 3}
_POINTER_FINGER = -2  # SC_POINTER_ID_GENERIC_FINGER


def pack_touch(action: str, x: int, y: int, w: int, h: int) -> bytes:
    a = _ACTIONS[action]
    pressure = 0 if a in (1, 3) else 0xFFFF
    return struct.pack(">BBqiiHHHII", 2, a, _POINTER_FINGER, int(x), int(y), int(w), int(h), pressure, 0, 0)


class ScrcpyTouch:
    def __init__(self, adb: "AdbClient") -> None:
        self.adb = adb
        self.scid = f"{secrets.randbits(31):08x}"
        self.port = 0
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._drain_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.size: Optional[tuple[int, int]] = None
        self.disabled_until = 0.0
        self.sent = 0
        self.errors = 0
        self.starts = 0
        self.last_error: Optional[str] = None

    @property
    def alive(self) -> bool:
        return (
            self._writer is not None
            and not self._writer.is_closing()
            and self._proc is not None
            and self._proc.returncode is None
        )

    def stats(self) -> dict:
        return {
            "enabled": SCRCPY_TOUCH,
            "alive": self.alive,
            "sent": self.sent,
            "errors": self.errors,
            "starts": self.starts,
            "size": list(self.size) if self.size else None,
            "last_error": self.last_error,
        }

    async def _adb(self, *args: str, timeout: float = 8.0) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            self.adb.adb_bin, "-s", self.adb.serial, *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            raise
        return proc.returncode or 0, out, err

    async def _start(self) -> None:
        await self.close()
        self.starts += 1
        self.scid = f"{secrets.randbits(31):08x}"
        rc, out, _ = await self._adb("shell", f"stat -c %s {_REMOTE_JAR} 2>/dev/null || echo 0")
        remote = 0
        with contextlib.suppress(Exception):
            remote = int((out or b"0").decode().strip().splitlines()[-1] or "0")
        if remote <= 0 or (os.path.exists(SCRCPY_SERVER_PATH) and os.path.getsize(SCRCPY_SERVER_PATH) != remote):
            rc, _, err = await self._adb("push", SCRCPY_SERVER_PATH, _REMOTE_JAR, timeout=30.0)
            if rc != 0:
                raise RuntimeError(f"push failed: {err[:120]!r}")
        size = await self.adb.wm_size()
        if not size.get("ok"):
            raise RuntimeError("wm size unknown")
        self.size = (int(size["width"]), int(size["height"]))
        opts = (
            f"scid={self.scid} tunnel_forward=true video=false audio=false control=true "
            f"cleanup=false send_device_meta=false send_dummy_byte=true clipboard_autosync=false"
        )
        self._proc = await asyncio.create_subprocess_exec(
            self.adb.adb_bin, "-s", self.adb.serial, "shell",
            f"CLASSPATH={_REMOTE_JAR} app_process / com.genymobile.scrcpy.Server {SCRCPY_VERSION} {opts}",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        rc, out, err = await self._adb("forward", "tcp:0", f"localabstract:scrcpy_{self.scid}")
        if rc != 0:
            raise RuntimeError(f"forward failed: {err[:120]!r}")
        self.port = int(out.decode().strip().splitlines()[-1])
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if self._proc.returncode is not None:
                raise RuntimeError("scrcpy control server exited")
            try:
                r, w = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", self.port), 1.0)
                b = await asyncio.wait_for(r.read(1), 1.0)
                if b:
                    self._reader, self._writer = r, w
                    self._drain_task = asyncio.create_task(self._drain(), name="scrcpy-touch-drain")
                    return
                w.close()
            except (OSError, asyncio.TimeoutError):
                pass
            await asyncio.sleep(0.1)
        raise RuntimeError("scrcpy control socket never opened")

    async def _drain(self) -> None:
        # Device → client messages (clipboard, acks). Read and drop so the
        # server never blocks on a full socket.
        r = self._reader
        with contextlib.suppress(Exception):
            while r is not None:
                if not await r.read(4096):
                    break

    async def close(self) -> None:
        w, self._writer, self._reader = self._writer, None, None
        if w is not None:
            w.close()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(w.wait_closed(), 1.0)
        t, self._drain_task = self._drain_task, None
        if t is not None:
            t.cancel()
        p, self._proc = self._proc, None
        if p is not None and p.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                p.kill()
        if self.port:
            with contextlib.suppress(Exception):
                await self._adb("forward", "--remove", f"tcp:{self.port}", timeout=3.0)
            self.port = 0
        with contextlib.suppress(Exception):
            await self._adb("shell", f"pkill -f 'scid={self.scid} tunnel_forward=true video=false audio=false control=true' || true", timeout=3.0)

    async def warm(self) -> bool:
        if not SCRCPY_TOUCH or time.time() < self.disabled_until:
            return False
        async with self._lock:
            if self.alive:
                return True
            try:
                await self._start()
                return True
            except Exception as e:  # noqa: BLE001
                self.errors += 1
                self.last_error = str(e)[:160]
                self.disabled_until = time.time() + 20.0
                await self.close()
                return False

    async def send(self, action: str, x: int, y: int) -> bool:
        """Inject one finger event. False → caller falls back to `input`."""
        if not SCRCPY_TOUCH or time.time() < self.disabled_until or action not in _ACTIONS:
            return False
        if not self.alive and not await self.warm():
            return False
        async with self._lock:
            w = self._writer
            if w is None or self.size is None:
                return False
            try:
                w.write(pack_touch(action, x, y, *self.size))
                await asyncio.wait_for(w.drain(), 0.5)
                self.sent += 1
                return True
            except Exception as e:  # noqa: BLE001
                self.errors += 1
                self.last_error = str(e)[:160]
                self.disabled_until = time.time() + 10.0
                asyncio.create_task(self.close())
                return False
