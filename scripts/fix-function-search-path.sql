-- Fix Function Search Path Security Issues
-- Addresses Supabase database linter warnings for functions with mutable search_path
-- 
-- This script sets search_path on all functions to prevent search path injection attacks.
-- The recommended approach is to set search_path = '' or 'public, pg_temp' for security.
--
-- Run this script in your Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- Fix Functions: Set search_path to prevent injection attacks
-- ============================================================================
-- This script sets search_path on all functions that don't have it set
-- Using 'public, pg_temp' allows access to public schema and temp functions

DO $$
DECLARE
    func_record RECORD;
    func_signature TEXT;
    func_oid OID;
    has_search_path BOOLEAN;
BEGIN
    -- Loop through all functions in public schema
    FOR func_record IN
        SELECT 
            p.oid,
            p.proname as function_name,
            pg_get_function_identity_arguments(p.oid) as function_args,
            p.proconfig as config_settings
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
        AND p.proname NOT LIKE 'pg_%'  -- Skip PostgreSQL internal functions
    LOOP
        BEGIN
            -- Check if search_path is already set in proconfig
            has_search_path := false;
            IF func_record.config_settings IS NOT NULL THEN
                SELECT EXISTS (
                    SELECT 1 FROM unnest(func_record.config_settings) AS setting
                    WHERE setting LIKE 'search_path=%'
                ) INTO has_search_path;
            END IF;
            
            IF has_search_path THEN
                RAISE NOTICE 'Function %(%) already has search_path set, skipping', 
                    func_record.function_name, func_record.function_args;
                CONTINUE;
            END IF;
            
            -- Build function signature for logging
            func_signature := func_record.function_name || '(' || 
                COALESCE(func_record.function_args, '') || ')';
            
            -- Set search_path for the function
            -- Use 'public, pg_temp' to allow access to public schema and temp functions
            EXECUTE format(
                'ALTER FUNCTION public.%I(%s) SET search_path = public, pg_temp',
                func_record.function_name,
                COALESCE(func_record.function_args, '')
            );
            
            RAISE NOTICE 'Set search_path for function: %', func_signature;
            
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Failed to set search_path for function %(%): %', 
                func_record.function_name, 
                COALESCE(func_record.function_args, ''), 
                SQLERRM;
        END;
    END LOOP;
    
    RAISE NOTICE 'Finished setting search_path on functions';
END $$;

-- ============================================================================
-- Alternative: Set search_path for specific functions (if above doesn't work)
-- ============================================================================
-- If the dynamic approach above doesn't work, you can manually set search_path
-- for each function. Here are the functions from the linter warnings:

-- Example for one function:
-- ALTER FUNCTION public.rebuild_question_ofc_links() SET search_path = public, pg_temp;
-- ALTER FUNCTION public.upsert_ofc_option(...) SET search_path = public, pg_temp;
-- etc.

-- ============================================================================
-- Verify Functions Have search_path Set
-- ============================================================================
-- Run this query to check which functions still need search_path set:
/*
SELECT 
    p.proname as function_name,
    pg_get_function_identity_arguments(p.oid) as function_args,
    CASE 
        WHEN p.proconfig IS NULL THEN 'NO search_path'
        ELSE array_to_string(p.proconfig, ', ')
    END as current_settings
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
AND p.proname NOT LIKE 'pg_%'
ORDER BY p.proname;
*/

-- ============================================================================
-- Notes on Extensions in Public Schema
-- ============================================================================
-- The linter also warns about extensions in public schema:
-- - pg_trgm (trigram extension for text search)
-- - vector (vector extension for embeddings)
--
-- To fix these, you would need to:
-- 1. Create a new schema (e.g., 'extensions')
-- 2. Move extensions to that schema
-- 3. Update any code that references these extensions
--
-- However, moving extensions can be complex and may break existing functionality.
-- These warnings are lower priority (WARN level) and may be acceptable to leave
-- if the extensions are needed in public schema for compatibility.
--
-- If you want to move them:
-- CREATE SCHEMA IF NOT EXISTS extensions;
-- ALTER EXTENSION pg_trgm SET SCHEMA extensions;
-- ALTER EXTENSION vector SET SCHEMA extensions;
--
-- Then update search_path in functions that use them:
-- ALTER FUNCTION ... SET search_path = public, extensions, pg_temp;

-- ============================================================================
-- Notes on Leaked Password Protection
-- ============================================================================
-- This is an Auth setting, not a database schema issue.
-- To enable leaked password protection:
-- 1. Go to Supabase Dashboard → Authentication → Settings
-- 2. Enable "Leaked Password Protection"
-- 3. This checks passwords against HaveIBeenPwned.org database
--
-- This cannot be fixed via SQL script - it's a Supabase Auth configuration setting.

