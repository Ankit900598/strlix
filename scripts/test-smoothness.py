#!/usr/bin/env python3
"""Encode alignment, OpusHead, and jitter-buffer checks. No device, no network.

    python3 scripts/test-smoothness.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.device_audio import FLAG_CONFIG, pack_audio, split_scrcpy_audio_packets  # noqa: E402
from app.smoothness import (  # noqa: E402
    FLAG_RESYNC,
    JITTER_MAX_MS,
    JITTER_MIN_MS,
    align_screenrecord_size,
    choose_scrcpy_max_size,
    latency_budget,
    next_jitter_ms,
    prepare_audio_packet,
    scrcpy_limited_size,
    webrtc_spike_status,
)


def test_pixel_size_is_not_484() -> None:
    # 1080×2400 phone, long edge capped at 1080. The old host estimate was
    # int(1080 * 1080/2400) & ~3 = 484, which is not a macroblock.
    max_size, width, height = choose_scrcpy_max_size(1080, 2400, 1080)
    assert (width, height) != (484, 1080), (max_size, width, height)
    assert width % 16 == 0 and height % 16 == 0, (width, height)
    assert width == 480 and height == 1072, (max_size, width, height)
    assert max_size == 1072
    for alignment in (4, 8, 16):
        w, h = scrcpy_limited_size(1080, 2400, max_size, alignment)
        assert w % 16 == 0 and h % 16 == 0, (alignment, w, h)


def test_already_aligned_phone_is_not_shrunk() -> None:
    # A cap above the device must not upscale, and must not shave a size
    # that is already a multiple of 16.
    max_size, width, height = choose_scrcpy_max_size(720, 1280, 1920)
    assert (width, height) == (720, 1280), (max_size, width, height)
    assert max_size == 1280


def test_screenrecord_alignment() -> None:
    width, height = align_screenrecord_size(1080, 2400, 1080)
    assert width % 16 == 0 and height % 16 == 0
    assert width == 1072
    assert height == 2368
    assert (width, height) != (484, 1080)


def test_opus_head_with_flags_zero_is_config() -> None:
    head = b"OpusHead" + b"\x01" * 11
    prepared = prepare_audio_packet(0, 0, head)
    assert prepared is not None
    flags, pts, payload = prepared
    assert flags == FLAG_CONFIG
    assert pts == 0
    assert payload == head
    assert prepare_audio_packet(0, 10, b"OpusTags" + b"\x00" * 8) is None
    # A real audio frame is left alone.
    frame = prepare_audio_packet(0, 48000, b"\xfc\x00audio")
    assert frame == (0, 48000, b"\xfc\x00audio")


def test_config_bit_still_roundtrips() -> None:
    payload = b"OpusHead\x01"
    pts_flags = (1 << 63) | 0
    raw = pts_flags.to_bytes(8, "big") + len(payload).to_bytes(4, "big") + payload
    packets, rest = split_scrcpy_audio_packets(raw)
    assert rest == b""
    flags, _pts, body = packets[0]
    assert flags == FLAG_CONFIG
    assert body.startswith(b"OpusHead")
    wire = pack_audio(1, FLAG_CONFIG | FLAG_RESYNC, 0, body)
    assert wire[1] == (FLAG_CONFIG | FLAG_RESYNC)


def test_jitter_stays_in_band() -> None:
    assert next_jitter_ms(40, underrun=True, slack_ms=0) == 56
    grown = 40
    for _ in range(20):
        grown = next_jitter_ms(grown, underrun=True, slack_ms=0)
    assert grown == JITTER_MAX_MS
    shrunk = next_jitter_ms(80, underrun=False, slack_ms=200)
    assert shrunk == 72
    assert next_jitter_ms(JITTER_MIN_MS, underrun=False, slack_ms=10) == JITTER_MIN_MS
    floor = JITTER_MIN_MS
    for _ in range(20):
        floor = next_jitter_ms(floor, underrun=False, slack_ms=10_000)
    assert floor == JITTER_MIN_MS


def test_webrtc_spike_does_not_replace_ws() -> None:
    spike = webrtc_spike_status()
    assert spike["enabled"] is False
    assert spike["replaces_ws_h264"] is False
    assert spike["front_door_carries_webrtc_media"] is False
    budget = latency_budget()
    assert "emulator_ws_front_door" in budget["paths_ms"]
    assert "redroid_guest_gpu_ws" in budget["paths_ms"]
    assert "redroid_host_nvenc_webrtc" in budget["paths_ms"]
    assert "RTT" in budget["physics"] or "RTT" in budget["physics"].upper() or "rtt" in budget["physics"].lower()


def main() -> None:
    test_pixel_size_is_not_484()
    test_already_aligned_phone_is_not_shrunk()
    test_screenrecord_alignment()
    test_opus_head_with_flags_zero_is_config()
    test_config_bit_still_roundtrips()
    test_jitter_stays_in_band()
    test_webrtc_spike_does_not_replace_ws()
    print("ok smoothness checks")


if __name__ == "__main__":
    main()
