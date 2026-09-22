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


def test_codec_and_packets() -> None:
    assert parse_codec_id(bytes.fromhex("6f707573")) == "opus"
    assert parse_codec_id((0x00616163).to_bytes(4, "big")) == "aac"
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
    asyncio.run(test_input_shell())
    print("ok phone touch/audio checks")


if __name__ == "__main__":
    main()
