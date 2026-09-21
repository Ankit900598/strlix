-- Seed a minimal device catalog (idempotent)
INSERT INTO market.devices_catalog (id, model, android, ram_gb, rom_gb, tier, price_hour_cents, price_day_cents, available, meta)
VALUES
  ('pixel-7a', 'Pixel 7a', 14, 8, 128, 'standard', 49, 299, true, '{"notes":"demo"}'::jsonb),
  ('pixel-8', 'Pixel 8', 14, 8, 128, 'premium', 79, 499, true, '{}'::jsonb),
  ('legacy-7', 'Legacy A7', 7, 2, 16, 'legacy', 19, 99, true, '{"compat":true}'::jsonb)
ON CONFLICT (id) DO UPDATE SET
  model = EXCLUDED.model,
  available = EXCLUDED.available,
  price_hour_cents = EXCLUDED.price_hour_cents,
  price_day_cents = EXCLUDED.price_day_cents;
