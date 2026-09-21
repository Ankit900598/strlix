# Entra External ID path (minimal — mostly portal)

**Goal:** optional CIAM for web-market / market-api without forcing login mid-demo.  
**This sprint:** NOTES + stub only. No production auth flip.

## Choose a path

| Option | When | Cost |
|--------|------|------|
| **A. External ID (CIAM) tenant** | Consumer sign-up / social later | MAU-based; free tier often enough for demo |
| **B. Workforce app registration** (current tenant `d0a3e72e-…`) | Internal / investor demos only | $0 |

Prefer **B** for tonight’s wiring notes; plan **A** when consumer signup is real.

## Portal steps (B — workforce stub)

1. Entra ID → App registrations → **New registration**  
   - Name: `strlix-market-web`  
   - Accounts: single tenant (or multi if External ID later)  
   - Redirect URI (SPA): `https://<afd-endpoint>/market/` and `http://127.0.0.1:8080/market/`
2. Expose an API / create app for `strlix-market-api` (audience `api://strlix-market`).
3. Certificates & secrets → new client secret → store **only** in `kv-zevi-strlix` as `entra-market-client-secret`.
4. Note `Application (client) ID` and `Directory (tenant) ID` as ACA env (non-secret).

## Later code flag (not enabled)

```text
STRLIX_AUTH_MODE=anon|entra   # default anon for demos
STRLIX_ENTRA_TENANT_ID=...
STRLIX_ENTRA_CLIENT_ID=...
STRLIX_ENTRA_AUDIENCE=api://strlix-market
```

Keep `/v1/auth/anon` + claim flow for phone-first preview. Entra is additive.

## Explicit non-goals tonight

- No forced login wall on catalog browse  
- No deletion of existing JWT anon sessions  
- No cross-RG identity work
