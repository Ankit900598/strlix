# Strlix Dual-Backend Architecture

> **Provenance:** Claude Code (`claude -p --output-format stream-json --verbose`) was run with `CLAUDE_PROMPT_SHORT.md`. The session entered extended thinking (~6k+ thinking tokens, stream stuck at `assistant` thinking blocks) and never emitted final markdown within the ops window. Raw stream preserved as `claude-stream.jsonl` (36KB). This document is the **implementation-aligned architecture** matching the live split under `services/` + `packages/common`, written from the same design brief.

**Date:** 2026-09-21 IST · **Full research:** `RESEARCH-FULL.md` · **Azure URLs:** `AZURE-DEPLOY.md` · **RG:** `rg-zevi-cloudphone` (eastus2) · **Never touch:** `phonecodex-*` · **Never sign out** Azure/AWS

---

## 1. Executive summary & separation of concerns

Strlix is **phone-first**: AI lives in the Android app (`com.zevi.agent`) via chat, voice, and Accessibility. The desktop/web UI is a **mirror** of one bound cloud/physical device — not the product chat surface.

| Backend | Port | Owns | Must not own |
|---------|-----:|------|--------------|
| **android-api** | 8788 | Chat/LLM, voice STT/TTS hooks, Accessibility tool protocol, device JWT | ADB screencap, H.264 fan-out, web viewer |
| **desktop-api** | 8789 | H.264/WS + JPEG stream, tap/swipe/key, session bind, static viewer | In-phone chat LLM loop, a11y tool protocol |
| **session-broker** | 8791 | Device pool lease → desktop JWT (`sid` + `device_id`) | Media encode |
| **pilot monolith** | 8787 | Legacy all-in-one (kept until cutover) | — |

**Why split:** Chat QPS and stream/device scarcity scale differently. The overnight monolith on `:8787` made “scale” look like a viewer problem when the real ceiling is **one ADB serial**.

---

## 2. Capacity honesty (device pool)

> **One Azure emulator ≠ a billion phones.**

| Concurrent user type | Scarce resource | Phase-1 reality |
|----------------------|-----------------|-----------------|
| In-phone chat / voice | Azure OpenAI + android-api replicas | Design target **100k** with Redis rate limits + PTU |
| Desktop viewer (watch) | `devices × ~12` H.264 viewers | **12** (1 device) |
| Desktop controller (tap) | `devices × 1` | **1** |

Marketing “billion concurrent” is aspiration. Engineering phase-1: **10M DAU / 100k concurrent chat**; viewer capacity grows only with the **device fleet**.

`GET :8791/v1/devices` returns `capacity.honest_note` stating this.

---

## 3. Service map

```
Android APK  --JWT aud=android-api-->  android-api:8788 --> Azure OpenAI / Speech hooks
   | a11y runs tools on-device
Browser viewer --JWT aud=desktop-api--> desktop-api:8789 --> ADB / H.264
                                              |
                                         session-broker:8791 (device pool)
```

**Later:** regional `stream-edge` (scrcpy-server / WebRTC); broker routes `sid → edge + device`.  
**Queues (phase-2):** Azure Service Bus for async TTS, fleet ops, session expiry.

---

## 4. Repo layout

```
zevi-cloudphone/
├── app/                         # LEGACY pilot (:8787) — keep running
├── static/                      # phone-first viewer HTML
├── android-agent/               # APK
├── packages/common/             # strlix_common — JWT, config, errors
├── services/
│   ├── android-api/             # :8788
│   ├── desktop-api/             # :8789
│   └── session-broker/          # :8791
├── scripts/run-split.sh
└── demo/scale/
    ├── ARCHITECTURE-claude.md   # this file
    ├── SPLIT-PLAN.md
    └── CAPACITY.md
```

---

## 5. Auth & device sessions

- **HS256** JWT via `STRLIX_JWT_SECRET` (≥32 bytes). Phase-2: Entra External ID / JWKS; **claim shape unchanged**.
- Audiences: `android-api` | `desktop-api`
- Claims: `sub`, `aud`, `sid`, `device_id`, `scopes` (`chat|voice|tools` vs `stream|input`)
- Android: `POST /v1/auth/device` `{device_id}` → Bearer
- Desktop: `POST /v1/sessions/bind` → broker lease + Bearer (`input` only if controller)
- `STRLIX_REQUIRE_AUTH=0` by default (existing APK keeps working)

---

## 6. API sketches

### android-api (:8788)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/auth/device` | Mint android JWT |
| POST | `/v1/chat` (+ `/chat`) | LLM turn + a11y tool proposals |
| POST | `/v1/tools/result` | Phone reports a11y outcomes |
| POST | `/v1/voice/speak` | TTS hook (on-device preferred) |
| POST | `/v1/voice/stt` | STT transcript ingest |
| GET | `/health` | Liveness (no ADB) |

