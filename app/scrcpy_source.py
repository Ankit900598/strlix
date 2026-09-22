"""scrcpy-server raw Annex-B H.264 over ADB forward (no SDL / no scrcpy UI).

Full scrcpy / ws-scrcpy still needs SDL + XDG on this box. The *server jar*
alone can emit a raw H.264 elementary stream when started with
``raw_stream=true tunnel_forward=true`` (see Genymobile scrcpy ``develop.md``).
That stream is byte-compatible with the existing ``/ws/h264`` Annex-B parser.

Lifecycle per segment
---------------------
1. ``adb push`` scrcpy-server (cached if unchanged)
2. ``adb forward tcp:<port> localabstract:scrcpy_<scid>`` (ephemeral port)
3. ``app_process … Server <ver> raw_stream=true …`` on device
4. TCP connect → read Annex-B until restart/stop
5. kill server + remove forward

Keyframe = kill + respawn (MediaCodec on the emulator ignores
``i-frame-interval``; same restart strategy as screenrecord).
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import secrets
import socket
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from .adb_client import AdbClient

def default_scrcpy_server_path() -> str:
    """Prefer the portable VM path, then the dev-box path."""
    env = os.environ.get("SCRCPY_SERVER_PATH", "").strip()
    if env:
        return env
    for path in (
        "/opt/strlix/scrcpy-server",
        "/home/box/.local/scrcpy/scrcpy-server",
        "/usr/local/share/scrcpy/scrcpy-server",
    ):
        if os.path.isfile(path):
            return path
    return "/opt/strlix/scrcpy-server"


def codec_options() -> str:
    """Low-latency MediaCodec extras. ``priority:int=0`` is realtime."""
    raw = os.environ.get(
        "SCRCPY_CODEC_OPTIONS", "i-frame-interval:int=1,latency:int=1"
    ).strip().strip(",")
    if "priority:" not in raw:
        raw = (raw + ",priority:int=0") if raw else "priority:int=0"
    return raw


def encoder_fps(serial: str, requested: int) -> tuple[int, str]:
    """Swiftshader emulators corrupt or stall when asked for 60–90 fps.

    The encoder misses deadlines, the browser then drops P-frames, and the
    picture turns into macroblocks. GPU / Redroid serials keep the request.
    """
    if serial.startswith("emulator-") and requested > 30:
        return 30, f"emulator fps clamped {requested}→30"
    return requested, ""


def encoder_bitrate(serial: str, requested: int) -> tuple[int, str]:
    """Cap emulator bitrate so one IDR cannot flood a phone decoder.

    1.8 Mbps at 486×1080 is enough for YouTube-in-a-phone. Higher targets on
    swiftshader show up as queue growth and broken reference frames, not as
    extra detail. GPU serials keep the request.
    """
    if serial.startswith("emulator-") and requested > 1_800_000:
        return 1_800_000, f"emulator bitrate clamped {requested}→1800000"
    return requested, ""


SCRCPY_SERVER_PATH = default_scrcpy_server_path()
SCRCPY_VERSION = os.environ.get("SCRCPY_VERSION", "4.1")
# 0 = ask adb to allocate an ephemeral local TCP port (preferred).
SCRCPY_PORT = int(os.environ.get("SCRCPY_PORT", "0"))
# 30 is the soft-launch emulator ceiling. Override on a GPU device.
SCRCPY_MAX_FPS = int(os.environ.get("SCRCPY_MAX_FPS", "30"))
# Cap long edge. 1080 keeps a 1080×2400 phone readable for YouTube.
SCRCPY_MAX_SIZE = int(os.environ.get("SCRCPY_MAX_SIZE", "1080"))
SCRCPY_CODEC_OPTIONS = codec_options()
# Device-side jar path (shell-writable).
_REMOTE_JAR = "/data/local/tmp/scrcpy-server.jar"


def ensure_xdg_runtime_dir() -> str:
    """Stub a writable XDG_RUNTIME_DIR for headless scrcpy *client* attempts.

    The jar path we ship does not need this. Full ``scrcpy`` / ws-scrcpy still
    wants SDL + a real session bus; this only stops the immediate
    "XDG_RUNTIME_DIR is not set" abort so we can measure how far headless gets.
    """
    path = os.environ.get("XDG_RUNTIME_DIR") or f"/tmp/runtime-{os.getuid()}"
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.environ["XDG_RUNTIME_DIR"] = path
    return path


class ScrcpyError(RuntimeError):
    pass


class ScrcpyRawSession:
    """One scrcpy-server segment exposing an asyncio StreamReader of Annex-B."""

    def __init__(
        self,
        adb: "AdbClient",
        *,
        max_size: int,
        bitrate: int,
        max_fps: int = SCRCPY_MAX_FPS,
        port: int = SCRCPY_PORT,
        server_path: str = SCRCPY_SERVER_PATH,
        version: str = SCRCPY_VERSION,
        codec_options: str = SCRCPY_CODEC_OPTIONS,
        scid: Optional[str] = None,
    ) -> None:
        self.adb = adb
        self.max_size = max(64, int(max_size))
        self.bitrate = int(bitrate)
        self.max_fps = max(1, int(max_fps))
        self.port = int(port)
        self.server_path = server_path
        self.version = version
        self.codec_options = (codec_options or "").strip()
        # scid is parsed as hex and must fit in 31 bits; socket is scrcpy_%08x.
        self.scid = scid or f"{secrets.randbits(31):08x}"
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._server_proc: Optional[asyncio.subprocess.Process] = None
        self._pushed = False
        self.started_at = 0.0
        self.ttfb_ms: Optional[float] = None
        self._stopped = False
        self._abstract = f"localabstract:scrcpy_{self.scid}"

    async def start(self) -> asyncio.StreamReader:
        if not os.path.isfile(self.server_path):
            raise ScrcpyError(f"scrcpy-server missing: {self.server_path}")
        await self._push_server()
        await self._forward()
        await self._kill_remote()
        await self._spawn_server()
        reader = await self._connect()
        self.reader = reader
        self.started_at = time.time()
        return reader

    async def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self.writer is not None:
            self.writer.close()
            with contextlib.suppress(Exception):
                await self.writer.wait_closed()
        self.writer = None
        self.reader = None
        proc = self._server_proc
        self._server_proc = None
        if proc is not None and proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(proc.wait(), 2.0)
        await self._kill_remote()
        await self._unforward()

    async def _adb(self, *args: str, timeout: float = 8.0) -> tuple[int, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            self.adb.adb_bin, "-s", self.adb.serial, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout)
        except asyncio.TimeoutError as e:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            raise ScrcpyError(f"adb {' '.join(args)} timed out") from e
        return proc.returncode or 0, out, err

    async def _push_server(self) -> None:
        rc, out, _ = await self._adb("shell", f"stat -c %s {_REMOTE_JAR} 2>/dev/null || echo 0")
        remote_size = 0
        with contextlib.suppress(Exception):
            remote_size = int((out or b"0").decode().strip().splitlines()[-1] or "0")
        local_size = os.path.getsize(self.server_path)
        if remote_size == local_size and remote_size > 0:
            self._pushed = True
            return
        rc, _, err = await self._adb("push", self.server_path, _REMOTE_JAR, timeout=30.0)
        if rc != 0:
            raise ScrcpyError(f"adb push failed: {err.decode(errors='replace')[:200]}")
        self._pushed = True

    async def _forward(self) -> None:
        """Install ``adb forward``. Port 0 → kernel-chosen local TCP port."""
        if self.port > 0:
            await self._adb("forward", "--remove", f"tcp:{self.port}")
            spec = f"tcp:{self.port}"
        else:
            spec = "tcp:0"
        rc, out, err = await self._adb("forward", spec, self._abstract)
        if rc != 0:
            raise ScrcpyError(f"adb forward failed: {err.decode(errors='replace')[:200]}")
        if self.port <= 0:
            # adb prints the allocated port on stdout when tcp:0 is requested.
            text = (out or b"").decode().strip().splitlines()
            if not text:
                raise ScrcpyError("adb forward tcp:0 returned no port")
            try:
                self.port = int(text[-1].strip())
            except ValueError as e:
                raise ScrcpyError(f"adb forward tcp:0 opaque: {text[-1]!r}") from e

    async def _unforward(self) -> None:
        if self.port > 0:
            await self._adb("forward", "--remove", f"tcp:{self.port}")

    async def _kill_remote(self) -> None:
        # Prefer our scid so we do not kill a sibling broker's server.
        await self._adb("shell", f"pkill -f 'scid={self.scid}' || true")

    async def _spawn_server(self) -> None:
        # raw_stream disables dummy byte + device/frame meta → pure Annex-B.
        opts = (
            f"scid={self.scid} tunnel_forward=true audio=false control=false "
            f"cleanup=false raw_stream=true max_size={self.max_size} "
            f"video_bit_rate={self.bitrate} max_fps={self.max_fps}"
        )
        if self.codec_options:
            # Commas inside the value are part of the option list; no spaces.
            opts += f" video_codec_options={self.codec_options}"
        args = (
            f"CLASSPATH={_REMOTE_JAR} app_process / "
            f"com.genymobile.scrcpy.Server {self.version} {opts}"
        )
        self._server_proc = await asyncio.create_subprocess_exec(
            self.adb.adb_bin, "-s", self.adb.serial, "shell", args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert self._server_proc.stdout is not None
        deadline = time.time() + 4.0
        buf = b""
        while time.time() < deadline:
            if self._server_proc.returncode is not None:
                raise ScrcpyError(
                    f"scrcpy-server exited early: {buf.decode(errors='replace')[:300]}"
                )
            try:
                chunk = await asyncio.wait_for(self._server_proc.stdout.read(256), 0.25)
            except asyncio.TimeoutError:
                chunk = b""
            if chunk:
                buf += chunk
                low = buf.lower()
                if b"device:" in low or b"using video encoder" in low:
                    return
                if b"error" in low or b"exception" in low:
                    raise ScrcpyError(buf.decode(errors="replace")[:400])
        # Proceed anyway — connect retries will tell us if listen isn't up.

    async def _connect(self) -> asyncio.StreamReader:
        """Connect and insist on real Annex-B bytes.

        ``adb forward`` accepts TCP even when nothing is listening on the
        device abstract socket; those sockets then EOF immediately. So a
        bare ``open_connection`` success is not enough — we must see a
        start code (or at least some payload) before handing the reader to
        the broker.
        """
        last_err: Optional[BaseException] = None
        t0 = time.time()
        if self._server_proc and self._server_proc.stdout:
            asyncio.create_task(self._drain_server_log(), name="scrcpy-log")
        for _attempt in range(50):
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", self.port), 0.4
                )
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
                last_err = e
                await asyncio.sleep(0.1)
                continue
            try:
                first = await asyncio.wait_for(reader.read(4096), 1.0)
            except asyncio.TimeoutError:
                first = b""
            if not first:
                writer.close()
                with contextlib.suppress(Exception):
                    await writer.wait_closed()
                last_err = ScrcpyError("forward connected but server sent no bytes")
                await asyncio.sleep(0.1)
                continue
            self.writer = writer
            self.ttfb_ms = (time.time() - t0) * 1000.0
            return _PrefixedReader(first, reader)
        raise ScrcpyError(f"TCP connect to scrcpy forward failed: {last_err}")

    async def _drain_server_log(self) -> None:
        proc = self._server_proc
        if proc is None or proc.stdout is None:
            return
        with contextlib.suppress(Exception):
            while True:
                chunk = await proc.stdout.read(512)
                if not chunk:
                    return


class _PrefixedReader:
    """StreamReader-like object that replays peeked bytes then proxies."""

    def __init__(self, prefix: bytes, inner: asyncio.StreamReader) -> None:
        self._prefix = prefix
        self._inner = inner

    async def read(self, n: int = -1) -> bytes:
        if self._prefix:
            if n < 0 or n >= len(self._prefix):
                out, self._prefix = self._prefix, b""
                if n < 0:
                    rest = await self._inner.read(-1)
                    return out + rest
                need = n - len(out)
                if need > 0:
                    out += await self._inner.read(need)
                return out
            out, self._prefix = self._prefix[:n], self._prefix[n:]
            return out
        return await self._inner.read(n)


def scrcpy_available(server_path: str = SCRCPY_SERVER_PATH) -> bool:
    return os.path.isfile(server_path)
