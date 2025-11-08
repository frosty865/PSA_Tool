-- Fix RLS Performance and Duplicate Index Issues
-- Addresses Supabase database linter warnings:
-- 1. auth_rls_initplan: Policies re-evaluating auth.*() functions per row
-- 2. multiple_permissive_policies: Multiple permissive policies for same role/action
-- 3. duplicate_index: Identical indexes on tables
--
-- Run this script in your Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- 1. Fix auth_rls_initplan: Wrap auth.*() calls in subqueries
-- ============================================================================
-- The issue: RLS policies that use auth.uid(), auth.jwt(), auth.role() directly
-- re-evaluate these functions for every row, causing performance issues.
-- Solution: Wrap them in subqueries: (select auth.uid()) instead of auth.uid()
--
-- This script dynamically finds and fixes all such policies.

DO $$
DECLARE
    policy_record RECORD;
    policy_def TEXT;
    fixed_def TEXT;
    table_schema_name TEXT;
    table_name_val TEXT;
    policy_name_val TEXT;
    policy_cmd TEXT;
    cmd_type TEXT;
BEGIN
    -- Loop through all RLS policies in public schema
    FOR policy_record IN
        SELECT 
            schemaname,
            tablename,
            policyname,
            permissive,
            roles,
            cmd,
            qual,
            with_check
        FROM pg_policies
        WHERE schemaname = 'public'
        AND (qual IS NOT NULL OR with_check IS NOT NULL)
    LOOP
        BEGIN
            table_schema_name := policy_record.schemaname;
            table_name_val := policy_record.tablename;
            policy_name_val := policy_record.policyname;
            cmd_type := policy_record.cmd;
            
            -- Check if policy uses auth.*() functions that need fixing
            policy_def := COALESCE(policy_record.qual, '') || ' ' || COALESCE(policy_record.with_check, '');
            
            -- Skip if policy doesn't use auth functions
            IF policy_def !~* 'auth\.(uid|jwt|role)\(' THEN
                CONTINUE;
            END IF;
            
            -- Check if already fixed (contains (select auth.)
            IF policy_def ~* '\(select\s+auth\.' THEN
                RAISE NOTICE 'Policy % on %.% already uses subquery pattern, skipping', 
                    policy_name_val, table_schema_name, table_name_val;
                CONTINUE;
            END IF;
            
            -- Fix the policy definition
            fixed_def := policy_def;
            
            -- Replace auth.uid() with (select auth.uid())
            fixed_def := regexp_replace(fixed_def, 
                '\bauth\.uid\(\)', 
                '(select auth.uid())', 
                'gi');
            
            -- Replace auth.jwt() with (select auth.jwt())
            fixed_def := regexp_replace(fixed_def, 
                '\bauth\.jwt\(\)', 
                '(select auth.jwt())', 
                'gi');
            
            -- Replace auth.role() with (select auth.role())
            fixed_def := regexp_replace(fixed_def, 
                '\bauth\.role\(\)', 
                '(select auth.role())', 
                'gi');
            
            -- Only proceed if we actually made changes
            IF fixed_def = policy_def THEN
                CONTINUE;
            END IF;
            
            -- Drop the old policy
            EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', 
                policy_name_val, table_schema_name, table_name_val);
            
            -- Recreate with fixed definition
            -- Parse the original qual and with_check separately
            DECLARE
                fixed_qual TEXT;
                fixed_with_check TEXT;
            BEGIN
                fixed_qual := COALESCE(policy_record.qual, '');
                fixed_with_check := COALESCE(policy_record.with_check, '');
                
                -- Fix qual
                IF fixed_qual != '' THEN
                    fixed_qual := regexp_replace(fixed_qual, '\bauth\.uid\(\)', '(select auth.uid())', 'gi');
                    fixed_qual := regexp_replace(fixed_qual, '\bauth\.jwt\(\)', '(select auth.jwt())', 'gi');
                    fixed_qual := regexp_replace(fixed_qual, '\bauth\.role\(\)', '(select auth.role())', 'gi');
                END IF;
                
                -- Fix with_check
                IF fixed_with_check != '' THEN
                    fixed_with_check := regexp_replace(fixed_with_check, '\bauth\.uid\(\)', '(select auth.uid())', 'gi');
                    fixed_with_check := regexp_replace(fixed_with_check, '\bauth\.jwt\(\)', '(select auth.jwt())', 'gi');
                    fixed_with_check := regexp_replace(fixed_with_check, '\bauth\.role\(\)', '(select auth.role())', 'gi');
                END IF;
                
                -- Build CREATE POLICY command
                policy_cmd := format('CREATE POLICY %I ON %I.%I FOR %s', 
                    policy_name_val, table_schema_name, table_name_val, cmd_type);
                
                -- Add permissive/restrictive
                IF policy_record.permissive = 'PERMISSIVE' THEN
                    policy_cmd := policy_cmd || ' AS PERMISSIVE';
                ELSE
                    policy_cmd := policy_cmd || ' AS RESTRICTIVE';
                END IF;
                
                -- Add roles if specified
                IF policy_record.roles IS NOT NULL AND array_length(policy_record.roles, 1) > 0 THEN
                    policy_cmd := policy_cmd || format(' TO %s', array_to_string(policy_record.roles, ', '));
                END IF;
                
                -- Add USING clause
                IF fixed_qual != '' THEN
                    policy_cmd := policy_cmd || format(' USING (%s)', fixed_qual);
                END IF;
                
                -- Add WITH CHECK clause
                IF fixed_with_check != '' THEN
                    policy_cmd := policy_cmd || format(' WITH CHECK (%s)', fixed_with_check);
                END IF;
                
                -- Execute the CREATE POLICY command
                EXECUTE policy_cmd;
                
                RAISE NOTICE 'Fixed policy % on %.% (wrapped auth.*() in subqueries)', 
                    policy_name_val, table_schema_name, table_name_val;
            END;
            
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Failed to fix policy % on %.%: %', 
                policy_name_val, table_schema_name, table_name_val, SQLERRM;
        END;
    END LOOP;
    
    RAISE NOTICE 'Finished fixing auth_rls_initplan issues';
