# Hardening + payments checklist (survives after credits)

## Front Door + WAF (CREATE)

```bash
# Sketch — refine origin hostnames from:
#   az containerapp show -g rg-zevi-cloudphone -n ca-market-api --query properties.configuration.ingress.fqdn -o tsv
#   az containerapp show -g rg-zevi-cloudphone -n ca-android-api --query properties.configuration.ingress.fqdn -o tsv

az afd profile create -g rg-zevi-cloudphone -n afd-zevi-strlix --sku Standard_AzureFrontDoor
az afd endpoint create -g rg-zevi-cloudphone --profile-name afd-zevi-strlix -n strlix-edge
# + origin groups for market-api / android-api
# + WAF policy association (Standard)
```

Est.: ~$35/mo base + egress + ~$2.5 WAF policy.

## Managed Redis Basic C0 (CREATE)

```bash
az redis create -g rg-zevi-cloudphone -n redis-zevi-strlix -l eastus2 --sku Basic --vm-size c0
# Store primary key in kv-zevi-strlix; update ca-market-api REDIS_URL; then scale ca-redis to 0
```

Est.: ~$16/mo. Prefer over container Redis for post-credit survival.

## Private Endpoints (CREATE selectively)

- **Yes:** Key Vault + Redis in eastus2 (same region as CAE).
- **No this sprint:** Postgres PE (server is **centralus** — fix region later).

## Entra External ID (NOTES only)

1. Decide: External ID (CIAM) tenant vs workforce app registration.
2. App registration for market web + API.
3. Redirect URI → web-market origin / AFD endpoint.
4. Secret → `kv-zevi-strlix`.
5. Feature-flag auth; keep anon preview path for demos.

## Payments live-readiness (gated)

Existing: `services/market-api` forces `pay_mode=test` (live → HTTP 503).

Wire:

1. KV secrets (test first): `stripe-secret-key`, `stripe-publishable-key`, `stripe-webhook-secret`.
2. ACA secret refs on `ca-market-api`.
3. Real Checkout Session + signed webhook behind **both** `pay_mode=live` and `ALLOW_LIVE_CHARGES=true`.
4. Ankit flips live keys only when ready — never commit `sk_live_*`.
