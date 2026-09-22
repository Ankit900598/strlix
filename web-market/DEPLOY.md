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

`window.STRLIX_MARKET` ships:

| Key | Value | Meaning |
|-----|--------|---------|
| `marketApi` | `""` | `fetch("/v1/…")` on the AFD host |
| `streamUrl` | Cloudflare HTTPS **or** `"/stream"` | iframe the interim tunnel, or same-origin once AFD `/stream` exists |
| `streamFallback` | `""` | reuse `streamUrl` |

**Current default** (AFD `/stream` is still 404):

```js
streamUrl: "https://graduation-cope-elementary-defence.trycloudflare.com"
```

Switch the string to `"/stream"` only after `ATTACH-AFD-STREAM.sh --apply` and `GET /stream/health` returns 200. JS drops `127.0.0.1` on any public host. An absolute `https://` URL is kept as-is (the iframe must not be rewritten to path-only `/stream/`).

`market-api` **0.6.8** grant `stream_url` defaults to `/stream` when env is unset. The page's https `streamUrl` wins over that relative path so a grant cannot knock phones back onto a 404 or onto localhost.

## Deploy static market + API — required after merge

Merging this PR does **not** change production. Live `/market/` stays the old catalog UI until operators **rebuild and redeploy** the market-api image (static files are baked into the image).

```bash
# from repo root, after this PR is on main
docker build -f services/market-api/Dockerfile -t market-api:0.6.8 .
az acr login -n acrzevistrlix
docker tag market-api:0.6.8 acrzevistrlix.azurecr.io/market-api:0.6.8
docker push acrzevistrlix.azurecr.io/market-api:0.6.8
az containerapp update -g rg-zevi-cloudphone -n ca-market-api \
  --image acrzevistrlix.azurecr.io/market-api:0.6.8
```

Production today is **0.6.7** (same-origin API + Cloudflare `streamUrl`, old HTML). 0.6.8 is the phone-first UI. Do not roll the stream URL back to `127.0.0.1`.

Optional env on the Container App:

```text
STRLIX_STREAM_URL=https://graduation-cope-elementary-defence.trycloudflare.com
STRLIX_STREAM_FALLBACK=
STRLIX_BILLING_MODE=free_month
STRLIX_PAY_MODE=test
PAYMENTS_LIVE=false
STRLIX_ALLOW_LIVE_CHARGES=false
```

When AFD `/stream` is healthy, set `STRLIX_STREAM_URL=/stream` and the same in `index.html`, then redeploy again.

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
2. View source: `marketApi` is `""`. `streamUrl` is the https tunnel **or** `/stream`. **No** `127.0.0.1`
3. Catalog loads (same-origin `GET /v1/devices`)
4. Tap the hero phone → immersive bezel opens
5. Stream iframe is `https://….trycloudflare.com/?embed=1` today, or `/stream/?embed=1` after AFD attach
6. Touch taps move the cloud phone; no mixed-content warnings
7. Ask stays **inside** the phone chrome (embed viewer), not a giant external chat panel
8. Free-month grant still works; Stripe live still off (`GET /v1/launch`)

## Local dev

```bash
cd web-market && python3 -m http.server 8765 --bind 127.0.0.1
# open with overrides:
# http://127.0.0.1:8765/?api=http://127.0.0.1:8792&stream=http://127.0.0.1:8789
```
