-- Safe seed script that checks actual table structures before making changes
-- This script adapts to whatever structure actually exists

-- ============================================
-- STEP 1: Diagnose current state
-- ============================================
DO $$ 
DECLARE
    groups_exists BOOLEAN;
    groups_has_id BOOLEAN;
    groups_has_name BOOLEAN;
    groups_has_description BOOLEAN;
    groups_has_is_active BOOLEAN;
    groups_has_created_at BOOLEAN;
    groups_has_updated_at BOOLEAN;
    
    perms_exists BOOLEAN;
    perms_has_id BOOLEAN;
    perms_has_name BOOLEAN;
    perms_has_description BOOLEAN;
    perms_has_resource BOOLEAN;
    perms_has_action BOOLEAN;
    perms_has_created_at BOOLEAN;
    perms_has_updated_at BOOLEAN;
    
    gp_exists BOOLEAN;
    profiles_exists BOOLEAN;
    profiles_has_group_id BOOLEAN;
BEGIN
    -- Check user_groups
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_groups'
    ) INTO groups_exists;
    
    IF groups_exists THEN
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'id'
        ) INTO groups_has_id;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'name'
        ) INTO groups_has_name;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'description'
        ) INTO groups_has_description;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'is_active'
        ) INTO groups_has_is_active;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'created_at'
        ) INTO groups_has_created_at;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'updated_at'
        ) INTO groups_has_updated_at;
        
        RAISE NOTICE 'user_groups exists: id=%, name=%, description=%, is_active=%, created_at=%, updated_at=%', 
            groups_has_id, groups_has_name, groups_has_description, groups_has_is_active, groups_has_created_at, groups_has_updated_at;
    ELSE
        RAISE NOTICE 'user_groups table does NOT exist';
    END IF;
    
    -- Check user_permissions
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_permissions'
    ) INTO perms_exists;
    
    IF perms_exists THEN
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'id'
        ) INTO perms_has_id;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'name'
        ) INTO perms_has_name;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'description'
        ) INTO perms_has_description;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'resource'
        ) INTO perms_has_resource;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'action'
        ) INTO perms_has_action;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'created_at'
        ) INTO perms_has_created_at;
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'updated_at'
        ) INTO perms_has_updated_at;
        
        RAISE NOTICE 'user_permissions exists: id=%, name=%, description=%, resource=%, action=%, created_at=%, updated_at=%', 
            perms_has_id, perms_has_name, perms_has_description, perms_has_resource, perms_has_action, perms_has_created_at, perms_has_updated_at;
    ELSE
        RAISE NOTICE 'user_permissions table does NOT exist';
    END IF;
    
    -- Check group_permissions
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'group_permissions'
    ) INTO gp_exists;
    RAISE NOTICE 'group_permissions exists: %', gp_exists;
    
    -- Check users_profiles
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users_profiles'
    ) INTO profiles_exists;
    
    IF profiles_exists THEN
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'users_profiles' AND column_name = 'group_id'
        ) INTO profiles_has_group_id;
        RAISE NOTICE 'users_profiles exists: group_id=%', profiles_has_group_id;
    ELSE
        RAISE NOTICE 'users_profiles table does NOT exist';
    END IF;
END $$;

-- ============================================
-- STEP 2: Create/Fix user_groups table
-- ============================================
DO $$ 
BEGIN
    -- Create table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_groups'
    ) THEN
        CREATE TABLE user_groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        RAISE NOTICE 'Created user_groups table';
    ELSE
        -- Add missing columns
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'id'
        ) THEN
            ALTER TABLE user_groups ADD COLUMN id UUID PRIMARY KEY DEFAULT gen_random_uuid();
            RAISE NOTICE 'Added id column to user_groups';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'name'
        ) THEN
            ALTER TABLE user_groups ADD COLUMN name TEXT NOT NULL UNIQUE;
            RAISE NOTICE 'Added name column to user_groups';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'description'
        ) THEN
            ALTER TABLE user_groups ADD COLUMN description TEXT;
            RAISE NOTICE 'Added description column to user_groups';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'is_active'
        ) THEN
            ALTER TABLE user_groups ADD COLUMN is_active BOOLEAN DEFAULT true;
            RAISE NOTICE 'Added is_active column to user_groups';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE user_groups ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
            RAISE NOTICE 'Added created_at column to user_groups';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'updated_at'
        ) THEN
            ALTER TABLE user_groups ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
            RAISE NOTICE 'Added updated_at column to user_groups';
        END IF;
        
        -- Check for display_name column (may exist in actual table)
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'display_name'
        ) THEN
            -- Only add if it doesn't exist - don't force it if table was created differently
            RAISE NOTICE 'Note: user_groups does not have display_name column';
        ELSE
            RAISE NOTICE 'Note: user_groups HAS display_name column (will be included in INSERT)';
        END IF;
    END IF;
