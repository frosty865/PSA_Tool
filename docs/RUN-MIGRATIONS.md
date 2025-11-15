# Running Discipline System Migrations with Supabase CLI

## Prerequisites

1. **Login to Supabase CLI** (if not already logged in):
   ```bash
   supabase login
   ```

2. **Link your project** (if not already linked):
   ```bash
   supabase link --project-ref <your-project-ref>
   ```
   You can find your project ref in the Supabase dashboard URL: `https://supabase.com/dashboard/project/<project-ref>`

## Option 1: Push All Migrations (Recommended)

This will apply all pending migrations in order:

```bash
cd "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"
supabase db push
```

This will:
- Apply all migrations in `supabase/migrations/` in chronological order
- Include the new discipline system migrations
- Show you a preview before applying

## Option 2: Apply Specific Migrations

If you want to apply just the new migrations:

```bash
# Apply the main migration
supabase migration up --file supabase/migrations/2025-01-16_discipline_system_rewrite.sql

# Apply the phase3 trigger update
supabase migration up --file supabase/migrations/2025-01-16_update_phase3_trigger_for_subtypes.sql
```

## Option 3: Use Supabase Dashboard

If you prefer the web interface:

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the contents of:
   - `supabase/migrations/2025-01-16_discipline_system_rewrite.sql`
   - Then `supabase/migrations/2025-01-16_update_phase3_trigger_for_subtypes.sql`
4. Run each migration in order

## Verification

After running the migrations, verify they worked:

```sql
-- Check that 10 disciplines exist
SELECT COUNT(*) FROM disciplines WHERE is_active = true;
-- Should return 10

-- Check that discipline_subtypes table exists
SELECT COUNT(*) FROM discipline_subtypes;
-- Should return the number of subtypes (varies by discipline)

-- Check that columns were added
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'submission_vulnerabilities' 
AND column_name = 'discipline_subtype_id';
-- Should return 'discipline_subtype_id'
```

## Rollback (if needed)

If you need to rollback:

```bash
# Option 1: Use the rollback migration
supabase migration up --file supabase/migrations/2025-01-16_discipline_system_rewrite_rollback.sql

# Option 2: Run in SQL Editor
# Copy and paste the contents of the rollback migration file
```

## Important Notes

- **Backup**: The migration automatically creates a `disciplines_backup` table
- **Idempotent**: Migrations are safe to run multiple times
- **Order Matters**: Run migrations in chronological order
- **Test First**: Consider running on a test/staging database first

## Troubleshooting

If you get connection errors:
- Make sure you're logged in: `supabase login`
- Check your project is linked: `supabase projects list`
- Verify your database connection in the Supabase dashboard

If migrations fail:
- Check the error message in the CLI output
- Review the migration SQL for syntax errors
- Check Supabase dashboard logs for detailed errors

