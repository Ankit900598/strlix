-- Payment intents: store ONLY provider intent/session ids + status per tenant.
-- Never store card PANs, full charge payloads, or live secrets.
-- Applied on Postgres with RLS matching market.orders.

CREATE TABLE IF NOT EXISTS market.payment_intents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES market.users(id),
  order_id UUID REFERENCES market.orders(id),
  provider TEXT NOT NULL,                 -- stripe|razorpay|stub
  provider_intent_id TEXT NOT NULL,       -- pi_xxx / cs_xxx / test_* stub
  status TEXT NOT NULL,                  -- requires_confirmation|open|succeeded|succeeded_test|failed|canceled|received
  amount_cents INT NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, provider_intent_id)
);

CREATE INDEX IF NOT EXISTS idx_payment_intents_user
  ON market.payment_intents (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_payment_intents_order
  ON market.payment_intents (order_id);

ALTER TABLE market.payment_intents ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.payment_intents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS payment_intents_isolation ON market.payment_intents;
CREATE POLICY payment_intents_isolation ON market.payment_intents
  USING (user_id = market.current_user_id())
  WITH CHECK (user_id = market.current_user_id());

-- Webhook worker updates by opaque provider id with app.user_id cleared.
DROP POLICY IF EXISTS payment_intents_webhook_update ON market.payment_intents;
CREATE POLICY payment_intents_webhook_update ON market.payment_intents
  FOR UPDATE
  USING (market.current_user_id() IS NULL);

GRANT SELECT, INSERT, UPDATE ON market.payment_intents TO strlix_app;

COMMENT ON TABLE market.payment_intents IS
  'Opaque Stripe/Razorpay intent ids + status only; no PANs; RLS by app.user_id';
