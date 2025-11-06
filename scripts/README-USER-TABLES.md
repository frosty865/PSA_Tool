# User Tables Setup Guide

This directory contains scripts to set up and populate the user management tables: `user_groups`, `user_permissions`, and `users_profiles`.

## Tables Overview

### 1. `user_groups`
Defines the three role groups:
- **Administrator**: Full system access
- **SPSA**: Supervisory Protective Security Advisor - Full admin access
- **PSA**: Protective Security Advisor - Standard user

### 2. `user_permissions`
Defines granular permissions for different resources and actions:
- Admin panel access
- User management (CRUD)
- Submission review (approve/reject/edit)
- Audit trail access
- System controls
- Learning metrics
- Document submission and viewing

### 3. `group_permissions`
Junction table linking groups to their permissions.

### 4. `users_profiles`
Extended user profile table (already exists) with added `group_id` column linking to `user_groups`.

## Setup Instructions

### Option 1: Run via Supabase SQL Editor

1. Open your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `seed-user-tables.sql`
4. Execute the script

### Option 2: Run via Supabase CLI

```bash
supabase db execute -f scripts/seed-user-tables.sql
```

### Option 3: Run via psql

```bash
psql -h <your-supabase-host> -U postgres -d postgres -f scripts/seed-user-tables.sql
```

## Verification

After running the script, verify the data:

```sql
-- Check groups
SELECT * FROM user_groups;

-- Check permissions
SELECT * FROM user_permissions ORDER BY resource, action;

-- Check group permissions
SELECT 
    ug.name as group_name,
    up.name as permission_name,
    up.resource,
    up.action
FROM group_permissions gp
JOIN user_groups ug ON gp.group_id = ug.id
JOIN user_permissions up ON gp.permission_id = up.id
ORDER BY ug.name, up.resource, up.action;

-- Check users with groups
SELECT 
    up.user_id,
    up.username,
    up.role,
    ug.name as group_name
FROM users_profiles up
LEFT JOIN user_groups ug ON up.group_id = ug.id;
```

## Permission Checking

Use the helper function to check if a user has a specific permission:

```sql
-- Check if user can access admin panel
SELECT user_has_permission(
    'user-uuid-here'::UUID,
    'admin_panel',
    'read'
);

-- Check if user can approve submissions
SELECT user_has_permission(
    'user-uuid-here'::UUID,
    'submission_review',
    'approve'
);
```

## Role Mapping

The system maps roles to groups as follows:

| Role (users_profiles.role) | Group (user_groups.name) | Access Level |
|---------------------------|-------------------------|--------------|
| `admin` | Administrator | Full admin access |
| `spsa` | SPSA | Full admin access |
| `psa` | PSA | Standard user access |
| Any other | PSA (default) | Standard user access |

## Updating Permissions

To add new permissions:

1. Insert into `user_permissions`:
```sql
INSERT INTO user_permissions (name, description, resource, action)
VALUES ('new_permission', 'Description', 'resource_name', 'action_name');
```

2. Assign to groups via `group_permissions`:
```sql
INSERT INTO group_permissions (group_id, permission_id)
SELECT 
    (SELECT id FROM user_groups WHERE name = 'Administrator'),
    (SELECT id FROM user_permissions WHERE name = 'new_permission');
```

## Notes

- The script is idempotent - it can be run multiple times safely
- Existing data in `users_profiles` will be updated to link to appropriate groups
- All groups and permissions are set to `is_active = true` by default
- The `user_has_permission()` function uses `SECURITY DEFINER` to bypass RLS for permission checks

