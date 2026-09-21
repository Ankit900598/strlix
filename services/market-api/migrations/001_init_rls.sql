-- Requires: az postgres flexible-server parameter set --name azure.extensions --value PGCRYPTO,CITEXT
-- Strlix market schema — per-user isolation via Postgres RLS
-- Isolation rule: user_id = current_setting('app.user_id', true)::uuid
-- Catalog tables are public-read; user tables are tenant-scoped.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS billing;

-- App role used by market-api (non-superuser so RLS is enforced)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'strlix_app') THEN
    CREATE ROLE strlix_app LOGIN PASSWORD NULL; -- password set by provision script
  END IF;
END$$;

GRANT USAGE ON SCHEMA market, auth, billing TO strlix_app;

-- ---------- users (PII minimized: email + display_name only) ----------
CREATE TABLE IF NOT EXISTS market.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT NOT NULL,
  display_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ NULL, -- soft-delete
  CONSTRAINT users_email_unique UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS idx_users_email ON market.users (email) WHERE deleted_at IS NULL;

-- ---------- devices catalog (global, not per-user) ----------
CREATE TABLE IF NOT EXISTS market.devices_catalog (
  id TEXT PRIMARY KEY,
  model TEXT NOT NULL,
  android INT,
  ram_gb INT,
  rom_gb INT,
  tier TEXT,
  price_hour_cents INT NOT NULL DEFAULT 0,
  price_day_cents INT NOT NULL DEFAULT 0,
  available BOOLEAN NOT NULL DEFAULT true,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- ---------- orders ----------
CREATE TABLE IF NOT EXISTS market.orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES market.users(id),
  device_id TEXT NOT NULL REFERENCES market.devices_catalog(id),
  plan TEXT NOT NULL CHECK (plan IN ('hour', 'day')),
  amount_cents INT NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  provider TEXT NOT NULL, -- stripe|razorpay|stub
  status TEXT NOT NULL,   -- draft|checkout|paid_test|failed|refunded_test
  provider_ref TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON market.orders (user_id, created_at DESC);

-- ---------- leases ----------
CREATE TABLE IF NOT EXISTS market.leases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES market.users(id),
  order_id UUID NOT NULL REFERENCES market.orders(id),
  broker_sid TEXT,
  device_id TEXT NOT NULL,
  starts_at TIMESTAMPTZ,
  ends_at TIMESTAMPTZ,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_leases_user ON market.leases (user_id, status);

-- ---------- sessions metadata (Redis is source of truth for live sess; PG for audit) ----------
CREATE TABLE IF NOT EXISTS auth.sessions (
  jti UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES market.users(id),
  kind TEXT NOT NULL CHECK (kind IN ('access', 'refresh')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ NULL,
  user_agent_hash TEXT, -- hash only — never store raw UA/IP as PII dump
  ip_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth.sessions (user_id) WHERE revoked_at IS NULL;

-- ---------- privacy audit log ----------
CREATE TABLE IF NOT EXISTS market.audit_log (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NULL, -- null for system
  action TEXT NOT NULL, -- login|checkout|soft_delete|hard_delete|export|admin
  resource_type TEXT,
  resource_id TEXT,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb, -- NO tokens, NO raw PII
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON market.audit_log (user_id, created_at DESC);

-- ---------- RLS ----------
ALTER TABLE market.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.users FORCE ROW LEVEL SECURITY;
ALTER TABLE market.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.orders FORCE ROW LEVEL SECURITY;
ALTER TABLE market.leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.leases FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE market.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE market.audit_log FORCE ROW LEVEL SECURITY;
-- devices_catalog: no RLS (public catalog)

-- Helper: current tenant from session GUC set by app: SET LOCAL app.user_id = '<uuid>'
CREATE OR REPLACE FUNCTION market.current_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
$$;

-- users: can only see/update self
DROP POLICY IF EXISTS users_isolation ON market.users;
CREATE POLICY users_isolation ON market.users
  USING (id = market.current_user_id())
  WITH CHECK (id = market.current_user_id());

-- Allow INSERT of self during registration when app.user_id matches new row
-- (registration path sets app.user_id to the new id before insert)

DROP POLICY IF EXISTS orders_isolation ON market.orders;
CREATE POLICY orders_isolation ON market.orders
  USING (user_id = market.current_user_id())
  WITH CHECK (user_id = market.current_user_id());

DROP POLICY IF EXISTS leases_isolation ON market.leases;
CREATE POLICY leases_isolation ON market.leases
  USING (user_id = market.current_user_id())
  WITH CHECK (user_id = market.current_user_id());

DROP POLICY IF EXISTS sessions_isolation ON auth.sessions;
CREATE POLICY sessions_isolation ON auth.sessions
  USING (user_id = market.current_user_id())
  WITH CHECK (user_id = market.current_user_id());

DROP POLICY IF EXISTS audit_isolation ON market.audit_log;
CREATE POLICY audit_isolation ON market.audit_log
  FOR SELECT USING (user_id = market.current_user_id() OR user_id IS NULL);
CREATE POLICY audit_insert ON market.audit_log
  FOR INSERT WITH CHECK (user_id = market.current_user_id() OR user_id IS NULL);

-- Grants for app role
GRANT SELECT, INSERT, UPDATE ON market.users TO strlix_app;
GRANT SELECT ON market.devices_catalog TO strlix_app;
GRANT SELECT, INSERT, UPDATE ON market.orders TO strlix_app;
GRANT SELECT, INSERT, UPDATE ON market.leases TO strlix_app;
GRANT SELECT, INSERT, UPDATE ON auth.sessions TO strlix_app;
GRANT SELECT, INSERT ON market.audit_log TO strlix_app;
GRANT USAGE, SELECT ON SEQUENCE market.audit_log_id_seq TO strlix_app;

-- Bypass role for migrations only (admin) — table owners bypass RLS unless FORCE (we FORCE).
-- Admin connections use strlixadmin which is table owner → still subject to FORCE RLS.
-- Provide BYPASSRLS for migration role:
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'strlix_migrator') THEN
    CREATE ROLE strlix_migrator BYPASSRLS LOGIN PASSWORD NULL;
  END IF;
END$$;
