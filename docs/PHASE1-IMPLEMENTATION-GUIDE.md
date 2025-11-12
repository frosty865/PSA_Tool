# Phase 1 Implementation Guide

## Quick Start

This guide walks you through implementing Phase 1 database enhancements for seamless VOFC Processor integration.

---

## Step 1: Run Database Migration

### Option A: Supabase SQL Editor (Recommended)

1. **Open Supabase Dashboard**
   - Go to your Supabase project
   - Navigate to **SQL Editor**

2. **Copy Migration Script**
   - Open `sql/phase1-migration.sql` from this project
   - Copy the entire contents

3. **Run the Script**
   - Paste into SQL Editor
   - Click **Run** (or press `Ctrl+Enter`)

4. **Verify Success**
   - Check for "Success" message
   - Review the verification queries at the end of the script
   - You should see 7 new columns listed

### Option B: Command Line (if you have psql access)

```bash
psql -h your-db-host -U postgres -d postgres -f sql/phase1-migration.sql
```

---

## Step 2: Verify Migration

Run these queries in Supabase SQL Editor to confirm:

```sql
-- Check all new columns exist
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'vulnerabilities'
    AND column_name IN (
        'dedupe_key', 'confidence', 'impact_level', 'follow_up', 
        'standard_reference', 'created_at', 'updated_at'
    )
ORDER BY column_name;

-- Should return 7 rows
```

```sql
-- Check indexes were created
SELECT 
    indexname
FROM pg_indexes
WHERE tablename = 'vulnerabilities'
    AND indexname LIKE 'idx_vulnerabilities_%'
ORDER BY indexname;

-- Should include:
-- - idx_vulnerabilities_dedupe_key
-- - idx_vulnerabilities_confidence
-- - idx_vulnerabilities_impact_level
-- - idx_vulnerabilities_follow_up
-- - idx_vulnerabilities_created_at
-- - idx_vulnerabilities_updated_at
```

```sql
-- Check constraint exists
SELECT constraint_name
FROM information_schema.table_constraints
WHERE table_name = 'vulnerabilities'
    AND constraint_name = 'check_dedupe_key_lowercase';

-- Should return 1 row
```

---

## Step 3: Restart VOFC-Processor

The processor code has been updated to use the new columns. Restart the service:

```powershell
nssm restart VOFC-Processor
```

---

## Step 4: Validate Processing

1. **Place a test PDF** in `C:\Tools\Ollama\Data\incoming\`

2. **Wait 30 seconds** for the processor to pick it up

3. **Check logs:**
   ```powershell
   Get-Content C:\Tools\Ollama\Data\logs\vofc_processor*.log -Tail 50
   ```

4. **Verify in Supabase:**
   ```sql
   SELECT 
       vulnerability,
       dedupe_key,
       confidence,
       impact_level,
       follow_up,
       standard_reference,
       created_at,
       updated_at
   FROM vulnerabilities
   ORDER BY created_at DESC
   LIMIT 5;
   ```

   You should see:
   - ✅ `dedupe_key` populated (40-char lowercase hash)
   - ✅ `confidence` populated (High/Medium/Low)
   - ✅ `impact_level` populated (High/Moderate/Low)
   - ✅ `follow_up` populated (true/false)
   - ✅ `standard_reference` populated (if provided by model)
   - ✅ `created_at` and `updated_at` timestamps

---

## Step 5: Test Deduplication

1. **Process the same document twice** (or a document with known duplicates)

2. **Check logs** for messages like:
   ```
   Vulnerability already exists (dedupe_key: abc12345...), linking instead of inserting
   ```

3. **Verify in Supabase:**
   ```sql
   -- Check for duplicate dedupe_keys (should be 0)
   SELECT dedupe_key, COUNT(*) as count
   FROM vulnerabilities
   WHERE dedupe_key IS NOT NULL
   GROUP BY dedupe_key
   HAVING COUNT(*) > 1;
   ```

   Should return 0 rows (no duplicates).

---

## Troubleshooting

### Issue: "column does not exist" errors

**Solution:** Migration didn't run successfully. Re-run the migration script and verify with the verification queries.

### Issue: Processor still shows warnings about missing columns

**Solution:** 
1. Verify columns exist in Supabase
2. Restart VOFC-Processor service
3. Check logs for any import errors

### Issue: dedupe_key constraint violation

**Solution:** The constraint enforces lowercase. The processor now ensures lowercase, but if you have existing uppercase hashes, you'll need to update them:

```sql
UPDATE vulnerabilities 
SET dedupe_key = lower(dedupe_key) 
WHERE dedupe_key IS NOT NULL AND dedupe_key != lower(dedupe_key);
```

### Issue: Updated_at not updating

**Solution:** Verify the trigger was created:

```sql
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_name = 'trg_update_timestamp';
```

---

## What's Next?

After Phase 1 is validated:

1. **Phase 2:** Add traceability (source_document, model_version)
2. **Phase 3:** Performance optimization (composite indexes, full-text search)
3. **Phase 4:** Data quality (validation constraints, audit trail)
4. **Phase 5:** Additional enhancements (reference_sources, soft delete)

See `docs/DB-ENHANCEMENT-PLAN.md` for complete details.

---

## Success Criteria

✅ All 7 columns exist in `vulnerabilities` table  
✅ All 6 indexes created successfully  
✅ Lowercase constraint on `dedupe_key` active  
✅ Trigger for `updated_at` working  
✅ Processor inserts data into new columns  
✅ Deduplication working (no duplicate `dedupe_key` values)  
✅ Logs show no "column does not exist" warnings  

Once all criteria are met, Phase 1 is complete! 🎉

