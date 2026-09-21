# Phone pool — provision and recycle

**Honest capacity today:** one emulator. Resource group `rg-zevi-cloudphone` only. Do not delete the VM or the container apps to "recycle" a phone.

## Two different clocks

| Record | Where | How long |
|--------|--------|----------|
| Free-month entitlement | market-api `leases` (`provider=free_month`, amount 0) | `STRLIX_FREE_MONTH_DAYS` (default 30) |
| Live interactive session | session-broker in memory | about 1 hour (`ttl_s` default 3600) |

A waitlist signup does not provision a new Android. The broker seeds a single device:

- id `STRLIX_PILOT_DEVICE_ID` (default `pilot-emulator-1`)
- serial `ADB_SERIAL` (default `127.0.0.1:5555`)
- `capacity_viewers` from `MAX_STREAM_CLIENTS` (default 12 watchers, **1** tap owner)
- label `kind=emulator`

Code: `services/session-broker/session_broker/pool.py`.

100 signups ≠ 100 phones. Chat can scale on android-api; the picture on screen cannot.

## Provision (when Ankit has another device)

1. Do not create a GPU VM. GPU quota is still a ticket (`demo/credit-burn/REMAINING.md`).
2. A physical phone or a second emulator must be reachable by ADB from the stream host.
3. Point `ADB_SERIAL` at it and set a new `STRLIX_PILOT_DEVICE_ID` only if you intend to replace the pilot id. Adding a second device means extending `DevicePool` — the phase-1 pool does not read a catalog from Postgres.
4. market-api catalog rows in `web-market/devices.json` are product SKUs. `available: true` with `preview: "mock"` is **not** a booted phone.

## Recycle

1. Stop new leases in the broker by marking the device `draining` (in-process; a restart of the broker clears memory and boots the seed device as `ready` again).
2. Wait for the current session `expires_at`. Don't kill the VM to force it — that drops the only phone.
3. Emulator userdata is not a customer backup. Wiping the AVD is fine for a demo reset and is not a privacy delete of market-api rows. Use `/v1/privacy/soft-delete` plus a support request for the waitlist email.
4. `ca-redis` scaled to min replicas 0 is the old sidecar. It is not the phone pool. Do not delete it from this runbook.

## Free-month abuse

market-api will not stack a second active free lease for the same user and device. Rate limits in `infra/hardening/ABUSE-CONTROLS.md` still apply. The free month does not add phones.
