# Strlix global soft launch — today

**Date:** 2026-09-22 (IST)
**Status:** Global soft launch is open today, with the limitations below.

## Public launch surface

- **Public URL now:** https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/
- **Health:** market-api **0.6.3**; `billing_mode=free_month`; `card_required=false`.
- **Legal:** live at https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/
- **Branded host:** `app.zevilabs.dev` is still **AFD Pending**. It needs the Name.com CNAME + TXT records before it can be used.

## What “global soft launch” means today

- The waitlist and free grant are open worldwide on the AFD URL above.
- Access uses shared cloud Android capacity; this is not a dedicated private phone.
- The first month is free. Live Stripe charging is not enabled.

## Capacity and honest boundaries

- Capacity is **Azure emulator + AWS Redroid on g4dn**; wiring is in progress.
- Not certified today: physical sub-100 ms latency, counsel review, iOS, live Stripe, or Azure GPU.
- This is a soft launch, not a claim that those items are complete or certified.

## Smoke curls

```bash
# Public market entry point: expect HTTP 200.
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/

# Health: expect 200 with version 0.6.3, billing_mode=free_month,
# and card_required=false.
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health

# Legal: expect HTTP 200.
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html

# Waitlist: expect status=joined and card_required=false.
curl -sS -X POST \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
```
