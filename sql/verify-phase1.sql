-- ============================================================
-- Phase 1 Verification Queries
-- ============================================================
-- Run these queries to verify Phase 1 migration was successful
-- ============================================================

-- 1. Check all new columns exist
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'vulnerabilities'
    AND column_name IN (
        'dedupe_key', 'confidence', 'impact_level', 'follow_up', 
        'standard_reference', 'created_at', 'updated_at'
    )
ORDER BY column_name;

-- Expected: 7 rows

-- 2. Check indexes were created
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'vulnerabilities'
    AND indexname LIKE 'idx_vulnerabilities_%'
ORDER BY indexname;

-- Expected: Should include:
-- - idx_vulnerabilities_dedupe_key
-- - idx_vulnerabilities_confidence
-- - idx_vulnerabilities_impact_level
-- - idx_vulnerabilities_follow_up
-- - idx_vulnerabilities_created_at
-- - idx_vulnerabilities_updated_at

-- 3. Check constraint exists
SELECT 
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'vulnerabilities'
    AND constraint_name LIKE '%dedupe_key%'
ORDER BY constraint_name;

-- Expected: Should see check_dedupe_key_lowercase

-- 4. Check trigger exists
SELECT 
    trigger_name,
    event_manipulation,
    event_object_table
FROM information_schema.triggers
WHERE trigger_name = 'trg_update_timestamp';

-- Expected: 1 row

-- 5. Check function exists
SELECT 
    routine_name,
    routine_type
FROM information_schema.routines
WHERE routine_name = 'update_timestamp';

-- Expected: 1 row

-- 6. Test constraint (should fail if uppercase)
-- Uncomment to test:
-- INSERT INTO vulnerabilities (vulnerability, dedupe_key) 
-- VALUES ('Test', 'ABCDEF1234567890ABCDEF1234567890ABCDEF12');
-- Should fail with constraint violation

-- 7. Test constraint (should succeed with lowercase)
-- Uncomment to test:
-- INSERT INTO vulnerabilities (vulnerability, dedupe_key) 
-- VALUES ('Test', 'abcdef1234567890abcdef1234567890abcdef12');
-- Should succeed

