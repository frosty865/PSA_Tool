# Supabase Connection Fix

## Problem
Supabase connection was failing because `supabase_upload.py` was only checking for `SUPABASE_ANON_KEY`, but the system was configured with `SUPABASE_SERVICE_ROLE_KEY` instead.

## Root Cause
- `supabase_client.py` correctly uses: `SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY`
- `supabase_upload.py` was only using: `SUPABASE_ANON_KEY` (which wasn't set)
- This caused uploads to fail silently because the client couldn't be initialized

## Fix Applied
Updated `services/processor/normalization/supabase_upload.py` to match the logic in `supabase_client.py`:

```python
# Before (WRONG):
supabase_key = Config.SUPABASE_ANON_KEY

# After (CORRECT):
supabase_key = Config.SUPABASE_SERVICE_ROLE_KEY or Config.SUPABASE_ANON_KEY
```

## Verification
Run the diagnostic script to verify connection:

```bash
python tools/test_supabase_connection.py
```

Expected output:
- ✅ Configuration looks good
- ✅ Connection is working
- ✅ Upload module client initialized successfully

## Files Changed
1. `services/processor/normalization/supabase_upload.py` - Fixed key selection logic
2. `tools/vofc_processor/vofc_processor.py` - Updated error message
3. `tools/test_supabase_connection.py` - New diagnostic script

## Next Steps
1. Restart the processor service to pick up the changes:
   ```powershell
   nssm restart VOFC-Processor
   ```

2. Check processor logs to verify uploads are working:
   ```powershell
   Get-Content C:\Tools\Ollama\Data\logs\vofc_processor.log -Tail 50
   ```

3. Process a test file and verify it appears in Supabase submissions table

## Configuration Notes
- The system uses `SUPABASE_SERVICE_ROLE_KEY` for admin operations (bypasses RLS)
- Falls back to `SUPABASE_ANON_KEY` if service role key is not available
- Both keys are checked in all Supabase client initialization code now

