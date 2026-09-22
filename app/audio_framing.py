"""Scrcpy audio socket → browser wire packets.

The soft-launch viewer decodes with WebCodecs ``AudioDecoder`` (codec
``opus``). That decoder wants:

* one raw Opus packet per ``EncodedAudioChunk`` (not Ogg, not ADTS)
* the Opus identification header (``OpusHead…``, RFC 7845 §5.1) passed as
  ``description``, never as a packet to ``decode()``

scrcpy (server 2.x) writes, when ``send_device_meta=false`` and
``send_dummy_byte=false``:

1. 4-byte big-endian codec id (``opus`` = ``0x6F707573``). ``0`` means the
   device disabled audio; ``1`` means a config error.
2. Repeated 12-byte frame headers: int64 PTS+flags, int32 packet size,
   then that many payload bytes. The config packet sets bit 63
   (``PACKET_FLAG_CONFIG``) and the payload is the OpusHead (scrcpy strips
   Android's ``AOPUSHDR`` wrapper before writing).

The browser wire (same 16-byte header as ``/ws/h264``) must set flags bit 0
on that config packet. Production was forwarding OpusHead with flags=0, so
the first ``decode()`` threw ``Decoding error`` and the decoder stayed dead.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

CODEC_OPUS = 0x6F707573  # "opus"
CODEC_AAC = 0x00616163
CODEC_RAW = 0x00726177
PACKET_FLAG_CONFIG = 1 << 63
PACKET_FLAG_KEY_FRAME = 1 << 62
WIRE = struct.Struct("<BBHId")
WIRE_VERSION = 1

# 64-byte scrcpy device-name block. Seen in the wild as ``\\x00sdk_gphone…``.
_DEVICE_META_LEN = 64


@dataclass(frozen=True)
class AudioPacket:
    """One browser-ready audio message."""

    payload: bytes
    pts_us: int
    config: bool
    codec: str = "opus"
    seq: int = 0

    @property
    def flags(self) -> int:
        return 1 if self.config else 0


@dataclass(frozen=True)
class Preface:
    codec_id: int
    codec: str
    disabled: bool
    error: bool
    note: str


def is_opus_head(payload: bytes) -> bool:
    return len(payload) >= 19 and payload.startswith(b"OpusHead")


def is_opus_tags(payload: bytes) -> bool:
    """Opus comment header. Also a description, not a decodable packet."""
    return len(payload) >= 8 and payload.startswith(b"OpusTags")


def opus_head_info(head: bytes) -> tuple[int, int]:
    """(channels, input_sample_rate) from an Opus identification header."""
    if not is_opus_head(head):
        return 2, 48000
    channels = head[9] or 2
    rate = int.from_bytes(head[12:16], "little") or 48000
    return channels, rate


def extract_opus_head(payload: bytes) -> bytes:
    """Return the OpusHead bytes WebCodecs should use as ``description``.

    Android's MediaCodec config buffer is an ``AOPUSHDR`` section list.
    scrcpy normally slices that down to OpusHead before the packet hits the
    socket; we still accept the raw wrapper so a missed slice cannot be
    fed to ``decode()``.
    """
    if is_opus_head(payload):
        if payload[18] == 0:
            return payload[:19]
        return payload
    if payload.startswith(b"AOPUSHDR") and len(payload) >= 16:
        size = int.from_bytes(payload[8:16], "little")
        if 19 <= size <= len(payload) - 16:
            head = payload[16 : 16 + size]
            if is_opus_head(head):
                return extract_opus_head(head)
    return payload


def _codec_name(codec_id: int) -> str:
    if codec_id == CODEC_OPUS:
        return "opus"
    if codec_id == CODEC_AAC:
        return "aac"
    if codec_id == CODEC_RAW:
        return "pcm"
    return f"0x{codec_id:08x}"


def _looks_like_device_name(block: bytes) -> bool:
    return b"sdk" in block or b"gphone" in block or b"redroid" in block


def strip_audio_preface(buf: bytes) -> tuple[bytes, str]:
    """Drop a tunnel dummy byte and/or 64-byte device-meta block.

    ``tunnel_forward=true`` already suppresses the dummy byte, and we pass
    ``send_device_meta=false``. This still repairs a socket that was opened
    with the defaults, which is how ``\\x00sdk_gphone…`` got parsed as a codec.
    The observed prefix is a dummy ``0x00`` plus a 64-byte name.
    """
    notes: list[str] = []
    if len(buf) >= 5 and buf[0:1] == b"\x00" and buf[1:5] == b"opus":
        buf = buf[1:]
        notes.append("skipped dummy byte")
    # dummy byte + 64-byte device name, then the 4-byte codec id
    if (
        len(buf) >= 1 + _DEVICE_META_LEN + 4
        and buf[0:1] == b"\x00"
        and _looks_like_device_name(buf[1 : 1 + _DEVICE_META_LEN])
    ):
        buf = buf[1 + _DEVICE_META_LEN :]
        notes.append("skipped dummy byte and device meta")
    elif (
        len(buf) >= _DEVICE_META_LEN + 4
        and _looks_like_device_name(buf[:_DEVICE_META_LEN])
        and not buf.startswith(b"opus")
    ):
        buf = buf[_DEVICE_META_LEN:]
        notes.append("skipped device meta")
    return buf, "; ".join(notes)


def parse_preface(buf: bytes) -> tuple[Preface | None, bytes]:
    """Consume the 4-byte codec id once ``buf`` is past dummy/device meta.

    Returns ``(None, buf)`` when more bytes are required.
    """
    buf, note = strip_audio_preface(buf)
    if len(buf) < 4:
        return None, buf
    codec_id = int.from_bytes(buf[:4], "big")
    preface = Preface(
        codec_id=codec_id,
        codec=_codec_name(codec_id) if codec_id > 1 else "opus",
        disabled=codec_id == 0,
        error=codec_id == 1,
        note=note,
    )
    return preface, buf[4:]


def pop_packets(buf: bytes, *, codec: str = "opus") -> tuple[list[AudioPacket], bytes]:
    """Pull every complete scrcpy audio packet out of ``buf``."""
    packets: list[AudioPacket] = []
    while len(buf) >= 12:
        pts_flags = int.from_bytes(buf[0:8], "big")
        size = int.from_bytes(buf[8:12], "big")
        if size < 0 or size > 1_000_000:
            # Lost sync. Drop one byte and let the caller count an error.
            buf = buf[1:]
            continue
        if len(buf) < 12 + size:
            break
        raw = buf[12 : 12 + size]
        buf = buf[12 + size :]
        config = bool(pts_flags & PACKET_FLAG_CONFIG)
        pts = 0 if config else (pts_flags & ~PACKET_FLAG_KEY_FRAME)
        payload = raw
        if config or raw.startswith(b"AOPUSHDR") or is_opus_head(raw):
            payload = extract_opus_head(raw)
            config = config or is_opus_head(payload) or raw.startswith(b"AOPUSHDR")
        # A config flag with a non-head payload is still not a decodable frame.
        if is_opus_head(payload) or is_opus_tags(payload):
            config = True
            pts = 0
        packets.append(AudioPacket(payload=payload, pts_us=pts, config=config, codec=codec))
    return packets, buf


def pack_audio(packet: AudioPacket) -> bytes:
    """16-byte little-endian header + payload. Bit 0 of flags marks OpusHead."""
    return WIRE.pack(
        WIRE_VERSION,
        packet.flags,
        0,
        packet.seq & 0xFFFFFFFF,
        float(packet.pts_us),
    ) + packet.payload


def normalize_annexb(data: bytes) -> bytes:
    """Rewrite 3-byte H.264 start codes as 4-byte start codes.

    WebCodecs on mobile Chrome has shown macroblock corruption on Annex-B
    that uses ``00 00 01`` while the same bytes decode cleanly in ffmpeg.
    Four-byte codes are the canonical form both accept.
    """
    if b"\x00\x00\x01" not in data:
        return data
    # Collapse existing 4-byte codes so the following replace is uniform.
    collapsed = data.replace(b"\x00\x00\x00\x01", b"\x00\x00\x01")
    return collapsed.replace(b"\x00\x00\x01", b"\x00\x00\x00\x01")
