# Running Migrations via Supabase Dashboard

Since `supabase link` is blocked by your ISP, use the Supabase Dashboard SQL Editor instead.

## Steps

1. **Go to your Supabase Dashboard:**
   - URL: `https://supabase.com/dashboard/project/wivohgbuuwxoyfyzntsd`
   - Navigate to **SQL Editor** (left sidebar)

2. **Run Migration 1: Main Discipline System Rewrite**
   - Click "New Query"
   - Copy the entire contents of `supabase/migrations/20250116120000_discipline_system_rewrite.sql`
   - Paste into the SQL Editor
   - Click "Run" (or press Ctrl+Enter)
   - Wait for completion (should show "Success")

3. **Run Migration 2: Phase3 Trigger Update**
   - Click "New Query" (or clear the editor)
   - Copy the entire contents of `supabase/migrations/20250116120001_update_phase3_trigger_for_subtypes.sql`
   - Paste into the SQL Editor
   - Click "Run"
   - Wait for completion

## Verification

After running both migrations, verify they worked:

```sql
-- Check that 10 disciplines exist
SELECT COUNT(*) FROM disciplines WHERE is_active = true;
-- Should return 10

-- Check that discipline_subtypes table exists and has data
SELECT COUNT(*) FROM discipline_subtypes;
-- Should return the number of subtypes (varies by discipline)

-- Check that columns were added
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'submission_vulnerabilities' 
AND column_name = 'discipline_subtype_id';
-- Should return 'discipline_subtype_id'

-- List all new disciplines
SELECT name, code, category FROM disciplines WHERE is_active = true ORDER BY name;
-- Should show the 10 new disciplines
```

## Rollback (if needed)

If you need to rollback, run:
- `supabase/migrations/20250116120002_discipline_system_rewrite_rollback.sql`

## Notes

- Migrations are idempotent (safe to run multiple times)
- The migration automatically creates a backup table `disciplines_backup`
- All changes are reversible via the rollback migration

