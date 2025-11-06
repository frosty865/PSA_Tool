-- Diagnostic script to check actual table structures
-- Run this FIRST to see what actually exists

-- ============================================
-- 1. Check if tables exist
-- ============================================
SELECT 
    'Table Existence Check' as check_type,
    table_name,
    CASE WHEN EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = t.table_name
    ) THEN 'EXISTS' ELSE 'MISSING' END as status
FROM (VALUES 
    ('user_groups'),
    ('user_permissions'),
    ('group_permissions'),
    ('users_profiles')
) AS t(table_name);

-- ============================================
-- 2. Check user_groups table structure
-- ============================================
SELECT 
    'user_groups columns' as check_type,
    column_name,
    data_type,
    is_nullable,
    column_default,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'user_groups'
ORDER BY ordinal_position;

-- ============================================
-- 3. Check user_permissions table structure
-- ============================================
SELECT 
    'user_permissions columns' as check_type,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'user_permissions'
ORDER BY ordinal_position;

-- ============================================
-- 4. Check group_permissions table structure
-- ============================================
SELECT 
    'group_permissions columns' as check_type,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'group_permissions'
ORDER BY ordinal_position;

-- ============================================
-- 5. Check users_profiles table structure (if exists)
-- ============================================
SELECT 
    'users_profiles columns' as check_type,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
  AND table_name = 'users_profiles'
ORDER BY ordinal_position;

-- ============================================
-- 6. Check existing constraints
-- ============================================
SELECT 
    'Foreign Key Constraints' as check_type,
    tc.table_name,
    tc.constraint_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND (tc.table_name IN ('user_groups', 'user_permissions', 'group_permissions', 'users_profiles')
       OR ccu.table_name IN ('user_groups', 'user_permissions', 'group_permissions', 'users_profiles'))
ORDER BY tc.table_name, tc.constraint_name;

-- ============================================
-- 7. Check existing data counts
-- ============================================
SELECT 'user_groups' as table_name, COUNT(*) as record_count FROM user_groups
UNION ALL
SELECT 'user_permissions', COUNT(*) FROM user_permissions
UNION ALL
SELECT 'group_permissions', COUNT(*) FROM group_permissions
UNION ALL
SELECT 'users_profiles', COUNT(*) FROM users_profiles WHERE EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'users_profiles'
);

