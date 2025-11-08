# Supabase Sync Fix Summary

## Issues Fixed

### 1. Invalid Service Role Key
**Problem**: The service role key was invalid or missing.

**Solution**: 
- Set the correct service role key from Supabase Dashboard
- Key must be 200+ characters and start with `eyJ` (JWT format)
- Set permanently: `[System.Environment]::SetEnvironmentVariable("SUPABASE_SERVICE_ROLE_KEY", "your-key", "User")`

### 2. Missing/Invalid Table Columns
**Problem**: The sync function was trying to insert into columns that don't exist:
- `submitter_email` (optional - stored in data JSONB instead)
- `parser_version`, `engine_version`, `auditor_version` (optional - stored in data JSONB instead)
- `audit_status` in `submission_vulnerabilities` and `submission_options_for_consideration`

**Solution**:
- Added graceful error handling that retries with minimal fields
- Stores optional metadata in `data` JSONB column when columns don't exist
- Removed `audit_status` from inserts (column doesn't exist in current schema)

### 3. Type Constraint Violation
**Problem**: Table has check constraint: `type IN ('vulnerability', 'ofc')`
- Sync was using `type='document'` which violated the constraint

**Solution**:
- Changed to `type='vulnerability'` (since documents contain vulnerabilities)
- Store actual document type in `data.document_type` JSONB field

### 4. Unicode Encoding Errors
**Problem**: Emoji characters in print statements caused encoding errors on Windows

**Solution**:
- Replaced all emojis with ASCII-safe markers: `[OK]`, `[ERROR]`, `[WARNING]`

## Current Status

✅ **Sync is working!**

The sync function now:
- Creates submissions in `submissions` table
- Inserts vulnerabilities into `submission_vulnerabilities`
- Inserts OFCs into `submission_options_for_consideration`
- Creates links in `submission_vulnerability_ofc_links`
- Inserts sources into `submission_sources`
- Preserves all data in `submissions.data` JSONB column

## How to Use

### Sync Existing Files
```powershell
# Sync all files in review/ directory
python scripts\sync-to-supabase.py --all

# Sync a specific file
python scripts\sync-to-supabase.py "C:\Tools\Ollama\Data\review\file_vofc.json"
```

### Automatic Sync
The processor automatically syncs files after successful processing. Make sure:
1. `SUPABASE_SERVICE_ROLE_KEY` is set in environment
2. Processor is running
3. Files are being processed successfully

### Manual Sync via API
From the review page (`/admin/review`), click "📤 Sync to Submissions" button.

## Verification

Run the test script to verify everything is working:
```powershell
python scripts\test-supabase-connection.py
```

This will:
1. Test Supabase connection
2. Test inserting a submission
3. Test the full sync function
4. Verify data in database

## Next Steps

1. ✅ Service role key is set permanently
2. ✅ Sync function is working
3. ⏭️ Process new documents (they will auto-sync)
4. ⏭️ Sync any existing files in `review/` directory
5. ⏭️ Check the review dashboard to see submissions