Tool names: `a11y_launch|a11y_tap|a11y_type|a11y_swipe|a11y_key|a11y_scroll`

### desktop-api (:8789)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/sessions/bind` | Lease device via broker |
| WS | `/ws/h264` | Annex-B AUs |
| WS | `/ws/stream` | JPEG fallback |
| GET | `/adb/preview` | Latest JPEG |
| POST | `/adb/tap\|swipe\|key\|type` | Input (controller scope) |
| GET | `/` | Phone-first viewer HTML |

### session-broker (:8791)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/devices` | Pool inventory + honest capacity |
| POST | `/v1/sessions` | Acquire lease + desktop JWT |
| GET/DELETE | `/v1/sessions/{sid}` | Inspect / release |

Docs: `http://127.0.0.1:8788/docs`, `:8789/docs`, `:8791/docs`

---

## 7. Data stores

| Store | Phase-1 | Phase-2 (10M DAU path) |
|-------|---------|-------------------------|
| Secrets | root `.env` | Azure Key Vault |
| Sessions / rate limits | in-process | Azure Cache for Redis |
| Accounts / devices | env-seeded 1 device | Azure Database for PostgreSQL |
| TTS audio | `demo/voice-audio/` | Blob Storage + CDN |
| Job queue | none | Service Bus / Storage Queue |
| LLM | Azure OpenAI `gpt-5.6-sol` | + PTU / regional failover |

---

## 8. Streaming fleet path

1. **Now:** `adb screenrecord` H.264 → WS (`app.h264_stream` reused by desktop-api)
2. **Next:** scrcpy-server on device VM
3. **Scale:** regional stream-edge; WebRTC to browsers; broker maps session → edge
4. **Never** put ADB screencap on the android-api hot path

---

## 9. Rate limits / backpressure / isolation

- Chat: `CHAT_RATE_PER_MIN=60` per sub/IP
- Input: `INPUT_RATE_PER_SEC=30` per IP
- H.264: `H264_MAX_CLIENTS=12` per device; late joiners get GOP replay
- WS heartbeat 15s / timeout 40s reclaims ghost tabs
- One `sid` ↔ one `device_id`; view-only sessions lack `input` scope

---

## 10. Migration without breaking pilot

```
:8787 monolith  ────────────── keep CF tunnel / demo
:8791 broker    ──┐
:8788 android   ──┼── additive split (./scripts/run-split.sh)
:8789 desktop   ──┘
```

1. Start split — **does not** kill uvicorn on 8787  
2. `adb reverse tcp:8788`; PilotClient prefers 8788, falls back 8787  
3. When desktop-api stream QA matches pilot, switch public tunnel to 8789  
4. Delete monolith routes only after both clients cut over  

**Port note:** **8790** is taken by box egress tunnel → broker listens on **8791**.  
**Caution:** Do not run pilot + desktop-api H.264 producers against the same ADB serial at once.

---

## 11. Phase roadmap

| Phase | Devices | Chat concurrent | Viewer slots | Work |
|------:|--------:|----------------:|-------------:|------|
| 0 (now) | 1 | pilot | 12 | Split services live |
| 1 | 10 | ~10k design | 120 | Redis sessions, APK URL cutover |
| 2 | 100–1k | 100k design | 1.2k–12k | VM scale set / device pool, Front Door |
| 3 | 10k+ | path to more | devices×12 | Multi-region edges, WebRTC, Entra auth |

---

## 12. Risks & non-goals

**Risks:** dual H.264 producers on one serial; short JWT secret; gpt-5.x rejecting `temperature`/`max_tokens` (use defaults + `max_completion_tokens`); conflating chat scale with viewer scale in decks.

**Non-goals:** restoring a big outside-web chat column as the product; touching `phonecodex-*`; signing out of cloud accounts; shipping OpenAI keys in the APK.

---

## 13. Azure deployment (2026-09-21 IST)

See **`AZURE-DEPLOY.md`** and **`RESEARCH-FULL.md`**.

| Service | Where |
|---------|--------|
| android-api | Azure Container Apps `ca-android-api` (eastus2, public HTTPS) |
| desktop-api + session-broker | systemd on `vm-zevi-cloudphone` (20.115.117.71:8789) |
| pilot `:8787` | Still on box — not broken by Azure deploy |

Placement rule (from research): chat BFF cloud-native next to OpenAI/Speech; stream BFF co-located with ADB/emulator.

---

## Live verification (2026-09-21 IST)

```bash
./scripts/run-split.sh
curl -s localhost:8788/health    # android-api
curl -s localhost:8789/health    # desktop-api
curl -s localhost:8791/health    # session-broker
curl -s localhost:8787/health    # pilot still up
```

Verified: `POST :8788/v1/chat` → `split-ok`; `POST :8789/v1/sessions/bind` → `pilot-emulator-1`; tap with desktop JWT ok.
