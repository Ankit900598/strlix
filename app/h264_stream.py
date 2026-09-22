"""Low-latency H.264 live video from the device — `screenrecord` → stdout → WS.

Why this exists
---------------
The JPEG :class:`~app.adb_client.FrameBroker` path is bounded by
``adb exec-out screencap -p`` (~230-350 ms per frame, ~3 fps) because every
frame is a full PNG round-trip plus a Pillow re-encode.  Interactive control at
that cadence always feels one frame behind.

This module runs a *single* ``adb exec-out screenrecord --output-format=h264 -``
process, parses the Annex-B elementary stream into access units (AUs), and fans
those AUs out to every WebSocket viewer.  The browser decodes with WebCodecs
(``VideoDecoder``), so the wire carries ~1.5 Mbps of already-compressed video
instead of ~120 KB JPEGs, and the device encoder pushes a frame whenever the
screen actually changes (nothing at all when it is static).

Chosen over scrcpy on purpose
-----------------------------
scrcpy/ws-scrcpy would need its own server jar pushed to the device, a second
control protocol, and version pinning against the device build.  ``screenrecord``
ships in every Android image (v1.3 here, API 34), needs no push, and is one
subprocess we already have the plumbing for.  The price is paid in three places,
all handled below:

1. **No length prefixes.**  Annex-B only tells you a NAL ended when the *next*
   start code arrives, so on a static screen the last frame would never flush.
   Handled with an idle-flush timer (:attr:`H264Broker.flush_idle`).
2. **Keyframes are rare.**  ``screenrecord`` emits one IDR at start and then
   (on this build) essentially none, so a late joiner cannot just start
   listening.  Handled with a bounded GOP buffer plus a rate-limited producer
   restart when that buffer is unusable — a restart is the only way to ask this
   encoder for a fresh IDR.
3. **Recording has a time limit.**  ``--time-limit 0`` removes it, but we
   deliberately re-segment anyway so the GOP buffer stays small and new viewers
   keep getting a cheap start.

The JPEG path stays as the fallback (older browsers, no WebCodecs, or a device
where ``screenrecord`` is unavailable) — see ``static/index.html``.
"""
from __future__ import annotations

