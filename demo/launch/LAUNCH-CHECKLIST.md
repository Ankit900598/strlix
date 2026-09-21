# Strlix soft public launch checklist

Phone-first cloud Android. First month free. No live Stripe. Resource group `rg-zevi-cloudphone` only.

Updated 21 September 2026.

## Done in this launch prep

- [x] **Free first month is the default.** `STRLIX_BILLING_MODE=free_month` and `STRLIX_FREE_LAUNCH_MODE=true`. Either one keeps the no-card path. Turning it off takes both (`BILLING_MODE=test|live` and `FREE_LAUNCH_MODE=false`).
- [x] **Waitlist.** `POST /v1/waitlist` stores email + `created_at`. Optional invite codes via `STRLIX_INVITE_CODES` (empty = open signup). Codes are hashed at rest.
- [x] **Phone grant without payment.** `POST /v1/access/grant` writes a $0 `provider=free_month` lease. `/v1/auth/anon` and `/v1/auth/claim` do not require checkout.
- [x] **Stripe stays test-gated.** `pay_mode=test`. Live calls still need `STRLIX_PAY_MODE=live` AND `PAYMENTS_LIVE=true` AND `STRLIX_ALLOW_LIVE_CHARGES=true`. Those stay off. Checkout is not required to open a phone.
- [x] **Copy.** Phone chrome and the catalog say "Free for your first month — no card required."
- [x] **Entra is implemented and off.** `STRLIX_AUTH_MODE=anon|entra`, default `anon`. Portal steps and env vars: `infra/hardening/ENTRA-EXTERNAL-ID.md`.
- [x] **Legal pages.** Terms, Privacy, Support, and what Strlix can/can't do in `static/legal/`. Served at `/static/legal/*` (phone host) and `/legal/*` (market-api). Placeholder company name and `support@strlix.app` are marked on the pages.
- [x] **Abuse controls documented and tightened.** Anon / login / waitlist limits, Redis fail-closed. WAF script does not match `/health`. See `infra/hardening/ABUSE-CONTROLS.md`.
- [x] **Custom domain script.** Dry-run unless `DOMAIN` is set. `infra/hardening/CUSTOM-DOMAIN.md`.
- [x] **Private Redis runbook.** Public access stays on. Disable only with `--apply` and `CONFIRM=yes`, and only after a CAE VNet exists. `infra/hardening/PRIVATE-REDIS.md`.
- [x] **Ops stubs.** Monitoring, phone-pool capacity, incident, Postgres + Key Vault backup. `infra/ops/`.

Postgres waitlist needs `services/market-api/migrations/006_free_month.sql` applied on `psql-zevi-strlix` before production `POST /v1/waitlist`. SQLite dev creates the table itself. The grant path falls back if the `orders.plan` check has not been widened yet.

## Needs Ankit (external blockers — do not fake these)

- [ ] **Domain DNS.** Own a zone, then `DOMAIN=app.strlix.app ./infra/hardening/ATTACH-CUSTOM-DOMAIN.sh --apply` and create the CNAME + `_dnsauth` TXT. `app.strlix.app` / `support@strlix.app` are placeholders until then. Set `STRLIX_SUPPORT_EMAIL_PLACEHOLDER=false` only after the mailbox exists, and edit the static legal banner in the same change.
- [ ] **AFD route for legal pages.** `./infra/hardening/EXTEND-AFD-ROUTES.sh --apply` so `/legal/*` is on `route-market`. Re-check `/health` is still 200. The phone viewer is desktop-api and is not on this Front Door.
- [ ] **Entra portal.** Create the app registration (workforce or External ID), optional claims for email, Key Vault secret if you mint a client secret. Keep `STRLIX_AUTH_MODE=anon` for demos. Steps: `infra/hardening/ENTRA-EXTERNAL-ID.md`.
- [ ] **Apply migration 006** on `psql-zevi-strlix` (centralus) before relying on the production waitlist.
- [ ] **GPU quota.** Azure ticket **2609210040005251**. AWS Case **179000526000600** / request `ab584e62c7f748b8908dd6e1e61c01bamRtt8Z1K`. Do not create a GPU VM while the limit is 0.
- [ ] **Physical phone.** Sub-100 ms is not certified. The live pool is one emulator (`pilot-emulator-1`). Emulator numbers do not count.
- [ ] **iOS signing.** No App Store credentials in this repo. There is no iOS ship in this launch.
- [ ] **Counsel pass** on `static/legal/*` before a wide (not soft) public launch. The pages say they are placeholders.
- [ ] **WAF apply (optional).** `./infra/hardening/TIGHTEN-WAF.sh --apply`, then curl `/health`. Skip if you have not reviewed the rules.
- [ ] **Alerts apply (optional).** `CONFIRM=yes SUPPORT_EMAIL=<real mailbox> ./infra/ops/CREATE-ALERTS.sh --apply`. Confirm metric names in the portal first.
- [ ] **Private Redis.** Only after `cae-zevi-strlix` has a VNet. It does not today, and this checklist does not recreate that environment. Public Redis stays Enabled. `CONFIRM=yes` is required to disable public access and should not be used yet.

## Deferred (after the free month, or explicitly out of this launch)

- [ ] **Live Stripe.** After the free month, and only with Key Vault live keys plus all three gates. Until then `pay_mode=test`. Runbook: `infra/hardening/PAYMENTS-KEYVAULT.md`.
- [ ] **Front Door Premium** managed WAF rules. Standard custom rules only for now (cost).
- [ ] **Key Vault private endpoint.** `kv-zevi-strlix` is eastus2; the VNet is eastus. Still skipped.
- [ ] **Postgres private endpoint.** Server is centralus. Still skipped.
- [ ] **`ROLE_ASSISTANT`.** `AssistantRoleHook` does not request or hold the role. Do not demo it as the Android default assistant.
- [ ] **On-device model.** The hook is disabled and must not invent model output.
- [ ] **One phone per user.** The free-month row is an entitlement. The broker TTL is about an hour on a shared emulator. See `infra/ops/CAPACITY-PHONE-POOL.md`.

## Smoke before telling anyone the URL

```bash
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
# expect ok, pay_mode=test, free_month_active=true, card_required=false, redis=true
```

Local:

```bash
python3 scripts/test-market-free-month.py
python3 scripts/test-market-entra.py
python3 scripts/test-market-anonymous.py
```

Anonymous session, waitlist, and free grant must pass with live charge gates off.
