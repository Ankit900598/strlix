# Entra workforce app — applied (soft launch)

**Status:** App registration + Key Vault secret created via Azure CLI.  
**Live ACA:** `ca-market-api` left on anon. **Do not flip** `STRLIX_AUTH_MODE` to `entra` until you intentionally enable it.

| Field | Value |
|-------|-------|
| kind | `workforce` |
| display name | `strlix-market-api` |
| tenant id | `d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2` |
| client id | `58e20155-d677-4985-86bf-ee48521dc6f8` |
| sign-in audience | single tenant (`AzureADMyOrg`) |
| identifier URIs | `api://strlix-market`, `api://58e20155-d677-4985-86bf-ee48521dc6f8` |
| audience (preferred) | `api://strlix-market` |
| access token version | 2 |
| optional claims (access token) | `email`, `preferred_username` (set via CLI) |
| Key Vault | `kv-zevi-strlix` / secret `entra-market-client-secret` |
| subscription | `a3dc5296-f948-427e-8656-c6bc52afee21` |
| account | `ay186mnc@gmail.com` |

No secret value is stored in git. The API validates JWTs with public JWKS; the client secret is for confidential-client / portal use only.

## What was done (CLI)

1. Confirmed `az account show` → ay186mnc / sub `a3dc5296-f948-427e-8656-c6bc52afee21`.
2. Created app `strlix-market-api` (did not already exist).
3. Set identifier URIs (`api://strlix-market` required `requestedAccessTokenVersion=2` under tenant URI policy; both URIs are registered).
4. Set optional claims `email` + `preferred_username` on access tokens.
5. Created a client secret and stored it only in Key Vault `kv-zevi-strlix` as `entra-market-client-secret`.
6. **Did not** update `ca-market-api` env. Live auth mode remains default anon (no `STRLIX_AUTH*` / `STRLIX_ENTRA*` env present on the container).

## Leftover portal clicks (optional)

None required for soft-launch JWT validation. Optional later:

- **Expose an API → Add a scope** `access_as_user` if a SPA will request tokens via OAuth.
- **Redirect URIs** when a browser SPA is wired (`https://<domain>/market/`, `http://127.0.0.1:8080/market/`).
- Do **not** grant admin-consent Graph permissions for soft launch.

## ACA env to set LATER (when flipping — not applied now)

Keep `STRLIX_AUTH_MODE=anon` until flip day. Exact vars for the flip:

```bash
az containerapp update -g rg-zevi-cloudphone -n ca-market-api \
  --set-env-vars \
    STRLIX_AUTH_MODE=entra \
    STRLIX_ENTRA_TENANT_ID=d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2 \
    STRLIX_ENTRA_CLIENT_ID=58e20155-d677-4985-86bf-ee48521dc6f8 \
    STRLIX_ENTRA_AUDIENCE=api://strlix-market \
    STRLIX_ENTRA_KIND=workforce
```

Optional explicit issuer/JWKS (derived automatically for workforce when empty):

```text
STRLIX_ENTRA_ISSUER=https://login.microsoftonline.com/d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2/v2.0
STRLIX_ENTRA_JWKS_URI=https://login.microsoftonline.com/d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2/discovery/v2.0/keys
```

Pre-stage non-secret Entra IDs **without** flipping mode (still anon):

```bash
az containerapp update -g rg-zevi-cloudphone -n ca-market-api \
  --set-env-vars \
    STRLIX_AUTH_MODE=anon \
    STRLIX_ENTRA_TENANT_ID=d0a3e72e-ad10-41f9-a96b-152c5d2d2cb2 \
    STRLIX_ENTRA_CLIENT_ID=58e20155-d677-4985-86bf-ee48521dc6f8 \
    STRLIX_ENTRA_AUDIENCE=api://strlix-market \
    STRLIX_ENTRA_KIND=workforce
```

See also `ENTRA-EXTERNAL-ID.md` for CIAM path and auth behavior.