END $$;

-- ============================================
-- STEP 3: Create/Fix user_permissions table
-- ============================================
DO $$ 
BEGIN
    -- Create table if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_permissions'
    ) THEN
        CREATE TABLE user_permissions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        RAISE NOTICE 'Created user_permissions table';
    ELSE
        -- Add missing columns
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'id'
        ) THEN
            ALTER TABLE user_permissions ADD COLUMN id UUID PRIMARY KEY DEFAULT gen_random_uuid();
            RAISE NOTICE 'Added id column to user_permissions';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'name'
        ) THEN
            ALTER TABLE user_permissions ADD COLUMN name TEXT NOT NULL UNIQUE;
            RAISE NOTICE 'Added name column to user_permissions';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'description'
        ) THEN
            ALTER TABLE user_permissions ADD COLUMN description TEXT;
            RAISE NOTICE 'Added description column to user_permissions';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'resource'
        ) THEN
            ALTER TABLE user_permissions ADD COLUMN resource TEXT NOT NULL DEFAULT '';
            RAISE NOTICE 'Added resource column to user_permissions';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'action'
        ) THEN
            ALTER TABLE user_permissions ADD COLUMN action TEXT NOT NULL DEFAULT '';
            RAISE NOTICE 'Added action column to user_permissions';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'created_at'
        ) THEN
            ALTER TABLE user_permissions ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW();
            RAISE NOTICE 'Added created_at column to user_permissions';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'updated_at'
        ) THEN
            ALTER TABLE user_permissions ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
            RAISE NOTICE 'Added updated_at column to user_permissions';
        END IF;
    END IF;
END $$;

-- ============================================
-- STEP 4: Create/Fix group_permissions table
-- ============================================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'group_permissions'
    ) THEN
        CREATE TABLE group_permissions (
            group_id UUID,
            permission_id UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (group_id, permission_id)
        );
        RAISE NOTICE 'Created group_permissions table';
    END IF;
END $$;

-- ============================================
-- STEP 5: Add foreign key constraints (only if tables and columns exist)
-- ============================================
DO $$ 
BEGIN
    -- Add group_id foreign key
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_groups'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'public' AND constraint_name = 'group_permissions_group_id_fkey'
    ) THEN
        ALTER TABLE group_permissions 
        ADD CONSTRAINT group_permissions_group_id_fkey 
        FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added group_id foreign key constraint';
    END IF;
    
    -- Add permission_id foreign key
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_permissions'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'user_permissions' AND column_name = 'id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'public' AND constraint_name = 'group_permissions_permission_id_fkey'
    ) THEN
        ALTER TABLE group_permissions 
        ADD CONSTRAINT group_permissions_permission_id_fkey 
        FOREIGN KEY (permission_id) REFERENCES user_permissions(id) ON DELETE CASCADE;
        RAISE NOTICE 'Added permission_id foreign key constraint';
    END IF;
END $$;

-- ============================================
-- STEP 6: Add group_id to users_profiles (if table exists)
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users_profiles'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'users_profiles' AND column_name = 'group_id'
    ) THEN
        ALTER TABLE users_profiles ADD COLUMN group_id UUID;
        RAISE NOTICE 'Added group_id column to users_profiles';
    END IF;
    
    -- Add foreign key if both tables exist
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users_profiles'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'user_groups'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'users_profiles' AND column_name = 'group_id'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'user_groups' AND column_name = 'id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_schema = 'public' AND constraint_name = 'users_profiles_group_id_fkey'
    ) THEN
        ALTER TABLE users_profiles 
        ADD CONSTRAINT users_profiles_group_id_fkey 
        FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE SET NULL;
        RAISE NOTICE 'Added group_id foreign key to users_profiles';
    END IF;
END $$;

-- ============================================
-- STEP 7: Insert/Update User Groups
-- ============================================
-- Check if display_name column exists and include it if it does
DO $$ 
DECLARE
    has_display_name BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
          AND table_name = 'user_groups' 
          AND column_name = 'display_name'
    ) INTO has_display_name;
    
    IF has_display_name THEN
        -- Insert with display_name
        INSERT INTO user_groups (name, display_name, description, is_active) VALUES
            ('Administrator', 'Administrator', 'Full system access with all administrative permissions', true),
            ('SPSA', 'SPSA', 'Supervisory Protective Security Advisor - Full admin access', true),
            ('PSA', 'PSA', 'Protective Security Advisor - Standard user with document submission access', true)
        ON CONFLICT (name) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            description = EXCLUDED.description,
            is_active = EXCLUDED.is_active,
            updated_at = NOW();
    ELSE
        -- Insert without display_name
        INSERT INTO user_groups (name, description, is_active) VALUES
            ('Administrator', 'Full system access with all administrative permissions', true),
            ('SPSA', 'Supervisory Protective Security Advisor - Full admin access', true),
            ('PSA', 'Protective Security Advisor - Standard user with document submission access', true)
        ON CONFLICT (name) DO UPDATE SET
            description = EXCLUDED.description,
            is_active = EXCLUDED.is_active,
            updated_at = NOW();
    END IF;
