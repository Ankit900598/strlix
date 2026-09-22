"""Pure helpers for the soft-launch smoothness path.

No ADB, no sockets. ``scripts/test-smoothness.py`` locks the math so a
later scrcpy or viewer change cannot quietly bring back a 484×1080
encode or an OpusHead packet decoded as audio.

What this module does not do
----------------------------
It does not open WebRTC. Azure Front Door (the soft-launch edge) speaks
HTTP and WebSocket only. ICE media is UDP. Turning on a second media
stack inside this process would not reach the browser through Front Door
and could break the working ``/ws/h264`` path. ``webrtc_spike_status``
records that decision so the design doc and the code agree.
"""
from __future__ import annotations

OPUS_HEAD = b"OpusHead"
OPUS_TAGS = b"OpusTags"

FLAG_CONFIG = 1
FLAG_RESYNC = 2

JITTER_MIN_MS = 40
JITTER_MAX_MS = 120
JITTER_GROW_MS = 16
JITTER_SHRINK_MS = 8

# H.264 macroblocks are 16×16. The emulator software encoder (the thing
# that paints YouTube) leaves a dirty edge when either side is not a
# multiple of 16. 484×1080 is that bug: 1080×2400 limited to max_size
# 1080 is 486×1080, then a 4-pixel alignment rounds 486 down to 484.
MACROBLOCK = 16


