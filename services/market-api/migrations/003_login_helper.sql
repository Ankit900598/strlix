-- Login helper: find-or-create user by email (bypasses RLS via SECURITY DEFINER)
CREATE OR REPLACE FUNCTION market.find_or_create_user(p_email citext, p_display_name text DEFAULT NULL)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = market, public
AS $$
DECLARE
  uid uuid;
BEGIN
  SELECT id INTO uid FROM market.users WHERE email = p_email AND deleted_at IS NULL;
  IF uid IS NULL THEN
    uid := gen_random_uuid();
    INSERT INTO market.users(id, email, display_name)
    VALUES (uid, p_email, COALESCE(p_display_name, split_part(p_email::text, '@', 1)));
  END IF;
  RETURN uid;
END;
$$;

REVOKE ALL ON FUNCTION market.find_or_create_user(citext, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION market.find_or_create_user(citext, text) TO strlix_app;
