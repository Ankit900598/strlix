# Real-device &lt;100ms path — emulator ceilings & physical checklist

**Updated:** 2026-09-21 ~19:45 IST (Asia/Calcutta)  
**Audience:** next agent / Ankit demo prep  
**Related evidence:** `demo/overnight/qa/latency-*.json` (emulator scrcpy tuning)

## What the emulator cannot do

| Ceiling | Why |
|---------|-----|
| True display→eye &lt;100ms interaction | Emulator frames go host GPU → QEMU → ADB/scrcpy encode → network/loopback → browser decode. Even on localhost, software encode + vsync stacks often land **150–400ms+** glass-to-glass. |
| Real WebRTC APM / AEC quality | Playwright + fake media devices do not exercise chromium AEC3 against a speaker. Barge VAD can be green on fake mic while physical USB/headset still false-barges. |
| WAN / cellular RTT | Emulator is loopback. Production cloud-phone path adds ACA/VM hop + user ISP. |
| GPU encode assist | Azure GPU worker is **NO-GO tonight** (quota=0). Emulator cannot stand in for NVENC/CUDA assist. |
| Real-app golden intents | Fixture APK (`com.zevi.goldenfixture`) proves harness wiring, **not** Gmail/Chrome/Photos account flows. |
| Touch sampling / input coalescing | Emulator input injection ≠ real digitizer rates; swipe feel differs. |

Overnight QA (`latency-scrcpy-tuned-summary.json` etc.) is useful for **relative** A/B of bitrate/FPS/codec flags — treat absolute ms as emulator-local, not product SLA.

## Target path for &lt;100ms (physical)

```
Physical Android (USB or low-latency Wi‑Fi)
  → ws-scrcpy / scrcpy server on device (H.264)
  → host viewer (Pilót :8787 or market stream)
  → phone-first bezel (static/index.html)
```

Stretch after GPU quota: device → encode assist on `NC4as_T4_v3` → viewer (still one hop; deallocate when idle).

## Physical device + ws-scrcpy checklist

1. **Device**
   - [ ] Developer options + USB debugging (or wireless debug on same LAN)
   - [ ] Stay-awake while charging; disable aggressive battery killers for scrcpy/helper
   - [ ] Unlock + screen on; confirm `adb devices` shows `device` (not `unauthorized`)
2. **Host**
   - [ ] Same machine as Pilot (`app/main.py` :8787) or VM `vm-zevi-cloudphone` with USB/IP forward
   - [ ] `scrcpy` / ws-scrcpy build matched to device API; prefer H.264 baseline, capped bitrate for demo Wi‑Fi
   - [ ] Flag set: low latency over quality (`--max-fps 60` or 30, bitrate trial 4–8 Mbps)
3. **Viewer**
   - [ ] Open bezel over **localhost or HTTPS** (AudioWorklet / mic permissions)
   - [ ] Live barge: physical mic; verify `window.__strlixLive.bargeStats.apm.aec === true`
   - [ ] Optional: `?bargeWorklet=1` after analyser baseline is clean
4. **Measure (honest)**
   - [ ] Camera-on-screen stopwatch OR LED flash + phone camera slow-mo for glass-to-glass
   - [ ] Log tap→first-frame and barge→TTS-silence separately (do not average them into one vanity number)
   - [ ] Record network RTT (`ping` to host) so &lt;100ms claims are not eaten by Wi‑Fi

## Golden intents on real apps — harness outline

Existing offline path (keep):

- `demo/ui-vision/golden-intent-eval/intents.json` (12 intents)
- `scripts/golden_intents_eval.py` — android-api contract/plan; Pilot gated with `--allow-device-actions`
- Fixture APK provider — synthetic 12/12 (not production apps)

**Real-app harness (outline — not claiming done):**

```
real_apps/
  accounts.md          # test Gmail/Chrome profiles; no prod credentials in git
  preconditions.json   # package installed, logged-in seed, locale
  runners/
    adb_ui.py          # optional uiautomator dump hooks
  postconditions/      # screenshot+a11y asserts per intent id
  reports/             # separate from fixture reports
```

Rules:

1. Default **read-only** proposals via android-api; Pilot execution requires explicit `--allow-device-actions` and a disposable account.
2. Destructive intents (send email, delete) stop at Needs-you / confirmation — never auto-complete in CI.
3. Score axes stay split: **contract / plan / completion** — do not collapse into one % for investor slides.
4. Emulator fixture numbers must not be relabeled as “real Gmail 95%”.

## Link to credit-burn

- GPU encode assist: blocked on quota (`infra/gpu-worker/REQUEST-quota.md`).
- Tonight: ship checklist + keep emulator tuning artifacts as relative baselines.
- When physical device is on the desk: run barge + one golden real-app intent, file report under `demo/ui-vision/golden-intent-eval/reports/real-device-…`.
