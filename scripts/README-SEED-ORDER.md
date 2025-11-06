# User Tables Seed Script Order

## IMPORTANT: Run scripts in this order

### Step 1: Diagnose (OPTIONAL but recommended)
Run `diagnose-user-tables.sql` first to see what actually exists in your database.

```sql
-- This will show you:
-- - Which tables exist
-- - What columns each table has
-- - What constraints exist
-- - Current data counts
```

### Step 2: Seed (REQUIRED)
Run `seed-user-tables-safe.sql` to create/populate the tables.

```sql
-- This script:
-- 1. Checks what actually exists
-- 2. Creates missing tables
-- 3. Adds missing columns to existing tables
-- 4. Adds foreign key constraints (only if prerequisites exist)
-- 5. Inserts/updates data
-- 6. Creates indexes
-- 7. Creates helper functions
```

## What the safe script does:

1. **Diagnoses** current state (logs what exists)
2. **Creates** tables if they don't exist
3. **Adds** missing columns to existing tables
4. **Adds** foreign key constraints (only when safe)
5. **Inserts** user groups (Administrator, SPSA, PSA)
6. **Inserts** permissions (15 total permissions)
7. **Links** permissions to groups
8. **Updates** existing users_profiles with group_id
9. **Creates** indexes for performance
10. **Creates** helper function for permission checks

## Notes:

- The script is **idempotent** - safe to run multiple times
- It **adapts** to whatever structure exists
- It **logs** what it's doing via RAISE NOTICE
- It **skips** operations if prerequisites don't exist
- It **never** drops existing data

## If you still get errors:

1. Run `diagnose-user-tables.sql` and share the output
2. Check the NOTICE messages in the safe script output
3. The script will tell you exactly what's missing

