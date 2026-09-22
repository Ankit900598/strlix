# Phone touch, fullscreen, and speakers

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
4. Android `input` injects the tap. The H.264 encoder emits when the screen changes. The viewer drops late frames (`decodeQueueSize > 1`).

The on-phone stamp `tap x,y · Nms` is step 2's HTTP time only (browser → desktop-api → response). It does not include encode or decode. Health RTT on the market chip is step 0, a different request.

Live encoder at measurement time (`/health` on the stream host): H.264 running, 540×1200, bitrate 1.5 Mbps, `flush_idle_ms` 30, `flush_tick_ms` 87.7, idle `fps` 2.9 because the launcher was not moving (`kbps` 7). Idle fps is not the cap. The flush window is now capped at 96 ms (`H264_FLUSH_CAP_MS`) and stalls decay faster (`×0.96`), so one slow read does not pin every later frame. That applies on the next desktop-api process start.

## Audio

`/ws/h264` is still video-only. Device sound is a second socket, `/ws/audio`:

- Preferred: scrcpy-server `video=false audio=true audio_codec=opus`, forwarded as Opus, decoded in the page with WebCodecs `AudioDecoder`, played on an `AudioContext` (the user's phone or PC speakers).
- The viewer starts that context on the first tap inside the phone, or on the speaker button. Browsers will not start audio from the market page's "Open phone" click alone.
- `scripts/start-emulator-on-vm.sh` no longer passes `-no-audio`. An emulator that is **already** running with `-no-audio` has no guest audio HAL. Scrcpy will fail, `/health` → `audio.reason` will say so, and the phone shows that sentence. Restart the emulator to hear apps. `STRLIX_EMULATOR_AUDIO=off` puts `-no-audio` back if QEMU cannot open a backend.
- Optional: `STRLIX_AUDIO_PULSE=<source>` plus `ffmpeg` captures host Pulse as PCM if scrcpy audio cannot start.

Assistant TTS is unchanged: it is still host-synthesized and played in the browser. It is not the cloud phone's speaker.
