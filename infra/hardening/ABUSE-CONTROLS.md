# Abuse controls — market-api rate limits and Front Door WAF

**RG lock:** `rg-zevi-cloudphone` only. Do not delete resources.  
**Free month:** `FREE_LAUNCH_MODE` / `BILLING_MODE=free_month` does **not** raise or disable these limits.

## market-api (Redis when `STRLIX_REDIS_URL` is set)

Implementation: `services/market-api/market_api/redis_client.py` (sorted-set window, 60 seconds). Keys are `rl:<id>`. Anonymous keys use a short hash of the client host, not the raw address, and not the email.

| Path | Env | Default | Key |
|------|-----|---------|-----|
| Authenticated API (`checkout`, `grant`, jobs, …) | `STRLIX_RATE_LIMIT_PER_MIN` | 60 / user | user id |
| `POST /v1/auth/anon` | `STRLIX_ANON_RATE_PER_MIN` | 5 / client | `anon_create:` + host hash |
| `POST /v1/auth/login` | `STRLIX_LOGIN_RATE_PER_MIN` | 10 / client+email hash | `login:` + hashes |
| `POST /v1/waitlist` | `STRLIX_WAITLIST_RATE_PER_MIN` | 8 / client | `waitlist:` + host hash |

`GET /health`, `GET /ready`, and `GET /v1/launch` are not limited so probes and the free-month banner keep working.

### Redis down

If `STRLIX_REDIS_URL` is set and Redis does not answer, `rate_limit()` returns false and the API responds **429**. It does not fall open to the in-process bucket. That is the production path (Managed Redis `redis-strlix-amr`).

If `STRLIX_REDIS_URL` is empty (local sqlite demos), the limiter is in-process only and is not shared across replicas.

Free-month grants also reuse an existing active `provider=free_month` lease instead of stacking new ones.

## android-api

`services/android-api/android_api/rate_limit.py` is an in-process bucket, default `CHAT_RATE_PER_MIN=60`. It is not Redis-backed and is not turned off by the free month. Replace it with Redis before running more than one android-api replica.

## WAF (`wafzevistrlix` on `afd-zevi-strlix`)

Day-1 policy is already **Prevention** and associated as `sp-waf`. Do not block `GET /health` (AFD origin probe and the public smoke check).

Managed OWASP / DRS rule sets need **Premium** Front Door. Do not upgrade the SKU in this launch. Custom rate-limit rules on Standard are the safe tightening.

Script (dry-run unless `--apply`):

```bash
./infra/hardening/TIGHTEN-WAF.sh
./infra/hardening/TIGHTEN-WAF.sh --apply
```

The script adds three custom rate-limit rules matched on request URI:

- `/v1/auth/anon`
- `/v1/waitlist`
- `/v1/auth/login`

Threshold is 100 requests / minute / client IP at the edge (looser than the app limits, so a single demo user is not blocked, and a flood still dies at the edge). It does not create a rule for `/health` or `/*`.

After apply, confirm:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health
```

Expect **200**. If a new rule starts returning 403 on `/health`, delete that rule. Do not delete the WAF policy or the Front Door profile.
