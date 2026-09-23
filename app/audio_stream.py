"""Device playback audio → ``/ws/audio`` Opus packets.

Separate scrcpy-server from the video one (``video=false audio=true``) so the
H.264 socket stays raw Annex-B. Framing lives in :mod:`app.audio_framing`.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import time
from typing import TYPE_CHECKING, Optional

from .audio_framing import (
    AudioPacket,
    Preface,
    extract_opus_head,
    is_opus_head,
    opus_head_info,
    pack_audio,
    parse_preface,
    pop_packets,
)
from .scrcpy_source import (
    SCRCPY_SERVER_PATH,
    ScrcpyError,
    ScrcpyRawSession,
    scrcpy_available,
)

if TYPE_CHECKING:  # pragma: no cover
    from .adb_client import AdbClient

AUDIO_ENABLED = os.environ.get("AUDIO_ENABLED", "1") not in ("0", "false", "no")
AUDIO_BITRATE = int(os.environ.get("AUDIO_BITRATE", "64000"))
AUDIO_MAX_CLIENTS = int(os.environ.get("AUDIO_MAX_CLIENTS", "8"))
_QUEUE_MAX = 48


class AudioError(RuntimeError):
    pass


class AudioSubscriber:
    def __init__(self, name: str) -> None:
        self.name = name
        self.queue: asyncio.Queue[AudioPacket] = asyncio.Queue(maxsize=_QUEUE_MAX)
        self.closed = False
        self.sent = 0
        self.dropped = 0

    def offer(self, packet: AudioPacket) -> None:
        if self.closed:
            return
        if packet.config:
            self._drain_keep_config()
        try:
            self.queue.put_nowait(packet)
        except asyncio.QueueFull:
            self.dropped += 1
            if packet.config:
                with contextlib.suppress(asyncio.QueueFull):
                    self.queue.put_nowait(packet)

    def _drain_keep_config(self) -> None:
        while True:
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                return


class _WireQueue:
    """DeviceAudio-compatible queue view: ``get()`` returns wire bytes.

    ``/ws/audio`` in ``main.py`` expects ``queue.get()`` → ``bytes`` (or a
    status ``dict``). AudioBroker's subscribers hold :class:`AudioPacket`
    objects; this adapter packs them the same way DeviceAudioBroker does.
    """

    def __init__(self, sub: AudioSubscriber, broker: "AudioBroker") -> None:
        self._sub = sub
        self._broker = broker

    async def get(self):
        packet = await self._sub.queue.get()
        return self._broker.wire(packet)


class ScrcpyAudioSession:
    """Audio-only scrcpy socket.

    Delegates to :class:`~app.scrcpy_source.ScrcpyRawSession` (``kind=audio``).

    The previous hand-rolled ``_connect`` returned as soon as ``adb forward``
    accepted TCP. That accept succeeds even when nothing is listening on the
    device abstract socket, so :class:`AudioBroker` sat forever on
    ``opening scrcpy audio socket`` while ``reader.read`` timed out empty.
    ``ScrcpyRawSession`` waits for encoder log lines and insists on real
    bytes before returning — the same path :class:`DeviceAudioBroker` uses.
    """

    def __init__(self, adb: "AdbClient") -> None:
        self.adb = adb
        self._raw: Optional[ScrcpyRawSession] = None

    async def start(self) -> asyncio.StreamReader:
        raw = ScrcpyRawSession(
            self.adb,
            max_size=64,
            bitrate=AUDIO_BITRATE,
            kind="audio",
        )
        self._raw = raw
        return await raw.start()

    async def stop(self) -> None:
        raw = self._raw
        self._raw = None
        if raw is not None:
            await raw.stop()


class AudioBroker:
    def __init__(self, adb: "AdbClient") -> None:
        self.adb = adb
        self.enabled = AUDIO_ENABLED
        self._subs: set[AudioSubscriber] = set()
        self._task: Optional[asyncio.Task] = None
        self._stopping = False
        self._session: Optional[ScrcpyAudioSession] = None
        self._seq = 0
        self._packets = 0
        self._bytes = 0
        self._config_packets = 0
        self._silence_run = 0
        self._last_at = 0.0
        self._started_at = 0.0
        self._errors = 0
        self._last_error: Optional[str] = None
        self._source = "idle"
        self._reason = "no listeners yet"
        self._codec = "opus"
        self._channels = 2
        self._sample_rate = 48000
        self._head: Optional[bytes] = None
        self._preface_note = ""
        self._peak = 0
        self._window: list[float] = []
        self._available = False

    @property
    def subscribers(self) -> int:
        return len(self._subs)

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def hello(self) -> dict:
        return {
            "type": "hello",
            "service": "audio",
            **self.stats(),
        }

    def stats(self) -> dict:
        now = time.time()
        rate = 0.0
        if len(self._window) >= 2:
            span = max(0.2, self._window[-1] - self._window[0])
            rate = (len(self._window) - 1) / span
        return {
            "enabled": self.enabled,
            "available": self._available,
            "source": self._source,
            "codec": self._codec,
            "reason": self._reason,
            "packets": self._packets,
            "config_packets": self._config_packets,
            "bytes": self._bytes,
            "subscribers": self.subscribers,
            "peak_subscribers": self._peak,
            "max_clients": AUDIO_MAX_CLIENTS,
            "packet_age_ms": round((now - self._last_at) * 1000) if self._last_at else None,
            "packet_rate": round(rate, 1),
            "channels": self._channels,
            "sample_rate": self._sample_rate,
            "silence_run": self._silence_run,
            "preface": self._preface_note or None,
            "errors": self._errors,
            "last_error": self._last_error,
            "emulator_audio": (
                "guest audio must be enabled — do not start the emulator with -no-audio"
            ),
            "playback": "browser AudioContext via /ws/audio",
            "scrcpy_server": SCRCPY_SERVER_PATH,
            "scrcpy_present": scrcpy_available(),
        }

    def _ensure(self) -> None:
        if self._stopping or not self.enabled:
            return
        if not self.running:
            self._task = asyncio.create_task(self._run(), name="audio-producer")

    @contextlib.asynccontextmanager
    async def subscribe(self, name: str = "ws"):
        """Yield a DeviceAudio-compatible queue (wire bytes via ``get()``)."""
        if not self.enabled:
            raise AudioError("audio disabled (AUDIO_ENABLED=0)")
        if len(self._subs) >= AUDIO_MAX_CLIENTS:
            raise AudioError("audio at capacity")
        sub = AudioSubscriber(name)
        self._subs.add(sub)
        self._peak = max(self._peak, len(self._subs))
        self._ensure()
        if self._head:
            sub.offer(AudioPacket(
                payload=self._head, pts_us=0, config=True, codec=self._codec, seq=0,
            ))
        try:
            yield _WireQueue(sub, self)
        finally:
            sub.closed = True
            self._subs.discard(sub)

    def _emit(self, packet: AudioPacket) -> None:
        if packet.config or is_opus_head(packet.payload):
            head = extract_opus_head(packet.payload)
            packet = AudioPacket(payload=head, pts_us=0, config=True, codec=packet.codec or "opus")
            self._head = head
            self._channels, self._sample_rate = opus_head_info(head)
            self._config_packets += 1
            self._codec = "opus"
        self._seq += 1
        packet = AudioPacket(
            payload=packet.payload,
            pts_us=packet.pts_us,
            config=packet.config,
            codec=packet.codec,
            seq=self._seq,
        )
        self._packets += 1
        self._bytes += len(packet.payload)
        self._last_at = time.time()
        self._window.append(self._last_at)
        cutoff = self._last_at - 3.0
        while self._window and self._window[0] < cutoff:
            self._window.pop(0)
        if not packet.config:
            if len(packet.payload) <= 8:
                self._silence_run += 1
            else:
                self._silence_run = 0
            if self._silence_run >= 40:
                self._reason = (
                    "packets are tiny (silence). Restart the emulator without -no-audio "
                    "so playback capture can hear YouTube."
                )
            elif self._source == "scrcpy":
                self._reason = "opus from scrcpy — browser plays it on user speakers"
        for sub in list(self._subs):
            sub.offer(packet)

    def wire(self, packet: AudioPacket) -> bytes:
        return pack_audio(packet)

    async def _run(self) -> None:
        self._started_at = time.time()
        try:
            while not self._stopping and self._subs:
                try:
                    await self._segment()
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self._errors += 1
                    self._last_error = f"{type(e).__name__}: {e}"
                    self._source = "error"
                    self._reason = self._last_error
                    self._available = False
                    await asyncio.sleep(0.8)
                if not self._subs:
                    return
        finally:
            self._task = None
            if not self._stopping and self._subs:
                self._task = asyncio.create_task(self._run(), name="audio-producer")

    async def _segment(self) -> None:
        self._source = "starting"
        self._reason = "opening scrcpy audio socket"
        with contextlib.suppress(Exception):
            await self.adb.ensure_connected()
        session = ScrcpyAudioSession(self.adb)
        self._session = session
        buf = b""
        preface: Optional[Preface] = None
        try:
            reader = await session.start()
            while not self._stopping and self._subs:
                try:
                    chunk = await asyncio.wait_for(reader.read(4096), 2.0)
                except asyncio.TimeoutError:
                    continue
                if not chunk:
                    break
                buf += chunk
                if preface is None:
                    preface, buf = parse_preface(buf)
                    if preface is None:
                        continue
                    self._preface_note = preface.note
                    self._codec = preface.codec
                    if preface.disabled or preface.error:
                        self._source = "error"
                        self._available = False
                        self._reason = (
                            "scrcpy disabled audio (codec id "
                            f"{preface.codec_id}). The emulator was likely started with "
                            "-no-audio, so there is no playback to capture."
                            if preface.disabled
                            else "scrcpy audio configuration error"
                        )
                        self._last_error = self._reason
                        return
                    self._source = "scrcpy"
                    self._available = True
                    self._reason = "opus from scrcpy — browser plays it on user speakers"
                packets, buf = pop_packets(buf, codec=self._codec)
                if len(buf) > 12 and not packets:
                    self._errors += 1
                    self._last_error = "audio demux lost sync"
                    buf = b""
                for packet in packets:
                    self._emit(packet)
        finally:
            self._session = None
            await session.stop()
