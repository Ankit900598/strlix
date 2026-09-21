# Strlix Dual-Backend Split Plan (implementable)

**Status:** phase-1 scaffolding live alongside pilot monolith `:8787`  
**Date:** 2026-09-21 (IST)  
**RG:** `rg-zevi-cloudphone` only · never touch `phonecodex-*`

## Why two backends

| Surface | Traffic shape | Scarce resource |
|---------|---------------|-----------------|
| **Android in-phone app** | Short HTTPS: chat, voice hooks, Accessibility tool protocol | LLM tokens / QPS |
| **Desktop/viewer** | Long-lived WS video + input | Physical/cloud **devices** |

Mixing them in one FastAPI process on `:8787` couples chat scale to ADB stream fan-out. They must scale independently.

### Honest capacity (read this twice)

> **One Azure emulator ≠ a billion phones.**

- **Chat-only concurrent users** scale on `android-api` (stateless-ish + Azure OpenAI + Redis rate limits).
- **Viewer sessions** consume a **device pool** slot via `session-broker`.  
  Phase-1 pool size = **1** (`pilot-emulator-1`, ADB `127.0.0.1:5555`).  
  Viewer concurrency ≈ `devices × ~12 shared H.264 viewers` (and **1 controller** for taps).
- Marketing "billion concurrent" is an aspiration. Engineering phase-1 design target: **10M DAU / 100k concurrent chat**; viewer capacity grows only as the device fleet grows.

---

## Repo / folder layout

```
zevi-cloudphone/
├── app/                      # LEGACY monolith (pilot) — keep running on :8787
├── static/                   # phone-first viewer HTML (served by pilot + desktop-api)
├── android-agent/            # com.zevi.agent APK
├── packages/
│   └── common/               # strlix_common: JWT auth, config, errors
├── services/
│   ├── android-api/          # :8788 — chat, voice hooks, a11y tool protocol
│   ├── desktop-api/          # :8789 — H.264/WS, tap/swipe, session bind
│   └── session-broker/       # :8791 — device pool lease → desktop JWT
├── demo/scale/
│   ├── ARCHITECTURE-claude.md
│   ├── SPLIT-PLAN.md         # this file
│   └── CLAUDE_PROMPT.md
└── scripts/
    └── run-split.sh          # start broker + android-api + desktop-api
```

---

## Services

### 1. `packages/common` (`strlix_common`)
- `TokenService` — HS256 JWT (`STRLIX_JWT_SECRET`), audiences `android-api` | `desktop-api`
- Claims: `sub`, `aud`, `sid`, `device_id`, `scopes`
- `CommonSettings` — Azure OpenAI / Speech / ADB / rate env from root `.env`
- Phase-2: swap secret for Azure Entra External ID / JWKS; claim shape stays

### 2. `services/android-api` — port **8788**
| Route | Purpose |
|-------|---------|
| `GET /health` | liveness; **no ADB** |
| `POST /v1/auth/device` | mint android JWT from `device_id` |
| `POST /v1/chat` (+ alias `POST /chat`) | Azure OpenAI + Accessibility tool proposals |
| `POST /v1/tools/result` | phone reports a11y outcomes |
| `POST /v1/voice/speak` | TTS hook (on-device preferred) |
| `POST /v1/voice/stt` | STT transcript ingest |
| `GET /v1/openapi-sketch` | compact map |

**Not here:** `/ws/h264`, `/adb/*`, web static viewer.

**Agent protocol:** LLM proposes `a11y_tap|swipe|type|key|launch|scroll`; phone executes via `ZeviAccessibilityService` and may POST results. No cloud screencap for millions of phones.

### 3. `services/desktop-api` — port **8789**
| Route | Purpose |
|-------|---------|
| `GET /` | existing `static/index.html` phone-first viewer |
| `GET /health` | ADB + stream + broker |
| `POST /v1/sessions/bind` | acquire device via broker → desktop JWT |
| `WS /ws/h264` | H.264 Annex-B (reuses `app.h264_stream`) |
| `WS /ws/stream` | JPEG fallback |
| `GET /adb/preview`, `GET /adb/size` | stills / geometry |
| `POST /adb/tap\|swipe\|key\|type` | input (requires `input` scope) |

**Not here:** `/chat`, Accessibility tool protocol.

Phase-1 reuses `app.adb_client` / `app.h264_stream` against the pilot serial so behavior matches `:8787`. Later: stream-edge fleet (scrcpy-server / WebRTC) per region.

### 4. `services/session-broker` — port **8791**
| Route | Purpose |
|-------|---------|
| `GET /health` | capacity report |
| `GET /v1/devices` | pool inventory |
| `POST /v1/sessions` | lease device → session + desktop JWT |
| `GET/DELETE /v1/sessions/{sid}` | inspect / release |

In-memory pool today; Redis + Postgres for multi-replica later.