END $$;

-- ============================================================================
-- 2. Fix multiple_permissive_policies: Consolidate duplicate policies
-- ============================================================================
-- The issue: Multiple permissive policies for the same role/action can be
-- consolidated into a single policy with OR conditions.
--
-- This script identifies and consolidates such policies.
-- NOTE: This is a conservative approach - it only consolidates policies with
-- identical roles and command types. Review the results carefully.

DO $$
DECLARE
    table_record RECORD;
    policy_group RECORD;
    consolidated_qual TEXT;
    consolidated_with_check TEXT;
    policy_names TEXT[];
    new_policy_name TEXT;
    cmd_type TEXT;
BEGIN
    -- Group policies by table, command type, and roles
    FOR table_record IN
        SELECT DISTINCT tablename, cmd
        FROM pg_policies
        WHERE schemaname = 'public'
        AND permissive = 'PERMISSIVE'
    LOOP
        -- For each table/command combination, find groups of policies that can be consolidated
        FOR policy_group IN
            SELECT 
                tablename,
                cmd,
                array_agg(policyname ORDER BY policyname) as policy_names,
                array_agg(qual ORDER BY policyname) as quals,
                array_agg(with_check ORDER BY policyname) as with_checks,
                roles
            FROM pg_policies
            WHERE schemaname = 'public'
            AND tablename = table_record.tablename
            AND cmd = table_record.cmd
            AND permissive = 'PERMISSIVE'
            GROUP BY tablename, cmd, roles
            HAVING count(*) > 1  -- Only consolidate if there are multiple policies
        LOOP
            BEGIN
                -- Only consolidate policies with identical roles and command type
                -- This is a conservative approach to avoid breaking access control
                
                -- Build consolidated USING clause
                consolidated_qual := NULL;
                policy_names := policy_group.quals;
                
                -- Filter out NULL quals and build OR condition
                SELECT string_agg(
                    CASE 
                        WHEN qual IS NOT NULL AND qual != '' THEN '(' || qual || ')'
                        ELSE NULL
                    END, 
                    ' OR '
                ) INTO consolidated_qual
                FROM unnest(policy_group.quals) AS qual
                WHERE qual IS NOT NULL AND qual != '';
                
                -- Build consolidated WITH CHECK clause
                consolidated_with_check := NULL;
                SELECT string_agg(
                    CASE 
                        WHEN with_check IS NOT NULL AND with_check != '' THEN '(' || with_check || ')'
                        ELSE NULL
                    END, 
                    ' OR '
                ) INTO consolidated_with_check
                FROM unnest(policy_group.with_checks) AS with_check
                WHERE with_check IS NOT NULL AND with_check != '';
                
                -- Only consolidate if we have valid conditions
                IF consolidated_qual IS NULL AND consolidated_with_check IS NULL THEN
                    CONTINUE;
                END IF;
                
                -- Create new consolidated policy name
                new_policy_name := 'Consolidated policy for ' || policy_group.tablename || ' ' || policy_group.cmd;
                
                -- Drop old policies
                FOR i IN 1..array_length(policy_group.policy_names, 1) LOOP
                    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', 
                        policy_group.policy_names[i], policy_group.tablename);
                END LOOP;
                
                -- Create new consolidated policy
                DECLARE
                    create_cmd TEXT;
                BEGIN
                    create_cmd := format('CREATE POLICY %I ON public.%I FOR %s AS PERMISSIVE', 
                        new_policy_name, policy_group.tablename, policy_group.cmd);
                    
                    IF policy_group.roles IS NOT NULL AND array_length(policy_group.roles, 1) > 0 THEN
                        create_cmd := create_cmd || format(' TO %s', array_to_string(policy_group.roles, ', '));
                    END IF;
                    
                    IF consolidated_qual IS NOT NULL THEN
                        create_cmd := create_cmd || format(' USING (%s)', consolidated_qual);
                    END IF;
                    
                    IF consolidated_with_check IS NOT NULL THEN
                        create_cmd := create_cmd || format(' WITH CHECK (%s)', consolidated_with_check);
                    END IF;
                    
                    EXECUTE create_cmd;
                    
                    RAISE NOTICE 'Consolidated % policies on public.% into single policy', 
                        array_length(policy_group.policy_names, 1), policy_group.tablename;
                END;
                
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Failed to consolidate policies on public.%: %', 
                    policy_group.tablename, SQLERRM;
            END;
        END LOOP;
    END LOOP;
    
    RAISE NOTICE 'Finished consolidating duplicate permissive policies';
