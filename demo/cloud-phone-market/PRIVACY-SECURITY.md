# Privacy & Security Checklist — Strlix market backend

**Date:** 2026-09-21 IST · **RG:** `rg-zevi-cloudphone` only

## Isolation
- [x] Postgres RLS on user-owned tables (`users`, `orders`, `leases`, `sessions`, `audit_log`)
- [x] FORCE ROW LEVEL SECURITY
- [x] App sets `app.user_id` per request
- [x] Cross-tenant read denied (Alice/Bob test)
- [x] Login via SECURITY DEFINER `market.find_or_create_user`

## Secrets
- [x] Key Vault `kv-zevi-strlix` RBAC + soft-delete + purge protection
- [x] Strong DB passwords + JWT secret in KV
- [x] ACA uses secret refs (not committed)
- [ ] Phase-2: direct Key Vault secretRef from MI without copying into ACA secret store

## Auth
- [x] JWT HS256 with `aud` + `iss` + `jti` + `typ`
- [x] Access TTL 15m, refresh 7d
- [x] Session key pattern `sess:{user_id}:{jti}`
- [x] Logout / soft-delete revoke path
- [ ] Entra External ID / JWKS (phase-2)

## Encryption & network
- [x] Postgres TLS required; clients `sslmode=require`
- [x] Azure-managed encryption at rest (CMEK later)
- [x] ACA HTTPS ingress; Redis requirepass + internal ingress
- [ ] Private Endpoints (need VNet CAE + eligible SKUs)
- [x] Documented: Azure Cache for Redis *create* retiring → ACA Redis foundation

## Privacy
- [x] PII minimized (email, display_name)
- [x] Audit log without tokens
- [x] Soft-delete API
- [x] Hard-delete stub
- [x] No live Stripe charges (`pay_mode=test`)

## Observability
- [x] App Insights `appi-zevi-strlix` → LAW
- [ ] OpenTelemetry SDK wiring (optional)
- [x] Policy: never log `Authorization` or raw tokens

## Dual-backend boundary
- [x] market-api ≠ android-api ≠ desktop-api ≠ session-broker
