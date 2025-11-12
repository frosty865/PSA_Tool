# Phase 1 Restart Guide

## Quick Restart Steps

### 1. Restart VOFC-Processor Service

**Run PowerShell as Administrator:**

```powershell
nssm restart VOFC-Processor
```

**Wait 5 seconds, then verify:**
```powershell
nssm status VOFC-Processor
```

Should show: `SERVICE_RUNNING`

---

### 2. Verify Migration in Supabase

**Open Supabase SQL Editor and run:**

```sql
-- Check columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'vulnerabilities'
    AND column_name IN (
        'dedupe_key', 'confidence', 'impact_level', 'follow_up', 
        'standard_reference', 'created_at', 'updated_at'
    )
ORDER BY column_name;
```

**Expected:** 7 rows returned

---

### 3. Check Logs After Restart

```powershell
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor*.log -Tail 30
```

**Look for:**
- ✅ `✓ Loaded X reference records from Supabase`
- ✅ `Fetched X vulnerabilities from Supabase`
- ❌ No "column does not exist" warnings

---

### 4. Test Processing

1. **Place a test PDF** in `C:\Tools\Ollama\Data\incoming\`

2. **Wait 30 seconds** for processing

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
       created_at
   FROM vulnerabilities
   ORDER BY created_at DESC
   LIMIT 5;
   ```

**Expected Results:**
- ✅ `dedupe_key` populated (40-char lowercase hash)
- ✅ `confidence` populated (High/Medium/Low)
- ✅ `impact_level` populated (High/Moderate/Low)
- ✅ `follow_up` populated (true/false)
- ✅ `created_at` timestamp set

---

## Troubleshooting

### If you still see "column does not exist" errors:

1. **Verify migration ran successfully:**
   - Check Supabase SQL Editor for any errors
   - Re-run `sql/verify-phase1.sql`

2. **Verify processor code is updated:**
   ```powershell
   # Check the service is using updated code
   Get-Content C:\Tools\py_scripts\vofc_processor\vofc_processor.py | Select-String "vulnerability_name"
   ```
   Should return nothing (no matches)

3. **Force service restart:**
   ```powershell
   nssm stop VOFC-Processor
   Start-Sleep -Seconds 3
   nssm start VOFC-Processor
   ```

### If dedupe_key constraint violation:

The constraint enforces lowercase. If you have existing uppercase hashes:

```sql
UPDATE vulnerabilities 
SET dedupe_key = lower(dedupe_key) 
WHERE dedupe_key IS NOT NULL 
  AND dedupe_key != lower(dedupe_key);
```

---

## Success Indicators

✅ No "column does not exist" warnings in logs  
✅ Reference data loads successfully  
✅ New records have `dedupe_key`, `confidence`, `impact_level` populated  
✅ `created_at` and `updated_at` timestamps working  
✅ Deduplication working (no duplicate `dedupe_key` values)  

Once all indicators are met, Phase 1 is complete! 🎉

