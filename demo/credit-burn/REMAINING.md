# Remaining work — soft-launch ledger

**Updated:** 2026-09-22 ~09:20 IST
**Billing:** first month **FREE**. Keep `pay_mode=test` and live-charge gates OFF until after the free period.

The AFD soft-launch route is `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/`; legal is under `/market/legal/`. The free-month path and Entra app are ready; `STRLIX_AUTH_MODE=anon` remains the demo default. See `demo/launch/LAUNCH-CHECKLIST.md` and `demo/launch/SOFT-LAUNCH-READY.md`.

## Needs Ankit / external

1. **Domain DNS + TLS on AFD** — still on the `*.azurefd.net` endpoint. Runbook: `infra/hardening/ATTACH-CUSTOM-DOMAIN.sh`.
2. **Physical phone** — real-device latency proof; the current pool is a shared emulator and does not qualify.
3. **Azure GPU ticket — OPEN** — Support **2609210040005251**: eastus2 NCasT4 / NVadsA10 still **limit 0**. Do not create an Azure GPU VM until cleared.
4. **Counsel** on `static/legal/*` before a wide public launch.
5. **iOS signing** — no App Store credentials; out of this launch.

## Deferred / gated

- **Live Stripe** — after the free month only; live-charge gates stay OFF.
- **Dedicated/private phone** — free entitlement ≠ dedicated device; no private-phone-for-30-days promise on the shared emulator.
- Private Redis and Key Vault/Postgres private endpoints — region/network work remains intentionally skipped.
- Front Door Premium managed WAF rules and other cost-increasing hardening.

## Done enough for soft-launch (do not redo)

- Entra app `strlix-market-api` provisioned via CLI (client `58e20155-d677-4985-86bf-ee48521dc6f8`, tenant `d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2`); Key Vault secret set; auth mode remains `anon`.
- Market-api **0.6.2** (`ca-market-api--0000006`) live; waitlist, free grant, `/health`, and `/market/legal/*` were smoked via AFD.
- Migration 006, WAF rules, and `ag-strlix-ops` alerts are applied. AWS GPU `i-0531c567f620877c3` remains **stopped**.
- Live Stripe remains **OFF**.
