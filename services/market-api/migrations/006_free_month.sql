-- Free-month launch: waitlist (email + created_at) and a plan value the
-- market can store once this migration is applied.
-- Safe to re-run. Does not drop data. Does not enable live Stripe.
-- Apply on psql-zevi-strlix (centralus) as a migrator / admin before
-- production waitlist inserts. SQLite dev databases create waitlist in-process.

ALTER TABLE market.orders DROP CONSTRAINT IF EXISTS orders_plan_check;
ALTER TABLE market.orders
  ADD CONSTRAINT orders_plan_check CHECK (plan IN ('hour', 'day', 'free_month'));

CREATE TABLE IF NOT EXISTS market.waitlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  invite_code_hash TEXT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS waitlist_email_unique ON market.waitlist (email);

ALTER TABLE market.waitlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.waitlist FORCE ROW LEVEL SECURITY;

-- Signup has no tenant yet. Inserts are allowed; listing emails is not.
DROP POLICY IF EXISTS waitlist_insert ON market.waitlist;
CREATE POLICY waitlist_insert ON market.waitlist
  FOR INSERT
  WITH CHECK (true);

GRANT INSERT ON market.waitlist TO strlix_app;