---

## How clients point where

| Client | Base URL (phase-1 local) | Notes |
|--------|--------------------------|-------|
| Android APK `PilotClient` | `http://10.0.2.2:8788` (emulator) or `adb reverse tcp:8788` | Prefer android-api; keep `:8787` reverse as fallback until cutover |
| Desktop browser | `http://127.0.0.1:8789/` or CF tunnel → desktop-api | Stream + tap only |
| Ops / pilot demo | `http://127.0.0.1:8787/` | Unchanged monolith until cutover |

### Android cutover steps
1. Run android-api on 8788 (done).
2. `adb reverse tcp:8788 tcp:8788` in addition to 8787.
3. Update `PilotClient` host preference: try `…:8788/v1/chat` then fall back `:8787/chat`.
4. When stable, set `STRLIX_REQUIRE_AUTH=1` and mint via `/v1/auth/device`.

### Desktop cutover steps
1. Point CF tunnel / public URL at `:8789` (or path-route `/` → desktop, `/chat` stays internal).
2. Viewer calls `POST /v1/sessions/bind` once, stores Bearer, sends on input routes (optional phase-1).

---

## OpenAPI sketch (condensed)

```yaml
# android-api
POST /v1/chat:
  request: { message: string, history?: object[], tool_results?: ToolResult[], language?: string }
  response: { ok, reply, tools: [{ id, name, args }], model?, usage? }

# desktop-api
POST /v1/sessions/bind:
  request: { user_id, ttl_s? }
  response: { session: { sid, device_id, adb_serial, controller }, access_token }
WS /ws/h264: binary AU frames after JSON hello (same as pilot)
POST /adb/tap: { x, y } → { ok }

# session-broker
POST /v1/sessions: { user_id, ttl_s?, prefer_device? } → session + access_token
```

Full interactive docs: `http://127.0.0.1:8788/docs`, `:8789/docs`, `:8791/docs`.

---

## Data stores (phase roadmap)

| Store | Phase-1 | Phase-2 (10M DAU path) |
|-------|---------|-------------------------|
| Secrets | root `.env` | Azure Key Vault |
| Sessions / rate limits | in-process dicts | Azure Cache for Redis |
| Accounts / devices | env-seeded 1 device | Azure Database for PostgreSQL |
| TTS audio | `demo/voice-audio/` (desktop Live) | Blob Storage + CDN |
| Job queue | none | Azure Service Bus / Storage Queue (async TTS, fleet ops) |
| LLM | Azure OpenAI `gpt-5.6-sol` | same + PTU / regional failover |

---

## Streaming fleet (path beyond screenrecord)

1. **Now:** `adb screenrecord` H.264 → WS (desktop-api / pilot).
2. **Next:** scrcpy-server on device VM, encoder closer to SurfaceFlinger.
3. **Scale:** regional **stream-edge** nodes in Azure (eastus2 first); WebRTC for browser; session-broker routes `sid → edge + device`.
4. Never put ADB screencap on the android-api hot path.

---

## Rate limits (phase-1 defaults)

- android-api chat: `CHAT_RATE_PER_MIN=60` per sub/IP
- desktop-api input: `INPUT_RATE_PER_SEC=30` per IP
- H.264 viewers / device: `H264_MAX_CLIENTS=12`
- Auth optional until `STRLIX_REQUIRE_AUTH=1`

---

## Migration without breaking the pilot

```
:8787 monolith  ──────────────────────────── keep serving demo + CF tunnel
:8791 broker    ──┐
:8788 android   ──┼── new split (additive)
:8789 desktop   ──┘
```

1. Start split with `./scripts/run-split.sh` — does **not** kill uvicorn on 8787.
2. Validate health on 8788/8789/8791.
3. Point one Android build at 8788; keep public demo on 8787.
4. When desktop-api matches pilot stream QA, switch public tunnel to 8789 and leave `/chat` proxy or android-only.
5. Delete monolith routes only after both clients are cut over.

---

## Run

```bash
cd /workspace/zevi-cloudphone
./scripts/run-split.sh          # broker 8791, android 8788, desktop 8789
curl -s localhost:8788/health | jq .
curl -s localhost:8789/health | jq .
curl -s localhost:8791/health | jq .
# pilot still:
curl -s localhost:8787/health | jq .
```

---

## Next concrete steps

1. Wire `PilotClient.java` base URL preference → `:8788` with fallback `:8787`.
2. Redis-backed rate limit + session store (still single region eastus2).
3. Register N emulator/device workers into session-broker (VM scale set).
4. Path-based ingress (Azure Front Door / App Gateway): `api.strlix…/android/*` vs `/viewer/*`.
5. Replace HS256 with Entra External ID before any public launch.
6. Stream-edge (scrcpy/WebRTC) spike; keep screenrecord as fallback.
