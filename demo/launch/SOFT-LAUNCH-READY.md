# Strlix soft-launch ready scoreboard

**Status:** ready for a limited soft launch at https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/
**Updated:** 22 September 2026 (~09:20 IST)
**Billing:** first month free; no live Stripe charges.

> **Honest device note:** this launch uses one shared emulator (`pilot-emulator-1`). It is not a private phone for 30 days. A free entitlement grants access to a shared emulator lease; **free entitlement ≠ dedicated device**.

## Done

- AFD `/market/` entry point is public; legal pages are under `/market/legal/`.
- Market-api **0.6.2** is live with waitlist, no-card free grant, Redis, WAF limits, and ops alerts.
- Entra app `strlix-market-api` was provisioned via CLI: client `58e20155-d677-4985-86bf-ee48521dc6f8`, tenant `d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2`; Key Vault secret `entra-market-client-secret` is set. `STRLIX_AUTH_MODE=anon` remains enabled for the demo.
- Stripe remains test-gated: `pay_mode=test`, `live_charges_allowed=false`.
- Legal, waitlist, and free-grant smoke checks passed via AFD. The old Cloudflare quick tunnel is stale and is not the soft-launch URL.

## Needs Ankit

- **Domain DNS/TLS** for the branded AFD hostname.
- **Physical phone** for real-device latency validation.
- **Azure GPU ticket OPEN** — Support **2609210040005251**, eastus2 NCasT4 / NVadsA10 still at **limit 0**; do not create a GPU VM.
- **Counsel** review of `static/legal/*` before a wide public launch.
- **iOS signing** and App Store credentials.

## Deferred

- Live Stripe, until after the free month and all live-charge gates are deliberately enabled.
- Private Redis / Key Vault / Postgres endpoints and Premium Front Door WAF rules.
- Dedicated or private phone capacity. Do not describe the shared emulator lease as a dedicated device or a 30-day private phone.
- `ROLE_ASSISTANT` and on-device model behavior remain out of this soft launch.

## Smoke curls

```bash
# Service health: expect 200 and free_month_active=true, pay_mode=test.
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health

# Public soft-launch entry point.
curl -sS -o /dev/null -w '%{http_code}
' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/

# Legal: expect 200.
curl -sS -o /dev/null -w '%{http_code}
' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html

# Waitlist: expect status=joined and card_required=false.
curl -sS -X POST \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
```