END $$;

-- ============================================================================
-- 3. Fix duplicate_index: Drop redundant indexes
-- ============================================================================
-- The issue: Multiple indexes on the same columns with the same definition
-- waste storage and slow down writes.
--
-- This script identifies and drops duplicate indexes, keeping the first one.

DO $$
DECLARE
    index_group RECORD;
    index_name_to_drop TEXT;
    kept_index_name TEXT;
    idx_counter INT;
BEGIN
    -- Find groups of duplicate indexes by comparing their normalized definitions
    -- (normalized = removing index name and schema qualifiers)
    FOR index_group IN
        WITH index_defs AS (
            SELECT 
                idx.schemaname,
                idx.tablename,
                idx.indexname,
                -- Normalize index definition: remove index name and schema
                regexp_replace(
                    regexp_replace(
                        pg_get_indexdef(i.indexrelid),
                        'CREATE\s+(UNIQUE\s+)?INDEX\s+[^\s]+\s+ON\s+[^\s]+\s+',
                        'CREATE \1INDEX ON ',
                        'gi'
                    ),
                    '\s+WHERE\s+.*$',
                    '',
                    'i'
                ) as normalized_def,
                i.indisunique,
                i.indisprimary,
                i.indexrelid
            FROM pg_indexes idx
            JOIN pg_class c ON c.relname = idx.indexname
            JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = idx.schemaname
            JOIN pg_index i ON i.indexrelid = c.oid
            WHERE idx.schemaname = 'public'
            AND NOT i.indisprimary  -- Don't drop primary key indexes
        )
        SELECT 
            schemaname,
            tablename,
            normalized_def,
            array_agg(indexname ORDER BY indexname) as index_names,
            count(*) as duplicate_count
        FROM index_defs
        GROUP BY schemaname, tablename, normalized_def
        HAVING count(*) > 1  -- Only process groups with duplicates
        ORDER BY tablename, normalized_def
    LOOP
        BEGIN
            -- Keep the first index (alphabetically), drop the rest
            kept_index_name := index_group.index_names[1];
            
            -- Drop all other indexes in the group
            FOR idx_counter IN 2..array_length(index_group.index_names, 1) LOOP
                index_name_to_drop := index_group.index_names[idx_counter];
                
                BEGIN
                    EXECUTE format('DROP INDEX IF EXISTS %I.%I', 
                        index_group.schemaname, index_name_to_drop);
                    RAISE NOTICE 'Dropped duplicate index %.% (keeping %.%)', 
                        index_group.schemaname, index_name_to_drop,
                        index_group.schemaname, kept_index_name;
                EXCEPTION WHEN OTHERS THEN
                    RAISE WARNING 'Failed to drop duplicate index %.%: %', 
                        index_group.schemaname, index_name_to_drop, SQLERRM;
                END;
            END LOOP;
            
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Error processing duplicate indexes on %.%: %', 
                index_group.schemaname, index_group.tablename, SQLERRM;
        END;
    END LOOP;
    
    RAISE NOTICE 'Finished removing duplicate indexes';
