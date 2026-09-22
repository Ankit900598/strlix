"""Device audio → browser speakers.

The H.264 socket is video-only (``audio=false`` / ``screenrecord``). This
module opens a *second* scrcpy-server with ``video=false audio=true`` and
forwards Opus packets on ``/ws/audio``. The viewer decodes them with
WebCodecs ``AudioDecoder`` and plays them on an ``AudioContext``, so YouTube
(or any app) on the cloud phone comes out of the user's phone or PC speakers.

What this is not
----------------
* It does not mux audio into the H.264 elementary stream.
* It cannot invent audio if the emulator was started with ``-no-audio``
  (no guest audio HAL → scrcpy exits). ``scripts/start-emulator-on-vm.sh``
  no longer passes that flag. A process that is already running stays silent
  until it is restarted without ``-no-audio``.
* Optional host fallback: set ``STRLIX_AUDIO_PULSE`` to a Pulse source (or
  ``default``) and this broker shells out to ``ffmpeg`` for s16le PCM when
  scrcpy audio cannot start.

Wire format (binary), little-endian, 16 bytes + payload — same layout as
``/ws/h264`` so the viewer can share the header parse:

    u8 version (1) | u8 flags (bit0 = codec config, bit1 = resync) | u16 reserved
    u32 seq | f64 pts_us | payload

Text JSON: ``hello``, ``audio`` (status), ``ping``.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import struct
import time
from typing import TYPE_CHECKING, Optional

from .scrcpy_source import AUDIO_CODEC_OPTIONS, SCRCPY_SERVER_PATH, ScrcpyError, ScrcpyRawSession
from .smoothness import FLAG_CONFIG, FLAG_RESYNC, JITTER_MIN_MS, prepare_audio_packet

if TYPE_CHECKING:  # pragma: no cover
    from .adb_client import AdbClient

# scrcpy 4.1 AudioCodec ids (big-endian fourcc). AAC and raw are
# 0x00 + three letters, not a trailing space. The spaced variants are
# accepted so an older jar still maps.
CODEC_OPUS = 0x6F707573  # "opus"
CODEC_AAC = 0x00616163  # "\0aac"
CODEC_FLAC = 0x666C6163  # "flac"
CODEC_PCM = 0x00726177  # "\0raw"
CODEC_NAMES = {
    CODEC_OPUS: "opus",
    CODEC_AAC: "aac",
    0x61616320: "aac",
    CODEC_FLAC: "flac",
    CODEC_PCM: "pcm",
    0x72617720: "pcm",
}

SCRCPY_FLAG_CONFIG = 1 << 63
SCRCPY_FLAG_KEY = 1 << 62
SCRCPY_PTS_MASK = SCRCPY_FLAG_KEY - 1

AUDIO_HEADER = struct.Struct("<BBHId")
AUDIO_WIRE_VERSION = 1
OPUS_HEAD_MAGIC = b"OpusHead"
OPUS_TAGS_MAGIC = b"OpusTags"

DEVICE_AUDIO = os.environ.get("DEVICE_AUDIO", "1") not in ("0", "false", "no")
AUDIO_BITRATE = int(os.environ.get("DEVICE_AUDIO_BITRATE", "160000"))
AUDIO_MAX_CLIENTS = int(os.environ.get("DEVICE_AUDIO_MAX_CLIENTS", "8"))
PULSE_SOURCE = os.environ.get("STRLIX_AUDIO_PULSE", "").strip()


def parse_codec_id(header: bytes) -> str:
    """Map the first 4 bytes of a scrcpy audio socket to a codec name."""
    if len(header) < 4:
        raise ValueError("short codec header")
    codec_id = int.from_bytes(header[:4], "big")
    name = CODEC_NAMES.get(codec_id)
    if not name:
        raise ValueError(f"unknown scrcpy audio codec 0x{codec_id:08x}")
    return name


def split_scrcpy_audio_packets(buf: bytes) -> tuple[list[tuple[int, int, bytes]], bytes]:
    """Pull complete scrcpy audio packets out of ``buf``.

    Each packet is big-endian ``u64 pts+flags`` + ``u32 size`` + payload.
    Returns ``(packets, leftover)``. A packet is ``(wire_flags, pts_us, payload)``.
    """
    packets: list[tuple[int, int, bytes]] = []
    offset = 0
    limit = len(buf)
    while offset + 12 <= limit:
        pts_flags = int.from_bytes(buf[offset : offset + 8], "big")
        size = int.from_bytes(buf[offset + 8 : offset + 12], "big")
        if size < 0 or size > 1_000_000:
            raise ValueError(f"audio packet size {size} is not usable")
        if offset + 12 + size > limit:
            break
        payload = buf[offset + 12 : offset + 12 + size]
        flags = FLAG_CONFIG if (pts_flags & SCRCPY_FLAG_CONFIG) else 0
        pts = pts_flags & SCRCPY_PTS_MASK
        # Live OpusHead arrives with bit 63 clear. WebCodecs must not decode it.
        if payload.startswith(OPUS_HEAD_MAGIC) or payload.startswith(OPUS_TAGS_MAGIC):
            flags |= FLAG_CONFIG
            pts = 0
        packets.append((flags, pts, payload))
        offset += 12 + size
    return packets, buf[offset:]


def pack_audio(seq: int, flags: int, pts_us: float, payload: bytes) -> bytes:
    return AUDIO_HEADER.pack(AUDIO_WIRE_VERSION, flags & 0xFF, 0, seq & 0xFFFFFFFF, float(pts_us)) + payload


class DeviceAudioBroker:
    """One capture task, many ``/ws/audio`` subscribers. Starts on first listen."""

    def __init__(self, adb: "AdbClient") -> None:
        self.adb = adb
        self.enabled = DEVICE_AUDIO
        self.codec: Optional[str] = None
        self.source = "idle"
        self.reason = "no listeners yet"
        self.packets = 0
        self.bytes = 0
        self.subscribers = 0
        self._peak = 0
        self._queues: set[asyncio.Queue] = set()
        self._task: Optional[asyncio.Task] = None
        self._stopping = False
        self._seq = 0
        self.started_at: Optional[float] = None
        self.last_packet_at: Optional[float] = None
        # Last OpusHead wire packet, replayed to subscribers who missed it.
        self._config_wire: Optional[bytes] = None
        self._prev_pts: Optional[int] = None

    def stats(self) -> dict:
        age = None
        if self.last_packet_at:
            age = round((time.time() - self.last_packet_at) * 1000)
        return {
            "enabled": self.enabled,
            "available": self.codec is not None and self.source not in ("idle", "error"),
            "source": self.source,
            "codec": self.codec,
            "reason": self.reason,
            "packets": self.packets,
            "bytes": self.bytes,
            "subscribers": self.subscribers,
            "peak_subscribers": self._peak,
            "max_clients": AUDIO_MAX_CLIENTS,
            "packet_age_ms": age,
            "emulator_audio": "requires a process started without -no-audio",
            "playback": "browser AudioContext via /ws/audio",
            "jitter_ms": JITTER_MIN_MS,
            "fec": "jitter + one-packet concealment; MediaCodec Opus has no portable in-band FEC key",
        }

    def _ensure(self) -> None:
        if self._stopping or not self.enabled:
            return
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(), name="device-audio")

    @contextlib.asynccontextmanager
    async def subscribe(self):
        if not self.enabled:
            raise RuntimeError("device audio disabled (DEVICE_AUDIO=0)")
        if self.subscribers >= AUDIO_MAX_CLIENTS:
            raise RuntimeError(f"audio at capacity ({AUDIO_MAX_CLIENTS})")
        q: asyncio.Queue = asyncio.Queue(maxsize=48)
        self._queues.add(q)
        self.subscribers += 1
        self._peak = max(self._peak, self.subscribers)
        if self._config_wire is not None:
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(self._config_wire)
        self._ensure()
        try:
            yield q
        finally:
            self._queues.discard(q)
            self.subscribers = max(0, self.subscribers - 1)

    def _publish(self, payload: bytes) -> None:
        self.packets += 1
        self.bytes += len(payload)
        self.last_packet_at = time.time()
        dead: list[asyncio.Queue] = []
        for q in self._queues:
            if q.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    q.get_nowait()
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._queues.discard(q)

    def _status(self, **extra: object) -> None:
        # Status is JSON text; binary messages are media. Viewers ignore text
        # they don't understand, so a dict on the queue is fine.
        note = {"type": "audio", "source": self.source, "codec": self.codec, "reason": self.reason, **extra}
        for q in list(self._queues):
            if q.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    q.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(note)

    async def _run(self) -> None:
        while not self._stopping and self.subscribers > 0 and self.enabled:
            try:
                if await self._capture_scrcpy():
                    continue
            except Exception as exc:  # noqa: BLE001
                self.source = "error"
                self.codec = None
                self.reason = f"scrcpy audio: {type(exc).__name__}: {exc}"[:300]
                self._status()
            if PULSE_SOURCE and self.subscribers > 0:
                try:
                    if await self._capture_pulse():
                        continue
                except Exception as exc:  # noqa: BLE001
                    self.reason = f"pulse fallback: {type(exc).__name__}: {exc}"[:300]
                    self._status()
            if self.subscribers <= 0 or self._stopping:
                break
            self.source = "error"
            if self.reason.startswith("no listeners"):
                self.reason = (
                    "no device audio. Restart the emulator without -no-audio "
                    "(scripts/start-emulator-on-vm.sh). Optional: STRLIX_AUDIO_PULSE."
                )
            self._status()
            await asyncio.sleep(8.0)
        self._task = None
        if self.subscribers <= 0:
            self.source = "idle"
            self.reason = "no listeners yet"

    async def _capture_scrcpy(self) -> bool:
        if not os.path.isfile(SCRCPY_SERVER_PATH):
            self.source = "error"
            self.reason = f"scrcpy-server missing at {SCRCPY_SERVER_PATH}"
            self._status()
            return False
        self.source = "starting"
        self.reason = "opening scrcpy audio socket"
        self._status()
        session = ScrcpyRawSession(
            self.adb,
            max_size=64,
            bitrate=AUDIO_BITRATE,
            kind="audio",
            audio_codec_options=AUDIO_CODEC_OPTIONS,
        )
        self._prev_pts = None
        try:
            reader = await session.start()
        except ScrcpyError as exc:
            self.source = "error"
            self.codec = None
            self.reason = str(exc)[:300]
            self._status()
            return False
        self.started_at = time.time()
        try:
            # tunnel_forward always prefixes one dummy byte before the codec id
            # (even with send_device_meta=false). Video raw_stream skips this;
            # audio must consume it or we parse "\x00sdk..." as a fake fourcc.
            await self._read_exact(reader, 1, timeout=8.0)
            header = await self._read_exact(reader, 4, timeout=8.0)
            self.codec = parse_codec_id(header)
            if self.codec != "opus":
                self.reason = f"scrcpy offered {self.codec}; viewer plays opus (or PCM fallback)"
            else:
                self.reason = "opus from scrcpy — browser plays it on user speakers"
            self.source = "scrcpy"
            self._status(codec=self.codec)
            buf = b""
            while not self._stopping and self.subscribers > 0:
                try:
                    chunk = await asyncio.wait_for(reader.read(4096), 5.0)
                except asyncio.TimeoutError:
                    continue
                if not chunk:
                    self.reason = "scrcpy audio socket closed"
                    self.source = "error"
                    self.codec = None
                    self._status()
                    return False
                buf += chunk
                packets, buf = split_scrcpy_audio_packets(buf)
                for flags, pts, payload in packets:
                    prepared = prepare_audio_packet(flags, pts, payload)
                    if prepared is None:
                        continue
                    flags, pts, payload = prepared
                    if not (flags & FLAG_CONFIG) and self._prev_pts is not None:
                        delta = pts - self._prev_pts
                        # A backwards clock or a hole longer than half a second
                        # is a new timeline. Tell the viewer to drop its buffer
                        # instead of playing the hole as silence-then-catchup.
                        if delta < -100_000 or delta > 500_000:
                            flags |= FLAG_RESYNC
                    if not (flags & FLAG_CONFIG):
                        self._prev_pts = pts
                    self._seq = (self._seq + 1) & 0xFFFFFFFF
                    wire = pack_audio(self._seq, flags, float(pts), payload)
                    if flags & FLAG_CONFIG:
                        self._config_wire = wire
                    self._publish(wire)
            return True
        finally:
            await session.stop()

    async def _capture_pulse(self) -> bool:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.reason = "STRLIX_AUDIO_PULSE is set but ffmpeg is not installed"
            self.source = "error"
            self._status()
            return False
        self.source = "pulse"
        self.codec = "pcm"
        self.reason = f"PCM from Pulse source {PULSE_SOURCE}"
        self._status(sample_rate=48000, channels=2)
        proc = await asyncio.create_subprocess_exec(
            ffmpeg,
            "-hide_banner", "-loglevel", "error",
            "-f", "pulse", "-i", PULSE_SOURCE,
            "-ac", "2", "-ar", "48000",
            "-f", "s16le", "pipe:1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            assert proc.stdout is not None
            while not self._stopping and self.subscribers > 0:
                chunk = await proc.stdout.read(3840)  # 20ms stereo s16le @ 48k
                if not chunk:
                    self.reason = "ffmpeg pulse capture ended"
                    self.source = "error"
                    self.codec = None
                    self._status()
                    return False
                self._seq = (self._seq + 1) & 0xFFFFFFFF
                self._publish(pack_audio(self._seq, 0, time.time() * 1_000_000, chunk))
            return True
        finally:
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                with contextlib.suppress(Exception):
                    await proc.wait()

    @staticmethod
    async def _read_exact(reader, n: int, timeout: float) -> bytes:
        buf = b""
        deadline = time.time() + timeout
        while len(buf) < n:
            remain = deadline - time.time()
            if remain <= 0:
                raise TimeoutError("timed out waiting for audio codec header")
            chunk = await asyncio.wait_for(reader.read(n - len(buf)), remain)
            if not chunk:
                raise EOFError("audio socket closed before codec header")
            buf += chunk
        return buf
