# Capacity honesty — Strlix dual backends

**Date:** 2026-09-21 IST

## One line

> One Azure emulator + one AWS Redroid T4 is not a billion phones. Chat scales on `android-api`. Viewer sessions scale with the **device pool**.

## Phase-1 numbers (what we run today)

| Resource | Count | Notes |
|----------|------:|-------|
| Azure emulator / ADB serial | **1** | `pilot-emulator-1` via SSH tunnel (`scripts/adb-tunnel.sh`) |
| AWS Redroid T4 / ADB serial | **1** | `aws-redroid-t4-1` via SSM (`scripts/adb-aws-redroid.sh` → `127.0.0.1:5556`) |
| H.264 shared viewers / device | **12** | `H264_MAX_CLIENTS` |
| Tap controllers / device | **1** | session `controller=true` |
| android-api replicas | 1 (box) | chat/voice only — no screencap |
| desktop-api replicas | 1 (box) | reuses `app.h264_stream` |
| session-broker | 1 (box) | in-memory pool on **:8791** |

## What "100k concurrent" means

| Kind of concurrent user | Scales with | Phase-1 realistic |
|-------------------------|-------------|-------------------|
| In-phone chat / voice (Android) | android-api + Azure OpenAI QPS | Design for 100k with Redis rate limits + PTU |
| Desktop viewer watching a phone | devices × ~12 viewers | **24** theoretical (2 devices × 12); broker still seeds **1** active |
| Desktop viewer controlling taps | devices × 1 controller | **1** today (seeded device) |

Path to more viewers = **grow the device fleet** (Azure VM scale set / Redroid-or-emulator pool / physical farm), not bigger FastAPI.

## Ports (do not collide with box egress tunnel on 8790)

| Service | Port |
|---------|-----:|
| pilot monolith (legacy) | 8787 |
| android-api | 8788 |
| desktop-api | 8789 |
| session-broker | **8791** |

## Run

```bash
./scripts/run-split.sh
curl -s localhost:8788/health | jq .service
curl -s localhost:8789/health | jq .service
curl -s localhost:8791/health | jq .service
```
