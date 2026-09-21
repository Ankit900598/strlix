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

Today `route-market` matches `/v1/*`, `/market/*`, `/health`, `/ready`. Legal pages need `/legal/*`:

```bash
./infra/hardening/EXTEND-AFD-ROUTES.sh
./infra/hardening/EXTEND-AFD-ROUTES.sh --apply
```

The phone-first viewer is served by desktop-api (`/` and `/static/legal/*`). It is not an origin on this Front Door. Linking a custom domain to AFD does not by itself put the phone UI on that host.

## Support email

Static legal pages say `support@strlix.app` and mark it as a placeholder. When the domain is real, set `SUPPORT_EMAIL` / `STRLIX_SUPPORT_EMAIL` on `ca-market-api` and `STRLIX_SUPPORT_EMAIL_PLACEHOLDER=false`. The static HTML does not read that env; update the banner in `static/legal/` in the same change.
