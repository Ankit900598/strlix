"""Framing tests for Opus config packets and Annex-B start codes.

No device, no network. Run: python3 scripts/test_stream_framing.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.audio_framing import (  # noqa: E402
    PACKET_FLAG_CONFIG,
    extract_opus_head,
    is_opus_head,
    normalize_annexb,
    opus_head_info,
    pack_audio,
    parse_preface,
    pop_packets,
)
from app.audio_stream import AudioBroker, AudioPacket  # noqa: E402
from app.scrcpy_source import encoder_bitrate, encoder_fps  # noqa: E402

OPUS_HEAD = bytes.fromhex("4f707573486561640102380180bb0000000000")  # 19-byte OpusHead


def scrcpy_packet(payload: bytes, *, config: bool = False, pts: int = 3327173549) -> bytes:
    flags = PACKET_FLAG_CONFIG if config else pts
    return flags.to_bytes(8, "big") + len(payload).to_bytes(4, "big") + payload


def test_opus_head_is_config_flag() -> None:
    preface_buf = bytes.fromhex("6f707573") + scrcpy_packet(OPUS_HEAD, config=True, pts=0)
    preface_buf += scrcpy_packet(bytes.fromhex("fcfffe"), config=False, pts=1000)
    preface, rest = parse_preface(preface_buf)
    assert preface is not None and preface.codec == "opus" and not preface.disabled
    packets, left = pop_packets(rest)
    assert left == b""
    assert len(packets) == 2
    assert packets[0].config and is_opus_head(packets[0].payload)
    assert not packets[1].config and packets[1].payload == bytes.fromhex("fcfffe")
    # The bug: flags bit 0 must be set or WebCodecs decode() throws.
    wire = pack_audio(AudioPacket(
        payload=packets[0].payload, pts_us=0, config=True, seq=1,
    ))
    assert wire[1] & 1 == 1
    assert wire[16:].startswith(b"OpusHead")
    media = pack_audio(AudioPacket(
        payload=packets[1].payload, pts_us=1000, config=False, seq=2,
    ))
    assert media[1] & 1 == 0


def test_unflagged_opus_head_still_marked() -> None:
    """A server that forgets PACKET_FLAG_CONFIG must still not be decoded."""
    raw = (0).to_bytes(8, "big") + len(OPUS_HEAD).to_bytes(4, "big") + OPUS_HEAD
    packets, left = pop_packets(raw)
    assert left == b"" and packets[0].config


def test_aopushdr_wrapper() -> None:
    head = OPUS_HEAD
    wrapped = b"AOPUSHDR" + len(head).to_bytes(8, "little") + head + b"AOPUSDLY"
    got = extract_opus_head(wrapped)
    assert got == OPUS_HEAD
    channels, rate = opus_head_info(got)
    assert (channels, rate) == (2, 48000)


def test_device_meta_and_dummy_are_skipped() -> None:
    # What production parsed as a codec: dummy 0x00 + "sdk_gphone…".
    name = b"sdk_gphone64_arm64".ljust(64, b"\x00")
    buf = b"\x00" + name + b"opus" + scrcpy_packet(OPUS_HEAD, config=True)
    preface, rest = parse_preface(buf)
    assert preface is not None and preface.codec == "opus"
    assert "device meta" in preface.note
    packets, left = pop_packets(rest)
    assert left == b"" and packets[0].config


def test_disabled_audio_codec_id() -> None:
    preface, rest = parse_preface(b"\x00\x00\x00\x00")
    assert preface is not None and preface.disabled and rest == b""


def test_annexb_start_codes() -> None:
    nal = b"\x00\x00\x01\x67\x42\x00" + b"\x00\x00\x00\x01\x68\xce"
    out = normalize_annexb(nal)
    assert out.startswith(b"\x00\x00\x00\x01")
    assert b"\x00\x00\x01" in out  # the 4-byte code contains a 3-byte suffix
    assert out.count(b"\x00\x00\x00\x01") == 2
    # idempotent
    assert normalize_annexb(out) == out


def test_emulator_caps() -> None:
    fps, note = encoder_fps("emulator-5554", 90)
    assert fps == 30 and "90" in note
    fps_gpu, note_gpu = encoder_fps("127.0.0.1:5556", 90)
    assert fps_gpu == 90 and note_gpu == ""
    br, br_note = encoder_bitrate("emulator-5554", 2_500_000)
    assert br == 1_800_000 and br_note
    br_gpu, _ = encoder_bitrate("127.0.0.1:5556", 2_500_000)
    assert br_gpu == 2_500_000


def test_broker_marks_head_on_wire() -> None:
    class _Adb:
        serial = "emulator-5554"
        adb_bin = "adb"

        async def ensure_connected(self):
            return "device"

    broker = AudioBroker(_Adb())  # type: ignore[arg-type]
    broker._emit(pop_packets(scrcpy_packet(OPUS_HEAD, config=True))[0][0])
    broker._emit(pop_packets(scrcpy_packet(bytes.fromhex("fcfffe"), pts=20000))[0][0])
    assert broker._head == OPUS_HEAD
    assert broker._channels == 2 and broker._sample_rate == 48000
    queued = []
    for sub in broker._subs:
        queued.append(sub)
    # No subscribers yet — emit still cached the head. Pack it the way /ws/audio will.
    from app.audio_framing import AudioPacket as AP
    wire = pack_audio(AP(payload=broker._head, pts_us=0, config=True, seq=1))
    ver, flags, _res, seq, ts = struct.unpack_from("<BBHId", wire)
    assert ver == 1 and flags == 1 and seq == 1 and ts == 0.0
    assert wire[16:] == OPUS_HEAD


def main() -> None:
    test_opus_head_is_config_flag()
    test_unflagged_opus_head_still_marked()
    test_aopushdr_wrapper()
    test_device_meta_and_dummy_are_skipped()
    test_disabled_audio_codec_id()
    test_annexb_start_codes()
    test_emulator_caps()
    test_broker_marks_head_on_wire()
    print("ok", 8, "framing tests")


if __name__ == "__main__":
    main()
