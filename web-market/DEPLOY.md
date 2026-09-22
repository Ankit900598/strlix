# web-market deploy — soft-launch phone path

Public market: `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/`

## What broke real phones

Live `index.html` hardcoded:

```js
marketApi: "http://127.0.0.1:8792",
streamUrl: "http://127.0.0.1:8789",
```

A phone browser on Azure Front Door cannot reach `127.0.0.1` on the operator laptop, and HTTPS pages block HTTP iframes (mixed content). That looked like “browser not working.”

## Same-origin config (this PR)

`window.STRLIX_MARKET` now uses:

| Key | Value | Meaning |
|-----|--------|---------|
| `marketApi` | `""` | `fetch("/v1/…")` on the AFD host |
| `streamUrl` | `"/stream"` | iframe ` /stream/?embed=1 ` |
| `streamFallback` | `"/stream"` | same until a second origin exists |

Safety net in `js/market.js`: if the page is not on loopback but config still points at `127.0.0.1`, it forces same-origin defaults. Local overrides: `?api=` / `?stream=`.

`market-api` grant payloads default `stream_url` / `stream_fallback` to `/stream` (version **0.6.5**).

## Deploy static market + API

Market UI is served from the **market-api** image (`StaticFiles` at `/market`).

```bash
# from repo root
docker build -f services/market-api/Dockerfile -t market-api:0.6.5 .
az acr login -n acrzevistrlix
docker tag market-api:0.6.5 acrzevistrlix.azurecr.io/market-api:0.6.5
docker push acrzevistrlix.azurecr.io/market-api:0.6.5
az containerapp update -g rg-zevi-cloudphone -n ca-market-api \
  --image acrzevistrlix.azurecr.io/market-api:0.6.5
```

Optional env on the Container App (relative paths are fine):

```text
STRLIX_STREAM_URL=/stream
STRLIX_STREAM_FALLBACK=/stream
STRLIX_BILLING_MODE=free_month
STRLIX_PAY_MODE=test
PAYMENTS_LIVE=false
STRLIX_ALLOW_LIVE_CHARGES=false
```

Stripe **live stays OFF**.

## Attach stream origin to Front Door (required for iframe)

AFD today only routes `/v1/*`, `/market/*`, `/health`, `/ready`. `/stream/` is **404** until operators attach desktop-api.

Dry-run (prints commands):

```bash
./infra/hardening/ATTACH-AFD-STREAM.sh
```

Apply:

```bash
# default origin: vm desktop-api 20.115.117.71:8789
./infra/hardening/ATTACH-AFD-STREAM.sh --apply

# or a Cloudflare quick tunnel hostname (HTTPS origin):
STREAM_ORIGIN_HOST=xxxx.trycloudflare.com STREAM_ORIGIN_HTTP_PORT=443 \
  ./infra/hardening/ATTACH-AFD-STREAM.sh --apply
```

Routes added (do **not** steal market `/v1/*`):

- `/stream`, `/stream/*` → viewer (URL rewrite strips `/stream` → `/` on origin)
- `/ws/*` → H.264 / JPEG / live / stt sockets (viewer uses `wss://<afd>/ws/…`)
- `/adb/*`, `/voice/*`, `/replay/*`, `/demo/*`, `/static/*`

Ensure the VM NSG allows Azure Front Door to hit `:8789`, or use a tunnel.

Smoke:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/stream/
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/stream/health
```

## If Chrome inside Redroid is missing

That is separate from the web iframe. After ADB is up:

```bash
./scripts/adb-aws-redroid.sh
export ADB_SERIAL=127.0.0.1:5556
# set CHROME_APK to a matching ABI APK, then:
./scripts/install-chrome-redroid.sh
```

## Real-phone verification checklist

On a **physical** phone browser (not desktop DevTools device mode):

1. Open `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/`
2. View source / DevTools: `STRLIX_MARKET.marketApi` is `""`, `streamUrl` is `"/stream"` — **no** `127.0.0.1`
3. Catalog loads (same-origin `GET /v1/devices`)
4. Tap the hero phone → immersive bezel opens
5. Stream iframe URL is same-host `/stream/?embed=1` (after AFD attach)
6. Touch taps move the cloud phone; no mixed-content warnings
7. Ask stays **inside** the phone chrome (embed viewer), not a giant external chat panel
8. Free-month grant still works; Stripe live still off (`GET /v1/launch`)

## Local dev

```bash
cd web-market && python3 -m http.server 8765 --bind 127.0.0.1
# open with overrides:
# http://127.0.0.1:8765/?api=http://127.0.0.1:8792&stream=http://127.0.0.1:8789
```
