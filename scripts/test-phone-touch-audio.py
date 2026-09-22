#!/usr/bin/env python3
"""Parser + fast-input shell checks for the phone touch/audio path.

No emulator and no network. Run from the repo root:

    python3 scripts/test-phone-touch-audio.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.adb_client import INPUT_SHELL_LOOP  # noqa: E402
from app.device_audio import (  # noqa: E402
    FLAG_CONFIG,
    pack_audio,
    parse_codec_id,
    split_scrcpy_audio_packets,
)
from app.h264_stream import align_screenrecord_size, choose_aligned_max_size  # noqa: E402
from app.scrcpy_source import encoder_max_fps, video_codec_options  # noqa: E402


def test_codec_and_packets() -> None:
    assert parse_codec_id(bytes.fromhex("6f707573")) == "opus"
    assert parse_codec_id(bytes.fromhex("61616320")) == "aac"  # scrcpy fourcc "aac "
    try:
        parse_codec_id(b"nope")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown codec should fail")

    payload = b"\x01\x02opus-frame"
    pts_flags = (1 << 63) | 48000  # config flag + pts
    raw = pts_flags.to_bytes(8, "big") + len(payload).to_bytes(4, "big") + payload
    # A second, non-config packet, plus a truncated tail that must stay buffered.
    payload2 = b"abcd"
    raw += (1200).to_bytes(8, "big") + len(payload2).to_bytes(4, "big") + payload2
    raw += b"\x00\x01"  # incomplete header
    packets, rest = split_scrcpy_audio_packets(raw)
    assert len(packets) == 2, packets
    flags, pts, body = packets[0]
    assert flags == FLAG_CONFIG
    assert pts == 48000
    assert body == payload
    assert packets[1][0] == 0
    assert packets[1][2] == payload2
    assert rest == b"\x00\x01"

    wire = pack_audio(7, FLAG_CONFIG, 48000, payload)
    assert wire[0] == 1
    assert wire[1] == FLAG_CONFIG
    assert wire[16:] == payload

    try:
        split_scrcpy_audio_packets((0).to_bytes(8, "big") + (5_000_000).to_bytes(4, "big"))
    except ValueError:
        pass
    else:
        raise AssertionError("huge packet should fail")

    # Live capture: OpusHead with scrcpy bit63 clear must still set wire bit0.
    head = bytes.fromhex("4f707573486561640102380180bb0000000000")
    assert head.startswith(b"OpusHead") and len(head) == 19
    raw = (0).to_bytes(8, "big") + len(head).to_bytes(4, "big") + head
    packets, rest = split_scrcpy_audio_packets(raw)
    assert rest == b""
    assert packets[0][0] == FLAG_CONFIG
    assert packets[0][1] == 0
    assert packets[0][2] == head
    wire = pack_audio(1, packets[0][0], packets[0][1], packets[0][2])
    assert wire[1] == FLAG_CONFIG
    assert wire[16:24] == b"OpusHead"

    tags = b"OpusTags" + b"\x00" * 8
    raw = (12345).to_bytes(8, "big") + len(tags).to_bytes(4, "big") + tags
    packets, _rest = split_scrcpy_audio_packets(raw)
    assert packets[0][0] == FLAG_CONFIG and packets[0][1] == 0

    frame = bytes.fromhex("fcfffe")
    raw = (3_000_000).to_bytes(8, "big") + len(frame).to_bytes(4, "big") + frame
    packets, _rest = split_scrcpy_audio_packets(raw)
    assert packets[0][0] == 0 and packets[0][1] == 3_000_000 and packets[0][2] == frame


def test_encode_alignment() -> None:
    # 1080×2400, cap 1080 used to report 484 (and scrcpy encoded 486). Neither % 16 == 0.
    ew, eh, max_size = choose_aligned_max_size(1080, 2400, 1080)
    assert (ew, eh, max_size) == (432, 960, 960), (ew, eh, max_size)
    assert ew % 16 == 0 and eh % 16 == 0
    sw, sh = align_screenrecord_size(1080, 2400, 1080)
    assert sw % 16 == 0 and sh % 16 == 0, (sw, sh)
    assert encoder_max_fps("emulator-5554", 90) == 30
    assert encoder_max_fps("192.168.0.8:5555", 90) == 90
    assert encoder_max_fps("redroid", 90) == 90
    opts = video_codec_options("i-frame-interval:int=1,latency:int=1")
    assert "i-frame-interval:int=1" in opts
    assert "latency:int=1" in opts
    assert opts.count("priority:") == 1


async def test_input_shell() -> None:
    proc = await asyncio.create_subprocess_exec(
        "sh", "-c", INPUT_SHELL_LOOP,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    assert proc.stdin and proc.stdout
    proc.stdin.write(b"echo hello-from-shell\n")
    await proc.stdin.drain()
    # Closing stdin ends `read`, which flushes the shell's stdout buffer.
    proc.stdin.close()
    out = await asyncio.wait_for(proc.stdout.read(), 2.0)
    await proc.wait()
    text = out.decode()
    assert "hello-from-shell" in text, text


def main() -> None:
    test_codec_and_packets()
    test_encode_alignment()
    asyncio.run(test_input_shell())
    print("ok phone touch/audio checks")


if __name__ == "__main__":
    main()
