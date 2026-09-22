# Who owns the H.264 / ADB stream?

**Rule:** only **one** process may run an H.264 (or JPEG) producer against a given ADB serial.

| Process | Port | Owns stream? | Owns chat? |
|---------|-----:|:------------:|:----------:|
| Pilot monolith `app.main` | 8787 | **YES (default for demo / CF tunnel)** | legacy yes |
| **desktop-api** | 8789 | **YES if you point viewers here** | no |
| **android-api** | 8788 | **NO** — never starts ADB encode | **YES (APK target)** |
| session-broker | 8791 | no | no |

## Phase-1 ops choice (pick one)

### A — Demo / public tunnel stays on pilot (recommended while validating APK cutover)
- Keep `uvicorn app.main:app :8787` as the **sole** stream producer.
- Do **not** open `/ws/h264` on desktop-api against the same serial.
- APK chat → android-api `:8788` (safe; no stream conflict).

### B — Viewer cutover to desktop-api
- Stop using pilot’s `/ws/h264` (or stop pilot entirely).
- Run desktop-api `:8789` as the **sole** stream producer.
- Point browser / CF tunnel at `:8789`.

## How to check who is encoding

```bash
curl -s localhost:8787/health | jq '{service:"pilot", h264:.h264}'
curl -s localhost:8789/health | jq '{service:.service, h264:.h264}'
# android-api must never show an encoder:
curl -s localhost:8788/health | jq .
```

If both pilot and desktop-api report `h264.running=true` on the same `ADB_SERIAL`, kill one.

## Why this matters

`screenrecord` / scrcpy-style encode is exclusive per device. Two producers → stalls, black frames, ADB contention, false “viewer is slow” bugs.

## Snapshot (2026-09-21 IST cutover)
- Emulator ADB: `127.0.0.1:5555` (SSH tunnel).
- APK chat owner: **android-api :8788** (verified).
- Prefer keeping **pilot :8787** as the sole stream producer until desktop-api viewer cutover.
- desktop-api :8789 may be up for health/bind tests — **do not open `/ws/h264`** against the same serial while pilot is streaming.

## Soft-launch Redroid serial (2026-09-22 IST)

- AWS Redroid ADB (after SSM): `127.0.0.1:5556` — `scripts/adb-aws-redroid.sh --watch`
- Env on stream host: `ADB_SERIAL=127.0.0.1:5556` · `STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1`
- Azure emulator remains `127.0.0.1:5555` / `pilot-emulator-1` (default)
- Still one producer per serial — do not open pilot + desktop-api `/ws/h264` on the same serial

