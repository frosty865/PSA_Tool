-- Seed script for user_profiles, user_groups, and user_permissions tables
-- This script sets up the role-based access control system

-- ============================================
-- 1. Create user_groups table (if not exists)
-- ============================================
CREATE TABLE IF NOT EXISTS user_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Note: If user_groups table exists without id column, it needs manual intervention
-- The CREATE TABLE IF NOT EXISTS above should create it correctly

-- ============================================
-- 2. Create user_permissions table (if not exists)
-- ============================================
CREATE TABLE IF NOT EXISTS user_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    resource TEXT NOT NULL, -- e.g., 'admin_panel', 'user_management', 'submission_review'
    action TEXT NOT NULL, -- e.g., 'read', 'write', 'delete', 'approve'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Note: If user_permissions table exists without id column, it needs manual intervention
-- The CREATE TABLE IF NOT EXISTS above should create it correctly

-- ============================================
-- 3. Create junction table: group_permissions
-- ============================================
-- Create table first without foreign keys, then add constraints
CREATE TABLE IF NOT EXISTS group_permissions (
    group_id UUID,
    permission_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (group_id, permission_id)
);

-- Add foreign key constraints after tables exist
DO $$ 
DECLARE
    groups_table_exists BOOLEAN;
    groups_has_id BOOLEAN;
    perms_table_exists BOOLEAN;
    perms_has_id BOOLEAN;
BEGIN
    -- Check if user_groups table exists and has id column
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_groups'
    ) INTO groups_table_exists;
    
    IF groups_table_exists THEN
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'user_groups' 
              AND column_name = 'id'
        ) INTO groups_has_id;
        
        IF groups_has_id THEN
            -- Add group_id foreign key if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_schema = 'public'
                  AND constraint_name = 'group_permissions_group_id_fkey'
            ) THEN
                ALTER TABLE group_permissions 
                ADD CONSTRAINT group_permissions_group_id_fkey 
                FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE;
            END IF;
        ELSE
            RAISE WARNING 'user_groups table exists but does not have id column. Skipping foreign key constraint.';
        END IF;
    ELSE
        RAISE WARNING 'user_groups table does not exist. Skipping foreign key constraint.';
    END IF;
    
    -- Check if user_permissions table exists and has id column
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_permissions'
    ) INTO perms_table_exists;
    
    IF perms_table_exists THEN
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' 
              AND table_name = 'user_permissions' 
              AND column_name = 'id'
        ) INTO perms_has_id;
        
        IF perms_has_id THEN
            -- Add permission_id foreign key if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_schema = 'public'
                  AND constraint_name = 'group_permissions_permission_id_fkey'
            ) THEN
                ALTER TABLE group_permissions 
                ADD CONSTRAINT group_permissions_permission_id_fkey 
                FOREIGN KEY (permission_id) REFERENCES user_permissions(id) ON DELETE CASCADE;
            END IF;
        ELSE
            RAISE WARNING 'user_permissions table exists but does not have id column. Skipping foreign key constraint.';
        END IF;
    ELSE
        RAISE WARNING 'user_permissions table does not exist. Skipping foreign key constraint.';
    END IF;
END $$;

-- ============================================
-- 4. Ensure users_profiles table has group_id column
-- ============================================
-- First check if the table exists, then add column
DO $$ 
BEGIN
    -- Check if users_profiles table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'users_profiles'
    ) THEN
        -- Add group_id column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'users_profiles' AND column_name = 'group_id'
        ) THEN
            ALTER TABLE users_profiles ADD COLUMN group_id UUID;
        END IF;
    END IF;
END $$;

-- Add foreign key constraint after both tables exist
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'users_profiles'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'user_groups'
    ) THEN
        -- Drop existing constraint if it exists
        IF EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'users_profiles_group_id_fkey'
        ) THEN
            ALTER TABLE users_profiles DROP CONSTRAINT users_profiles_group_id_fkey;
        END IF;
        
        -- Add foreign key constraint
        ALTER TABLE users_profiles 
        ADD CONSTRAINT users_profiles_group_id_fkey 
        FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================
