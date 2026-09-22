# Public phone stream — status (2026-09-22 IST)

## Goal
Make Strlix cloud-phone **stream** reachable from a real phone browser via HTTPS (Azure Front Door), not `localhost`.

## Inventory (what serves the stream today)

| Piece | Where | Port / URL | Notes |
|-------|-------|------------|-------|
| **desktop-api** (viewer + `/ws/h264` + `/ws/stream` + `/adb/*`) | Azure VM `vm-zevi-cloudphone` (`20.115.117.71`) in `rg-zevi-cloudphone` | `0.0.0.0:8789` | systemd `strlix-desktop-api.service`; ADB to **local emulator** `emulator-5554` (not public). NSG allows 8789 from `*`. |
| session-broker | same VM | `127.0.0.1:8791` | not public |
| pilot monolith (legacy) | agent box historically `:8787` | not used for phone path | cloudflared-to-8787 on box is dead (`Tunnel not found`) |
| box desktop-api | agent box `:8789` | local/dev only | ADB via SSH tunnel to VM `:5555` |
| AWS Redroid GPU worker | `i-0531c567f620877c3` (g4dn) | ADB via SSM → `127.0.0.1:5556` | **kept running** for demos; not wired into this public viewer path yet |
| market-api + `/market/` static | Container App `ca-market-api` behind AFD | `/market/*`, `/v1/*`, `/health` | image **0.6.7** |

ADB is **not** opened to `0.0.0.0/0` for the phone path (emulator stays on VM loopback / SSH tunnel). Port **8789** is the HTTP viewer API only.

## What is live for phones now

| URL | Purpose |
|-----|---------|
| `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/` | Market UI (AFD → ca-market-api) |
| `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/*` | market-api (grant / devices / anon auth) — **same-origin** |
| `https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health` | market-api health (`0.6.7`) |
| `https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/` | **Public HTTPS stream viewer** (AFD → desktop-api `:8789`) |
| `https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/health` | desktop-api health (audio + h264 + client_debug) |
| `wss://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/ws/h264` | H.264 WS |
| `wss://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/ws/audio` | Opus WS (flags bit 0 = OpusHead) |

Market `index.html` sets:

```js
marketApi: "",  // same-origin via AFD
streamUrl: "https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net",
streamFallback: "/stream",
```

Touch, audio, and what “feels like a phone” can and cannot mean:
`demo/launch/PHONE-TOUCH-AUDIO.md`.

## AFD stream path — healthy as of 2026-09-22

`GET /health` on `strlix-stream-aabqdheycacyfah2.z03.azurefd.net` returns desktop-api JSON (HTTP 200, `access-control-allow-origin: *`). Market `streamUrl` points here. The trycloudflare hostname is no longer the phone path.

Created in `rg-zevi-cloudphone` / profile `afd-zevi-strlix`:

- Origin group `og-desktop-api` → `20.115.117.71.sslip.io:8789` (HTTP, cert check off)
- Endpoint `strlix-stream` → `https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net`
- Route `route-desktop-all` patterns `/*` (HttpOnly forward)
- Also on main edge: `route-stream-ws` `/ws/*`, `route-stream-adb` `/adb/*`
- Profile `originResponseTimeoutSeconds` raised to **240** for WS idle

## Remaining blockers for “real phone stream” polish

1. **Restart the emulator without `-no-audio`** or YouTube stays silent. See `PHONE-TOUCH-AUDIO.md`.
2. **Wire AWS Redroid** into desktop-api ADB serial for GPU demos on the same public viewer (today public viewer = Azure emulator). Sub-50 ms game latency is that path, not this emulator.
4. **Custom domain** `app.zevilabs.dev` still blocked on Name.com DNS (see `CUSTOM-DOMAIN-BLOCKER.md`).
5. Do **not** expose ADB (`5555`/`5556`) publicly; keep SSM/SSH tunnels only.

## Ops cheats

```bash
# market
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health | jq .version
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/ | grep streamUrl

# stream
curl -sS https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/health | jq '{version,audio:.audio.codec,h264:.h264.source}'

# AFD stream (expect 200 once fixed)
curl -sS -D- -o /dev/null https://strlix-stream-aabqdheycacyfah2.z03.azurefd.net/health | head
```
