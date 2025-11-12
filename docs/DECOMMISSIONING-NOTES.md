# Decommissioning Notes - Phase-Based Pipeline

## Date: 2025-01-XX

## Replaced System

The old phase-based processing pipeline has been completely replaced with a unified `vofc_processor` service.

### Removed Files

- ✅ `ollama_auto_processor.py` - Old multi-phase processor (deleted)
- ✅ `services/phase2_engine.py` - Phase 2 extraction engine (deleted)
- ✅ `services/phase2_lite_classifier.py` - Phase 2 lite classifier (deleted)
- ✅ `services/phase3_auditor.py` - Phase 3 auditor (deleted)

### Removed Services

The following Windows services should be manually removed using NSSM:

- `VOFC-Phase1`
- `VOFC-AutoProcessor`
- `VOFC-Auditor`

**To remove a service:**
```powershell
nssm stop <ServiceName>
nssm remove <ServiceName> confirm
```

### New System

**Location:** `/tools/vofc_processor/`

**Files:**
- `vofc_processor.py` - Unified pipeline processor
- `requirements.txt` - Dependencies
- `install_service.ps1` - NSSM installer script
- `__init__.py` - Package init

**New Service Name:** `VOFC-Processor`

### Architecture Changes

**Old (Phase-Based):**
```
PDF → Phase 1 Parser → Phase 2 Engine → Phase 3 Auditor → Supabase
```

**New (Unified):**
```
PDF → text extraction → vofc-engine:latest → JSON validation → Supabase → archive
```

### Key Differences

1. **Single Model**: Only uses `vofc-engine:latest` (no phase separation)
2. **Simpler Flow**: Direct extraction → model → validation → upload
3. **Reference Context**: Optional reference subset from VOFC_Library.xlsx
4. **Self-Healing**: Malformed JSON is logged and can be retried
5. **No Duplicate Logic**: Model handles deduplication internally

### Preserved Directories

- `/library` - Archive of processed documents
- `/processed` - JSON output files
- `/incoming` - Input directory for new PDFs

### Migration Checklist

- [ ] Stop old services (VOFC-Phase1, VOFC-AutoProcessor, VOFC-Auditor)
- [ ] Remove old services using NSSM
- [ ] Install new service using `tools\vofc_processor\install_service.ps1`
- [ ] Verify environment variables (SUPABASE_URL, SUPABASE_KEY)
- [ ] Verify `vofc-engine:latest` model is available
- [ ] Test with a sample PDF in `/incoming`
- [ ] Verify JSON output in `/processed`
- [ ] Verify submission in Supabase
- [ ] Verify file moved to `/library`

### Environment Variables Required

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
VOFC_DATA_DIR=C:\Tools\Ollama\Data  # Optional, defaults to C:\Tools\Ollama\Data
```

### Testing

1. Drop a PDF in `C:\Tools\Ollama\Data\incoming`
2. Check logs in `C:\Tools\Ollama\Data\logs\`
3. Verify JSON output in `C:\Tools\Ollama\Data\processed\`
4. Check Supabase `submissions` table for new record
5. Verify PDF moved to `C:\Tools\Ollama\Data\library\`

