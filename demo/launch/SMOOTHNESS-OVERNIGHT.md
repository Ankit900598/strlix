# Smoothness overnight — gaming, movies, downloads

**Date:** 2026-09-22. Soft launch stays on the Azure emulator, scrcpy H.264 + Opus, WebSocket, Azure Front Door. This note is what that path can honestly do, what this PR changes, and how a started GPU Redroid session would take over later.

The AWS GPU worker was **not** started. Stripe and the domain were not touched. Azure scripts stay on `rg-zevi-cloudphone`.

## What “as smooth as possible” means here

A phone in your hand has no network. Strlix always has at least one round trip for the finger and one for the pixels. Feeling “vastly better than a personal phone” is about the picture, the sound, and the frame rate. It is not about beating ~16 ms of local touch. If the user’s RTT is 80 ms, the floor is already about two of those plus encode time.

Measured in this repo, not guessed:

| Fact | Where |
| --- | --- |
| Front Door `/health` samples 157–986 ms | `demo/launch/PHONE-TOUCH-AUDIO.md` |
| Host swipe → next H.264 access unit ~250 ms after scrcpy (was ~576 ms on `screenrecord`) | `demo/overnight/SCRCPY.md` |
| That 250 ms is **not** glass-to-glass. It stops when the bytes exist on the host. | same |

Anything below that is not in the tables is an estimate and is labeled as one.

## What the serious stacks actually do

### Cloud gaming (GeForce Now, Xbox Cloud, Luna, Moonlight)

They do not send JPEGs and they do not wait for `pointerup`.