-- 5. Ensure user_groups table has all required columns
-- ============================================
DO $$ 
BEGIN
    -- Add description column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_groups' 
          AND column_name = 'description'
    ) THEN
        ALTER TABLE user_groups ADD COLUMN description TEXT;
    END IF;
    
    -- Add is_active column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_groups' 
          AND column_name = 'is_active'
    ) THEN
        ALTER TABLE user_groups ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;
    
    -- Add created_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_groups' 
          AND column_name = 'created_at'
    ) THEN
        ALTER TABLE user_groups ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
    
    -- Add updated_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_groups' 
          AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE user_groups ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- ============================================
-- 6. Insert User Groups
-- ============================================
INSERT INTO user_groups (name, description, is_active) VALUES
    ('Administrator', 'Full system access with all administrative permissions', true),
    ('SPSA', 'Supervisory Protective Security Advisor - Full admin access', true),
    ('PSA', 'Protective Security Advisor - Standard user with document submission access', true)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- ============================================
-- 7. Ensure user_permissions table has all required columns
-- ============================================
DO $$ 
BEGIN
    -- Add description column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_permissions' 
          AND column_name = 'description'
    ) THEN
        ALTER TABLE user_permissions ADD COLUMN description TEXT;
    END IF;
    
    -- Add resource column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_permissions' 
          AND column_name = 'resource'
    ) THEN
        ALTER TABLE user_permissions ADD COLUMN resource TEXT NOT NULL DEFAULT '';
    END IF;
    
    -- Add action column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_permissions' 
          AND column_name = 'action'
    ) THEN
        ALTER TABLE user_permissions ADD COLUMN action TEXT NOT NULL DEFAULT '';
    END IF;
    
    -- Add created_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_permissions' 
          AND column_name = 'created_at'
    ) THEN
        ALTER TABLE user_permissions ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
    
    -- Add updated_at column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_permissions' 
          AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE user_permissions ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- ============================================
-- 8. Insert Permissions
-- ============================================
INSERT INTO user_permissions (name, description, resource, action) VALUES
    -- Admin Panel Permissions
    ('admin_panel_read', 'Access admin panel', 'admin_panel', 'read'),
    ('admin_panel_write', 'Modify admin panel settings', 'admin_panel', 'write'),
    
    -- User Management Permissions
    ('user_management_read', 'View user list', 'user_management', 'read'),
    ('user_management_create', 'Create new users', 'user_management', 'create'),
    ('user_management_update', 'Edit existing users', 'user_management', 'update'),
    ('user_management_delete', 'Delete users', 'user_management', 'delete'),
    
    -- Submission Review Permissions
    ('submission_review_read', 'View pending submissions', 'submission_review', 'read'),
    ('submission_review_approve', 'Approve submissions', 'submission_review', 'approve'),
    ('submission_review_reject', 'Reject submissions', 'submission_review', 'reject'),
    ('submission_review_edit', 'Edit submissions', 'submission_review', 'edit'),
    
    -- Audit Trail Permissions
    ('audit_trail_read', 'View audit trail', 'audit_trail', 'read'),
    
    -- System Controls Permissions
    ('system_controls_read', 'View system status', 'system_controls', 'read'),
    ('system_controls_write', 'Control system operations', 'system_controls', 'write'),
    
    -- Learning Metrics Permissions
    ('learning_metrics_read', 'View learning metrics dashboard', 'learning_metrics', 'read'),
    
    -- Document Submission Permissions
    ('document_submit', 'Submit documents for processing', 'documents', 'submit'),
    ('document_view_own', 'View own submissions', 'documents', 'read_own'),
    ('document_view_approved', 'View approved production data', 'documents', 'read_approved')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    updated_at = NOW();

-- ============================================
-- 9. Assign Permissions to Groups
-- ============================================

