# Remaining work — soft-launch ledger

**Updated:** 2026-09-22 ~09:12 IST  
**Billing:** first month **FREE**. Keep `pay_mode=test` and live-charge gates OFF until after the free period.

Free-month path (flag, waitlist, no-card grant, legal pages, Entra-ready auth defaulting to anon) is live. Split of done vs blocked vs deferred: `demo/launch/LAUNCH-CHECKLIST.md`.  
Ops notes: `../launch/OPS-ALERTS.md`, `../launch/PRIVATE-REDIS-PATH.md`, `../launch/SOFT-LAUNCH-STATUS.md`.

## Remaining list (Needs Ankit / external)

1. **Domain DNS + TLS on AFD** — still on `strlix-edge-….azurefd.net`. Runbook: `infra/hardening/ATTACH-CUSTOM-DOMAIN.sh` (Ankit DNS).
2. **Entra portal** — if CLI cannot finish app registration / secrets; code defaults stay `anon`.
3. **Physical phone** — real-device latency proof; emulator does not qualify.
4. **Azure GPU wait** — Support **2609210040005251**: eastus2 NCasT4 / NVadsA10 still **limit 0**. Do not create an Azure GPU VM until cleared.
5. **Counsel** on `static/legal/*` before wide public launch.
6. **iOS** — no App Store credentials; out of this launch.
7. **AFD legal:** edge `/legal/*` still Azure-404s; use `/market/legal/*` (0.6.2 / `ca-market-api--0000006`). See CUSTOM-DOMAIN.md.

## Done enough for soft-launch (do not redo)

- Migration **006** applied on `psql-zevi-strlix`.
- WAF apply DONE: RateLimitAuthAnon / RateLimitWaitlist / RateLimitAuthLogin on `wafzevistrlix`.
- Alerts DONE: `ag-strlix-ops`.
- Free-month market-api **0.6.1** live (`ca-market-api--0000005`); `/health` via AFD **200** · `pay_mode=test` · `redis:true` · `free_month_active:true`.
- Waitlist + grant smoked via AFD (2026-09-22).
- AFD `route-market` patterns include `/legal/*` (with `/health` retained).
- AWS GPU `i-0531c567f620877c3` / `strlix-gpu-worker-1` created then **STOPPED** (idle). Start when needed; do not terminate.
- `cae-infra-subnet` `10.0.2.0/23` reserved (eastus). Redis public access still Enabled — do not disable.
- Live Stripe **OFF**.

## Deferred / gated

- Private Redis cutover (CAE/VNet region split) — subnet only; `CONFIRM=yes` not used.
- Key Vault / Postgres private endpoints — region mismatch; skipped.
- Live Stripe — after free month only.
