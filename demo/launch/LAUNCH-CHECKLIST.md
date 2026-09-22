# Strlix soft public launch checklist

Phone-first cloud Android. First month free. No live Stripe. Resource group `rg-zevi-cloudphone` only.

**Public soft-launch URL:** https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/
Legal pages are under `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/` (for example, `terms.html`). The old Cloudflare quick-tunnel URL is stale and is not the launch URL; `demo/public-url.txt` points to this AFD market route.

Updated 22 September 2026 (~10:37 IST).

## Done in this launch prep

- [x] **Free first month is the default.** `STRLIX_BILLING_MODE=free_month` and `STRLIX_FREE_LAUNCH_MODE=true`. Either one keeps the no-card path. Turning it off takes both (`BILLING_MODE=test|live` and `FREE_LAUNCH_MODE=false`).
- [x] **Waitlist.** `POST /v1/waitlist` stores email + `created_at`. Optional invite codes via `STRLIX_INVITE_CODES` (empty = open signup). Codes are hashed at rest. **Smoked 2026-09-22** via AFD → **200** `status=joined`, `card_required=false`.
- [x] **Phone grant without payment.** `POST /v1/access/grant` writes a $0 `provider=free_month` lease. `/v1/auth/anon` and `/v1/auth/claim` do not require checkout. **Smoked 2026-09-22** → **200** `granted_free` for `pixel-7a-a14`.
- [x] **Stripe stays test-gated.** `pay_mode=test`. Live calls still need `STRLIX_PAY_MODE=live` AND `PAYMENTS_LIVE=true` AND `STRLIX_ALLOW_LIVE_CHARGES=true`. Those stay off. Checkout is not required to open a phone.
- [x] **Copy.** Phone chrome and the catalog say "Free for your first month — no card required."
- [x] **Legal pages (soft-launch rewrite).** Terms, Privacy, Support, and what Strlix can/can't do. Canonical HTML is `static/legal/`; the same bytes are in `web-market/legal/`. Public Front Door URLs are `/market/legal/*.html` (already inside `/market/*`). The phone host still serves `/static/legal/*`. The pages name Strlix and the configurable support address. They do not name a registered company. The banner is a soft-launch notice, not a counsel sign-off. Default `support@strlix.app`: the mailbox is being set up. Free month ≠ private phone for 30 days.
- [x] **Public AFD market route.** `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/` is the soft-launch entry point; legal is served below `/market/legal/`. No new AFD pattern required (`EXTEND-AFD-ROUTES.sh --apply` not needed).
- [x] **Entra app provisioned via CLI.** App `strlix-market-api`, client `58e20155-d677-4985-86bf-ee48521dc6f8`, tenant `d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2`, and Key Vault secret `entra-market-client-secret` set. `STRLIX_AUTH_MODE=anon` remains the demo mode; Entra is additive and not a login wall.
- [x] **Abuse controls / WAF apply DONE.** `TIGHTEN-WAF.sh --apply` on `wafzevistrlix`: **RateLimitAuthAnon** (110), **RateLimitWaitlist** (120), **RateLimitAuthLogin** (130) — 100/min/IP. `/health` not matched.
- [x] **Ops alerts DONE.** Action group `ag-strlix-ops` (see `demo/launch/OPS-ALERTS.md`).
- [x] **Postgres migration 006 DONE** on `psql-zevi-strlix` (waitlist + free_month plan).
- [x] **AWS GPU worker exists** — currently **RUNNING** for soft launch. `i-0531c567f620877c3` / `strlix-gpu-worker-1` (`g4dn.xlarge`, us-east-1) ≈$0.526/hr — **stop when idle**; do not terminate.
- [x] **cae-infra-subnet reserved.** `10.0.2.0/23` on `vm-zevi-cloudphone-vnet` (eastus), delegated `Microsoft.App/environments`. Redis public access still **Enabled**. Do not disable public Redis yet.
- [x] **Custom domain script.** Dry-run unless `DOMAIN` is set. `infra/hardening/CUSTOM-DOMAIN.md`.
- [x] **Private Redis runbook.** Public access stays on. Disable only with `--apply` and `CONFIRM=yes`, and only after a CAE VNet exists. `infra/hardening/PRIVATE-REDIS.md` / `PRIVATE-REDIS-NEXT.sh`.
- [x] **Ops stubs.** Monitoring, phone-pool capacity, incident, Postgres + Key Vault backup. `infra/ops/`.

