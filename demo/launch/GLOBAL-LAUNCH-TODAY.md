# Strlix global soft launch — today

**Date:** 2026-09-22 (IST)
**Status:** Global soft launch is open today, with the limitations below.

## Public launch surface

- **Public URL now:** https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/
- **Health:** market-api **0.6.4**; `billing_mode=free_month`; `card_required=false`.
- **Legal:** live at https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/
- **Branded host:** `app.zevilabs.dev` is still **AFD Pending** / domain **SKIPPED** — stay on `*.azurefd.net`.

## What “global soft launch” means today

- The waitlist and free grant are open worldwide on the AFD URL above.
- Access uses shared cloud Android capacity; this is not a dedicated private phone.
- The first month is free. Live Stripe charging is not enabled.

## Capacity wired (AWS Redroid in phone path)

| Piece | Status |
|-------|--------|
| AWS `strlix-gpu-worker-1` `i-0531c567f620877c3` | **RUNNING** · pub `44.204.83.61` · SSM Online |
| Redroid `strlix-redroid-1` | **UP** · ADB host `127.0.0.1:5556` · `boot_completed=1` · Android 12 |
| ADB from box / Azure | **SSM port-forward** → `127.0.0.1:5556` · `scripts/adb-aws-redroid.sh` |
| Catalog device id | **`aws-redroid-t4-1`** in `web-market/devices.json` (`available: true`, `preview: live`) |
| Free-month grant | `POST /v1/access/grant` with `device_id=aws-redroid-t4-1` |
| SG inbound ADB | **Closed** (SSM preferred). Never open `0.0.0.0/0` for ADB. |
| Azure pilot fallback | `pilot-emulator-1` via `scripts/adb-tunnel.sh` → `127.0.0.1:5555` |

### Operator commands

```bash
# 1) Tunnel + prove
./scripts/adb-aws-redroid.sh
# Expect: 127.0.0.1:5556  device product:redroid_x86_64_only …  boot_completed=1

# 2) Point pilot / android-api / session-broker at Redroid (stream host)
export ADB_SERIAL=127.0.0.1:5556
export STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1

# 3) Azure pilot remains fallback
./scripts/adb-tunnel.sh   # 127.0.0.1:5555 → vm-zevi-cloudphone
```

### Honest boundaries

- Capacity is **Azure emulator + AWS Redroid on g4dn** (T4 guest GPU).
- Not certified today: physical sub-100 ms latency, counsel review, iOS, live Stripe, or Azure GPU.
- Phase-1 `DevicePool` seeds **one** env device — set `STRLIX_PILOT_DEVICE_ID` + `ADB_SERIAL` to stream Redroid; keep tunnel with `./scripts/adb-aws-redroid.sh --watch`.
- Idle AWS cost ≈ **$0.526/hr** — stop (do not terminate) when unused.

## Docs

- Live worker: `infra/gpu-worker/aws/WORKER-LIVE.md`
- Pool honesty: `infra/ops/CAPACITY-PHONE-POOL.md`
- Status snapshot: `demo/launch/SOFT-LAUNCH-STATUS.md`

## Smoke curls

```bash
# Public market entry point: expect HTTP 200.
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/

# Health: expect 200 with version 0.6.4, billing_mode=free_month,
# and card_required=false.
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health

# Catalog: expect aws-redroid-t4-1 available.
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/devices | jq '.devices[]|select(.id=="aws-redroid-t4-1")'

# Legal: expect HTTP 200.
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html

# Waitlist: expect status=joined and card_required=false.
curl -sS -X POST \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
```
