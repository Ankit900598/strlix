-- Anonymous first session: no email/PII until the visitor chooses to save a rental.
-- Apply after 001_init_rls.sql and 003_login_helper.sql.

ALTER TABLE market.users ALTER COLUMN email DROP NOT NULL;
ALTER TABLE market.users ADD COLUMN IF NOT EXISTS is_anonymous BOOLEAN NOT NULL DEFAULT false;

CREATE OR REPLACE FUNCTION market.create_anon_user()
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = market, public
AS $$
DECLARE
  uid uuid;
BEGIN
  INSERT INTO market.users(email, display_name, is_anonymous)
  VALUES (NULL, NULL, true)
  RETURNING id INTO uid;
  RETURN uid;
END;
$$;

CREATE OR REPLACE FUNCTION market.claim_anon_user(
  p_user_id uuid,
  p_email citext,
  p_display_name text DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = market, public
AS $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM market.users
    WHERE email = p_email AND deleted_at IS NULL AND id <> p_user_id
  ) THEN
    RAISE EXCEPTION 'email already belongs to another account' USING ERRCODE = 'unique_violation';
  END IF;

  UPDATE market.users
     SET email = p_email,
         display_name = COALESCE(p_display_name, split_part(p_email::text, '@', 1)),
         is_anonymous = false,
         updated_at = now()
   WHERE id = p_user_id AND is_anonymous = true AND deleted_at IS NULL;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;
  RETURN p_user_id;
END;
$$;

REVOKE ALL ON FUNCTION market.create_anon_user() FROM PUBLIC;
REVOKE ALL ON FUNCTION market.claim_anon_user(uuid, citext, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION market.create_anon_user() TO strlix_app;
GRANT EXECUTE ON FUNCTION market.claim_anon_user(uuid, citext, text) TO strlix_app;
