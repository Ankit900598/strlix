# Custom domain on the existing Front Door endpoint

**Endpoint (already live):** `strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net`  
**Profile:** `afd-zevi-strlix` · **endpoint resource:** `strlix-edge`  
**RG lock:** `rg-zevi-cloudphone` only. Do not delete the profile, endpoint, or WAF.

This repo does **not** own `strlix.app`. `app.strlix.app` is a placeholder hostname until Ankit controls DNS.

## Script

```bash
# prints commands using the placeholder host; does not call Azure
./infra/hardening/ATTACH-CUSTOM-DOMAIN.sh

# real hostname you control
DOMAIN=app.strlix.app ./infra/hardening/ATTACH-CUSTOM-DOMAIN.sh --apply
```

`--apply` exits 2 when `DOMAIN` is unset so a placeholder cannot be applied by accident.

## DNS (registrar, outside Azure)

| Record | Name | Value |
|--------|------|--------|
| CNAME | `app` (or the host you set) | `strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net` |
| TXT | `_dnsauth.app` | validation token from `az afd custom-domain show` |

The managed certificate stays pending until both records validate. Leave the `*.azurefd.net` name linked (`--link-to-default-domain Enabled`) so `/health` keeps working during cutover.

## Routes

Today `route-market` matches `/v1/*`, `/market/*`, `/health`, `/ready` (the bicep skeleton also lists `/docs` and `/openapi.json`). Public legal pages are `/market/legal/*.html`, which `/market/*` already matches. Do not apply a new pattern for the soft launch.

`infra/hardening/EXTEND-AFD-ROUTES.sh` only adds a direct `/legal/*` alias. It is optional and was not applied. market-api still mounts `static/legal` at `/legal` when that directory is on disk. The market-api image copies `web-market/`, not `static/`, so the path that works on Front Door is `/market/legal/`.

The phone-first viewer is served by desktop-api (`/` and `/static/legal/*`). It is not an origin on this Front Door. Linking a custom domain to AFD does not by itself put the phone UI on that host. `static/legal/` and `web-market/legal/` are the same bytes.

## Support email

The default address on the static pages is `support@strlix.app`. While `STRLIX_SUPPORT_EMAIL_PLACEHOLDER` is true, the pages say that mailbox is being set up. `GET /v1/launch` returns the configured address (`SUPPORT_EMAIL` or `STRLIX_SUPPORT_EMAIL`). The HTML does not read that env. When the inbox is monitored, set `STRLIX_SUPPORT_EMAIL_PLACEHOLDER=false` and edit `static/legal/` and `web-market/legal/` in the same change.