import asyncio
import contextlib
import os
import struct
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .scrcpy_source import (
    SCRCPY_CODEC_OPTIONS,
    SCRCPY_MAX_SIZE,
    ScrcpyError,
    ScrcpyRawSession,
    scrcpy_available,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .adb_client import AdbClient

# ---- ops knobs (env) ------------------------------------------------------
H264_ENABLED = os.environ.get("H264_ENABLED", "1") not in ("0", "false", "no")
H264_WIDTH = int(os.environ.get("H264_WIDTH", "1080"))
H264_BITRATE = int(os.environ.get("H264_BITRATE", "2500000"))
H264_MAX_CLIENTS = int(os.environ.get("H264_MAX_CLIENTS", "12"))
# Re-segment the recording this often (seconds). Each new segment starts with
# SPS/PPS + IDR, which is what makes a late joiner cheap. 0 = never re-segment
# (screenrecord's own --time-limit 0).
H264_SEGMENT_S = int(os.environ.get("H264_SEGMENT_S", "15"))
H264_IDLE_STOP_S = float(os.environ.get("H264_IDLE_STOP_S", "10"))
# GOP replay budget for late joiners.
H264_GOP_MAX_BYTES = int(os.environ.get("H264_GOP_MAX_BYTES", str(3 * 1024 * 1024)))
H264_GOP_MAX_AUS = int(os.environ.get("H264_GOP_MAX_AUS", "600"))
# Above this the replay itself becomes the slow part of joining, so a fresh IDR
# is the cheaper start — provided no one else is watching to be interrupted.
H264_GOP_REPLAY_MAX_BYTES = int(os.environ.get("H264_GOP_REPLAY_MAX_BYTES", str(1024 * 1024)))
# Per-client send queue budget before we start dropping.
H264_QUEUE_MAX_AUS = int(os.environ.get("H264_QUEUE_MAX_AUS", "180"))
H264_QUEUE_MAX_BYTES = int(os.environ.get("H264_QUEUE_MAX_BYTES", str(4 * 1024 * 1024)))
# A NAL is considered complete after this much silence on the pipe.
H264_FLUSH_IDLE_MS = float(os.environ.get("H264_FLUSH_IDLE_MS", "12"))
# Don't let joiners restart the encoder more often than this.
H264_KEYFRAME_COOLDOWN_S = float(os.environ.get("H264_KEYFRAME_COOLDOWN_S", "2.5"))

# Producer: "screenrecord" (default legacy), "scrcpy" (server jar, no SDL), or
# "auto" (try scrcpy once per process, fall back to screenrecord on failure).
H264_SOURCE = os.environ.get("H264_SOURCE", "auto").strip().lower()
# Shorter segments → more IDRs (screenrecord ignores i-frame-interval).
# 15s keeps joins cheap without restarting on every tap.
if "H264_SEGMENT_S" not in os.environ:
    # Only override the module default when the operator did not set it — the
    # assignment above already read the env; re-bind a tighter default for new
    # deploys that omit the knob.
    pass

START_CODE = b"\x00\x00\x01"
# Ceiling for the measured mid-NAL stall. A pause longer than this is the link
# misbehaving, not framing, and must not drag every frame's latency up with it.
MAX_INTRA_GAP_S = float(os.environ.get("H264_MAX_INTRA_GAP_MS", "120")) / 1000.0

NAL_SLICE = 1
NAL_IDR = 5
NAL_SEI = 6
NAL_SPS = 7
NAL_PPS = 8
NAL_AUD = 9
VCL_TYPES = (NAL_SLICE, 2, 3, 4, NAL_IDR)


class H264Error(RuntimeError):
    pass


# Wire framing for /ws/h264: one binary message per access unit so the browser
# never has to correlate a JSON header with a following binary payload (that
# pairing is what made the JPEG socket fiddly). Little-endian, 16 bytes:
#   u8 version | u8 flags (bit0 = key) | u16 reserved | u32 seq | f64 ts_us
AU_HEADER = struct.Struct("<BBHId")
AU_WIRE_VERSION = 1


def pack_au(au: "AccessUnit") -> bytes:
    return AU_HEADER.pack(AU_WIRE_VERSION, 1 if au.key else 0, 0, au.seq & 0xFFFFFFFF,
                          float(au.ts_us)) + au.data


@dataclass(frozen=True)
class AccessUnit:
    """One decodable unit: Annex-B bytes for exactly one frame."""

    seq: int
    ts_us: int          # presentation timestamp handed to WebCodecs
    wall: float         # host time the AU finished arriving (latency accounting)
    data: bytes         # Annex-B, config NALs prepended on key AUs
    key: bool

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass(eq=False)   # identity-hashed: subscribers live in a set
class Subscriber:
    """One viewer. Owns a bounded queue; the producer never blocks on it."""

    name: str
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=H264_QUEUE_MAX_AUS + 8))
    queued_bytes: int = 0
    needs_key: bool = True
    dropped: int = 0
    sent: int = 0
    sent_bytes: int = 0
    joined: float = field(default_factory=time.time)
    closed: bool = False

    def offer(self, au: AccessUnit) -> bool:
        """Non-blocking enqueue with a latest-wins-under-pressure policy."""
        if self.closed:
            return False
        if self.needs_key and not au.key:
            self.dropped += 1
            return False
        over = (
            self.queue.qsize() >= H264_QUEUE_MAX_AUS
            or self.queued_bytes + au.size > H264_QUEUE_MAX_BYTES
        )
        if over:
            if not au.key:
                # Dropping a P-frame breaks every frame that references it, so
                # stop sending until the next IDR instead of shipping garbage.
                self.dropped += 1
                self.needs_key = True
                return False
            # A key AU resets the decoder: throw the backlog away, keep the key.
            self.drain()
        try:
            self.queue.put_nowait(au)
        except asyncio.QueueFull:  # pragma: no cover - drain() makes this unlikely
            self.dropped += 1
            self.needs_key = True
            return False
        self.queued_bytes += au.size
        if au.key:
            self.needs_key = False
        return True

    def drain(self) -> None:
        while True:
            try:
                self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        self.queued_bytes = 0

    def took(self, au: AccessUnit) -> None:
        self.queued_bytes = max(0, self.queued_bytes - au.size)
        self.sent += 1
        self.sent_bytes += au.size

    def stats(self) -> dict:
        return {
            "name": self.name,
            "sent": self.sent,
            "sent_kb": round(self.sent_bytes / 1024),
            "dropped": self.dropped,
            "queued": self.queue.qsize(),
            "queued_kb": round(self.queued_bytes / 1024),
            "needs_key": self.needs_key,
            "age_s": round(time.time() - self.joined, 1),
        }


