# Entra External ID — additive auth (code shipped, default off)

**Goal:** real-user sign-in for market-api without forcing a login wall on the phone preview.  
**RG lock:** `rg-zevi-cloudphone` only.  
**Default:** `STRLIX_AUTH_MODE=anon`. `/v1/auth/anon` and `/v1/auth/claim` keep working in both modes.

Code: `services/market-api/market_api/auth.py`  
- Local HS256 session tokens are checked first.  
- Only when `STRLIX_AUTH_MODE=entra` does a non-local bearer get RS256 validation against Entra JWKS.  
- Entra tokens must carry `email` or `preferred_username`. The API maps that email onto a market user. It does not replace the anon session store.  
- Incomplete Entra env returns **503** for Entra bearers and still accepts anon bearers.  
- Do not flip the ACA env to `entra` for demos until the portal app exists.

No client secret is read from git. If you create one, store it only in `kv-zevi-strlix` as `entra-market-client-secret`. The API validates access tokens with the public JWKS, so the secret is for a confidential client or portal setup, not for this process.

## Choose a path

| Option | When | Cost |
|--------|------|------|
| **A. External ID (CIAM)** | Consumer sign-up / social later | MAU-based; free tier is often enough for a soft launch |
| **B. Workforce app registration** in the current tenant | Investor / operator demos | $0 |

Ship demos on **anon**. Use **B** first if you only need operator login. Plan **A** when strangers sign up with email/social.

## Portal steps — B, workforce

1. Entra admin center → **App registrations** → **New registration**.  
   - Name: `strlix-market-api`  
   - Supported accounts: single tenant  
   - Redirect URI: leave blank for this API (the phone preview does not redirect yet). If you add a SPA later: `https://<your-domain>/market/` and `http://127.0.0.1:8080/market/`.
2. Copy **Application (client) ID** and **Directory (tenant) ID**.
3. **Expose an API** → Application ID URI: `api://strlix-market` (or `api://<client-id>`). Add a scope `access_as_user` if a SPA will request a token. For a hand-minted test, the audience you put in `STRLIX_ENTRA_AUDIENCE` must match the token `aud` claim.
4. **Token configuration** → **Add optional claim** → Access token → `email` and `preferred_username`. Without one of those, market-api returns 401 and does not create a user.
5. **Certificates & secrets** → new client secret only if a confidential client needs it. Store the value in Key Vault, never in git:

```bash
az keyvault secret set --vault-name kv-zevi-strlix \
  -n entra-market-client-secret --value '<secret-from-portal>'
```

6. API permissions: nothing extra is required for this API to *validate* tokens. Don't grant admin-consent Graph permissions for the soft launch.

## Portal steps — A, External ID (CIAM)

1. Microsoft Entra admin center → **External Identities** → **Create a tenant** → **Customer** (External ID).  
2. Switch into that tenant. Create an app registration `strlix-market-api` the same way as B.  
3. User flow: **External Identities → User flows → New user flow** (sign up and sign in). Email + password is enough. Social IdPs can wait.  
4. Link the app to the user flow.  
5. Token configuration: same email / preferred_username claims.  
6. Issuer and JWKS for CIAM (replace `<tenant-id>`):

```text
issuer: https://<tenant-id>.ciamlogin.com/<tenant-id>/v2.0
jwks:   https://<tenant-id>.ciamlogin.com/<tenant-id>/discovery/v2.0/keys
```

Set `STRLIX_ENTRA_KIND=ciam` so the API can derive those URLs from the tenant id when the explicit issuer is empty.

## Env vars (ACA `ca-market-api`)

Leave these **unset or anon** until you have finished the portal steps. Names match `market_api/settings.py` (`STRLIX_` prefix).

```text
STRLIX_AUTH_MODE=anon
# flip to entra only after the values below are real:
# STRLIX_AUTH_MODE=entra

STRLIX_ENTRA_TENANT_ID=<directory-tenant-id>
STRLIX_ENTRA_CLIENT_ID=<application-client-id>
STRLIX_ENTRA_AUDIENCE=api://strlix-market
STRLIX_ENTRA_KIND=workforce          # or ciam
# Optional overrides. When empty, issuer + JWKS are derived from tenant id + kind.
STRLIX_ENTRA_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
STRLIX_ENTRA_JWKS_URI=https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys
```

Workforce derivation (kind `workforce`):

```text
issuer: https://login.microsoftonline.com/<tenant-id>/v2.0
jwks:   https://login.microsoftonline.com/<tenant-id>/discovery/v2.0/keys
```

The client id is accepted as a second audience so a token whose `aud` is the raw client id still validates when `STRLIX_ENTRA_CLIENT_ID` is set.

Example ACA update (non-secret values only; does **not** force entra):

```bash
az containerapp update -g rg-zevi-cloudphone -n ca-market-api \
  --set-env-vars \
    STRLIX_AUTH_MODE=anon \
    STRLIX_ENTRA_TENANT_ID=<tenant-id> \
    STRLIX_ENTRA_CLIENT_ID=<client-id> \
    STRLIX_ENTRA_AUDIENCE=api://strlix-market \
    STRLIX_ENTRA_KIND=workforce
```

## What stays true

- `/v1/auth/anon`, `/v1/auth/claim`, `/v1/auth/refresh`, `/v1/auth/logout` are unchanged for local tokens.  
- Catalog browse and the phone preview do not require Entra.  
- Entra login does not mint a refresh token. The client keeps using Entra's own refresh. Logout of an Entra access token cannot revoke it server-side before `exp` (there is no local `jti` session).  
- No cross-RG identity work. No deletion of existing anon sessions.
