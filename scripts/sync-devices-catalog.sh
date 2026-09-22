#!/usr/bin/env bash
# Upsert web-market/devices.json into market.devices_catalog on Postgres.
# Usage:
#   STRLIX_DATABASE_URL=… ./scripts/sync-devices-catalog.sh
#   # or: pulls database-url from kv-zevi-strlix when az is logged in
# Does not print the URL. Does not enable Stripe / Entra / GPU creates.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -z "${STRLIX_DATABASE_URL:-}" ]]; then
  STRLIX_DATABASE_URL="$(az keyvault secret show -n database-url --vault-name kv-zevi-strlix --query value -o tsv)"
  export STRLIX_DATABASE_URL
fi
python3 - <<'PY'
import json, os, sys
try:
    import psycopg
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "psycopg[binary]"])
    import psycopg

url = os.environ["STRLIX_DATABASE_URL"]
if url.startswith("postgres://"):
    url = "postgresql://" + url[len("postgres://") :]
devs = json.load(open("web-market/devices.json"))["devices"]
sql = """
INSERT INTO market.devices_catalog
  (id, model, android, ram_gb, rom_gb, tier, price_hour_cents, price_day_cents, available, meta)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
ON CONFLICT (id) DO UPDATE SET
  model=EXCLUDED.model, android=EXCLUDED.android, ram_gb=EXCLUDED.ram_gb,
  rom_gb=EXCLUDED.rom_gb, tier=EXCLUDED.tier,
  price_hour_cents=EXCLUDED.price_hour_cents, price_day_cents=EXCLUDED.price_day_cents,
  available=EXCLUDED.available, meta=EXCLUDED.meta
"""
with psycopg.connect(url, connect_timeout=20) as con:
    with con.cursor() as cur:
        for d in devs:
            meta = {
                "codename": d.get("codename"),
                "region": d.get("region"),
                "preview": d.get("preview"),
                "kind": d.get("kind"),
                "notes": d.get("notes"),
                "host": d.get("host"),
                "source": "sync-devices-catalog.sh",
            }
            cur.execute(
                sql,
                (
                    d["id"],
                    d["model"],
                    int(d.get("android") or 0),
                    int(d.get("ram_gb") or 0),
                    int(d.get("rom_gb") or 0),
                    d.get("tier") or "standard",
                    int(d.get("price_hour_cents") or 0),
                    int(d.get("price_day_cents") or 0),
                    bool(d.get("available", True)),
                    json.dumps(meta),
                ),
            )
        con.commit()
        cur.execute("SELECT id FROM market.devices_catalog ORDER BY id")
        ids = [r[0] for r in cur.fetchall()]
print(f"synced {len(devs)} devices.json rows; catalog now has {len(ids)} ids")
print("has aws-redroid-t4-1:", "aws-redroid-t4-1" in ids)
PY
