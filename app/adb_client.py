"""ADB helper: talks to a device via local adb (SSH tunnel or direct connect).

Live-view architecture (overnight sprint fix)
---------------------------------------------
Previously every MJPEG client and every ``/adb/preview`` request ran its own
``screencap`` behind a single ``_preview_lock``, so N viewers each got roughly
``1/N`` of an already-slow 2.5 fps pipeline.

Now there is exactly one **frame producer** (:class:`FrameBroker`) that owns the
ADB serial for screen capture.  It captures -> encodes JPEG -> publishes into an
in-memory slot guarded by an ``asyncio.Condition``.  Every consumer (MJPEG,
WebSocket, ``/adb/preview``) reads the latest published frame; nobody captures
on their own and nothing touches the disk.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .h264_stream import H264Broker

ADB_BIN = os.environ.get("ADB_BIN", "/workspace/zevi-cloudphone/platform-tools/adb")
DEFAULT_SERIAL = os.environ.get("ADB_SERIAL", "127.0.0.1:5555")
SCREENSHOT_DIR = Path(os.environ.get("SCREENSHOT_DIR", "/workspace/zevi-cloudphone/demo"))

# Live stream tuning (env-overridable so ops can tweak without a code change)
STREAM_QUALITY = int(os.environ.get("STREAM_QUALITY", "50"))
STREAM_MAX_WIDTH = int(os.environ.get("STREAM_MAX_WIDTH", "480"))
STREAM_INTERVAL_MS = int(os.environ.get("STREAM_INTERVAL_MS", "250"))
STREAM_IDLE_STOP_S = float(os.environ.get("STREAM_IDLE_STOP_S", "12"))
# How many screen-*.png files to keep in demo/ (pilot/chat saves only)
SCREENSHOT_RETENTION = int(os.environ.get("SCREENSHOT_RETENTION", "40"))


class AdbError(RuntimeError):
    pass


@dataclass(frozen=True)
class Frame:
    """One published live frame. Immutable so consumers can hold it safely."""

    version: int
    ts: float
    jpeg: bytes
    png: bytes
    image_width: int
    image_height: int
    device_width: int
    device_height: int
    capture_ms: float
    encode_ms: float


def _encode_jpeg(png: bytes, quality: int, max_width: int) -> tuple[bytes, int, int, int, int]:
    """PNG bytes -> (jpeg, img_w, img_h, device_w, device_h). Runs in a thread."""
    from PIL import Image

    img = Image.open(io.BytesIO(png))
    img.load()
    device_w, device_h = img.size
    if img.mode != "RGB":
        img = img.convert("RGB")
    if max_width and device_w > max_width:
        ratio = max_width / float(device_w)
        img = img.resize(
            (max_width, max(1, int(round(device_h * ratio)))),
            Image.Resampling.BILINEAR,
        )
    buf = io.BytesIO()
    # optimize=True buys ~17% bytes for ~1ms; worth it on a slow uplink.
    img.save(buf, format="JPEG", quality=int(quality), optimize=True)
    return buf.getvalue(), img.size[0], img.size[1], device_w, device_h


class FrameBroker:
    """Single-producer / many-consumer live frame cache.

    * Starts capturing when the first consumer subscribes.
    * Stops after ``idle_stop`` seconds with no consumers (no ADB churn when
      nobody is watching).
    * ``nudge()`` short-circuits the inter-frame sleep so a tap is reflected on
      screen as fast as ADB physically allows (~350-400ms).
    """

    def __init__(
        self,
        adb: "AdbClient",
        *,
        quality: int = STREAM_QUALITY,
        max_width: int = STREAM_MAX_WIDTH,
        interval_ms: int = STREAM_INTERVAL_MS,
        idle_stop: float = STREAM_IDLE_STOP_S,
    ) -> None:
        self.adb = adb
        self.quality = quality
        self.max_width = max_width
        self.interval = max(0.05, interval_ms / 1000.0)
        self.idle_stop = idle_stop

        self._frame: Optional[Frame] = None
        self._version = 0
        self._cond = asyncio.Condition()
        self._nudge = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._subscribers = 0
        self._peak_subscribers = 0
        self._frames_produced = 0
        self._errors = 0
        self._last_error: Optional[str] = None
        self._last_capture_ms = 0.0
        self._last_encode_ms = 0.0
        # Strong refs for fire-and-forget nudge tasks (asyncio may GC otherwise)
        self._pending: set[asyncio.Task] = set()
        # In-flight capture, so an input can abandon a frame that is already
        # known-stale instead of waiting ~330ms for it to finish.
        self._capture_task: Optional[asyncio.Task] = None
        self._capture_started: float = 0.0
        self._last_abort: float = 0.0
        self._aborted = 0
        self._abort_requested = False
        self._stopping = False
        self._restarts = 0

    # ---- lifecycle -------------------------------------------------------
    @property
    def subscribers(self) -> int:
        return self._subscribers

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def _ensure_task(self) -> None:
        if self._stopping:
            return
        if not self.running:
            self._task = asyncio.create_task(self._produce(), name="frame-producer")

    # A capture younger than this still has most of its ~330ms round-trip left,
    # so throwing it away and restarting is a net latency win.
    ABORT_IF_YOUNGER_THAN = 0.18
    ABORT_COOLDOWN = 0.8

    def nudge(self) -> None:
        """Ask the producer to capture right now instead of finishing its sleep.

        If a capture is in flight but only just started, it necessarily predates
        the caller's input — abandon it so the next capture (the one that will
        actually show the result) starts immediately.
        """
        self._ensure_task()
        self._nudge.set()
        task = self._capture_task
        if task is None or task.done():
            return
        try:
            now = asyncio.get_running_loop().time()
        except RuntimeError:
            return
        age = now - self._capture_started
        if age < self.ABORT_IF_YOUNGER_THAN and (now - self._last_abort) > self.ABORT_COOLDOWN:
            self._last_abort = now
            self._aborted += 1
            self._abort_requested = True
            task.cancel()

    def nudge_soon(self, delays: tuple[float, ...] = (0.05, 0.35, 0.90)) -> None:
        """Nudge now plus a couple of follow-ups so animations settle on screen."""
        self.nudge()

        async def _later() -> None:
            for d in delays[1:]:
                await asyncio.sleep(d)
                self.nudge()

        with contextlib.suppress(RuntimeError):
            t = asyncio.create_task(_later(), name="frame-nudge")
            self._pending.add(t)
            t.add_done_callback(self._pending.discard)

    @contextlib.asynccontextmanager
    async def subscribe(self):
        """Register a live consumer for as long as the context is open."""
        self._subscribers += 1
        self._peak_subscribers = max(self._peak_subscribers, self._subscribers)
        self._ensure_task()
        self.nudge()
        try:
            yield self
        finally:
            self._subscribers -= 1

    async def aclose(self) -> None:
        self._stopping = True
        task = self._task
        self._task = None
        cap = self._capture_task
        if cap and not cap.done():
            cap.cancel()
        if task and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    # ---- producer --------------------------------------------------------
    async def _sleep_or_nudge(self, timeout: float) -> None:
        if timeout <= 0:
            self._nudge.clear()
            return
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._nudge.wait(), timeout)
        self._nudge.clear()

    async def _produce(self) -> None:
        loop = asyncio.get_running_loop()
        idle_since: Optional[float] = None
        try:
            while not self._stopping:
                if self._subscribers <= 0:
                    now = loop.time()
                    if idle_since is None:
                        idle_since = now
                    elif now - idle_since > self.idle_stop:
                        return  # nobody watching: release the ADB serial
                    await self._sleep_or_nudge(0.25)
                    continue
                idle_since = None

                t0 = loop.time()
                try:
                    self._capture_started = t0
                    self._capture_task = asyncio.create_task(
                        self.adb._screencap_png(timeout=20), name="screencap"
                    )
                    try:
                        png = await self._capture_task
                    except asyncio.CancelledError:
                        # Distinguish "we abandoned a stale frame" from "the whole
                        # producer is being shut down" — only the former resumes.
                        if not self._abort_requested:
                            raise
                        self._abort_requested = False
                        self._nudge.clear()
                        continue
                    finally:
                        self._capture_task = None
                    t1 = loop.time()
                    jpeg, iw, ih, dw, dh = await loop.run_in_executor(
                        None, _encode_jpeg, png, self.quality, self.max_width
                    )
                    t2 = loop.time()
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self._errors += 1
                    self._last_error = f"{type(e).__name__}: {e}"
                    await self._sleep_or_nudge(1.0)
                    continue

                self._last_capture_ms = (t1 - t0) * 1000.0
                self._last_encode_ms = (t2 - t1) * 1000.0
                self.adb._remember_size(dw, dh)
                await self._publish(
                    Frame(
                        version=self._version + 1,
                        ts=time.time(),
                        jpeg=jpeg,
                        png=png,
                        image_width=iw,
                        image_height=ih,
                        device_width=dw,
                        device_height=dh,
                        capture_ms=self._last_capture_ms,
                        encode_ms=self._last_encode_ms,
                    )
                )
                await self._sleep_or_nudge(self.interval - (t2 - t0))
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — never leave viewers stranded
            self._errors += 1
            self._last_error = f"producer_crash:{type(e).__name__}: {e}"
        finally:
            self._task = None
            # P0: auto-restart whenever viewers are still attached.
            if not self._stopping and self._subscribers > 0:
                self._restarts += 1
                self._task = asyncio.create_task(self._produce(), name="frame-producer")

    async def _publish(self, frame: Frame) -> None:
        async with self._cond:
            self._version = frame.version
            self._frame = frame
            self._frames_produced += 1
            self._cond.notify_all()

    # ---- consumers -------------------------------------------------------
    @property
    def latest(self) -> Optional[Frame]:
        return self._frame

    async def next_frame(self, after_version: int = 0, timeout: float = 12.0) -> Optional[Frame]:
        """Await a frame newer than ``after_version`` (None on timeout)."""
        self._ensure_task()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        async with self._cond:
            while self._frame is None or self._frame.version <= after_version:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return None
                try:
                    await asyncio.wait_for(self._cond.wait(), remaining)
                except asyncio.TimeoutError:
                    return None
            return self._frame

    async def current_frame(self, *, max_age: float = 1.0, timeout: float = 12.0) -> Frame:
        """Latest frame if fresh enough, otherwise wait for the next capture."""
        async with self.subscribe():
            frame = self._frame
            if frame is not None and (time.time() - frame.ts) <= max_age:
                return frame
            after = frame.version if frame else 0
            fresh = await self.next_frame(after_version=after, timeout=timeout)
            if fresh is not None:
                return fresh
            if frame is not None:
                return frame
            raise AdbError(self._last_error or "no frame available (device not ready?)")

    def stats(self) -> dict:
        f = self._frame
        return {
            "running": self.running,
            "subscribers": self._subscribers,
            "peak_subscribers": self._peak_subscribers,
            "frames_produced": self._frames_produced,
            "errors": self._errors,
            "aborted_captures": self._aborted,
            "restarts": self._restarts,
            "last_error": self._last_error,
            "quality": self.quality,
            "max_width": self.max_width,
            "interval_ms": round(self.interval * 1000),
            "last_capture_ms": round(self._last_capture_ms),
            "last_encode_ms": round(self._last_encode_ms),
            "frame_age_ms": round((time.time() - f.ts) * 1000) if f else None,
            "frame_bytes": len(f.jpeg) if f else None,
            "device": [f.device_width, f.device_height] if f else None,
        }


class AdbClient:
    def __init__(self, serial: Optional[str] = None, adb_bin: Optional[str] = None):
        self.serial = serial or DEFAULT_SERIAL
        self.adb_bin = adb_bin or ADB_BIN
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self._size_cache: Optional[tuple[int, int]] = None
        self._size_cache_at: float = 0.0
        # Serializes *screen captures* only (one owner of the ADB serial for the
        # heavy 300ms+ screencap). Taps/keys/swipes stay fully concurrent.
        self._capture_lock = asyncio.Lock()
        self._last_connect_at: float = 0.0
        # Two live paths share this client:
        #   frames — JPEG screencap broker (universal fallback, /adb/preview)
        #   h264   — screenrecord H.264 broker (preferred, WebCodecs viewers)
        self.frames = FrameBroker(self)
        self.h264 = H264Broker(self)

    # ---- plumbing --------------------------------------------------------
    def _remember_size(self, w: int, h: int) -> None:
        self._size_cache = (w, h)
        self._size_cache_at = time.time()

    async def _run(self, *args: str, timeout: float = 60.0) -> tuple[int, bytes, bytes]:
        cmd = [self.adb_bin, "-s", self.serial, *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise AdbError(f"adb timed out: {' '.join(args)}")
        except asyncio.CancelledError:
            # Abandoned screencap (see FrameBroker.nudge): don't leak the child.
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            raise
        return proc.returncode or 0, stdout, stderr

    async def ensure_connected(self, force: bool = False) -> str:
        now = time.time()
        # Reconnect at most every 8s unless forced (avoids hammering on every frame)
        if force or (now - self._last_connect_at) > 8.0:
            if ":" in self.serial and not self.serial.startswith("emulator-"):
                hostport = self.serial
                proc = await asyncio.create_subprocess_exec(
                    self.adb_bin, "connect", hostport,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                self._last_connect_at = now
        code, out, err = await self._run("get-state", timeout=15)
        state = out.decode().strip()
        if state != "device":
            # One forced reconnect then retry
            if ":" in self.serial and not self.serial.startswith("emulator-"):
                proc = await asyncio.create_subprocess_exec(
                    self.adb_bin, "connect", self.serial,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                self._last_connect_at = time.time()
                code, out, err = await self._run("get-state", timeout=15)
                state = out.decode().strip()
            if state != "device":
                raise AdbError(f"device not ready: state={state!r} stderr={err.decode().strip()}")
        return state

    def _normalize_png(self, out: bytes) -> bytes:
        if out.startswith(b"\x89PNG\r\n\x1a\n"):
            return out
        if out.startswith(b"\x89PNG\n\x1a\n"):
            return b"\x89PNG\r\n\x1a\n" + out[7:]
        return out

    async def _screencap_png(self, timeout: float = 20.0) -> bytes:
        """Raw device PNG. Serialized: one screencap on the wire at a time."""
        async with self._capture_lock:
            await self.ensure_connected()
            code, out, err = await self._run("exec-out", "screencap", "-p", timeout=timeout)
            if code != 0 or len(out) < 100:
                # reconnect once and retry
                await self.ensure_connected(force=True)
                code, out, err = await self._run("exec-out", "screencap", "-p", timeout=timeout)
        if code != 0 or len(out) < 100:
            raise AdbError(f"screencap failed rc={code} err={err.decode().strip()} bytes={len(out)}")
        return self._normalize_png(out)

    # ---- screenshots -----------------------------------------------------
    def _prune_screenshots(self, keep: int = SCREENSHOT_RETENTION) -> None:
        """Cap demo/ growth. Only touches the screen-*.png we generate."""
        try:
            shots = sorted(
                SCREENSHOT_DIR.glob("screen-2*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for stale in shots[keep:]:
                stale.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    async def screenshot(self, *, save: bool = True) -> dict:
        """Full PNG screenshot. Writes to demo/ only when save=True (pilot/chat).

        Always captures fresh: the agent calls this right after acting, so a
        cached live frame could legitimately predate its own tap.
        """
        out = await self._screencap_png(timeout=45)
        path_str = ""
        if save:
            ts = time.strftime("%Y%m%d-%H%M%S")
            path = SCREENSHOT_DIR / f"screen-{ts}.png"
            path.write_bytes(out)
            path_str = str(path)
            self._prune_screenshots()
        b64 = base64.b64encode(out).decode("ascii")
        return {
            "ok": True,
            "path": path_str,
            "bytes": len(out),
            "mime": "image/png",
            "base64": b64,
        }

    async def preview_jpeg(
        self,
        *,
        quality: int = 55,
        max_width: int = 540,
        max_age: float = 1.0,
    ) -> dict:
        """Fast JPEG preview served from the shared frame cache — no disk write.

        When the caller wants the stream's own quality/width we hand back the
        already-encoded bytes (zero work). Otherwise we re-encode from the
        cached PNG, which is ~50ms and still costs no ADB round-trip.
        """
        frame = await self.frames.current_frame(max_age=max_age)
        if quality == self.frames.quality and max_width == self.frames.max_width:
            data, iw, ih = frame.jpeg, frame.image_width, frame.image_height
        else:
            loop = asyncio.get_running_loop()
            data, iw, ih, _dw, _dh = await loop.run_in_executor(
                None, _encode_jpeg, frame.png, quality, max_width
            )
        return {
            "ok": True,
            "bytes": data,
            "mime": "image/jpeg",
            "size": len(data),
            "version": frame.version,
            "age_ms": round((time.time() - frame.ts) * 1000),
            "image_width": iw,
            "image_height": ih,
            "device_width": frame.device_width,
            "device_height": frame.device_height,
            "base64": base64.b64encode(data).decode("ascii"),
        }

    # ---- input -----------------------------------------------------------
    async def tap(self, x: int, y: int) -> dict:
        await self.ensure_connected()
        code, out, err = await self._run("shell", "input", "tap", str(int(x)), str(int(y)))
        if code != 0:
            raise AdbError(err.decode().strip() or "tap failed")
        self.frames.nudge_soon()
        return {"ok": True, "action": "tap", "x": int(x), "y": int(y)}

    @staticmethod
    def _safe_download_name(filename: str) -> str:
        """Return a portable basename; never let a browser choose an ADB path."""
        name = Path(filename or "dropped-file").name
        name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
        if not name:
            name = "dropped-file"
        return name[:120]

    async def push_file(self, local_path: str, filename: str) -> dict:
        """Push one bounded host upload into the device Downloads directory.

        Collision handling happens on-device and never overwrites an existing
        file.  The caller owns the temporary host file and removes it after
        this method returns.
        """
        await self.ensure_connected()
        safe = self._safe_download_name(filename)
        stem, suffix = Path(safe).stem, Path(safe).suffix
        await self._run("shell", "mkdir", "-p", "/sdcard/Download")
        remote = f"/sdcard/Download/{safe}"
        for index in range(1, 100):
            code, _out, _err = await self._run("shell", "test", "-e", remote)
            if code != 0:
                break
            remote = f"/sdcard/Download/{stem} ({index}){suffix}"
        else:
            raise AdbError("Downloads is full of similarly named files")
        code, _out, err = await self._run("push", local_path, remote, timeout=120)
        if code != 0:
            raise AdbError(err.decode(errors="replace").strip() or "file push failed")
        self.frames.nudge_soon()
        return {
            "ok": True,
            "action": "push",
            "name": Path(remote).name,
            "path": remote,
        }

    async def _clipboard_bridge_installed(self) -> bool:
        code, _out, _err = await self._run("shell", "pm", "path", "com.zevi.agent", timeout=15)
        return code == 0

    async def clipboard_set(self, text: str, *, paste: bool = False) -> dict:
        """Set the Android clipboard through the Strlix ADB bridge when present.

        Android 10+ does not expose a stable `adb shell` clipboard command.
        The debug Strlix agent therefore owns a tiny explicit receiver.  ADB
        input text remains the endpoint-level fallback for focused fields.
        """
        await self.ensure_connected()
        if not await self._clipboard_bridge_installed():
            raise AdbError("device clipboard bridge unavailable; install the Strlix agent")
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        code, _out, err = await self._run(
            "shell", "am", "broadcast", "--user", "current",
            "-n", "com.zevi.agent/.ClipboardBridgeReceiver",
            "-a", "com.zevi.agent.CLIPBOARD_SET",
            "--es", "text_b64", encoded, timeout=20,
        )
        if code != 0:
            raise AdbError(err.decode(errors="replace").strip() or "clipboard set failed")
        pasted = False
        if paste:
            await self.key("PASTE")
            pasted = True
        self.frames.nudge_soon()
        return {"ok": True, "action": "clipboard_set", "chars": len(text), "pasted": pasted}

    async def clipboard_get(self) -> dict:
        """Read the device clipboard via the debug agent's private export file.

        Android 10+ only allows ordinary apps to read clipboard contents while
        the app is foreground (or is a privileged IME/device owner). Refuse to
        return an empty value when that privacy gate is active.
        """
        await self.ensure_connected()
        code, out, _err = await self._run("shell", "dumpsys", "activity", "activities", timeout=15)
        foreground = re.search(r"topResumedActivity=.*com\.zevi\.agent/", out.decode(errors="replace"))
        if code != 0 or not foreground:
            raise AdbError("Android only permits clipboard read while Strlix is foreground")
        if not await self._clipboard_bridge_installed():
            raise AdbError("device clipboard bridge unavailable; install the Strlix agent")
        code, _out, err = await self._run(
            "shell", "am", "broadcast", "--user", "current",
            "-n", "com.zevi.agent/.ClipboardBridgeReceiver",
            "-a", "com.zevi.agent.CLIPBOARD_EXPORT", timeout=20,
        )
        if code != 0:
            raise AdbError(err.decode(errors="replace").strip() or "clipboard export failed")
        code, out, err = await self._run(
            "shell", "run-as", "com.zevi.agent", "cat", "files/.strlix-clipboard.b64", timeout=20,
        )
        # Best effort cleanup: clipboard contents should not persist in the app
        # sandbox longer than one bridge read.
        await self._run("shell", "run-as", "com.zevi.agent", "rm", "files/.strlix-clipboard.b64", timeout=20)
        if code != 0:
            raise AdbError(err.decode(errors="replace").strip() or "clipboard read unavailable")
        try:
            text = base64.b64decode(out.strip(), validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise AdbError("device clipboard returned invalid data") from exc
        return {"ok": True, "action": "clipboard_get", "text": text, "chars": len(text)}

    async def type_text(self, text: str) -> dict:
        await self.ensure_connected()
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        code, out, err = await self._run("shell", "input", "text", escaped)
        if code != 0:
            raise AdbError(err.decode().strip() or "type failed")
        self.frames.nudge_soon()
        return {"ok": True, "action": "type", "text": text}

    async def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> dict:
        await self.ensure_connected()
        code, out, err = await self._run(
            "shell", "input", "swipe",
            str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duration_ms)),
        )
        if code != 0:
            raise AdbError(err.decode().strip() or "swipe failed")
        self.frames.nudge_soon()
        return {
            "ok": True,
            "action": "swipe",
            "x1": int(x1),
            "y1": int(y1),
            "x2": int(x2),
            "y2": int(y2),
            "duration_ms": int(duration_ms),
        }

    async def key(self, keycode: str | int) -> dict:
        await self.ensure_connected()
        mapping = {
            "HOME": "3", "BACK": "4", "ENTER": "66", "DEL": "67",
            "APP_SWITCH": "187", "RECENTS": "187", "POWER": "26", "TAB": "61", "PASTE": "279",
            "MENU": "82", "VOLUME_UP": "24", "VOLUME_DOWN": "25",
            "SEARCH": "84", "NOTIFICATION": "83",
        }
        kc = str(keycode)
        kc = mapping.get(kc.upper(), kc)
        code, out, err = await self._run("shell", "input", "keyevent", kc)
        if code != 0:
            raise AdbError(err.decode().strip() or "key failed")
        self.frames.nudge_soon()
        return {"ok": True, "action": "key", "keycode": kc}

    async def shell(self, command: str) -> dict:
        await self.ensure_connected()
        code, out, err = await self._run("shell", command, timeout=60)
        return {
            "ok": code == 0,
            "rc": code,
            "stdout": out.decode(errors="replace")[:4000],
            "stderr": err.decode(errors="replace")[:1000],
        }

    async def wm_size(self) -> dict:
        if self._size_cache and (time.time() - self._size_cache_at) < 60:
            w, h = self._size_cache
            return {"ok": True, "width": w, "height": h, "cached": True}
        r = await self.shell("wm size")
        # Physical size: 1080x2400
        text = (r.get("stdout") or "") + "\n" + (r.get("stderr") or "")
        w = h = None
        for line in text.splitlines():
            if "Physical size:" in line or "Override size:" in line:
                try:
                    part = line.split(":")[-1].strip()
                    w_s, h_s = part.split("x")
                    w, h = int(w_s), int(h_s)
                    if "Override" in line:
                        break
                except Exception:  # noqa: BLE001
                    pass
        if w and h:
            self._remember_size(w, h)
            return {"ok": True, "width": w, "height": h, "raw": text.strip()}
        return {"ok": False, "raw": text.strip()}