-- Administrator Group - ALL permissions
INSERT INTO group_permissions (group_id, permission_id)
SELECT 
    (SELECT id FROM user_groups WHERE name = 'Administrator'),
    id
FROM user_permissions
ON CONFLICT (group_id, permission_id) DO NOTHING;

-- SPSA Group - ALL permissions (same as Administrator)
INSERT INTO group_permissions (group_id, permission_id)
SELECT 
    (SELECT id FROM user_groups WHERE name = 'SPSA'),
    id
FROM user_permissions
ON CONFLICT (group_id, permission_id) DO NOTHING;

-- PSA Group - Limited permissions (standard user)
INSERT INTO group_permissions (group_id, permission_id)
SELECT 
    (SELECT id FROM user_groups WHERE name = 'PSA'),
    id
FROM user_permissions
WHERE name IN (
    'document_submit',
    'document_view_own',
    'document_view_approved'
)
ON CONFLICT (group_id, permission_id) DO NOTHING;

-- ============================================
-- 10. Update existing users_profiles to link to groups based on role
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'users_profiles'
    ) THEN
        UPDATE users_profiles up
        SET group_id = (
            CASE 
                WHEN up.role = 'admin' THEN (SELECT id FROM user_groups WHERE name = 'Administrator')
                WHEN up.role = 'spsa' THEN (SELECT id FROM user_groups WHERE name = 'SPSA')
                WHEN up.role = 'psa' THEN (SELECT id FROM user_groups WHERE name = 'PSA')
                ELSE (SELECT id FROM user_groups WHERE name = 'PSA') -- Default to PSA
            END
        )
        WHERE up.group_id IS NULL;
    END IF;
END $$;

-- ============================================
-- 11. Create indexes for performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_user_groups_name ON user_groups(name);
CREATE INDEX IF NOT EXISTS idx_user_groups_active ON user_groups(is_active);
CREATE INDEX IF NOT EXISTS idx_user_permissions_resource ON user_permissions(resource);
CREATE INDEX IF NOT EXISTS idx_user_permissions_action ON user_permissions(action);
CREATE INDEX IF NOT EXISTS idx_group_permissions_group ON group_permissions(group_id);
CREATE INDEX IF NOT EXISTS idx_group_permissions_permission ON group_permissions(permission_id);
-- Only create index if table exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'users_profiles'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_users_profiles_group ON users_profiles(group_id);
    END IF;
END $$;

-- ============================================
-- 12. Create helper function to check permissions
-- ============================================
CREATE OR REPLACE FUNCTION user_has_permission(
    p_user_id UUID,
    p_resource TEXT,
    p_action TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM users_profiles up
        JOIN group_permissions gp ON up.group_id = gp.group_id
        JOIN user_permissions perm ON gp.permission_id = perm.id
        WHERE up.user_id = p_user_id
          AND up.is_active = true
          AND perm.resource = p_resource
          AND perm.action = p_action
    );
EXCEPTION
    WHEN OTHERS THEN
        -- Return false if table doesn't exist or any error occurs
        RETURN false;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Summary
-- ============================================
DO $$ 
DECLARE
    groups_count INTEGER;
    perms_count INTEGER;
    group_perms_count INTEGER;
    users_with_groups_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO groups_count FROM user_groups;
    SELECT COUNT(*) INTO perms_count FROM user_permissions;
    SELECT COUNT(*) INTO group_perms_count FROM group_permissions;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'users_profiles'
    ) THEN
        SELECT COUNT(*) INTO users_with_groups_count 
        FROM users_profiles 
        WHERE group_id IS NOT NULL;
    ELSE
        users_with_groups_count := 0;
    END IF;
    
    RAISE NOTICE 'User Groups: %', groups_count;
    RAISE NOTICE 'User Permissions: %', perms_count;
    RAISE NOTICE 'Group Permissions: %', group_perms_count;
    RAISE NOTICE 'Users with Groups: %', users_with_groups_count;
END $$;

