-- ==============================================================================
-- SUPABASE DASHBOARD PROJECT - DATABASE SETUP
-- ==============================================================================

-- 1. By default, the client API cannot query the `auth.users` table for security reasons.
-- To allow our frontend to securely fetch a read-only list of users, we create a
-- PostgreSQL function (RPC - Remote Procedure Call) with the `SECURITY DEFINER` tag.
-- This tells Supabase to run this function with admin privileges, allowing it to
-- read the internal `auth.users` table.

CREATE OR REPLACE FUNCTION get_users_overview()
RETURNS TABLE (
    id UUID,
    email VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    last_sign_in_at TIMESTAMP WITH TIME ZONE
)
SECURITY DEFINER 
SET search_path = public
AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        u.id, 
        -- We only return the email if you want to. In production, you might want to obscure this further.
        u.email::VARCHAR, 
        u.created_at, 
        u.last_sign_in_at
    FROM auth.users u
    ORDER BY u.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- 2. Grant execution permission to the public (anon) role
-- Since our app allows even unauthenticated users to see the dashboard in this demo
-- (or maybe we want only authenticated users to see it). 
-- Usually, we grant execution to `anon` and `authenticated`.
GRANT EXECUTE ON FUNCTION get_users_overview() TO anon, authenticated;

-- ==============================================================================
-- 3. ADMIN ACTION: Delete a user by ID
-- ==============================================================================
-- This function allows an authenticated admin user to delete another user from
-- auth.users. The SECURITY DEFINER tag grants it elevated privileges to perform
-- the deletion on the restricted auth schema.
-- NOTE: In production, add a role check to restrict this to admins only.

CREATE OR REPLACE FUNCTION delete_user(target_user_id UUID)
RETURNS VOID
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    DELETE FROM auth.users WHERE id = target_user_id;
END;
$$ LANGUAGE plpgsql;

-- Only allow authenticated (logged-in) users to call this action
GRANT EXECUTE ON FUNCTION delete_user(UUID) TO authenticated;

-- ==============================================================================
-- 4. SEED DATA: Fake Users for Dashboard Demo
-- ==============================================================================
-- These users are inserted directly into auth.users for demo/educational purposes.
-- Passwords are hashed using bcrypt (the string below = "password123").
-- Dates are spread over ~3 months to make the growth chart look realistic.
-- last_sign_in_at is NULL for some users to appear as "Offline" in the dashboard.
-- 
-- ⚠️  Run this block ONCE. Running it again will throw duplicate-email errors.
--     Wrap in DO $$ ... $$ to safely skip existing users.

DO $$
DECLARE
  pw TEXT := '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy'; -- bcrypt of "password123"
BEGIN

  -- Users from ~3 months ago
  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'alice.johnson@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'alice.johnson@example.com', pw, NOW(), NOW() - INTERVAL '90 days', NOW(), NOW() - INTERVAL '2 days', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'bob.martinez@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'bob.martinez@example.com', pw, NOW(), NOW() - INTERVAL '85 days', NOW(), NOW() - INTERVAL '30 days', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'carol.white@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'carol.white@example.com', pw, NOW(), NOW() - INTERVAL '75 days', NOW(), NULL, '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  -- Users from ~2 months ago
  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'david.kim@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'david.kim@example.com', pw, NOW(), NOW() - INTERVAL '60 days', NOW(), NOW() - INTERVAL '1 hour', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'emma.davis@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'emma.davis@example.com', pw, NOW(), NOW() - INTERVAL '55 days', NOW(), NOW() - INTERVAL '15 days', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'frank.chen@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'frank.chen@example.com', pw, NOW(), NOW() - INTERVAL '48 days', NOW(), NULL, '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'grace.patel@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'grace.patel@example.com', pw, NOW(), NOW() - INTERVAL '40 days', NOW(), NOW() - INTERVAL '3 hours', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  -- Users from ~1 month ago
  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'henry.wilson@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'henry.wilson@example.com', pw, NOW(), NOW() - INTERVAL '28 days', NOW(), NOW() - INTERVAL '5 days', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'isabelle.nguyen@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'isabelle.nguyen@example.com', pw, NOW(), NOW() - INTERVAL '20 days', NOW(), NOW() - INTERVAL '20 minutes', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  -- Recent users (last 7 days → shows up in "New This Week" stat)
  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'jack.robinson@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'jack.robinson@example.com', pw, NOW(), NOW() - INTERVAL '5 days', NOW(), NOW() - INTERVAL '5 days', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'kate.sharma@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'kate.sharma@example.com', pw, NOW(), NOW() - INTERVAL '2 days', NOW(), NOW() - INTERVAL '10 minutes', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

  IF NOT EXISTS (SELECT 1 FROM auth.users WHERE email = 'liam.oconnor@example.com') THEN
    INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, aud, role)
    VALUES (gen_random_uuid(), 'liam.oconnor@example.com', pw, NOW(), NOW() - INTERVAL '1 day', NOW(), NOW() - INTERVAL '30 minutes', '{"provider":"email","providers":["email"]}', '{}', 'authenticated', 'authenticated');
  END IF;

END $$;

-- ==============================================================================
-- 5. NOTES TABLE — for the Notes page feature
-- ==============================================================================
-- Each user can create, read, update, and delete their own notes.
-- Row Level Security ensures users ONLY ever see and modify their own rows.

CREATE TABLE IF NOT EXISTS public.notes (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title       TEXT NOT NULL DEFAULT 'Untitled note',
    content     TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Enable Row Level Security
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;

-- Policy: users can only access their own notes
CREATE POLICY "Users manage their own notes"
    ON public.notes FOR ALL
    USING  (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Trigger function: automatically update updated_at on every row edit
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS notes_touch_updated_at ON public.notes;
CREATE TRIGGER notes_touch_updated_at
    BEFORE UPDATE ON public.notes
    FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();
