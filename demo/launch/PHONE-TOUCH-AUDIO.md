# Phone touch, fullscreen, and speakers

## Stream break (Opus flags + 16-aligned encode)

Live `/ws/audio` sent the first Opus packet as `OpusHead` with flags=0. The viewer called `AudioDecoder.decode` on that header and closed with "Decoding error". The server now sets wire bit0 when the payload starts with `OpusHead` or `OpusTags`. The viewer does the same check if an older server forgets the flag.

`GET /health` → `h264.size` on a 1080×2400 phone was 484×1080 (`int(w*scale) & ~3`). scrcpy itself encoded 486×1080. Neither width is a multiple of 16, which is what the software encoder smears under YouTube motion. The encoder is now started with a `max_size` whose integer scale is already a multiple of 16 (1080×2400, cap 1080 → max_size 960 → 432×960) and `min_size_alignment=16`. `emulator-*` fps is capped at 30. Other serials keep `SCRCPY_MAX_FPS`. This is not an AFD truncation, and it is not a claim that the soft-launch emulator is a 10× or sub-50 ms phone.

Open phone stays in the market iframe (one tap, Close remains). Finger taps use 28 px of slop so a small jitter is not a swipe. Taps still map the painted video rect onto `wm size`.

Measured 2026-09-22 from this workspace against the live hosts (four `/health` samples after a cold first hit). These numbers are the network floor. They are not glass-to-glass, and they are not a physical handset.

## Health RTT (not the tap)

| Host | Samples | What it is |
| --- | --- | --- |
| Market `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/` | 126 ms (one GET) | The page. It does not receive taps. |
| Stream AFD `https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/health` | 986, 157, 396, 560 ms | Same desktop-api the iframe should use. Spread is large. |
| Old tunnel `https://graduation-cope-elementary-defence.trycloudflare.com/health` | 118, 95, 107, 133 ms | Same process (`uptime_s` matched). Faster that hour, and the name rotates. |

The market page now points `streamUrl` at the AFD stream host. The tunnel stays out of the default config because it is flaky, not because it was slower in this sample. A tap cannot beat the stream host's RTT: the iframe is that origin, and `POST /adb/tap` is same-origin to it.

## Input path (what a tap actually does)

1. Browser `pointerup` on `#touchLayer` (pointer events, `touch-action: none`, `touchstart` preventDefault so there is no 300 ms click delay).
2. `fetch POST /adb/tap` is started before replay bookkeeping. The ripple is painted on `pointerdown`.
3. desktop-api → `AdbClient.tap`.
   - Warm path: one long-lived `adb shell` (`InputPump`) writes `input tap x y` and waits for an ack. No new process per tap.
   - Cold path: `adb shell input tap` (one process). `get-state` is skipped for 8 s after a successful check.
4. Android `input` injects the tap. The H.264 encoder emits when the screen changes. The viewer only skips a backed-up P-frame (`decodeQueueSize > 8`) by waiting for the next IDR. Dropping one delta and decoding the next one is what paints broken blocks.

The on-phone stamp `tap x,y · Nms` is step 2's HTTP time only (browser → desktop-api → response). It does not include encode or decode. Health RTT on the market chip is step 0, a different request.

Live encoder at measurement time (`/health` on the stream host): H.264 running, 540×1200, bitrate 1.5 Mbps, `flush_idle_ms` 30, `flush_tick_ms` 87.7, idle `fps` 2.9 because the launcher was not moving (`kbps` 7). Idle fps is not the cap. The flush window is now capped at 96 ms (`H264_FLUSH_CAP_MS`) and stalls decay faster (`×0.96`), so one slow read does not pin every later frame. That applies on the next desktop-api process start.

## Audio

`/ws/h264` is still video-only. Device sound is a second socket, `/ws/audio`:

- Preferred: scrcpy-server `video=false audio=true audio_codec=opus`, forwarded as Opus, decoded in the page with WebCodecs `AudioDecoder`, played on an `AudioContext` (the user's phone or PC speakers).
- The viewer starts that context on the first tap inside the phone, or on the speaker button. Browsers will not start audio from the market page's "Open phone" click alone.
- `scripts/start-emulator-on-vm.sh` no longer passes `-no-audio`. An emulator that is **already** running with `-no-audio` has no guest audio HAL. Scrcpy will fail, `/health` → `audio.reason` will say so, and the phone shows that sentence. Restart the emulator to hear apps. `STRLIX_EMULATOR_AUDIO=off` puts `-no-audio` back if QEMU cannot open a backend.
- Optional: `STRLIX_AUDIO_PULSE=<source>` plus `ffmpeg` captures host Pulse as PCM if scrcpy audio cannot start.

Assistant TTS is unchanged: it is still host-synthesized and played in the browser. It is not the cloud phone's speaker.
