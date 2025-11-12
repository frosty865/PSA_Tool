# First Approved Extraction Checklist

## Goal
Get at least ONE submission approved and moved to production tables so the pattern extraction tool can learn from it.

## Prerequisites

### 1. Run Database Migration
**File**: `supabase/migrations/2025-01-10_mirror_production_schema.sql`

This migration:
- Adds `vulnerability_name` column to `submission_vulnerabilities` (mirrors production)
- Adds `description` column to `submission_vulnerabilities` (mirrors production)
- Adds `sector_id` and `subsector_id` to `submission_options_for_consideration` (mirrors production)
- Migrates existing data from `vulnerability` → `vulnerability_name`

**How to run**:
```sql
-- Execute in Supabase SQL Editor or via migration tool
-- File: supabase/migrations/2025-01-10_mirror_production_schema.sql
```

### 2. Verify Sync Code
**File**: `services/supabase_sync_individual_v2.py`

✅ Already updated to use:
- `vulnerability_name` (not `vulnerability`)
- `description` field
- `sector_id` and `subsector_id` for OFCs

### 3. Process a Test Document

**Steps**:
1. Place a test PDF in: `C:\Tools\Ollama\Data\incoming\`
2. Wait for `ollama_auto_processor.py` to process it
3. Check logs: `C:\Tools\VOFC_Logs\vofc_engine.log`
4. Verify JSON output in: `C:\Tools\Ollama\Data\review\temp\*_phase2_engine.json`
5. Check Supabase `submissions` table for new entry

**Expected Result**:
- Submission created with `status = 'pending_review'`
- `submission_vulnerabilities` table has entries with `vulnerability_name` and `description`
- `submission_options_for_consideration` table has entries with `sector_id` and `subsector_id`

### 4. Approve Submission via UI

**Steps**:
1. Go to Admin Review page (`/admin/review`)
2. Find the pending submission
3. Click "Approve"
4. Verify success message

**What Happens** (from `app/api/submissions/[id]/approve/route.js`):
1. Updates `submissions.status = 'approved'`
2. Reads data from `submissions.data` JSONB field
3. Extracts vulnerabilities and OFCs
4. Inserts into production tables:
   - `vulnerabilities` (with `vulnerability_name`, `description`, etc.)
   - `options_for_consideration` (with `option_text`, `sector_id`, `subsector_id`)
   - `vulnerability_ofc_links` (links vulnerabilities to OFCs)
5. Creates learning events for pattern extraction

### 5. Verify Production Tables

**Check**:
```sql
-- Check production vulnerabilities
SELECT COUNT(*) FROM vulnerabilities;

-- Check production OFCs
SELECT COUNT(*) FROM options_for_consideration;

-- Check links
SELECT COUNT(*) FROM vulnerability_ofc_links;
```

**Expected Result**:
- At least 1 vulnerability in `vulnerabilities` table
- At least 1 OFC in `options_for_consideration` table
- At least 1 link in `vulnerability_ofc_links` table

### 6. Run Pattern Extraction

**After approval**:
```bash
python tools\extract_production_patterns.py
```

**Expected Result**:
- Patterns extracted from approved production data
- Training examples generated
- Quality reference dataset created

## Troubleshooting

### No Submissions Created
- Check `ollama_auto_processor.py` logs
- Verify Supabase credentials in `.env`
- Check `services/supabase_sync_individual_v2.py` is being called

### Approval Fails
- Check browser console for errors
- Check Next.js API route logs
- Verify `submissions.data` JSONB field has correct structure
- Check production table schemas match expected format

### Production Tables Empty After Approval
- Check approval route logs
- Verify taxonomy IDs (sector_id, subsector_id) can be resolved
- Check for foreign key constraint errors
- Verify `vulnerability_name` and `description` fields are populated

## Success Criteria

✅ Submission created in `submissions` table  
✅ Submission has `status = 'pending_review'`  
✅ `submission_vulnerabilities` has entries with `vulnerability_name`  
✅ Approval succeeds via UI  
✅ Production `vulnerabilities` table has at least 1 entry  
✅ Production `options_for_consideration` table has at least 1 entry  
✅ Pattern extraction tool can read from production tables  

## Next Steps After First Approval

1. Run pattern extraction: `python tools\extract_production_patterns.py`
2. Review patterns in `training_data/production_patterns/`
3. Patterns will auto-enhance prompts in `ollama_auto_processor.py`
4. Process more documents to improve extraction quality

