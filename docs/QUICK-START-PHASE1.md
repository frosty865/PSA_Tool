# Quick Start: Phase 1 Implementation

## 5-Minute Setup

### Step 1: Run Database Migration (2 minutes)

1. **Open Supabase Dashboard**
   - Go to your project
   - Click **SQL Editor**

2. **Run Migration**
   - Open `sql/phase1-migration.sql`
   - Copy entire contents
   - Paste into SQL Editor
   - Click **Run**

3. **Verify**
   - Run `sql/verify-phase1.sql`
   - Should see 7 columns, 6 indexes, 1 constraint

---

### Step 2: Restart Service (1 minute)

**Run PowerShell as Administrator:**

```powershell
nssm restart VOFC-Processor
```

**Verify:**
```powershell
nssm status VOFC-Processor
```

Should show: `SERVICE_RUNNING`

---

### Step 3: Test Processing (2 minutes)

1. **Place a PDF** in `C:\Tools\Ollama\Data\incoming\`

2. **Wait 30 seconds**

3. **Check logs:**
   ```powershell
   Get-Content C:\Tools\Ollama\Data\logs\vofc_processor*.log -Tail 30
   ```

4. **Verify in Supabase:**
   ```sql
   SELECT 
       vulnerability,
       dedupe_key,
       confidence,
       impact_level
   FROM vulnerabilities
   ORDER BY created_at DESC
   LIMIT 5;
   ```

---

## Success Indicators

✅ No "column does not exist" errors  
✅ `dedupe_key` populated (40-char hash)  
✅ `confidence` populated (High/Medium/Low)  
✅ `impact_level` populated (High/Moderate/Low)  
✅ `created_at` timestamp set  

---

## Troubleshooting

**Still seeing errors?**
- Verify migration ran: Check Supabase SQL Editor
- Restart service: `nssm restart VOFC-Processor` (as Admin)
- Check code is updated: Service should be using `C:\Tools\py_scripts\vofc_processor\vofc_processor.py`

**No data in new columns?**
- Check logs for processing errors
- Verify model is returning data
- Check Supabase connection

---

## Next: Phase 2

Once Phase 1 is working:
- Run `sql/phase2-migration.sql`
- Processor already supports Phase 2 features
- Adds source document tracking and model version

Ready to go! 🚀