END $$;

-- ============================================
-- STEP 8: Insert/Update Permissions
-- ============================================
INSERT INTO user_permissions (name, description, resource, action) VALUES
    ('admin_panel_read', 'Access admin panel', 'admin_panel', 'read'),
    ('admin_panel_write', 'Modify admin panel settings', 'admin_panel', 'write'),
    ('user_management_read', 'View user list', 'user_management', 'read'),
    ('user_management_create', 'Create new users', 'user_management', 'create'),
    ('user_management_update', 'Edit existing users', 'user_management', 'update'),
    ('user_management_delete', 'Delete users', 'user_management', 'delete'),
    ('submission_review_read', 'View pending submissions', 'submission_review', 'read'),
    ('submission_review_approve', 'Approve submissions', 'submission_review', 'approve'),
    ('submission_review_reject', 'Reject submissions', 'submission_review', 'reject'),
    ('submission_review_edit', 'Edit submissions', 'submission_review', 'edit'),
    ('audit_trail_read', 'View audit trail', 'audit_trail', 'read'),
    ('system_controls_read', 'View system status', 'system_controls', 'read'),
    ('system_controls_write', 'Control system operations', 'system_controls', 'write'),
    ('learning_metrics_read', 'View learning metrics dashboard', 'learning_metrics', 'read'),
    ('document_submit', 'Submit documents for processing', 'documents', 'submit'),
    ('document_view_own', 'View own submissions', 'documents', 'read_own'),
    ('document_view_approved', 'View approved production data', 'documents', 'read_approved')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    resource = EXCLUDED.resource,
    action = EXCLUDED.action,
    updated_at = NOW();

-- ============================================
-- STEP 9: Assign Permissions to Groups
-- ============================================
-- Administrator Group - ALL permissions
INSERT INTO group_permissions (group_id, permission_id)
SELECT 
    (SELECT id FROM user_groups WHERE name = 'Administrator'),
    id
FROM user_permissions
ON CONFLICT (group_id, permission_id) DO NOTHING;

-- SPSA Group - ALL permissions
INSERT INTO group_permissions (group_id, permission_id)
SELECT 
    (SELECT id FROM user_groups WHERE name = 'SPSA'),
    id
FROM user_permissions
ON CONFLICT (group_id, permission_id) DO NOTHING;

-- PSA Group - Limited permissions
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
-- STEP 10: Update existing users_profiles to link to groups
-- ============================================
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users_profiles'
    ) THEN
        UPDATE users_profiles up
        SET group_id = (
            CASE 
                WHEN up.role = 'admin' THEN (SELECT id FROM user_groups WHERE name = 'Administrator')
                WHEN up.role = 'spsa' THEN (SELECT id FROM user_groups WHERE name = 'SPSA')
                WHEN up.role = 'psa' THEN (SELECT id FROM user_groups WHERE name = 'PSA')
                ELSE (SELECT id FROM user_groups WHERE name = 'PSA')
            END
        )
        WHERE up.group_id IS NULL;
        RAISE NOTICE 'Updated users_profiles with group_id';
    END IF;
END $$;

-- ============================================
-- STEP 11: Create indexes
-- ============================================
CREATE INDEX IF NOT EXISTS idx_user_groups_name ON user_groups(name);
CREATE INDEX IF NOT EXISTS idx_user_groups_active ON user_groups(is_active);
CREATE INDEX IF NOT EXISTS idx_user_permissions_resource ON user_permissions(resource);
CREATE INDEX IF NOT EXISTS idx_user_permissions_action ON user_permissions(action);
CREATE INDEX IF NOT EXISTS idx_group_permissions_group ON group_permissions(group_id);
CREATE INDEX IF NOT EXISTS idx_group_permissions_permission ON group_permissions(permission_id);

DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'users_profiles'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_users_profiles_group ON users_profiles(group_id);
    END IF;
END $$;

-- ============================================
-- STEP 12: Create helper function
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
        RETURN false;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- Summary
-- ============================================
SELECT 
    'User Groups' as table_name,
    COUNT(*) as record_count
FROM user_groups
UNION ALL
SELECT 
    'User Permissions',
    COUNT(*)
FROM user_permissions
UNION ALL
SELECT 
    'Group Permissions',
    COUNT(*)
FROM group_permissions;

