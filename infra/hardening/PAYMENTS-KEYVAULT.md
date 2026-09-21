# Flip Stripe live keys via Key Vault (no git secrets)

**Deferred.** The soft launch is a free first month. Do not run the "Flip live" section until that period is over. `STRLIX_PAY_MODE` stays `test`. `PAYMENTS_LIVE` and `STRLIX_ALLOW_LIVE_CHARGES` stay false. Phone access uses `POST /v1/access/grant`, which never calls Stripe.

**RG lock:** `rg-zevi-cloudphone` only. Vault: `kv-zevi-strlix` (eastus2).  
**Default:** TEST. Live charges stay off until Ankit flips **three** gates.

## Secrets to create (test first)

```bash
# TEST values — safe to store; still do not commit
az keyvault secret set --vault-name kv-zevi-strlix -n stripe-publishable-key --value 'pk_test_...'
az keyvault secret set --vault-name kv-zevi-strlix -n stripe-secret-key      --value 'sk_test_...'
az keyvault secret set --vault-name kv-zevi-strlix -n stripe-webhook-secret  --value 'whsec_test_...'
```

When ready for live (portal Stripe dashboard → live mode keys):

```bash
# LIVE — never paste into git, .env on the box, or chat logs
az keyvault secret set --vault-name kv-zevi-strlix -n stripe-publishable-key --value 'pk_live_...'
az keyvault secret set --vault-name kv-zevi-strlix -n stripe-secret-key      --value 'sk_live_...'
az keyvault secret set --vault-name kv-zevi-strlix -n stripe-webhook-secret  --value 'whsec_...'
```

## Wire ACA `ca-market-api` to KV references

```bash
# Sketch — refine with current revision env before apply
az containerapp secret set -g rg-zevi-cloudphone -n ca-market-api \
  --secrets \
    stripe-publishable-key=keyvaultref:https://kv-zevi-strlix.vault.azure.net/secrets/stripe-publishable-key,identityref:system \
    stripe-secret-key=keyvaultref:https://kv-zevi-strlix.vault.azure.net/secrets/stripe-secret-key,identityref:system \
    stripe-webhook-secret=keyvaultref:https://kv-zevi-strlix.vault.azure.net/secrets/stripe-webhook-secret,identityref:system

az containerapp update -g rg-zevi-cloudphone -n ca-market-api \
  --set-env-vars \
    STRLIX_STRIPE_PUBLISHABLE_KEY=secretref:stripe-publishable-key \
    STRLIX_STRIPE_SECRET_KEY=secretref:stripe-secret-key \
    STRLIX_STRIPE_WEBHOOK_SECRET=secretref:stripe-webhook-secret \
    STRLIX_PAY_MODE=test \
    PAYMENTS_LIVE=false \
    STRLIX_ALLOW_LIVE_CHARGES=false
```

Grant the Container App system-assigned identity `Key Vault Secrets User` on `kv-zevi-strlix` first.

## Flip live (Ankit only)

1. Confirm Stripe webhook endpoint → `https://<afd-or-ca-market-api>/v1/webhooks/stripe` with signing secret in KV.
2. Swap KV secrets to `pk_live_` / `sk_live_` / live `whsec_`.
3. Set **all three** on `ca-market-api`:
   - `STRLIX_PAY_MODE=live`
   - `PAYMENTS_LIVE=true`
   - `STRLIX_ALLOW_LIVE_CHARGES=true`
4. Smoke with $0.50 product; watch `/v1/payments/status` and App Insights.
5. To abort: set any gate back to false/test — API immediately returns TEST path / 503 for half-live.

## What we store

`market.payment_intents` (RLS): `provider_intent_id` + `status` + amount + tenant `user_id`.  
**Never** card numbers, CVV, full charge JSON, or secret keys.
