# Private path for `pe-redis-strlix-amr` (do not cut public access yet)

**RG lock:** `rg-zevi-cloudphone` only. Do not delete Redis, the private endpoint, the VNet, or `ca-redis`.

## What is already true

| Piece | State |
|-------|--------|
| Managed Redis | `redis-strlix-amr` in **eastus**, public network access **Enabled** |
| Private endpoint | `pe-redis-strlix-amr` on `pe-subnet` `10.0.1.0/27` of `vm-zevi-cloudphone-vnet` (eastus), private IP `10.0.1.4` |
| Private DNS | zone `privatelink.redis.azure.net` linked to that eastus VNet |
| market-api | `ca-market-api` on Container Apps env `cae-zevi-strlix` in **eastus2** |
| Cutover | market-api uses the **public** `rediss://` host. `/health` reports `redis: true`. |

Public access stays on until a private path from the Container App actually resolves and connects. Disabling it earlier takes down sessions and rate limits.

## Why this is not a one-command flip

`cae-zevi-strlix` was created as a consumption environment **without** VNet integration. Azure does not let you bolt a VNet onto that existing environment in place. Recreating the environment would force new container apps and is **out of scope** — do not delete `cae-zevi-strlix`.

A private path needs all of the following:

1. A VNet that the Container Apps environment can use (today: **missing**).
2. Peering from that VNet (eastus2) to `vm-zevi-cloudphone-vnet` (eastus). Cross-region peering works and costs extra; it is not free.
3. The private DNS zone `privatelink.redis.azure.net` linked to the CAE VNet so `redis-strlix-amr.eastus.redis.azure.net` resolves to `10.0.1.4` inside the app, not the public IP.
4. A smoke from `ca-market-api` (`/health` → `redis: true`) **before** public access changes.
5. `CONFIRM=yes` on the disable step.

Until step 1 is true, stop. The script exits 0 and leaves public access Enabled.

## Script

```bash
./infra/hardening/PRIVATE-REDIS-PATH.sh                 # inspect + print
./infra/hardening/PRIVATE-REDIS-PATH.sh --apply         # peering + DNS link ONLY if a CAE VNet exists
CONFIRM=yes ./infra/hardening/PRIVATE-REDIS-PATH.sh --apply   # also disable public access after the probe
```

`CONFIRM=yes` without `--apply` does not change Azure. `--apply` without `CONFIRM=yes` never calls the public-access update.

## Rollback if public access was disabled and health goes false

```bash
az redisenterprise update -g rg-zevi-cloudphone -n redis-strlix-amr \
  --public-network-access Enabled
```

Then force a new `ca-market-api` revision only if the app cached a failed client (`redis_client` latches a failure until process restart). Do not delete the private endpoint while rolling back.

## Key Vault

The primary key stays in `kv-zevi-strlix` / `redis-primary-key`. Do not copy it into git. The URL shape is:

```text
rediss://:<key>@redis-strlix-amr.eastus.redis.azure.net:10000/0
```

That hostname is correct for both public and private access; private DNS overrides the A record inside the linked VNet.
