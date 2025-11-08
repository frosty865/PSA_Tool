-- Fix RLS Security Issues
-- Addresses Supabase database linter warnings:
-- 1. Enable RLS on tables that have policies but RLS disabled
-- 2. Enable RLS on public tables that don't have RLS enabled
-- 3. Note: SECURITY DEFINER views are left as-is (may be intentional for admin views)

-- ============================================================================
-- 1. Enable RLS on user_profiles table
-- ============================================================================
-- The linter detected that user_profiles has RLS policies but RLS is not enabled
DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_profiles'
    ) THEN
        -- Enable RLS
        ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'Enabled RLS on user_profiles table';
    ELSE
        RAISE NOTICE 'user_profiles table does not exist, skipping';
    END IF;
END $$;

-- Also check for users_profiles (in case of naming inconsistency)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users_profiles'
    ) THEN
        ALTER TABLE public.users_profiles ENABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'Enabled RLS on users_profiles table';
    END IF;
END $$;

-- ============================================================================
-- 2. Enable RLS on processing_logs table
-- ============================================================================
-- The linter detected that processing_logs is public but RLS is not enabled
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'processing_logs'
    ) THEN
        -- Enable RLS
        ALTER TABLE public.processing_logs ENABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'Enabled RLS on processing_logs table';
        
        -- Create basic RLS policies if they don't exist
        -- Policy: Admins and service role can view all logs
        -- Note: We use a simple policy that doesn't reference columns that might not exist
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies 
            WHERE schemaname = 'public' 
            AND tablename = 'processing_logs' 
            AND policyname = 'Admins and service role can view processing logs'
        ) THEN
            -- Check if user_profiles table exists to determine policy structure
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'user_profiles'
            ) THEN
                -- Policy with user_profiles check
                EXECUTE '
                CREATE POLICY "Admins and service role can view processing logs"
                    ON public.processing_logs
                    FOR SELECT
                    USING (
                        EXISTS (
                            SELECT 1 FROM public.user_profiles
                            WHERE user_id = auth.uid() AND role IN (''admin'', ''spsa'')
                        )
                        OR
                        auth.jwt() ->> ''role'' = ''service_role''
                    )';
            ELSIF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'users_profiles'
            ) THEN
                -- Policy with users_profiles check (alternative naming)
                EXECUTE '
                CREATE POLICY "Admins and service role can view processing logs"
                    ON public.processing_logs
                    FOR SELECT
                    USING (
                        EXISTS (
                            SELECT 1 FROM public.users_profiles
                            WHERE user_id = auth.uid() AND role IN (''admin'', ''spsa'')
                        )
                        OR
                        auth.jwt() ->> ''role'' = ''service_role''
                    )';
            ELSE
                -- Fallback: Only service role can view (most restrictive)
                EXECUTE '
                CREATE POLICY "Service role can view processing logs"
                    ON public.processing_logs
                    FOR SELECT
                    USING (auth.jwt() ->> ''role'' = ''service_role'')';
            END IF;
            RAISE NOTICE 'Created RLS policy for processing_logs';
        END IF;
        
        -- Policy: Only service role can insert/update/delete (backend operations)
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies 
            WHERE schemaname = 'public' 
            AND tablename = 'processing_logs' 
            AND policyname = 'Service role can manage processing logs'
        ) THEN
            EXECUTE '
            CREATE POLICY "Service role can manage processing logs"
                ON public.processing_logs
                FOR ALL
                USING (auth.jwt() ->> ''role'' = ''service_role'')
                WITH CHECK (auth.jwt() ->> ''role'' = ''service_role'')';
            RAISE NOTICE 'Created RLS policy for processing_logs management';
        END IF;
    ELSE
        RAISE NOTICE 'processing_logs table does not exist, skipping';
    END IF;
END $$;

-- ============================================================================
-- 3. Verify RLS is enabled
-- ============================================================================
-- Check status of RLS on affected tables
DO $$
DECLARE
    rls_status text;
BEGIN
    -- Check user_profiles
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_profiles'
    ) THEN
        SELECT relforcerowsecurity::text INTO rls_status
        FROM pg_class
        WHERE relname = 'user_profiles' AND relnamespace = 'public'::regnamespace;
        RAISE NOTICE 'user_profiles RLS status: %', rls_status;
    END IF;
    
    -- Check processing_logs
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'processing_logs'
    ) THEN
        SELECT relforcerowsecurity::text INTO rls_status
        FROM pg_class
        WHERE relname = 'processing_logs' AND relnamespace = 'public'::regnamespace;
        RAISE NOTICE 'processing_logs RLS status: %', rls_status;
    END IF;
END $$;

-- ============================================================================
-- Notes on SECURITY DEFINER Views
-- ============================================================================
-- The following views have SECURITY DEFINER:
-- - v_recent_softmatches
-- - rls_verification
-- - subsector_metrics
-- - v_learning_overview
-- - compliance_report
-- - sector_metrics
--
-- These views may intentionally use SECURITY DEFINER for:
-- 1. Admin/reporting views that need elevated permissions
-- 2. Views that aggregate data across multiple tables with RLS
-- 3. System verification views
--
-- If you want to remove SECURITY DEFINER from these views, you would need to:
-- 1. Review each view's purpose and access requirements
-- 2. Ensure proper RLS policies exist on underlying tables
-- 3. Recreate views without SECURITY DEFINER:
--    CREATE OR REPLACE VIEW view_name AS ... (without SECURITY DEFINER)
--
-- For now, these are left as-is since they may be intentional for admin access.

