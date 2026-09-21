# Implementation Status — Cloud Phone Market + Azure Security Foundation

**Updated:** 2026-09-21 18:34 IST

## Shipped — billion-user security foundation

| Item | Status | Notes |
|------|--------|-------|
| Architecture doc | **Done** | `AZURE-BACKEND.md` |
| Privacy checklist | **Done** | `PRIVACY-SECURITY.md` |
| Bicep modules | **Done** | KV, PG (centralus), App Insights, market-api-aca, redis-aca |
| Key Vault | **Live** | `kv-zevi-strlix` |
| Postgres Flexible B1ms | **Live** | `psql-zevi-strlix` @ centralus |
| RLS migrations | **Applied** | `services/market-api/migrations/001–003` |
| App Insights | **Live** | `appi-zevi-strlix` |
| Redis | **Live** | `ca-redis` internal TCP (target 6379 / frontend 6380); market-api sessions use a Redis 7 sidecar because this Consumption CAE blackholes cross-app TCP |
| market-api 0.2.2 | **Live** | Postgres+RLS, JWT pair, Redis-backed sessions/rate limits, privacy APIs |
| ACA `ca-market-api` | **Live** | https://ca-market-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io |
| RLS test | **Pass** | `scripts/test-market-rls.py` |
| Redis session test | **Pass** | `/health` reports `redis:true`; login + authenticated orders round-trip; keys use `sess:{user_id}:{jti}` |

## Pass K — anonymous first session / account after first wow

| Item | Status | Notes |
|------|--------|-------|
| Anonymous API session | **Done** | `POST /v1/auth/anon` creates a PII-free user only when checkout starts; IP hash rate limit, JWT `anon` flag, Redis-backed session |
| Anonymous rental | **Done** | Existing `/v1/checkout/session` + `/v1/checkout/confirm` work unchanged for anonymous users; Postgres RLS remains user-scoped |
| Post-wow account claim | **Done** | `POST /v1/auth/claim` attaches optional email to the same user id and preserves orders/leases; duplicate email returns 409 |
| SQLite compatibility | **Done** | Existing local market DBs receive `is_anonymous` lazily; smoke test at `scripts/test-market-anonymous.py` |
| Web-market wiring | **Done** | Preview stays zero-auth; first rent creates anonymous session; successful phone open shows dismissible save-email prompt; access token memory-only |
| Azure migration | **Ready** | `services/market-api/migrations/004_anonymous_sessions.sql`; apply before deploying market-api 0.3.0 |

Privacy note: no email-shaped identity is synthesized or stored before the first successful rental. `STRLIX_PAY_MODE` remains `test`; no live payment path was changed.

## Pass M — Bring Strlix home (a11y rehearsal)

| Item | Status | Notes |
|------|--------|-------|
| TalkBack labels | **Done** | Home setup, Ask, widget, conversation messages, Live/STT, and Replay controls expose action/state labels instead of icon-only names. |
| Focus order + skip links | **Done** | Home starts with “Skip setup and ask Strlix now”; Ask starts with “Skip suggestions and go to the message field”; setup/chip order is explicit and 48dp targets are retained. |
| High contrast | **Done** | Raised dark-theme accent/muted tokens; status changes and Live captions announce through polite accessibility updates. |
| Phone-first IA | **Done** | Ask stays the primary in-phone entry; no outside chat added. Live, STT, Replay, screen-control, overlay, and Home bar flows remain intact. |
| Web phone stage | **Done** | Added phone-preview/stream skip links, visible-on-focus skip styling, labeled stream application, and live stage status. |
| Rehearsal evidence | **Pass** | `android-agent:app:assembleDebug`; UI tree verified on emulator `127.0.0.1:5555`; screenshots `shipped/05-home-a11y.png` and `shipped/06-ask-a11y.png`; `node --check web-market/js/market.js`. |

Design basis: accepted Claude M33/M49/M53 accessibility direction, applied to the existing Android phone home and web phone-stage entry.

## Pass N — Phone daily loop (2026-09-21 IST)

|| Item | Status | Notes |
|---|---|---|
| Recurring Ask entry | **Shipped** | Android phone Ask chip opens a small daily/weekly schedule dialog with local persistence and edit/pause. |
| Notification triage strip | **Shipped** | In-phone strip opens the notification shade or sends a user-approved triage Ask; no web-side cockpit or silent notification scraping. |
| Scheduled execution boundary | **Shipped** | Trigger posts a visible reminder and opens Ask prefilled; autonomous async execution stays deferred. |

This market track only records the phone-first surface; the implementation lives in `android-agent/`.

## Pass O — async job status seam (2026-09-21 IST)

| Item | Status | Notes |
|---|---|---|
| Authenticated async job shell | **Shipped** | `POST /v1/jobs` and `GET /v1/jobs/{job_id}` expose privacy-safe `queued → running → done` status. Records are process-local and owner-scoped; no prompt, chat, device content, or outside destination is accepted. |
| Phone-first poller | **Shipped** | `window.StrlixJobs` in `web-market/js/market.js` provides create/get/poll with bounded intervals and timeout. |
| Durable execution | **Deferred** | Queue persistence, retries, cancellation, and worker orchestration remain later work. |

## Previously shipped (market UI / research)

Marketplace UI, research docs, android-api ACA, dual-backend split — see sections below / git history.

## Deferred (phase 2 — do not burn credits yet)

Front Door/WAF, AKS, global Cosmos, Private Endpoints + VNet CAE, Managed Redis, Entra External ID, live payments, CMEK.

## Verify

```bash
curl -s https://ca-market-api.salmonrock-c8e120f0.eastus2.azurecontainerapps.io/health
az resource list -g rg-zevi-cloudphone -o table
```

## Cost (new foundation only)

Approx **$25–55/mo** at current SKUs (PG B1ms + ACA Redis + market-api scale-to-zero + KV/AI).

---

