# Brief: scrcpy-server raw H.264 producer (no SDL)

## Goal
True low-latency path toward <100ms glass-to-glass for Strlix phone viewer.
Full scrcpy-web (SDL/XDG + jar browser protocol) stays blocked. Ship **scrcpy-server
over ADB forward + existing `/ws/h264` Annex-B wire** — same WebCodecs client.

## Proven on this box (2026-09-21)
```
adb push /home/box/.local/scrcpy/scrcpy-server /data/local/tmp/scrcpy-server.jar
adb forward tcp:27183 localabstract:scrcpy
adb shell CLASSPATH=... app_process / com.genymobile.scrcpy.Server 4.1 \
  tunnel_forward=true audio=false control=false cleanup=false raw_stream=true \
  max_size=1200 video_bit_rate=1500000 max_fps=60
# TCP connect → pure Annex-B H.264 (NO dummy byte with raw_stream). ffmpeg OK.
# 540x1200, TTFB ~600ms cold, then frames on change. i-frame-interval=1 IGNORED by emu encoder.
```
Full `scrcpy` binary: `--no-playback --no-window --record=` works despite XDG warn;
interactive mirror still wants SDL/XDG.

## Implement in /workspace/zevi-cloudphone only
1. Extend `app/h264_stream.py`: `H264_SOURCE=scrcpy|screenrecord|auto` (default auto:
   try scrcpy, fall back screenrecord). Same AU parser + `/ws/h264` pack_au.
2. Do NOT break JPEG `/ws/stream` or tap/swipe. Keep keyframe-on-tap.
3. Stats: `"source": "scrcpy"|"screenrecord"`. Hello JSON too.
4. Document `demo/overnight/SCRCPY.md` with blockers + before/after latency.
5. Measure with existing `scripts/qa_latency_ab.py` / a small probe.

## Non-goals
- ws-scrcpy full UI, SDL window, audio, replacing adb tap with scrcpy control
- Signing out of anything; touching other repos
