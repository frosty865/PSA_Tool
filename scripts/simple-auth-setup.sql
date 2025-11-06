-- SIMPLE AUTH SETUP - No complex tables, just what you need
-- This uses Supabase auth + a simple users_profiles table with role

-- ============================================
-- 1. Ensure users_profiles table exists with role column
-- ============================================
DO $$ 
BEGIN
    -- Create table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users_profiles'
    ) THEN
        CREATE TABLE users_profiles (
            user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            role TEXT NOT NULL DEFAULT 'psa', -- 'admin', 'spsa', or 'psa'
            organization TEXT DEFAULT 'CISA',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        RAISE NOTICE 'Created users_profiles table';
    ELSE
        -- Add role column if missing
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users_profiles' AND column_name = 'role'
        ) THEN
            ALTER TABLE users_profiles ADD COLUMN role TEXT NOT NULL DEFAULT 'psa';
            RAISE NOTICE 'Added role column to users_profiles';
        END IF;
        
        -- Add other columns if missing (non-critical)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users_profiles' AND column_name = 'is_active'
        ) THEN
            ALTER TABLE users_profiles ADD COLUMN is_active BOOLEAN DEFAULT true;
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users_profiles' AND column_name = 'organization'
        ) THEN
            ALTER TABLE users_profiles ADD COLUMN organization TEXT DEFAULT 'CISA';
        END IF;
    END IF;
END $$;

-- ============================================
-- 2. Create index on role for fast lookups
-- ============================================
CREATE INDEX IF NOT EXISTS idx_users_profiles_role ON users_profiles(role);
CREATE INDEX IF NOT EXISTS idx_users_profiles_active ON users_profiles(is_active);

-- ============================================
-- 3. Helper function to check if user is admin
-- ============================================
CREATE OR REPLACE FUNCTION is_admin(user_id_param UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM users_profiles
        WHERE user_id = user_id_param
          AND role IN ('admin', 'spsa')
          AND is_active = true
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- 4. Helper function to get user role
-- ============================================
CREATE OR REPLACE FUNCTION get_user_role(user_id_param UUID)
RETURNS TEXT AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role
    FROM users_profiles
    WHERE user_id = user_id_param AND is_active = true;
    
    RETURN COALESCE(user_role, 'psa'); -- Default to psa if not found
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Done! That's it.
-- Your API code just needs to:
-- 1. Get user from Supabase auth
-- 2. Check users_profiles.role
-- 3. If role = 'admin' OR role = 'spsa' → full access
-- 4. If role = 'psa' → standard user

SELECT 'Simple auth setup complete!' as status;

