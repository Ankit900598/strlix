# Phone pool — provision and recycle

**Honest capacity today:** **2** reachable Androids (Azure pilot emulator + AWS Redroid T4). Resource group `rg-zevi-cloudphone` only for Azure. Do not delete the VM or the container apps to "recycle" a phone. Do not terminate the AWS GPU instance.

## Live devices (2026-09-22 IST soft launch)

| Pool / catalog id | Where | ADB serial (after tunnel) | Kind |
|-------------------|--------|---------------------------|------|
| `pilot-emulator-1` | Azure `vm-zevi-cloudphone` `20.115.117.71` | `127.0.0.1:5555` via `scripts/adb-tunnel.sh` | emulator |
| **`aws-redroid-t4-1`** | AWS `strlix-gpu-worker-1` `i-0531c567f620877c3` | `127.0.0.1:5556` via `scripts/adb-aws-redroid.sh` (SSM) | redroid (T4 guest GPU) |

Free-month grants target catalog `id` values in `web-market/devices.json`. Prefer **`aws-redroid-t4-1`** for GPU capacity while Azure NCasT4 / NVadsA10 remain limit 0.

## Two different clocks

| Record | Where | How long |
|--------|--------|----------|
| Free-month entitlement | market-api `leases` (`provider=free_month`, amount 0) | `STRLIX_FREE_MONTH_DAYS` (default 30) |
| Live interactive session | session-broker in memory | about 1 hour (`ttl_s` default 3600) |

A waitlist signup does not provision a new Android. The broker still **seeds one** device from env (phase-1):

- id `STRLIX_PILOT_DEVICE_ID` (default `pilot-emulator-1`; set `aws-redroid-t4-1` to point stream at Redroid)
- serial `ADB_SERIAL` (default `127.0.0.1:5555`; use `127.0.0.1:5556` after AWS SSM forward)
- `capacity_viewers` from `MAX_STREAM_CLIENTS` (default 12 watchers, **1** tap owner)
- label `kind=emulator` or `kind=redroid`

Code: `services/session-broker/session_broker/pool.py`.

100 signups ≠ 100 phones. Chat can scale on android-api; the picture on screen cannot.

## AWS Redroid path (preferred)

```bash
# From box (or any host with AWS CLI + session-manager-plugin):
./scripts/adb-aws-redroid.sh
# Expect: 127.0.0.1:5556 device … boot_completed=1
export ADB_SERIAL=127.0.0.1:5556
export STRLIX_PILOT_DEVICE_ID=aws-redroid-t4-1
```

Do **not** open SG `0.0.0.0/0` for ADB. Redroid publishes `127.0.0.1:5556` on the instance. Details: `infra/gpu-worker/aws/WORKER-LIVE.md`.

## Provision (when Ankit has another device)

1. Do not create an Azure GPU VM. GPU quota is still a ticket (`demo/credit-burn/REMAINING.md`). AWS T4 is the soft-launch GPU seat.
2. A physical phone or a second emulator must be reachable by ADB from the stream host.
3. Point `ADB_SERIAL` at it and set a new `STRLIX_PILOT_DEVICE_ID` only if you intend to replace the pilot id. Adding a second **simultaneous** broker device means extending `DevicePool` — the phase-1 pool does not read a catalog from Postgres.
4. market-api catalog rows in `web-market/devices.json` are product SKUs. `available: true` with `preview: "mock"` is **not** a booted phone. `preview: "live"` on `aws-redroid-t4-1` / `pixel-7a-a14` means a real path exists.

## Recycle

1. Stop new leases in the broker by marking the device `draining` (in-process; a restart of the broker clears memory and boots the seed device as `ready` again).
2. Wait for the current session `expires_at`. Don't kill the Azure VM or **terminate** the AWS instance to force it.
3. Emulator / Redroid userdata is not a customer backup. Wiping is fine for a demo reset and is not a privacy delete of market-api rows. Use `/v1/privacy/soft-delete` plus a support request for the waitlist email.
4. `ca-redis` scaled to min replicas 0 is the old sidecar. It is not the phone pool. Do not delete it from this runbook.
5. Idle AWS cost: `aws ec2 stop-instances --region us-east-1 --instance-ids i-0531c567f620877c3` (keeps EBS; public IP changes on start).

## Free-month abuse

market-api will not stack a second active free lease for the same user and device. Rate limits in `infra/hardening/ABUSE-CONTROLS.md` still apply. The free month does not add phones.
