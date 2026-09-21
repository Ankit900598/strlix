# Incident — short runbook

**RG lock:** `rg-zevi-cloudphone` only. Do not delete resources to "stop the bleeding" unless Ankit says so in writing. Prefer disable, scale, or revert an env var.

## First checks

```bash
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
curl -sS "https://$(az containerapp show -g rg-zevi-cloudphone -n ca-market-api --query properties.configuration.ingress.fqdn -o tsv)/health"
curl -sS "https://$(az containerapp show -g rg-zevi-cloudphone -n ca-android-api --query properties.configuration.ingress.fqdn -o tsv)/health"
```

Healthy market JSON includes `ok: true`, `pay_mode: "test"`, `free_month_active: true`, `card_required: false`, `redis: true`.

## Severity

| Level | Example | Do |
|-------|---------|----|
| 1 | `/health` down, or Redis public access disabled and clients cannot connect | Re-enable Redis public access (below). Do not recreate CAE. |
| 2 | 429 storm, WAF 403 on `/health` | Remove the new WAF rule only (`TIGHTEN-WAF.sh` prints the delete). Keep the policy. |
| 2 | Anyone is asked for a card, or `live_charges_allowed: true` | Set `STRLIX_PAY_MODE=test`, `PAYMENTS_LIVE=false`, `STRLIX_ALLOW_LIVE_CHARGES=false` on `ca-market-api`. Free month stays on. |
| 3 | One emulator wedged | Restart the stream process / ADB. Don't delete `vm-zevi-cloudphone`. |
| 3 | Entra 503s | Set `STRLIX_AUTH_MODE=anon`. Anon sessions must keep working. |

## Redis public access rollback

```bash
az redisenterprise update -g rg-zevi-cloudphone -n redis-strlix-amr \
  --public-network-access Enabled
```

If `/health` still says `redis: false`, restart `ca-market-api` (new revision) so the client drops a latched failure. See `infra/hardening/PRIVATE-REDIS.md`.

## Payments

Live Stripe is deferred. A half-configured live mode returns 503 from checkout and must not be "fixed" by setting the three live gates during an incident. The free path is `POST /v1/access/grant`, which does not call Stripe.

## Talk track

Say what is true: one emulator, free month, no card, assistant role not granted. Don't promise a physical device or a restored latency number you have not measured.

Contact placeholder: `support@strlix.app` until `SUPPORT_EMAIL` is a domain Ankit owns.
