-- Seed AWS Redroid free-month grant target into devices_catalog.
-- devices.json already lists aws-redroid-t4-1 for /v1/devices, but orders.device_id
-- FKs to market.devices_catalog — missing row caused POST /v1/access/grant → 500.
-- Idempotent. Does not enable Stripe live. Does not change auth mode.
-- Applied on psql-zevi-strlix 2026-09-22 ~10:37 IST (box soft-launch smoke).

INSERT INTO market.devices_catalog
  (id, model, android, ram_gb, rom_gb, tier, price_hour_cents, price_day_cents, available, meta)
VALUES
  (
    'aws-redroid-t4-1',
    'Strlix Redroid T4',
    12,
    4,
    32,
    'gpu',
    15,
    249,
    true,
    '{"codename":"redroid-t4","region":"US East (AWS)","preview":"live","kind":"redroid","host":"strlix-gpu-worker-1","source":"007_seed_aws_redroid_catalog","notes":"Live AWS g4dn.xlarge Redroid; ADB via SSM 127.0.0.1:5556"}'::jsonb
  )
ON CONFLICT (id) DO UPDATE SET
  model = EXCLUDED.model,
  android = EXCLUDED.android,
  ram_gb = EXCLUDED.ram_gb,
  rom_gb = EXCLUDED.rom_gb,
  tier = EXCLUDED.tier,
  price_hour_cents = EXCLUDED.price_hour_cents,
  price_day_cents = EXCLUDED.price_day_cents,
  available = EXCLUDED.available,
  meta = EXCLUDED.meta;
