# Strlix soft public launch checklist

Phone-first cloud Android. First month free. No live Stripe. Resource group `rg-zevi-cloudphone` only.

Updated 22 September 2026 (~03:49 IST).

## Done in this launch prep

- [x] **Free first month is the default.** `STRLIX_BILLING_MODE=free_month` and `STRLIX_FREE_LAUNCH_MODE=true`. Either one keeps the no-card path. Turning it off takes both (`BILLING_MODE=test|live` and `FREE_LAUNCH_MODE=false`).
- [x] **Waitlist.** `POST /v1/waitlist` stores email + `created_at`. Optional invite codes via `STRLIX_INVITE_CODES` (empty = open signup). Codes are hashed at rest. **Smoked 2026-09-22** via AFD → **200** `status=joined`, `card_required=false`.
- [x] **Phone grant without payment.** `POST /v1/access/grant` writes a $0 `provider=free_month` lease. `/v1/auth/anon` and `/v1/auth/claim` do not require checkout. **Smoked 2026-09-22** → **200** `granted_free` for `pixel-7a-a14`.
- [x] **Stripe stays test-gated.** `pay_mode=test`. Live calls still need `STRLIX_PAY_MODE=live` AND `PAYMENTS_LIVE=true` AND `STRLIX_ALLOW_LIVE_CHARGES=true`. Those stay off. Checkout is not required to open a phone.
- [x] **Copy.** Phone chrome and the catalog say "Free for your first month — no card required."
- [x] **Legal pages in image.** Terms/Privacy/Support/Capabilities in `static/legal/` (origin `/legal/*`) **and** `web-market/legal/` (AFD-safe `/market/legal/*`). **market-api 0.6.2**. Prefer `*.html` paths. Public links use `/market/legal/...`.
- [x] **AFD legal via `/market/legal/*`.** `route-market` still lists `/legal/*`, but edge `/legal/*` returns Azure 404 (~266KB) while origin is 200. Use `https://strlix-edge-….azurefd.net/market/legal/terms.html` → **200**. See `infra/hardening/CUSTOM-DOMAIN.md`.
- [x] **Entra applied (code + docs).** `STRLIX_AUTH_MODE=anon|entra`, default `anon`. Portal steps: `infra/hardening/ENTRA-EXTERNAL-ID.md`. Keep anon for demos until portal app is finished.
- [x] **Abuse controls / WAF apply DONE.** `TIGHTEN-WAF.sh --apply` on `wafzevistrlix`: **RateLimitAuthAnon** (110), **RateLimitWaitlist** (120), **RateLimitAuthLogin** (130) — 100/min/IP. `/health` not matched.
- [x] **Ops alerts DONE.** Action group `ag-strlix-ops` (see `demo/launch/OPS-ALERTS.md`).
- [x] **Postgres migration 006 DONE** on `psql-zevi-strlix` (waitlist + free_month plan).
- [x] **AWS GPU worker exists and is STOPPED.** `i-0531c567f620877c3` / `strlix-gpu-worker-1` (`g4dn.xlarge`, us-east-1) — stop when idle; do not terminate.
- [x] **cae-infra-subnet reserved.** `10.0.2.0/23` on `vm-zevi-cloudphone-vnet` (eastus), delegated `Microsoft.App/environments`. Redis public access still **Enabled**. Do not disable public Redis yet.
- [x] **Custom domain script.** Dry-run unless `DOMAIN` is set. `infra/hardening/CUSTOM-DOMAIN.md`.
- [x] **Private Redis runbook.** Public access stays on. Disable only with `--apply` and `CONFIRM=yes`, and only after a CAE VNet exists. `infra/hardening/PRIVATE-REDIS.md` / `PRIVATE-REDIS-NEXT.sh`.
- [x] **Ops stubs.** Monitoring, phone-pool capacity, incident, Postgres + Key Vault backup. `infra/ops/`.

Live market-api: **0.6.2** (`ca-market-api--0000006`), `billing_mode=free_month`, `pay_mode=test`, `redis:true`, `live_charges_allowed:false`.

## Needs Ankit (external blockers — do not fake these)

- [ ] **Domain DNS.** Own a zone, then `DOMAIN=app.strlix.app ./infra/hardening/ATTACH-CUSTOM-DOMAIN.sh --apply` and create the CNAME + `_dnsauth` TXT. `app.strlix.app` / `support@strlix.app` are placeholders until then. Set `STRLIX_SUPPORT_EMAIL_PLACEHOLDER=false` only after the mailbox exists, and edit the static legal banner in the same change.
- [ ] **Entra portal** (if CLI cannot finish). Create the app registration (workforce or External ID), optional claims for email, Key Vault secret if you mint a client secret. Keep `STRLIX_AUTH_MODE=anon` for demos. Steps: `infra/hardening/ENTRA-EXTERNAL-ID.md`.
- [ ] **Physical phone.** Sub-100 ms is not certified. The live pool is one emulator (`pilot-emulator-1`). Emulator numbers do not count.
- [ ] **Azure GPU ticket.** Support **2609210040005251** — eastus2 NCasT4 / NVadsA10 still limit 0. Do not create an Azure GPU VM until cleared.
- [ ] **Counsel pass** on `static/legal/*` before a wide (not soft) public launch. The pages say they are placeholders.
- [ ] **iOS signing.** No App Store credentials in this repo. There is no iOS ship in this launch.
- [x] **AFD legal smoke via `/market/legal/*`.** Edge `/legal/*` still mysteriously 404s; public URLs use `/market/legal/*` until resolved.

## Deferred (after the free month, or explicitly out of this launch)

- [ ] **Live Stripe.** After the free month, and only with Key Vault live keys plus all three gates. Until then `pay_mode=test`. Runbook: `infra/hardening/PAYMENTS-KEYVAULT.md`.
- [ ] **Front Door Premium** managed WAF rules. Standard custom rules only for now (cost).
- [ ] **Key Vault private endpoint.** `kv-zevi-strlix` is eastus2; the VNet is eastus. Still skipped.
- [ ] **Postgres private endpoint.** Server is centralus. Still skipped.
- [ ] **Private Redis cutover.** Region split CAE eastus2 vs VNet/Redis eastus — subnet reserved only; no public-access disable until eastus CAE Option B.
- [ ] **`ROLE_ASSISTANT`.** `AssistantRoleHook` does not request or hold the role. Do not demo it as the Android default assistant.
- [ ] **On-device model.** The hook is disabled and must not invent model output.
- [ ] **One phone per user.** The free-month row is an entitlement. The broker TTL is about an hour on a shared emulator. See `infra/ops/CAPACITY-PHONE-POOL.md`.

## Smoke before telling anyone the URL

```bash
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
# expect ok, version 0.6.2+, pay_mode=test, free_month_active=true, card_required=false, redis=true

curl -sS -o /dev/null -w '%{http_code}\n' https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html
# expect 200 (prefer /market/legal/* — AFD /legal/* still Azure-404s)

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
