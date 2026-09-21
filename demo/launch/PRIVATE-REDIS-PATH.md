# Private Redis path — CAE ↔ AMR findings (docs-only)

**When:** 2026-09-21 ~23:40 IST  
**Rule:** do **NOT** disable Redis `publicNetworkAccess` yet. PE already exists; market-api still uses public TLS to AMR.

## Current topology

| Piece | Region | State |
|-------|--------|--------|
| `cae-zevi-strlix` | **eastus2** | Consumption profile; **`vnetConfiguration: null`** (no VNet integration) |
| `ca-market-api` | eastus2 | Public ingress FQDN; secrets → `redis-strlix-amr.eastus.redis.azure.net:10000` |
| `redis-strlix-amr` (Managed Redis B0) | **eastus** | Running; **publicNetworkAccess=Enabled** |
| `pe-redis-strlix-amr` | eastus | Succeeded / Approved on `pe-subnet` (10.0.1.4) |
| `vm-zevi-cloudphone-vnet` | **eastus** | `10.0.0.0/16`; subnets `default` 10.0.0.0/24, `pe-subnet` 10.0.1.0/27 |
| Private DNS | global | `privatelink.redis.azure.net` linked to eastus VNet |

AFD + origin `/health` currently report `redis:true` over the **public** AMR endpoint.

## Can CAE get VNet integration with the existing VNet / pe-subnet?

### Short answer

**Not without a recreate + same-region networking redesign.** Attaching `cae-zevi-strlix` to `vm-zevi-cloudphone-vnet` is **blocked by region mismatch** (CAE eastus2 vs VNet eastus). `pe-subnet` (/27) is also **too small** and wrong purpose (PE only; CAE needs a delegated infra subnet, typically **≥ /23** for Consumption).

### Constraints

1. **Same-region rule** — Container Apps Environment custom VNet must be in the **same region** as the CAE.
2. **Immutable-ish** — VNet integration is set at CAE create time for this environment; current env has `vnetConfiguration: null`. Practical path = **new CAE** (or carefully planned recreate), then re-point apps — downtime / re-bind secrets / AFD origins.
3. **Subnet size** — Microsoft requires a dedicated subnet delegated to `Microsoft.App/environments`. Consumption commonly needs **/23** (512 addresses). Existing free space in `10.0.0.0/16` can host e.g. `10.0.2.0/23`, but only if CAE moves to **eastus**.
4. **PE locality** — Redis PE must stay in **eastus** next to `redis-strlix-amr`. An eastus2 CAE would need **VNet peering** (eastus2 CAE VNet ↔ eastus Redis VNet) plus DNS for `privatelink.redis.azure.net` on the CAE VNet — extra moving parts, still not “just flip PE”.

### Cheap paths ranked

| Option | Est. extra spend | Downtime | Verdict for soft-launch |
|--------|------------------|----------|-------------------------|
| **A. Keep public Redis** (status quo) | **$0** | None | **Recommended now** |
| **B. Recreate CAE in eastus** on new `/23` in existing VNet; apps use PE DNS | VNet free; possible brief CAE recreate; same-region PE works | Medium (app cutover) | Best *private* path later; still don’t disable public until smoke passes |
| **C. New eastus2 VNet + new CAE + peering to eastus PE VNet** | Peering ~pennies–few $/mo + dual VNet complexity | Medium–high | Avoid for soft-launch |
| **D. Move/recreate AMR in eastus2** | B0 was `InsufficientCapacity` in eastus2 previously | High | Blocked by capacity history |

### Spend note

No huge mandatory spend for Option B beyond operational risk: no new NAT Gateway required if egress stays on Azure defaults for many setups, but **verify egress / ACR pull** after VNet join. Do **not** add App Gateway / Firewall “for Redis” — overkill vs B0 (~$12/mo) + existing PE (~$7–8/mo).

## Gate before disabling public access

Only after **all** are true:

1. CAE (or jump host) resolves `redis-strlix-amr.eastus.redis.azure.net` → **private** IP `10.0.1.4` (or successor).
2. `ca-market-api` `/health` → `redis:true` with public access temporarily restricted in a controlled window (or dual-stack test from inside VNet).
3. AFD `/health` still 200 during the window.
4. Explicit operator approval.

Until then: **`publicNetworkAccess=Enabled` stays.**

## Related

- PE applied notes: `../credit-burn/HARDENING-APPLIED.md` §3  
- Remaining gates: `../credit-burn/REMAINING.md`
