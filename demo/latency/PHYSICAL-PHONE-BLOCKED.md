# Physical-phone latency proof — BLOCKED

**Status:** BLOCKED: no physical USB Android device is attached to this box.
**Checked:** 2026-09-22 (IST)

## Exact blocker

`adb devices -l` on the box returned only:

```text
List of devices attached
127.0.0.1:5555         device product:sdk_gphone64_x86_64 model:sdk_gphone64_x86_64 device:emu64xa transport_id:1167
```

`127.0.0.1:5555` is a TCP ADB endpoint, not USB. The local port is an SSH forward to Azure VM `vm-zevi-cloudphone` (`20.115.117.71`), where the only device is `emulator-5554` running `sdk_gphone64_x86_64` (Android 14). Therefore this is emulator evidence only; it cannot certify physical display, digitizer, cellular/WAN, AEC, or glass-to-glass latency.

## What ran without a physical device

- Tool validation passed: `scripts/adb-tunnel.sh`, `scripts/start-emulator-on-vm.sh`, `scripts/qa_scrcpy_latency.py`, and `scripts/qa_h264_browser.py` syntax-checked successfully.
- The tunneled Azure emulator transport probe ran with `scripts/qa_scrcpy_latency.py`: 5 rounds, `source=scrcpy`, `size=360x800`, median **252.2 ms**, min **209.5 ms**, max **344.1 ms**, `glass_to_glass_under_100ms=false`. This is explicitly **not** a physical-phone or glass-to-glass result. Raw output was written outside the repository at `/tmp/strlix-latency-check/latency-azure-emulator-check.json`.
- The browser H.264 probe was attempted but stopped before its tap measurement: the viewer’s `.stage` intercepted the scripted HOME toolbar click. No browser latency result is claimed.

Do not relabel the emulator numbers as physical or sub-100 ms.

## Exact steps for Ankit to attach a phone

1. On the Android phone, enable Developer options (tap **Build number** seven times), then enable **USB debugging**.
2. Connect an unlocked phone with a data-capable USB cable; accept the phone’s **Allow USB debugging** RSA prompt.
3. From the Strlix checkout, run `adb devices -l`. The phone must show a unique USB serial in state `device`; do not use `127.0.0.1:5555` or any `emulator-*` entry.
4. Start/restart Pilot with `ADB_SERIAL=<that USB serial>` (and the normal `ADB_BIN` for the checkout) so port `8787` is using the phone, not the Azure emulator. Keep the phone unlocked and screen-on.
5. With Pilot serving on `http://127.0.0.1:8787`, run this **one measurement command** from the checkout:

```bash
python3 scripts/qa_scrcpy_latency.py --base http://127.0.0.1:8787 --rounds 10 --swipe-ms 80 --tag physical-usb --out demo/latency
```

This records swipe-to-first encoded-frame transport latency in `demo/latency/latency-physical-usb.json`. It is not by itself a glass-to-glass claim: pair it with the documented camera/LED slow-motion measurement, and report tap-to-first-frame and barge-to-TTS-silence separately. Never claim `<100 ms` unless the physical measurement actually supports it.
