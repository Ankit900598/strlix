# GLOBAL soft launch — TODAY (2026-09-22 IST)

**Goal:** Ship free-month market path with **real GPU phone capacity** on AWS Redroid while Azure GPU quota stays at 0. Stripe **live OFF**.

**Tip:** `a9619b5` (stream glue). **Smoke:** 2026-09-22 ~10:37 IST — health/market/legal/devices/waitlist/grant(redroid) OK. Catalog FK for `aws-redroid-t4-1` seeded (`007_seed_aws_redroid_catalog.sql`).

## Public launch surface

- **Public URL now:** https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/
- **Health:** market-api **0.6.4**; `billing_mode=free_month`; `card_required=false`.
- **Legal:** https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html (and privacy/support/capabilities). Bare `/market/legal/` is 404.
- **Branded host:** `app.zevilabs.dev` **AFD Pending**; Name.com **Cloudflare Turnstile** blocks DNS (token `_48ncbg9vt1u4zxek55jon1osqixlr88` expires ~2026-09-29). Soft launch stays on `*.azurefd.net`.

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

## Stream-host runbook (AWS Redroid)

Phase-1 `DevicePool` / pilot seeds **one** env device. Defaults stay Azure (`pilot-emulator-1` @ `127.0.0.1:5555`). To stream Redroid:

```bash
# Terminal A — keep tunnel alive (required)
./scripts/adb-aws-redroid.sh --watch
# Expect once:
#   127.0.0.1:5556  device product:redroid_x86_64_only …
#   boot_completed=1
#   ADB_SERIAL=127.0.0.1:5556  STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1

# Verify anytime:
adb devices -l
# must show 127.0.0.1:5556 state=device

# Terminal B — stream host (pilot) or session-broker
export ADB_SERIAL=127.0.0.1:5556
export STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1
# optional explicit labels:
# export STRLIX_PILOT_KIND=redroid
# export STRLIX_STREAM_ADB=aws-redroid

./scripts/run-pilot.sh
# or: services/session-broker/run.sh  (same env)
```

**Azure fallback (default, unchanged):**

```bash
unset STRLIX_STREAM_ADB STRLIX_PILOT_KIND
export STRLIX_PILOT_DEVICE_ID=pilot-emulator-1
export ADB_SERIAL=127.0.0.1:5555
./scripts/adb-tunnel.sh --watch   # other terminal
./scripts/run-pilot.sh
```

Only **one** H.264 producer per serial — see `demo/scale/STREAM-OWNER.md`.

### Honest boundaries

- Capacity is **Azure emulator + AWS Redroid on g4dn** (T4 guest GPU).
- Not certified today: physical sub-100 ms latency, counsel review, iOS, live Stripe, or Azure GPU.
- Phase-1 `DevicePool` seeds **one** env device — set `STRLIX_PILOT_DEVICE_ID` + `ADB_SERIAL` to stream Redroid; keep tunnel with `./scripts/adb-aws-redroid.sh --watch`.
- Multi-lease Azure+AWS simultaneously is **not** built (single-env Phase-1).
- Idle AWS cost ≈ **$0.526/hr** — stop (do not terminate) when unused.

## Catalog smoke

```bash
./scripts/smoke-catalog-redroid.sh
# expects aws-redroid-t4-1 available=true on AFD /v1/devices
```

## Smoke curls

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/

# Health: expect 200 with version 0.6.4, billing_mode=free_month,
# and card_required=false.
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/health

# Catalog: expect aws-redroid-t4-1 available.
curl -sS https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/devices \
  | jq '.devices[]|select(.id=="aws-redroid-t4-1")'

# Legal: expect HTTP 200.
curl -sS -o /dev/null -w '%{http_code}\n' \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/market/legal/terms.html

curl -sS -X POST \
  https://strlix-edge-fwf6grbbbzbggxbs.z03.azurefd.net/v1/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com"}'
```

## Docs

- Live worker: `infra/gpu-worker/aws/WORKER-LIVE.md`
- Pool honesty: `infra/ops/CAPACITY-PHONE-POOL.md`
- Status snapshot: `demo/launch/SOFT-LAUNCH-STATUS.md`

## Remaining / out of scope (honest)

1. Idle AWS ≈ **$0.526/hr** — `aws ec2 stop-instances --region us-east-1 --instance-ids i-0531c567f620877c3` (do **not** terminate).
2. External blockers: Name.com Turnstile → `app.zevilabs.dev` DNS; physical USB phone; Azure GPU quota 0; lawyer pass; live Stripe deferred; private Redis CAE region mismatch.
3. Multi-lease Azure+AWS broker — **out of scope** (Phase-1 single-env).