- **Encode on a GPU.** NVIDIA’s encoder API has an ultra-low-latency tuning and presets P1 (fastest) through P7. The usual cloud-gaming choice is ultra-low-latency, CBR, no B-frames. NVENC on a T4 is that class of encoder. Published guidance is the [NVENC programming guide](https://docs.nvidia.com/video-technologies/video-codec-sdk/13.1/nvenc-video-encoder-api-prog-guide/index.html). A few milliseconds to about 10 ms of encode is the shape of that preset; we have not measured it on our worker.
- **Transport is UDP**, or WebRTC (which is UDP plus a TURN fallback). Moonlight is RTP. They do not put media through an HTTP reverse proxy.
- **The client drops late frames** instead of letting a queue grow. A queue is latency you can see.
- **Input is a datagram sent on contact**, not an HTTP request after the finger lifts. Client-side prediction of *the game’s physics* is not something a cloud phone can do: Android is the simulation, and we don’t have it. What they do predict is only the local cursor. We already paint the ripple immediately. This PR also sends the press on `pointerdown`.
- **Audio is Opus** with a jitter buffer (WebRTC’s is NetEQ, often aiming around a few tens of milliseconds). In-band FEC is a libopus encoder switch (`useinbandfec`) plus a loss percentage. The decoder can only use FEC if it is told a packet was lost. WebCodecs `AudioDecoder.decode()` does not have that call.

### Cloud phones (now.gg, Anbox Cloud, Genymotion, scrcpy itself)

- The product path for a browser is **WebRTC or a custom streaming gateway**, not `adb shell input tap`.
- **Multi-touch** is a streaming-protocol message with a pointer id. scrcpy’s control socket does this (up to 10 pointers). `adb shell input motionevent` does not: it is one finger, no slot.
- **Sound is the Android mix**, stereo, after the audio HAL. Spatial audio inside an app does not survive that mix. A cloud phone cannot give you per-app 3D audio unless the app’s spatializer runs and we capture more than a stereo bus. We capture the stereo bus. That limit stays.
- **scrcpy 4.1** (our pinned server) added `min_size_alignment` because “multiple of 8” was sometimes too loose. H.264 macroblocks are 16×16. The emulator’s software encoder reports a weaker alignment, so a 1080×2400 screen limited to 1080 became **484×1080** (486 rounded down to a multiple of 4). That dirty edge is the YouTube smear. Docs: [scrcpy video](https://github.com/Genymobile/scrcpy/blob/v4.1/doc/video.md), [scrcpy 4.0 notes](https://github.com/Genymobile/scrcpy/releases/tag/v4.0) (`--min-size-alignment`), [scrcpy 4.1](https://github.com/Genymobile/scrcpy/releases/tag/v4.1).

### Azure Front Door

Front Door serves HTTP, HTTPS, and WebSocket. It does not proxy UDP, ICE, or RTP. WebSocket idle timeout is 5 minutes and a socket is dropped by 4 hours ([Microsoft’s WebSocket doc](https://learn.microsoft.com/en-us/azure/frontdoor/standard-premium/websocket)). The soft-launch viewer can keep using `wss://…/ws/h264`. It cannot grow a WebRTC media path *through* Front Door.

`app/smoothness.py` → `webrtc_spike_status()` is the spike. It returns `enabled: false`. `?webrtc=1` on the viewer only logs that sentence. `/ws/h264` is unchanged.

## What this PR changes on the live path

### Picture

- `min_size_alignment=16` on the scrcpy video server (4.1 honors it; an older jar logs the unknown key and continues).
- `choose_scrcpy_max_size()` picks the cap so that rounding to 4, 8, **or** 16 still lands on multiples of 16. For the 1080×2400 phone at cap 1080 that is **max_size 1072 → 480×1072**, not 484×1080. Checked in `scripts/test-smoothness.py`.
- `screenrecord` fallback gets the same 16-pixel rule (`align_screenrecord_size`). 1080×2400 at width cap 1080 becomes 1072×2368.
- Codec options add `bitrate-mode:int=2` (CBR) and `priority:int=0` (realtime). VBR is what lets a YouTube scene eat the bit budget and then fall apart. CBR spends the budget steadily. Rollback: set `SCRCPY_CODEC_OPTIONS` back to `i-frame-interval:int=1,latency:int=1`.
- The viewer still drops late P-frames while you are touching (`decodeQueueSize > 1` for 5 s after input). When you are just watching, it allows a queue of 3 so a single late frame does not tear the movie until the next keyframe.

### Sound

Opus in-band FEC is **not** turned on. Android’s MediaCodec Opus encoder has no portable key for it, and a wrong key fails `configure` and kills audio. `DEVICE_AUDIO_CODEC_OPTIONS` is there if a specific encoder accepts one. Default is empty.

What did ship:

- **OpusHead is never decoded as audio.** If the payload starts with `OpusHead`, it is a codec description even when flags=0. That is the client-side half of the confirmed decode error. A separate fix can still set the config bit; both are safe together. `OpusTags` is dropped.
- The broker **replays the last OpusHead** to a subscriber who connected after it was sent.
- A PTS jump (backwards, or forward by more than 500 ms) sets flag bit 1. The viewer resets its playout clock instead of stretching a hole.
- **Jitter target starts at 40 ms** (two 20 ms Opus frames) and moves between 40 and 120 ms. An underrun grows it by 16 ms. A buffer that sits 30 ms above the target shrinks by 8 ms. One lost packet is concealed by replaying the previous buffer quieter, once. That is concealment, not FEC. WebCodecs cannot ask libopus to apply FEC.
- Default Opus bitrate is 160 kbit/s (was 128). Still one stereo mix.

### Touch

- If `/health` → `input.motion` is true (the image’s `input` help lists `motionevent`), the viewer sends **DOWN on pointerdown**, coalesced **MOVE** (at most one in flight, 50 ms, 3 px), and **UP on pointerup**. The game sees the press one finger-down earlier. Previously the whole gesture waited for lift, then one `input swipe`.
- MOVE requests are serialized. Parallel `fetch` would reorder a drag. A backlog of every move would be N × RTT late, so only the latest MOVE is kept.
- The old tap/swipe path remains when motion is not probed or the device has no `motionevent`.
- **One finger only.** A second pointer is ignored. Two-thumb games need scrcpy’s control socket, which is not on in this PR (`control=false` so the video server does not fight `adb`).
- **Warm path.** Process start and every `/ws/h264` connect call `warm_input`: connect ADB, probe motion, cache `wm size`, push the scrcpy jar if the bytes differ, open the long-lived shell. The first tap should not pay for a process spawn or a jar upload.

### What did not change

- No WebRTC media. No new public debug port.
- Assistant TTS is still host audio, not the phone’s speaker. Phone sound is `/ws/audio`.
- Input rate limit stays 30/s. Motion is coalesced so a drag does not eat that budget.
- Stripe, domain, and the GPU instance were left alone.

## GPU Redroid cutover (when someone starts the instance)

The worker `i-0531c567f620877c3` (`g4dn.xlarge`, T4) is documented in `infra/gpu-worker/aws/WORKER-LIVE.md`. This agent did not start it. While it is stopped there is nothing to measure.

### Do this only after the instance is running

1. Start is an operator action, not this PR: `aws ec2 start-instances --region us-east-1 --instance-ids i-0531c567f620877c3`. Wait until SSM is Online.
2. On the stream host (Azure VM in `rg-zevi-cloudphone` only): `./scripts/adb-aws-redroid.sh` so `127.0.0.1:5556` is the guest. Do not open the security group to the world.
3. Point the desktop-api process at it and restart that process:

   ```bash
   export ADB_SERIAL=127.0.0.1:5556
   export STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1
   ```

4. Keep **one** H.264 producer on that serial. `demo/scale/STREAM-OWNER.md`: do not open pilot `:8787` and desktop-api `:8789` `/ws/h264` together.
5. Confirm `adb shell getprop sys.boot_completed` is `1`, then `/health` shows `h264.source=scrcpy`, `h264.size` both multiples of 16, and `audio.source=scrcpy`.
6. Stop the instance when the session is over. Do not terminate it. Public IP changes on the next start; the SSM tunnel does not care.

### What you actually gain

`androidboot.redroid_gpu_mode=guest` draws with the host GPU inside the guest. Games and YouTube stop going through SwiftShader. **Encode is still MediaCodec inside the guest.** Guest GPU is not NVENC. Glass-to-glass is still two Front Door crossings plus that encoder.

The path that can approach cloud-gaming latency is a later project:

1. Capture the guest framebuffer on the **host**.
2. Encode with NVENC, ultra-low-latency tuning, preset P1, CBR, no B-frames. H.264 width/height should still be multiples of 16 so the browser’s decoder is not guessing a crop. (HEVC on this generation of NVENC pads coded height to 32 and sets a conformance window; we would stay on H.264 for the WebCodecs client we already have.)
3. Send media over UDP or WebRTC to a hop that is **not** Front Door. Signaling can stay HTTPS. Media cannot.
4. Only then does the jitter buffer of 20–40 ms plus one RTT become the budget, instead of two HTTP RTTs plus a software encoder.

Until that exists, “start the T4 and set `ADB_SERIAL`” is the right cutover for a gaming session, and it should be said that way to users: smoother motion, same network floor.

## Latency budget

Numbers are milliseconds. “Repo” means we measured it and wrote it down. “Estimate” means it follows from how the stage works.

| Stage | Emulator + WS + Front Door (today) | Redroid guest GPU + same WS | Host NVENC + UDP (not built) |
| --- | --- | --- | --- |
| Touch network | 1× RTT. Repo: Front Door health 157–986 ms | Same | ~1× RTT, UDP, no Front Door |
| Inject | ~5–20 after the warm shell. Estimate, was a process spawn before | Same | scrcpy control, a few ms. Estimate |
| Compose | SwiftShader. The large, ugly term | Guest GPU. Estimate: tens of ms, **not measured** (instance stayed stopped) | Same draw, then NVENC |
| Encode | Software MediaCodec. Repo: swipe→AU ~250 ms on the old host clock, which includes compose | Still MediaCodec. Estimate: lower because the frame is already on a GPU | NVENC ull. Estimate: a few ms to ~10 |
| Video network | 1× RTT on the WebSocket | Same | ~1× RTT UDP |
| Decode + paint | WebCodecs, a few ms + one frame. The HUD’s `decodeMs` is the live number | Same | Same class |
| Audio | 20 ms frame + 40–120 ms adaptive buffer | Same | NetEQ-style ~20–40 ms if we ever have real FEC |

**Floor today:** two RTTs + the emulator encoder. An 80 ms RTT is already ~160 ms before encode. A 200 ms RTT cannot feel like a local phone no matter what we do to the codec.

**Floor after the T4 is started but encode stays in the guest:** two RTTs still, with a better picture under motion.

**Floor after host NVENC and a UDP hop:** on the order of two RTTs of *UDP* plus ~10 ms encode plus a small jitter buffer. That is the first time the physics match a cloud-gaming product. It is not this deploy.

## What you should understand

1. **16 vs 4.** Video encoders think in blocks. A width of 484 is 30 blocks plus a sliver. The software encoder paints the sliver wrong. Forcing 16 fixes the sliver without a new codec.
2. **DOWN on pointerdown** saves the time the finger was down (often 80–200 ms) plus it lets a game see a drag. It does not save the RTT.
3. **Jitter is a trade.** 40 ms hides one late Opus packet. 120 ms hides a bad Wi-Fi moment and makes dialogue late. The viewer moves between them instead of us picking one forever.
4. **FEC is not concealment.** FEC is extra data in the *next* packet that rebuilds the lost one. We cannot ask the emulator’s Opus encoder for it safely, and WebCodecs will not apply it. Replaying the last slice quietly is the honest fallback.
5. **Front Door is an HTTP product.** WebSocket video can ride it. WebRTC media cannot. That is why the spike is a function that says no, not a second player.

## How to check

```bash
python3 scripts/test-smoothness.py
python3 scripts/test-phone-touch-audio.py
```

On a running stream host, after deploy: `/health` → `h264.size` both divisible by 16, `h264.scrcpy_min_size_alignment` 16, `input.motion` true on an API 28+ image, `audio.jitter_ms` 40. Play a video, confirm the speaker button is not stuck on a decode error. Drag in a game: the press should start at contact, not at lift.