def _split_nals(buf: bytes) -> tuple[list[bytes], bytes, int]:
    """Split an Annex-B buffer into complete NALs, remainder, and skipped bytes.

    The remainder always starts at a start code; the last NAL is held back
    because only the *next* start code proves it ended. ``skipped`` counts
    leading bytes that are *not* the head of a NAL — after the first NAL that
    can only mean we published a NAL before it had finished arriving, which the
    producer uses to widen its idle-flush window and resync.
    """
    nals: list[bytes] = []
    start = buf.find(START_CODE)
    if start < 0:
        return nals, buf, 0
    # A 4-byte start code (00 00 00 01) is found at its 3-byte tail, and legal
    # trailing_zero_8bits sit in front of it too — zeros are never "garbage".
    head = buf[:start]
    skipped = 0 if head.count(0) == len(head) else len(head)
    while True:
        nxt = buf.find(START_CODE, start + 3)
        if nxt < 0:
            return nals, buf[start:], skipped
        nal = buf[start:nxt]
        if nal:
            nals.append(nal)
        start = nxt


def _joins_new_nal(buf: bytes, chunk: bytes) -> bool:
    """True if `chunk` starts a new NAL (start code at, or across, the seam)."""
    return START_CODE in (buf[-3:] + chunk[:4])


def _nal_payload(nal: bytes) -> bytes:
    """Strip the leading 3- or 4-byte start code."""
    if nal.startswith(b"\x00\x00\x00\x01"):
        return nal[4:]
    if nal.startswith(START_CODE):
        return nal[3:]
    return nal


def _nal_type(nal: bytes) -> int:
    p = _nal_payload(nal)
    return (p[0] & 0x1F) if p else 0


def _starts_new_au(nal: bytes) -> bool:
    """True if this NAL can only be the first NAL of an access unit."""
    t = _nal_type(nal)
    if t in (NAL_AUD, NAL_SPS, NAL_PPS, NAL_SEI):
        return True
    if t in VCL_TYPES:
        p = _nal_payload(nal)
        # first_mb_in_slice is the leading ue(v); == 0 iff the top bit is set.
        return len(p) > 1 and bool(p[1] & 0x80)
    return False


def codec_string_from_sps(sps: bytes) -> str:
    """avc1.PPCCLL from the SPS NAL (profile / constraints / level)."""
    p = _nal_payload(sps)
    if len(p) < 4:
        return "avc1.42E01E"
    return "avc1." + "".join(f"{b:02X}" for b in p[1:4])


