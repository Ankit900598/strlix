# CLAUDE-SOLUTION (rollup of accepted designs)

**Date:** 2026-09-21 IST  
**Claude files:** 55/55 in `claude-solutions/MXX.md` (all `SOURCE: claude-cli`)  
**Verification:** see `VERIFICATION.md` — ACCEPT majority; REVISE on M06, M11, M16, M21, M38 (latency honesty, no anti-detect theater, defer fleet sync, default non-root).

## Information architecture
1. `/` (`web-market/`) — marketing + **mini-phone CTA** + device catalog filters.
2. Fullscreen overlay `#phoneStage` — immersive bezel; embeds live viewer (`:8789` or `:8787`).
3. Checkout modal — test-mode Stripe/Razorpay stub via `market-api` or local stub.
4. AI remains **inside** phone (Ask-in-bezel / Agent app / bubble) — **zero** side chat column (M15/M55).

## Homepage → fullscreen
- Mini phone card (`#miniPhone`) → `#phoneStage` (M29).
- Esc / Close exits; focus to Close.
- Stream rect is sovereign — no upsell overlays (M48).

## Device picker
- Filters: Android, RAM, ROM, tier, search (M13).
- Cards: honest notes, **published $/hr·$/day**, `network: datacenter` chip (M02/M11), legacy Android chips.
- Capability honesty: real ARM stream vs browser-fingerprint products separated in IA (M20); no Multilogin-style Identity merge (M21 revise).

## Connection honesty
- `#latencyChip` measures HTTP RTT to stream `/health`, labeled **RTT est. N ms**; shows **—** if unmeasured — never hardcoded (M06 revise).
- Degraded/JPEG path documented for Android 7+ web shells (M14).

## Payment
- `POST /v1/checkout/session` + `/confirm` → `paid_test` only.
- Visible **PAY: TEST** pill; live mode hard-blocked.
- Single meter / cold-start naming direction (M17/M18); Razorpay stub path (M52).

## Android 7+ / graceful web
- Viewer ladder: H.264 WebCodecs → JPEG (existing static viewer).
- Market UI: `prefers-reduced-motion`, focus-visible, skip link, native `<select>` (M53).
- Catalog includes Android 7.1 / 8.1 SKUs conceptually.

## File plan shipped
```
web-market/index.html|css/market.css|js/market.js|devices.json|README.md
services/market-api/market_api/{main,db,settings}.py  (+ /market static mount)
deploy/azure/bicep/market-backend.bicep   # NOT applied — credit gate
wrappers/{android,ios,desktop}/README.md
demo/cloud-phone-market/* (research, mistakes, BP, verification, status)
```

## Shipped from verification revises
- M06: live `RTT est. N ms` chip in fullscreen chrome
- M11: `network: datacenter` on every SKU card
- M14 note: Android 7 JPEG fallback in catalog/compat note

## Deferred (accepted but not fully built)
- Warm anonymous trial pool with Turnstile (M01)
- Snapshot restore across host restarts (M07)
- Fleet sync rails only if multi-device ships later (M16 revise) — no live mirror
- Entra ID / magic link production auth
- Postgres Flexible + Redis provision (bicep ready; spend gated)
- In-VM Agent APK + ghost-cursor overlay (M55) beyond current ask-hint
- Audio sync controls (M54), region RTT picker (M40), status incidents (M50)

## Serve note (this box)
- Prefer `:8790` when free; here `:8790`/`:8791` are `sand-egress-tunnel`
- Use **http://127.0.0.1:8765/** or **http://127.0.0.1:8792/market/**