Live market-api: **0.6.4** (`ca-market-api--0000010`); keep `billing_mode=free_month`, `pay_mode=test`, `redis:true`, `live_charges_allowed:false`. Catalog FK for `aws-redroid-t4-1` seeded (migration 007).

## Needs Ankit (external blockers — do not fake these)

- [ ] **Domain DNS — Name.com Cloudflare Turnstile.** `app.zevilabs.dev` AFD Pending; token `_48ncbg9vt1u4zxek55jon1osqixlr88` expires ~2026-09-29. Soft-launch URL remains `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/`. Do **not** buy domains or run `ATTACH-CUSTOM-DOMAIN.sh --apply` until Turnstile cleared. `support@strlix.app` stays a default until the mailbox is monitored.
- [ ] **Physical phone.** Sub-100 ms is not certified. The live pool is one shared emulator (`pilot-emulator-1`); emulator numbers do not count.
- [ ] **Azure GPU ticket — OPEN.** Support **2609210040005251** — eastus2 NCasT4 / NVadsA10 remains at **limit 0**. Do not create an Azure GPU VM until cleared.
- [ ] **Counsel / independent legal review** on `static/legal/*` before a wide (not soft) public launch. Soft-launch pages are an operator draft — not legal advice, not a counsel sign-off, not a registered company claim.
- [ ] **iOS signing.** No App Store credentials in this repo. There is no iOS ship in this launch.

## Deferred (after the free month, or explicitly out of this launch)

- [ ] **Live Stripe.** After the free month, and only with Key Vault live keys plus all three gates. Until then `pay_mode=test`. Runbook: `infra/hardening/PAYMENTS-KEYVAULT.md`.
- [ ] **Front Door Premium** managed WAF rules. Standard custom rules only for now (cost).
- [ ] **Key Vault private endpoint.** `kv-zevi-strlix` is eastus2; the VNet is eastus. Still skipped.
- [ ] **Postgres private endpoint.** Server is centralus. Still skipped.
- [ ] **Private Redis cutover.** Region split CAE eastus2 vs VNet/Redis eastus — subnet reserved only; no public-access disable until eastus CAE Option B.
- [ ] **Dedicated/private phone per user.** The soft-launch entitlement is free access to a shared emulator lease, not a dedicated device and not a promise of a private phone for 30 days. See `infra/ops/CAPACITY-PHONE-POOL.md`.
- [ ] **`ROLE_ASSISTANT`.** `AssistantRoleHook` does not request or hold the role. Do not demo it as the Android default assistant.
- [ ] **On-device model.** The hook is disabled and must not invent model output.
- [ ] **Custom branded domain.** Deferred indefinitely for soft launch per Ankit (stay on azurefd.net).

## Smoke before telling anyone the URL

```bash
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
# expect ok, version with legal rewrite, pay_mode=test, free_month_active=true, card_required=false, redis=true

curl -sS -o /dev/null -w '%{http_code}\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html
# expect 200 (use /market/legal/*; AFD /legal/* is not the public path)

curl -sS -X POST https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' -d '{"email":"you@example.com"}'
```

Local:

```bash
python3 scripts/test-market-free-month.py
python3 scripts/test-market-entra.py
python3 scripts/test-market-anonymous.py
```

Anonymous session, waitlist, and free grant must pass with live charge gates off.