class H264Broker:
    """Single ``screenrecord`` producer, many WebSocket consumers."""

    def __init__(
        self,
        adb: "AdbClient",
        *,
        width: int = H264_WIDTH,
        bitrate: int = H264_BITRATE,
        segment_s: int = H264_SEGMENT_S,
        idle_stop: float = H264_IDLE_STOP_S,
    ) -> None:
        self.adb = adb
        self.width = width
        self.bitrate = bitrate
        self.segment_s = segment_s
        self.idle_stop = idle_stop
        self.flush_idle = H264_FLUSH_IDLE_MS / 1000.0
        self._base_flush_idle = self.flush_idle
        self.enabled = H264_ENABLED
        self._source_pref = H264_SOURCE if H264_SOURCE in ("screenrecord", "scrcpy", "auto") else "auto"
        self._active_source = "screenrecord"
        self._scrcpy_disabled = False  # sticky fallback after hard fail
        self._scrcpy: Optional[ScrcpyRawSession] = None

        self._subs: set[Subscriber] = set()
        self._task: Optional[asyncio.Task] = None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._stopping = False
        self._restart = asyncio.Event()
        # Set once this segment's SPS is parsed, i.e. codec/geometry are real.
        self._ready = asyncio.Event()

        # stream state
        self._sps: Optional[bytes] = None
        self._pps: Optional[bytes] = None
        self._codec: str = "avc1.42E01E"
        self._enc_width = 0
        self._enc_height = 0
        self._device_size: tuple[int, int] = (0, 0)
        self._seq = 0
        self._t0 = 0.0

        # GOP replay buffer (AUs since the last key AU)
        self._gop: list[AccessUnit] = []
        self._gop_bytes = 0
        self._gop_valid = False
        self._key_au: Optional[AccessUnit] = None

        # telemetry
        self._started_at = 0.0
        self._segment_started = 0.0
        self._segments = 0
        self._restarts = 0
        self._keyframes = 0
        self._aus = 0
        self._bytes = 0
        self._last_au_at = 0.0
        self._first_frame_ms: Optional[float] = None
        self._fps = 0.0
        self._kbps = 0.0
        self._window: list[tuple[float, int]] = []
        self._errors = 0
        self._last_error: Optional[str] = None
        self._last_keyframe_req = 0.0
        self._keyframe_reqs = 0
        self._last_keyframe_why: Optional[str] = None
        self._consecutive_failures = 0
        self._peak_subs = 0
        self._idle_flushes = 0
        # Largest observed gap *inside* a NAL. The idle-flush window has to sit
        # above this or we publish half-written slices; it decays so a one-off
        # stall does not permanently slow the stream down.
        self._intra_gap_max = 0.0
        self._misflushes = 0
        self._misflush_bytes = 0
        self._clean_flushes = 0
        # Two quiet ticks publish one frame, so this ceiling is ~2× added
        # latency. 96ms (was 250ms) keeps a safety margin over a ~70ms ADB
        # stall without letting the window grow into a noticeable tap delay.
        cap_ms = float(os.environ.get("H264_FLUSH_CAP_MS", "96"))
        self.max_flush_idle = min(max(0.25, self.flush_idle * 8), max(self.flush_idle, cap_ms / 1000.0))
        self._unavailable = False   # screenrecord not usable on this device

    # ---- introspection ---------------------------------------------------
    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def subscribers(self) -> int:
        return len(self._subs)

    @property
    def codec(self) -> str:
        return self._codec

    @property
    def available(self) -> bool:
        """False once screenrecord has proved unusable on this device."""
        return self.enabled and not self._unavailable

    def hello(self) -> dict:
        dw, dh = self._device_size
        return {
            "type": "hello",
            "codec": self._codec,
            "annexb": True,
            "width": self._enc_width or self.width,
            "height": self._enc_height,
            "device_width": dw or None,
            "device_height": dh or None,
            "bitrate": self.bitrate,
            "scrcpy_max_size": SCRCPY_MAX_SIZE,
            "scrcpy_codec_options": SCRCPY_CODEC_OPTIONS or None,
            "viewers": self.subscribers,
            "max_clients": H264_MAX_CLIENTS,
            "gop_ready": self._gop_valid,
            "source": self._active_source,
        }

    def stats(self) -> dict:
        now = time.time()
        return {
            "enabled": self.enabled,
            "source": self._active_source,
            "source_pref": self._source_pref,
            "scrcpy_available": scrcpy_available(),
            "scrcpy_disabled": self._scrcpy_disabled,
            "available": not self._unavailable,
            "running": self.running,
            "subscribers": self.subscribers,
            "peak_subscribers": self._peak_subs,
            "max_clients": H264_MAX_CLIENTS,
            "codec": self._codec,
            "size": [self._enc_width, self._enc_height] if self._enc_width else None,
            "device": list(self._device_size) if self._device_size[0] else None,
            "bitrate": self.bitrate,
            "scrcpy_max_size": SCRCPY_MAX_SIZE,
            "scrcpy_codec_options": SCRCPY_CODEC_OPTIONS or None,
            "segment_s": self.segment_s,
            "segments": self._segments,
            "restarts": self._restarts,
            "access_units": self._aus,
            "keyframes": self._keyframes,
            "mbytes": round(self._bytes / 1048576.0, 2),
            "fps": round(self._fps, 1),
            "kbps": round(self._kbps),
            "first_frame_ms": round(self._first_frame_ms) if self._first_frame_ms else None,
            "frame_age_ms": round((now - self._last_au_at) * 1000) if self._last_au_at else None,
            "uptime_s": round(now - self._started_at, 1) if self._started_at else None,
            "gop_valid": self._gop_valid,
            "gop_aus": len(self._gop),
            "gop_kb": round(self._gop_bytes / 1024),
            "idle_flushes": self._idle_flushes,
            "misflushes": self._misflushes,
            "flush_idle_ms": round(self.flush_idle * 1000, 1),
            "flush_tick_ms": round(self._tick() * 1000, 1),
            "intra_gap_max_ms": round(self._intra_gap_max * 1000, 1),
            "keyframe_requests": self._keyframe_reqs,
            "last_keyframe_why": self._last_keyframe_why,
            "errors": self._errors,
            "last_error": self._last_error,
            "clients": [s.stats() for s in self._subs],
        }

    # ---- lifecycle -------------------------------------------------------
    def _ensure_task(self) -> None:
        if self._stopping or not self.enabled:
            return
        if not self.running:
            self._task = asyncio.create_task(self._run(), name="h264-producer")

    @contextlib.asynccontextmanager
    async def subscribe(self, name: str = "ws"):
        """Attach a viewer; primes it with the replayable GOP when we have one."""
        if not self.enabled:
            raise H264Error("h264 disabled (H264_ENABLED=0)")
        sub = Subscriber(name=name)
        self._subs.add(sub)
        self._peak_subs = max(self._peak_subs, len(self._subs))
        self._ensure_task()
        self._prime(sub)
        try:
            yield sub
        finally:
            sub.closed = True
            sub.drain()
            self._subs.discard(sub)

    def _prime(self, sub: Subscriber) -> None:
        """Give a joiner something decodable: replay the GOP, else force an IDR.

        Replaying is instant and disturbs nobody, so it wins by default. Once
        the GOP grows past :data:`H264_GOP_REPLAY_MAX_BYTES` the replay is the
        slow part of joining — then a restart is cheaper, but only if this
        viewer is alone, because a restart freezes everyone else for ~700 ms.
        """
        alone = len(self._subs) <= 1
        if self._gop_valid and self._gop:
            if self._gop_bytes > H264_GOP_REPLAY_MAX_BYTES and alone:
                self.request_keyframe("join-gop-too-big")
                return
            for au in self._gop:
                sub.offer(au)
            return
        self.request_keyframe("join")

    async def wait_ready(self, timeout: float = 2.5) -> bool:
        """Block until the encoder's SPS is known (real codec string + size).

        Without this a joiner's ``hello`` would advertise the placeholder codec
        and a zero height, because the producer may still be spawning.
        """
        self._ensure_task()
        if self._ready.is_set():
            return True
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self._ready.wait(), timeout)
        return self._ready.is_set()

    def request_keyframe(self, why: str = "manual") -> bool:
        """Restart the encoder to mint a fresh IDR (rate-limited).

        ``screenrecord`` offers no way to request a sync frame on a running
        encoder, so a restart is it. Existing viewers see a ~250 ms freeze, not
        a glitch, because their decoders simply get no new AUs during the gap.
        """
        self._ensure_task()
        now = time.time()
        if (now - self._last_keyframe_req) < H264_KEYFRAME_COOLDOWN_S:
            return False
        self._last_keyframe_req = now
        self._keyframe_reqs += 1
        self._last_keyframe_why = why
        self._restart.set()
        self._kill_proc()
        return True

    def _kill_proc(self) -> None:
        proc = self._proc
        if proc is not None and proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
        sc = self._scrcpy
        if sc is not None:
            # Fire-and-forget async stop from sync context: schedule if loop runs.
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(sc.stop())
            except RuntimeError:
                pass
            self._scrcpy = None

    async def aclose(self) -> None:
        self._stopping = True
        self._restart.set()
        self._kill_proc()
        task = self._task
        self._task = None
        if task and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    # ---- producer --------------------------------------------------------
    async def _device_geometry(self) -> tuple[int, int, int, int]:
        """(device_w, device_h, enc_w, enc_h) — encoder size keeps the aspect."""
        dw = dh = 0
        with contextlib.suppress(Exception):
            size = await self.adb.wm_size()
            if size.get("ok"):
                dw, dh = int(size["width"]), int(size["height"])
        if not dw or not dh:
            dw, dh = 1080, 2400
        self._device_size = (dw, dh)
        ew = min(self.width, dw)
        ew -= ew % 4                                  # AVC encoders want even dims
        eh = int(round(ew * dh / float(dw)))
        eh -= eh % 4
        return dw, dh, max(4, ew), max(4, eh)

    async def _run(self) -> None:
        self._started_at = time.time()
        try:
            while not self._stopping:
                if not self._subs:
                    # Nobody watching: let the encoder go so the device is idle.
                    idle_deadline = time.time() + self.idle_stop
                    while not self._subs and time.time() < idle_deadline and not self._stopping:
                        await asyncio.sleep(0.25)
                    if not self._subs:
                        return
                self._restart.clear()
                seg_started = time.time()
                aus_before = self._aus
                try:
                    await self._segment_dispatch()
                except asyncio.CancelledError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self._errors += 1
                    self._last_error = f"{type(e).__name__}: {e}"
                if self._aus > aus_before:
                    self._consecutive_failures = 0
                elif (time.time() - seg_started) < 1.0:
                    # Instant, frameless exit: device gone or screenrecord
                    # unusable. Back off instead of spinning on subprocesses.
                    self._consecutive_failures += 1
                    if self._consecutive_failures >= 6:
                        self._unavailable = True
                        self._last_error = self._last_error or "screenrecord produced no frames"
                        return
                    await asyncio.sleep(min(4.0, 0.4 * (2 ** (self._consecutive_failures - 1))))
        except asyncio.CancelledError:
            raise
        finally:
            self._kill_proc()
            self._task = None
            # Viewers still attached and we exited unexpectedly: come back.
            if not self._stopping and self._subs:
                self._restarts += 1
                self._task = asyncio.create_task(self._run(), name="h264-producer")

    def _want_scrcpy(self) -> bool:
        if self._scrcpy_disabled:
            return False
        if self._source_pref == "screenrecord":
            return False
        if self._source_pref == "scrcpy":
            return scrcpy_available()
        # auto
        return scrcpy_available()

    async def _segment_dispatch(self) -> None:
        """Pick scrcpy-server (preferred) or screenrecord; sticky-fallback on fail."""
        if self._want_scrcpy():
            try:
                await self._segment_scrcpy()
                return
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                self._errors += 1
                self._last_error = f"scrcpy: {type(e).__name__}: {e}"
                # Hard fail → stick to screenrecord for this process so the
                # viewer is never wedged in a scrcpy crash loop.
                self._scrcpy_disabled = True
                self._active_source = "screenrecord"
        await self._segment()

    async def _segment_scrcpy(self) -> None:
        """One scrcpy-server raw Annex-B segment (no SDL)."""
        dw, dh, _ew_legacy, _eh_legacy = await self._device_geometry()
        self._active_source = "scrcpy"
        # Prefer SCRCPY_MAX_SIZE (long-edge cap). Do NOT inherit H264_WIDTH (screenrecord
        # JPEG-era 360 default) — that under-reported size and starved gaming sharpness.
        max_size = SCRCPY_MAX_SIZE if SCRCPY_MAX_SIZE > 0 else max(dw, dh)
        if max_size > 0 and max(dw, dh) > 0:
            scale = min(1.0, max_size / float(max(dw, dh)))
            ew = max(4, int(dw * scale) & ~3)
            eh = max(4, int(dh * scale) & ~3)
        else:
            ew, eh = _ew_legacy, _eh_legacy
        self._enc_width, self._enc_height = ew, eh
        session = ScrcpyRawSession(
            self.adb,
            max_size=max_size,
            bitrate=self.bitrate,
            codec_options=SCRCPY_CODEC_OPTIONS,
        )
        self._scrcpy = session
        self._segment_started = time.time()
        self._segments += 1
        self._reset_gop()
        self._sps = self._pps = None
        self._first_frame_ms = None
        self._ready.clear()
        try:
            reader = await session.start()
            await self._pump_annexb(reader)
        finally:
            self._scrcpy = None
            await session.stop()

    async def _pump_annexb(self, stdout) -> None:
        """Shared Annex-B → AU pump used by screenrecord *and* scrcpy."""
        buf = b""
        pending: list[bytes] = []
        pending_has_vcl = False
        quiet_len = -1
        last_read = time.time()
        while not self._stopping and not self._restart.is_set():
            try:
                chunk = await asyncio.wait_for(stdout.read(65536), self._tick())
            except asyncio.TimeoutError:
                if buf and len(buf) == quiet_len:
                    nal, buf = buf, b""
                    quiet_len = -1
                    self._idle_flushes += 1
                    pending, pending_has_vcl = self._absorb(
                        nal, pending, pending_has_vcl, force_flush=True
                    )
                elif buf:
                    quiet_len = len(buf)
                elif pending:
                    self._emit(pending)
                    pending, pending_has_vcl = [], False
                    quiet_len = -1
                continue
            if not chunk:
                break
            now = time.time()
            if len(buf) > 8 and not _joins_new_nal(buf, chunk):
                gap = now - last_read
                if gap > self._intra_gap_max:
                    self._intra_gap_max = min(MAX_INTRA_GAP_S, gap)
                else:
                    # Decay stalls quickly so one slow read does not pin
                    # every later frame ~2 ticks behind (touch feels late).
                    self._intra_gap_max *= 0.96
            last_read = now
            quiet_len = -1
            buf += chunk
            nals, buf, skipped = _split_nals(buf)
            if skipped and self._aus:
                self._note_misflush(skipped)
            for nal in nals:
                pending, pending_has_vcl = self._absorb(nal, pending, pending_has_vcl)
        if pending:
            self._emit(pending)

    async def _segment(self) -> None:
        """One ``screenrecord`` invocation, streamed until it ends or restarts."""
        self._active_source = "screenrecord"
        dw, dh, ew, eh = await self._device_geometry()
        self._enc_width, self._enc_height = ew, eh
        limit = str(self.segment_s if self.segment_s > 0 else 0)
        cmd = [
            self.adb.adb_bin, "-s", self.adb.serial, "exec-out",
            f"screenrecord --output-format=h264 --size {ew}x{eh} "
            f"--bit-rate {self.bitrate} --time-limit {limit} -",
        ]
        self._segment_started = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=1 << 21,
        )
        self._proc = proc
        self._segments += 1
        # Config from the previous segment no longer describes this one.
        self._reset_gop()
        self._sps = self._pps = None
        self._first_frame_ms = None
        self._ready.clear()

        buf = b""
        pending: list[bytes] = []          # NALs of the AU being assembled
        pending_has_vcl = False
        quiet_len = -1                     # buffer length at the last quiet tick
        last_read = time.time()
        assert proc.stdout is not None
        try:
            while not self._stopping and not self._restart.is_set():
                try:
                    chunk = await asyncio.wait_for(proc.stdout.read(65536), self._tick())
                except asyncio.TimeoutError:
                    # Quiet pipe. The held bytes are *probably* a finished NAL
                    # (the encoder writes one frame per burst) — but a stalled
                    # TCP write looks identical for one tick, and publishing
                    # half a slice corrupts every frame until the next IDR. So
                    # require two consecutive quiet ticks with an unchanged
                    # buffer before publishing.
                    if buf and len(buf) == quiet_len:
                        nal, buf = buf, b""
                        quiet_len = -1
                        self._idle_flushes += 1
                        pending, pending_has_vcl = self._absorb(
                            nal, pending, pending_has_vcl, force_flush=True
                        )
                    elif buf:
                        quiet_len = len(buf)
                    elif pending:
                        self._emit(pending)
                        pending, pending_has_vcl = [], False
                        quiet_len = -1
                    continue
                if not chunk:
                    break
                now = time.time()
                if len(buf) > 8 and not _joins_new_nal(buf, chunk):
                    # This chunk continues the NAL already in `buf`, so the gap
                    # in front of it is a genuine mid-NAL stall — the thing the
                    # flush window must clear. Gaps in front of a *new* NAL are
                    # just the screen being idle and must not inflate it.
                    gap = now - last_read
                    if gap > self._intra_gap_max:
                        self._intra_gap_max = min(MAX_INTRA_GAP_S, gap)
                    else:
                        self._intra_gap_max *= 0.96
                last_read = now
                quiet_len = -1
                buf += chunk
                nals, buf, skipped = _split_nals(buf)
                if skipped and self._aus:
                    self._note_misflush(skipped)
                for nal in nals:
                    pending, pending_has_vcl = self._absorb(nal, pending, pending_has_vcl)
            if pending:
                self._emit(pending)
        finally:
            self._proc = None
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
            err = b""
            with contextlib.suppress(Exception):
                _, err = await asyncio.wait_for(proc.communicate(), 3.0)
            msg = err.decode(errors="replace").strip()
            if msg and "Time limit reached" not in msg and self._aus == 0:
                self._errors += 1
                self._last_error = msg[:300]
                low = msg.lower()
                if "inaccessible or not found" in low or "not found" in low:
                    self._unavailable = True
                    self.enabled = False

    def _absorb(
        self,
        nal: bytes,
        pending: list[bytes],
        pending_has_vcl: bool,
        *,
        force_flush: bool = False,
    ) -> tuple[list[bytes], bool]:
        """Add one NAL to the AU under construction, emitting on AU boundaries."""
        t = _nal_type(nal)
        if t == NAL_SPS:
            self._sps = nal
            self._codec = codec_string_from_sps(nal)
            self._ready.set()
        elif t == NAL_PPS:
            self._pps = nal

        is_vcl = t in VCL_TYPES
        boundary = _starts_new_au(nal) if is_vcl else t in (NAL_AUD, NAL_SPS, NAL_SEI)
        if pending and pending_has_vcl and boundary:
            self._emit(pending)
            pending, pending_has_vcl = [], False
        pending.append(nal)
        pending_has_vcl = pending_has_vcl or is_vcl
        if force_flush and pending_has_vcl:
            self._emit(pending)
            return [], False
        return pending, pending_has_vcl

    def _emit(self, nals: list[bytes]) -> None:
        if not nals:
            return
        types = [_nal_type(n) for n in nals]
        if not any(t in VCL_TYPES for t in types):
            return  # config-only: cached above, nothing to decode yet
        key = NAL_IDR in types
        payload = b"".join(nals)
        if key and self._sps and self._pps and NAL_SPS not in types:
            # Every key AU must be independently decodable.
            payload = self._sps + self._pps + payload

        now = time.time()
        if not self._t0:
            self._t0 = now
        self._seq += 1
        au = AccessUnit(
            seq=self._seq,
            ts_us=int((now - self._t0) * 1_000_000),
            wall=now,
            data=payload,
            key=key,
        )
        self._aus += 1
        if self._first_frame_ms is None and self._segment_started:
            self._first_frame_ms = (now - self._segment_started) * 1000.0
        self._bytes += au.size
        self._last_au_at = now
        if key:
            self._keyframes += 1
        self._track_rate(now, au.size)
        self._clean_flushes += 1
        if self._clean_flushes >= 120 and self.flush_idle > self._base_flush_idle:
            self.flush_idle = max(self._base_flush_idle, self.flush_idle * 0.8)
            self._clean_flushes = 0
        self._remember(au)
        for sub in list(self._subs):
            sub.offer(au)

    def _tick(self) -> float:
        """How long the pipe must be quiet before a buffered NAL looks finished."""
        # Two unchanged ticks are needed to publish, so the real quiet window
        # is 2x this — 2.5x the worst mid-NAL stall we have actually measured.
        return min(self.max_flush_idle, max(self.flush_idle, 1.25 * self._intra_gap_max))

    def _note_misflush(self, skipped: int) -> None:
        """We published a NAL early: widen the window and re-sync the decoders.

        The orphaned tail is already dropped by :func:`_split_nals`; the frame
        it belonged to is corrupt and every P-frame after it references that
        corruption, so the only real repair is a fresh IDR.
        """
        self._misflushes += 1
        self._misflush_bytes += skipped
        self.flush_idle = min(self.max_flush_idle, self.flush_idle * 1.6)
        self._clean_flushes = 0
        self.request_keyframe("misflush")

    def _track_rate(self, now: float, size: int) -> None:
        self._window.append((now, size))
        cutoff = now - 3.0
        while self._window and self._window[0][0] < cutoff:
            self._window.pop(0)
        span = max(0.35, now - self._window[0][0]) if self._window else 1.0
        self._fps = len(self._window) / span
        self._kbps = (sum(s for _, s in self._window) * 8 / 1000.0) / span

    def _reset_gop(self) -> None:
        self._gop = []
        self._gop_bytes = 0
        self._gop_valid = False
        self._key_au = None

    def _remember(self, au: AccessUnit) -> None:
        """Keep the replayable tail so a new viewer can start without a restart."""
        if au.key:
            self._gop = [au]
            self._gop_bytes = au.size
            self._gop_valid = True
            self._key_au = au
            return
        if not self._gop_valid:
            return
        self._gop.append(au)
        self._gop_bytes += au.size
        if self._gop_bytes > H264_GOP_MAX_BYTES or len(self._gop) > H264_GOP_MAX_AUS:
            # Too expensive to replay — drop it and make joiners force an IDR.
            self._reset_gop()