END $$;

-- ============================================================================
-- Alternative: Manual Fix for Specific Cases
-- ============================================================================
-- If the dynamic fixes above don't work for all cases, you can manually fix
-- specific policies or indexes. Here are some common patterns:

-- Example: Fix a specific policy manually
-- DROP POLICY IF EXISTS "Policy name" ON public.table_name;
-- CREATE POLICY "Policy name" ON public.table_name FOR SELECT
--   USING ((select auth.uid()) = user_id);

-- Example: Drop a specific duplicate index
-- DROP INDEX IF EXISTS idx_table_column_duplicate;

-- ============================================================================
-- Verification Queries
-- ============================================================================
-- Run these queries to verify the fixes:

-- Check for policies still using auth.*() without subqueries:
/*
SELECT 
    schemaname,
    tablename,
    policyname,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
AND (
    qual ~* 'auth\.(uid|jwt|role)\([^)]*\)' AND qual !~* '\(select\s+auth\.'
    OR 
    with_check ~* 'auth\.(uid|jwt|role)\([^)]*\)' AND with_check !~* '\(select\s+auth\.'
);
*/

-- Check for remaining duplicate indexes:
/*
SELECT 
    t.relname as table_name,
    array_agg(i.indexrelid::regclass::text ORDER BY i.indexrelid) as duplicate_indexes,
    pg_get_indexdef(i.indexrelid) as index_definition
FROM pg_index i
JOIN pg_class t ON i.indrelid = t.oid
JOIN pg_namespace n ON t.relnamespace = n.oid
WHERE n.nspname = 'public'
AND NOT i.indisprimary
GROUP BY t.relname, pg_get_indexdef(i.indexrelid)
HAVING count(*) > 1;
*/

-- Check for multiple permissive policies on same table/action:
/*
SELECT 
    tablename,
    cmd,
    count(*) as policy_count,
    array_agg(policyname ORDER BY policyname) as policy_names
FROM pg_policies
WHERE schemaname = 'public'
AND permissive = 'PERMISSIVE'
GROUP BY tablename, cmd
HAVING count(*) > 1
ORDER BY policy_count DESC;
*/