def _align_down(value: int, alignment: int) -> int:
    if alignment <= 1:
        return int(value)
    aligned = (int(value) // alignment) * alignment
    return aligned if aligned >= alignment else alignment


def scrcpy_limited_size(
    device_w: int,
    device_h: int,
    max_size: int,
    alignment: int = MACROBLOCK,
) -> tuple[int, int]:
    """Reproduce scrcpy 4.1 ``Size.constrain`` when encoder caps are not applied.

    scrcpy 4.1 ignores encoder size caps until the first configure failure,
    so the first (and usual) size is: scale the long edge to ``max_size``,
    keep aspect with integer division, then round both edges *down* to
    ``alignment``. ``min_size_alignment=16`` is that alignment.
    """
    width, height = int(device_w), int(device_h)
    if width <= 0 or height <= 0:
        return 0, 0
    alignment = max(1, int(alignment))
    limit = int(max_size)
    if limit > 0 and (width > limit or height > limit):
        if width > height:
            scaled_w = limit
            scaled_h = height * limit // width
        else:
            scaled_w = width * limit // height
            scaled_h = limit
    else:
        scaled_w, scaled_h = width, height
    return _align_down(scaled_w, alignment), _align_down(scaled_h, alignment)


def choose_scrcpy_max_size(
    device_w: int,
    device_h: int,
    cap: int,
) -> tuple[int, int, int]:
    """Pick ``max_size`` so the encoded picture is 16-aligned on scrcpy 4.1 and older.

    Returns ``(max_size, enc_w, enc_h)``.

    ``min_size_alignment=16`` (4.1) floors both edges to 16. Older jars
    warn-and-ignore unknown keys and round to 8, or the emulator encoder
    reports alignment 4 and produces 484×1080. The search keeps only a cap
    whose 4-, 8-, and 16-align results are all multiples of 16, so the
    picture is clean on the jar we ship and on the jar that ignored the key.
    """
    width, height = int(device_w), int(device_h)
    if width < MACROBLOCK or height < MACROBLOCK:
        return 0, 0, 0
    long_edge = max(width, height)
    requested = int(cap) if int(cap) > 0 else long_edge
    requested = min(requested, long_edge)
    start = requested - (requested % MACROBLOCK)
    if start < MACROBLOCK:
        start = MACROBLOCK
    floor = max(MACROBLOCK * 4, (int(requested * 0.85) // MACROBLOCK) * MACROBLOCK)
    if floor > start:
        floor = start
    candidate = start
    while candidate >= floor:
        sizes = [
            scrcpy_limited_size(width, height, candidate, alignment)
            for alignment in (4, 8, MACROBLOCK)
        ]
        if all(w >= MACROBLOCK and h >= MACROBLOCK and w % MACROBLOCK == 0 and h % MACROBLOCK == 0 for w, h in sizes):
            enc_w, enc_h = sizes[-1]
            return candidate, enc_w, enc_h
        candidate -= MACROBLOCK
    enc_w, enc_h = scrcpy_limited_size(width, height, start, MACROBLOCK)
    return start, enc_w, enc_h


def align_screenrecord_size(device_w: int, device_h: int, width_cap: int) -> tuple[int, int]:
    """Exact ``screenrecord --size`` pair. Both edges are multiples of 16.

    ``screenrecord`` does not know ``min_size_alignment``. Passing 484×1080
    (the old ``% 4`` estimate) is what the software encoder artifacts on.
    """
    width, height = int(device_w), int(device_h)
    if width <= 0 or height <= 0:
        return MACROBLOCK, MACROBLOCK
    cap = int(width_cap) if int(width_cap) > 0 else width
    enc_w = min(cap, width)
    enc_w = max(MACROBLOCK, (enc_w // MACROBLOCK) * MACROBLOCK)
    enc_h = int(round(enc_w * height / float(width)))
    enc_h = max(MACROBLOCK, (enc_h // MACROBLOCK) * MACROBLOCK)
    return enc_w, enc_h


def prepare_audio_packet(flags: int, pts_us: int, payload: bytes) -> tuple[int, int, bytes] | None:
    """Normalize one scrcpy audio packet before it hits the browser.

    ``OpusHead`` is the codec description. WebCodecs ``AudioDecoder`` errors
    if that blob is fed to ``decode()``. Scrcpy should set the config bit;
    a confirmed bug sends it with flags=0. Sniffing the 8-byte magic fixes
    the viewer either way (the other fix can still set the bit).

    ``OpusTags`` is a comment header, not audio and not the description
    WebCodecs wants. Drop it.
    """
    if payload.startswith(OPUS_TAGS):
        return None
    if payload.startswith(OPUS_HEAD):
        flags = FLAG_CONFIG
    return int(flags), int(pts_us), payload


def next_jitter_ms(current_ms: int, *, underrun: bool, slack_ms: float) -> int:
    """Adaptive playout delay for device audio.

    40 ms is two 20 ms Opus frames: enough to hide one late packet, small
    enough that a tap's sound is not obviously late. Underruns grow it.
    A buffer that sits more than 30 ms above the target shrinks it, so a
    movie that started glitchy does not stay at 120 ms forever. Hard cap
    is 120 ms — past that, picture and sound drift apart.
    """
    current = int(current_ms)
    if current < JITTER_MIN_MS:
        current = JITTER_MIN_MS
    if current > JITTER_MAX_MS:
        current = JITTER_MAX_MS
    if underrun:
        return min(JITTER_MAX_MS, current + JITTER_GROW_MS)
    if slack_ms > current + 30:
        return max(JITTER_MIN_MS, current - JITTER_SHRINK_MS)
    return current


def webrtc_spike_status() -> dict:
    """Why this PR does not replace ``/ws/h264`` with WebRTC.

    The function is the spike: a checked-in decision, not a second encoder.
    """
    return {
        "enabled": False,
        "replaces_ws_h264": False,
        "front_door_carries_webrtc_media": False,
        "reason": (
            "Azure Front Door serves HTTP, HTTPS, and WebSocket. It does not "
            "proxy UDP ICE/RTP. A WebRTC media path has to terminate somewhere "
            "Front Door is not (a regional SFU or TURN). The soft-launch viewer "
            "stays on /ws/h264 and /ws/audio."
        ),
        "when": (
            "After a gaming session is pinned to a started GPU worker, add a "
            "host-side NVENC encode and a UDP hop that does not go through Front Door."
        ),
    }


def latency_budget() -> dict:
    """Order-of-magnitude glass-to-glass budgets. Not a bench run.

    Rows are milliseconds. ``measured_in_repo`` cites an existing doc.
    Everything else is an estimate from how the stage works, labeled so
    nobody quotes it as a stopwatch result. The user's RTT is added twice
    on the HTTP path (touch goes to the phone, pixels come back).
    """
    return {
        "physics": (
            "Glass-to-glass cannot beat about two network crossings plus "
            "encode, decode, and a jitter buffer. A personal phone has no "
            "network crossing. Strlix can look and sound better than a handset "
            "(resolution, steady frames, loudspeakers) and still be slower to "
            "the finger by the user's RTT."
        ),
        "paths_ms": {
            "emulator_ws_front_door": {
                "where": "Current soft launch. SwiftShader emulator, scrcpy, WebSocket, Azure Front Door.",
                "touch_network": "1× user RTT. Front Door /health samples in PHONE-TOUCH-AUDIO.md were 157–986 ms.",
                "inject": "5–20 after the warm shell. Was a process spawn (often 50–200) before InputPump.",
                "compose_and_encode": "Emulator software encode is the big device cost. Host swipe→next AU was ~250 ms in demo/overnight/SCRCPY.md (not glass-to-glass).",
                "video_network": "1× user RTT on the same WebSocket.",
                "decode_paint": "A few milliseconds in WebCodecs plus one compositor frame. The viewer reports decodeMs.",
                "audio_buffer": f"{JITTER_MIN_MS}–{JITTER_MAX_MS} adaptive, on top of a 20 ms Opus frame.",
                "floor": "Two RTTs + encode floor. With a 80 ms RTT that is already ~200 ms before the emulator's encoder.",
            },
            "redroid_guest_gpu_ws": {
                "where": "ADB pointed at Redroid on the T4 after someone starts the stopped instance. Same WebSocket and Front Door.",
                "what_improves": "Guest GPU draws the game/video. SwiftShader stops being the compose bottleneck.",
                "what_does_not": (
                    "scrcpy inside the guest still uses Android MediaCodec. "
                    "guest GPU mode is not NVENC. Touch and video still cross Front Door."
                ),
                "encode": "Still MediaCodec, but a GPU-composited frame. Expect tens of milliseconds, not the emulator's hundreds. Not measured: this agent did not start the instance.",
                "floor": "Still about two RTTs. Better motion, same network physics.",
            },
            "redroid_host_nvenc_webrtc": {
                "where": "Future. Host captures the guest framebuffer, NVENC ultra-low-latency, WebRTC or Moonlight-style UDP that does not enter Front Door.",
                "encode": "NVENC tuning ultra-low-latency, preset P1, CBR, no B-frames. A few milliseconds to ~10 ms is the usual published range for that preset, not a number we measured.",
                "network": "About 1× RTT of UDP each way, plus a 20–40 ms jitter buffer. No Front Door on the media packets.",
                "floor": "This is the first path that can land near cloud-gaming latency. It is not the soft launch.",
            },
        },
    }
