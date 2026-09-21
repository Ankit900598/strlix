# APK → android-api cutover (2026-09-21 IST)

## What changed
- `PilotClient` probe order: **8788 android-api first**, then 8787 pilot, then public HTTPS.
- Chat path on 8788: `POST /v1/chat` (pilot fallback still `POST /chat`).
- Live `/voice/turn` falls back to pilot if android-api returns 404/405.
- `install-and-launch.sh` + `adb-reverse-apis.sh`: `adb reverse tcp:8788` **and** `tcp:8787`.
- APK `0.3.1-split` (versionCode 4) installed on emulator `127.0.0.1:5555`.

## Verified on device
```
StrlixPilot: health OK via http://127.0.0.1:8788 (android-api · …)
StrlixPilot: chat → http://127.0.0.1:8788/v1/chat
android-api.log: POST /v1/chat 200
UI reply: "verify8788hit received."
```

## Stream ownership
See `STREAM-OWNER.md`. android-api never encodes. Do not run pilot + desktop-api H.264 producers on the same ADB serial.
