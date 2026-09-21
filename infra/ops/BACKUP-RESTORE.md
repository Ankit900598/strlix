# Backup and restore — Postgres and Key Vault

**RG lock:** `rg-zevi-cloudphone` only.  
**Do not delete** `psql-zevi-strlix` or `kv-zevi-strlix` as part of a restore. A restore creates a **new** server or recovers a secret in place. Keep the original until the new one is proven.

No connection strings or secret values belong in this file or in git.

## Postgres `psql-zevi-strlix` (centralus, Flexible Server, B1ms)

Automated backups are on the server (Flexible Server default retention is 7 days unless the portal shows otherwise). HA is off, so this is backup-restore, not a hot standby.

List backups (names drift by CLI version; confirm with `--help` if this 404s):

```bash
az postgres flexible-server backup list \
  -g rg-zevi-cloudphone -n psql-zevi-strlix -o table
```

Point-in-time restore into a **new** server name. Do not reuse `psql-zevi-strlix`:

```bash
az postgres flexible-server restore \
  -g rg-zevi-cloudphone \
  --name psql-zevi-strlix-restore \
  --source-server psql-zevi-strlix \
  --restore-time "<ISO-8601 inside the retention window>"
```

Then:

1. Point a scratch `STRLIX_DATABASE_URL` at the new server (Key Vault, not git) and run `GET /health` plus a read of one known order.  
2. Apply `services/market-api/migrations/006_free_month.sql` if the backup predates the waitlist table.  
3. Cut `ca-market-api` over only after that read works. Leave the original server up.  
4. Deleting the original is a separate decision. This runbook does not do it.

`market-api` SQLite files are dev-only. They are not the production backup.

## Key Vault `kv-zevi-strlix` (eastus2)

Soft-delete and purge protection are on. A deleted secret can be recovered until purge protection says otherwise. Do not purge.

```bash
az keyvault secret list-deleted --vault-name kv-zevi-strlix -o table
az keyvault secret recover --vault-name kv-zevi-strlix -n <secret-name>
```

Secrets that matter for this launch (names only):

| Name | Use |
|------|-----|
| `redis-primary-key` | Managed Redis |
| `stripe-publishable-key`, `stripe-secret-key`, `stripe-webhook-secret` | Test values only until the free month ends |
| `entra-market-client-secret` | Only after the portal app exists |

Recovering a secret does not put it in the container app. Re-bind the ACA secret reference if the revision was created while the secret was missing. See `infra/hardening/PAYMENTS-KEYVAULT.md`.

## What backup does not cover

- The emulator userdata on `vm-zevi-cloudphone` (not customer records).  
- In-memory session-broker leases (they expire; the market-api lease row is the entitlement).  
- Front Door configuration (re-apply the scripts under `infra/hardening/`; don't delete the live profile to "restore" it).
