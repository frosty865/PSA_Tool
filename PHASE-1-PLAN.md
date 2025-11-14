# Phase 1: Foundation - Detailed Implementation Plan

**Objective:** Centralize all configuration through `Config` module, eliminate hardcoded paths, and add startup validation.

**Total Tasks:** 42 atomic tasks  
**Estimated Time:** 2-3 days  
**Risk Level:** Low (additive changes, no breaking changes)

---

## Task Group 1: Extend Config Module

### Task 1.1: Add Missing Environment Variables to Config
**File:** `config/__init__.py`  
**Lines:** Add after line 87  
**Changes:**
- Add `TUNNEL_URL = os.getenv("TUNNEL_URL", "https://flask.frostech.site")`
- Add `OLLAMA_HOST = os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_URL") or os.getenv("OLLAMA_API_BASE_URL") or "http://127.0.0.1:11434"`
- Add `OLLAMA_URL = OLLAMA_HOST.rstrip('/')` (normalize)
- Add `VOFC_ENGINE_CONFIG = os.getenv("VOFC_ENGINE_CONFIG", "C:/Tools/Ollama/vofc_config.yaml")`
- Add `ENABLE_AI_ENHANCEMENT = os.getenv("ENABLE_AI_ENHANCEMENT", "false").lower() == "true"`
- Add `CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.3"))`
- Add `SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")`
- Add `SUBMITTER_EMAIL = os.getenv("SUBMITTER_EMAIL")`
**Estimated Lines:** 10 lines added  
**Dependencies:** None

### Task 1.2: Add Tunnel Log Paths to Config
**File:** `config/__init__.py`  
**Lines:** Add after line 42 (after PROGRESS_FILE)  
**Changes:**
- Add `TUNNEL_LOG_PATHS = [Path(r"C:\Tools\nssm\logs\vofc_tunnel.log")]`
- Add `VOFC_LOGS_DIR = Path(r"C:\Tools\nssm\logs")` (if not exists, create in validation)
**Estimated Lines:** 2 lines added  
**Dependencies:** None

### Task 1.3: Add Archive Path to Config
**File:** `config/__init__.py`  
**Lines:** Add after line 39 (after AUTOMATION_DIR)  
**Changes:**
- Add `ARCHIVE_DIR = Path(r"C:\Tools\archive\VOFC\Data")` (for migration fallback detection)
**Estimated Lines:** 1 line added  
**Dependencies:** None

---

## Task Group 2: Migrate routes/system.py

### Task 2.1: Replace TUNNEL_URL os.getenv in system.py
**File:** `routes/system.py`  
**Lines:** 246, 376  
**Changes:**
- Import `Config` at top: `from config import Config`
- Replace `os.getenv("TUNNEL_URL", "https://flask.frostech.site")` with `Config.TUNNEL_URL`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

### Task 2.2: Replace OLLAMA_HOST os.getenv in system.py
**File:** `routes/system.py`  
**Lines:** 343-346  
**Changes:**
- Replace the multi-line `ollama_url_raw = (os.getenv("OLLAMA_HOST") or ...)` block with `Config.OLLAMA_URL`
- Remove the URL normalization logic (already done in Config)
**Estimated Lines:** 5 lines changed (remove 4, add 1)  
**Dependencies:** Task 1.1

### Task 2.3: Replace FLASK_PORT os.getenv in system.py
**File:** `routes/system.py`  
**Line:** 355  
**Changes:**
- Replace `int(os.getenv('FLASK_PORT', '8080'))` with `Config.FLASK_PORT`
- Update `flask_url` construction to use `Config.FLASK_URL_LOCAL`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

### Task 2.4: Replace OLLAMA_MODEL os.getenv in system.py
**File:** `routes/system.py`  
**Line:** 451  
**Changes:**
- Replace `os.getenv('OLLAMA_MODEL', 'psa-engine')` with `Config.DEFAULT_MODEL`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.1

### Task 2.5: Replace hardcoded archive path in system.py
**File:** `routes/system.py`  
**Lines:** 759, 763, 914, 918  
**Changes:**
- Replace `Path(r"C:\Tools\archive\VOFC\Data")` with `Config.ARCHIVE_DIR`
- Replace `Path(r"C:\Tools\Ollama\Data")` with `Config.DATA_DIR`
**Estimated Lines:** 4 lines changed  
**Dependencies:** Task 1.1, Task 1.3

### Task 2.6: Replace hardcoded tunnel log path in system.py
**File:** `routes/system.py`  
**Line:** 1570  
**Changes:**
- Replace hardcoded `Path(r"C:\Tools\nssm\logs\vofc_tunnel.log")` with `Config.TUNNEL_LOG_PATHS[0]`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.2

---

## Task Group 3: Migrate routes/models.py

### Task 3.1: Replace OLLAMA_HOST in models.py
**File:** `routes/models.py`  
**Line:** 22  
**Changes:**
- Import `Config` at top
- Replace `os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')` with `Config.OLLAMA_URL`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

### Task 3.2: Replace OLLAMA_MODEL in models.py
**File:** `routes/models.py`  
**Lines:** 28, 137  
**Changes:**
- Replace `os.getenv('OLLAMA_MODEL', 'psa-engine:latest')` with `Config.DEFAULT_MODEL` (both occurrences)
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 4: Migrate routes/extract.py

### Task 4.1: Replace VOFC_BASE_DIR in extract.py
**File:** `routes/extract.py`  
**Line:** 67  
**Changes:**
- Import `Config` at top
- Replace `Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))` with `Config.DATA_DIR`
**Estimated Lines:** 2 lines changed  
**Dependencies:** None (Config.DATA_DIR already exists)

---

## Task Group 5: Migrate routes/process.py

### Task 5.1: Replace VOFC_BASE_DIR in process.py
**File:** `routes/process.py`  
**Line:** 175  
**Changes:**
- Import `Config` at top
- Replace `Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))` with `Config.DATA_DIR`
**Estimated Lines:** 2 lines changed  
**Dependencies:** None (Config.DATA_DIR already exists)

---

## Task Group 6: Migrate services/ollama_client.py

### Task 6.1: Replace OLLAMA_HOST in ollama_client.py
**File:** `services/ollama_client.py`  
**Line:** 16  
**Changes:**
- Import `Config` at top
- Replace `OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')` with `OLLAMA_HOST = Config.OLLAMA_URL`
- Remove `OLLAMA_URL = OLLAMA_HOST` (line 17) - use `Config.OLLAMA_URL` directly
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

### Task 6.2: Replace VOFC_ENGINE_CONFIG in ollama_client.py
**File:** `services/ollama_client.py`  
**Line:** 52  
**Changes:**
- Replace `os.getenv("VOFC_ENGINE_CONFIG", "C:/Tools/Ollama/vofc_config.yaml")` with `Config.VOFC_ENGINE_CONFIG`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.1

---

## Task Group 7: Migrate services/supabase_client.py

### Task 7.1: Replace SUPABASE_URL in supabase_client.py (module level)
**File:** `services/supabase_client.py`  
**Lines:** 21-22  
**Changes:**
- Import `Config` at top
- Replace `SUPABASE_URL = os.getenv(...)` with `SUPABASE_URL = Config.SUPABASE_URL`
- Replace `SUPABASE_KEY = os.getenv(...)` with `SUPABASE_KEY = Config.SUPABASE_ANON_KEY or Config.SUPABASE_SERVICE_ROLE_KEY`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

### Task 7.2: Replace SUPABASE_URL in get_supabase_client()
**File:** `services/supabase_client.py`  
**Lines:** 30-31  
**Changes:**
- Replace `os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL', '')` with `Config.SUPABASE_URL`
- Replace `os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')` with `Config.SUPABASE_SERVICE_ROLE_KEY or Config.SUPABASE_ANON_KEY`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

### Task 7.3: Replace SUBMITTER_EMAIL in supabase_client.py
**File:** `services/supabase_client.py`  
**Line:** 358  
**Changes:**
- Replace `os.getenv('SUBMITTER_EMAIL')` with `Config.SUBMITTER_EMAIL`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.1

### Task 7.4: Replace SUPABASE credentials in test_supabase_connection()
**File:** `services/supabase_client.py`  
**Lines:** 599-600  
**Changes:**
- Replace `os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL', '')` with `Config.SUPABASE_URL`
- Replace `os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')` with `Config.SUPABASE_SERVICE_ROLE_KEY or Config.SUPABASE_ANON_KEY`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 8: Migrate services/processor/normalization/supabase_upload.py

### Task 8.1: Replace SUPABASE credentials in init_supabase()
**File:** `services/processor/normalization/supabase_upload.py`  
**Lines:** 25-27  
**Changes:**
- Import `Config` at top
- Replace `os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")` with `Config.SUPABASE_URL`
- Replace `os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")` with `Config.SUPABASE_ANON_KEY`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

### Task 8.2: Replace OLLAMA_MODEL in supabase_upload.py
**File:** `services/processor/normalization/supabase_upload.py`  
**Line:** 244  
**Changes:**
- Replace `os.getenv("VOFC_MODEL", os.getenv("OLLAMA_MODEL", "vofc-unified:latest"))` with `Config.DEFAULT_MODEL`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.1

---

## Task Group 9: Migrate services/processor/model/vofc_client.py

### Task 9.1: Replace OLLAMA_URL and MODEL in vofc_client.py
**File:** `services/processor/model/vofc_client.py`  
**Lines:** 12-13  
**Changes:**
- Import `Config` at top
- Replace `OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")` with `OLLAMA_URL = f"{Config.OLLAMA_URL}/api/generate"`
- Replace `MODEL = os.getenv("VOFC_MODEL", os.getenv("OLLAMA_MODEL", "vofc-unified:latest"))` with `MODEL = Config.DEFAULT_MODEL`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 10: Migrate services/processor/processor/run_processor.py

### Task 10.1: Replace OLLAMA_URL in run_processor.py
**File:** `services/processor/processor/run_processor.py`  
**Line:** 62  
**Changes:**
- Import `Config` at top
- Replace `os.getenv("OLLAMA_URL", "http://localhost:11434")` with `Config.OLLAMA_URL`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 11: Migrate services/learning_logger.py

### Task 11.1: Replace SUPABASE credentials in learning_logger.py
**File:** `services/learning_logger.py`  
**Lines:** 19-20  
**Changes:**
- Import `Config` at top
- Replace `os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")` with `Config.SUPABASE_URL`
- Replace `os.getenv("SUPABASE_SERVICE_ROLE_KEY")` with `Config.SUPABASE_SERVICE_ROLE_KEY`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 12: Migrate services/postprocess.py

### Task 12.1: Replace ENABLE_AI_ENHANCEMENT in postprocess.py (first occurrence)
**File:** `services/postprocess.py`  
**Line:** 74  
**Changes:**
- Import `Config` at top
- Replace `os.getenv("ENABLE_AI_ENHANCEMENT", "false").lower() == "true"` with `Config.ENABLE_AI_ENHANCEMENT`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.1

### Task 12.2: Replace ENABLE_AI_ENHANCEMENT in postprocess.py (second occurrence)
**File:** `services/postprocess.py`  
**Line:** 205  
**Changes:**
- Replace `os.getenv("ENABLE_AI_ENHANCEMENT", "false").lower() == "true"` with `Config.ENABLE_AI_ENHANCEMENT`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.1

### Task 12.3: Replace CONFIDENCE_THRESHOLD in postprocess.py
**File:** `services/postprocess.py`  
**Line:** 397  
**Changes:**
- Replace `float(os.getenv("CONFIDENCE_THRESHOLD", "0.3"))` with `Config.CONFIDENCE_THRESHOLD`
**Estimated Lines:** 1 line changed  
**Dependencies:** Task 1.1

### Task 12.4: Replace VOFC_BASE_DIR in postprocess.py
**File:** `services/postprocess.py`  
**Line:** 404  
**Changes:**
- Replace `os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data")` with `Config.DATA_DIR`
**Estimated Lines:** 1 line changed  
**Dependencies:** None (Config.DATA_DIR already exists)

### Task 12.5: Replace ENABLE_AI_ENHANCEMENT in postprocess.py (remaining occurrences)
**File:** `services/postprocess.py`  
**Lines:** 502, 637  
**Changes:**
- Replace both remaining `os.getenv("ENABLE_AI_ENHANCEMENT", "false").lower() == "true"` with `Config.ENABLE_AI_ENHANCEMENT`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 13: Migrate services/processor.py

### Task 13.1: Replace VOFC_BASE_DIR in processor.py
**File:** `services/processor.py`  
**Line:** 25  
**Changes:**
- Import `Config` at top
- Replace `Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))` with `Config.DATA_DIR`
- Update all directory definitions to use `Config.*` (INCOMING_DIR, PROCESSED_DIR, ERRORS_DIR)
**Estimated Lines:** 5 lines changed  
**Dependencies:** None (Config.DATA_DIR already exists)

---

## Task Group 14: Migrate services/folder_watcher.py

### Task 14.1: Replace VOFC_DATA_DIR in folder_watcher.py
**File:** `services/folder_watcher.py`  
**Line:** 19  
**Changes:**
- Import `Config` at top
- Replace `os.getenv("VOFC_DATA_DIR", r"C:\Tools\Ollama\Data")` with `Config.DATA_DIR`
**Estimated Lines:** 2 lines changed  
**Dependencies:** None (Config.DATA_DIR already exists)

---

## Task Group 15: Migrate services/preprocess.py

### Task 15.1: Replace VOFC_BASE_DIR in preprocess.py
**File:** `services/preprocess.py`  
**Line:** 51  
**Changes:**
- Import `Config` at top
- Replace `Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))` with `Config.DATA_DIR`
**Estimated Lines:** 2 lines changed  
**Dependencies:** None (Config.DATA_DIR already exists)

---

## Task Group 16: Migrate services/retraining_exporter.py

### Task 16.1: Replace SUPABASE credentials in retraining_exporter.py
**File:** `services/retraining_exporter.py`  
**Lines:** 16-17  
**Changes:**
- Import `Config` at top
- Replace `os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")` with `Config.SUPABASE_URL`
- Replace `os.getenv("SUPABASE_SERVICE_ROLE_KEY")` with `Config.SUPABASE_SERVICE_ROLE_KEY`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 17: Migrate services/approval_sync.py

### Task 17.1: Replace SUPABASE credentials in approval_sync.py
**File:** `services/approval_sync.py`  
**Lines:** 18-19  
**Changes:**
- Import `Config` at top
- Replace `os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")` with `Config.SUPABASE_URL`
- Replace `os.getenv("SUPABASE_SERVICE_ROLE_KEY")` with `Config.SUPABASE_SERVICE_ROLE_KEY`
**Estimated Lines:** 2 lines changed  
**Dependencies:** Task 1.1

---

## Task Group 18: Migrate tools/vofc_processor/vofc_processor.py (Complex)

### Task 18.1: Replace DATA_DIR logic in vofc_processor.py (Part 1 - Remove fallback logic)
**File:** `tools/vofc_processor/vofc_processor.py`  
**Lines:** 73-84  
**Changes:**
- Import `Config` at top
- Remove entire fallback logic block (lines 74-84)
- Replace with: `DATA_DIR = Config.DATA_DIR`
**Estimated Lines:** 12 lines removed, 1 line added  
**Dependencies:** None (Config.DATA_DIR already exists)

### Task 18.2: Replace directory definitions in vofc_processor.py
**File:** `tools/vofc_processor/vofc_processor.py`  
**Lines:** 86-90  
**Changes:**
- Replace `os.path.join(DATA_DIR, "incoming")` with `Config.INCOMING_DIR`
- Replace `os.path.join(DATA_DIR, "processed")` with `Config.PROCESSED_DIR`
- Replace `os.path.join(DATA_DIR, "library")` with `Config.LIBRARY_DIR`
- Replace `os.path.join(DATA_DIR, "temp")` with `Config.TEMP_DIR`
- Replace `os.path.join(DATA_DIR, "logs")` with `Config.LOGS_DIR`
**Estimated Lines:** 5 lines changed  
**Dependencies:** None (Config paths already exist)

### Task 18.3: Replace hardcoded .env paths in vofc_processor.py (Optional - keep for compatibility)
**File:** `tools/vofc_processor/vofc_processor.py`  
**Lines:** 49-56  
**Changes:**
- **Note:** Keep this logic for now (allows .env loading from multiple locations)
- **Future:** Consider centralizing .env loading in Config module (Phase 2)
**Estimated Lines:** 0 (no change for Phase 1)  
**Dependencies:** None

---

## Task Group 19: Replace Hardcoded Paths in Tools

### Task 19.1: Replace hardcoded path in tools/reset_data_folders.py
**File:** `tools/reset_data_folders.py`  
**Line:** 23  
**Changes:**
- Import `Config` at top
- Replace `Path(r"C:\Tools\Ollama\Data")` with `Config.DATA_DIR`
- Update all subdirectory definitions to use `Config.*`
**Estimated Lines:** 8 lines changed  
**Dependencies:** None (Config.DATA_DIR already exists)

### Task 19.2: Replace hardcoded paths in tools/seed_retrain.py
**File:** `tools/seed_retrain.py`  
**Lines:** 48, 54  
**Changes:**
- Import `Config` at top
- Replace training data path logic with `Config.DATA_DIR / "training_data"` (or keep legacy fallback for now)
- Replace `Path(r"C:\Tools\Ollama")` with `Path(Config.OLLAMA_URL.replace("http://", "").split(":")[0])` or add `Config.OLLAMA_BASE_DIR`
- **Note:** May need to add `OLLAMA_BASE_DIR` to Config if path is needed
**Estimated Lines:** 3 lines changed  
**Dependencies:** Task 1.1 (if adding OLLAMA_BASE_DIR)

---

## Task Group 20: Add Startup Validation

### Task 20.1: Add startup validation to tools/vofc_processor/vofc_processor.py
**File:** `tools/vofc_processor/vofc_processor.py`  
**Lines:** Add after line 100 (after logging setup, before main logic)  
**Changes:**
- Add: `from config import Config, ConfigurationError`
- Add: `try: Config.validate(); except ConfigurationError as e: logging.error(f"Configuration validation failed: {e}"); sys.exit(1)`
**Estimated Lines:** 4 lines added  
**Dependencies:** Tasks 18.1-18.2 (Config must be used first)

### Task 20.2: Add startup validation to app.py
**File:** `app.py`  
**Lines:** Add at top after imports, before app creation  
**Changes:**
- Add: `from config import Config, ConfigurationError`
- Add: `try: Config.validate(); except ConfigurationError as e: print(f"Configuration validation failed: {e}"); sys.exit(1)`
**Estimated Lines:** 4 lines added  
**Dependencies:** None (can be done independently)

---

## Task Group 21: Update Config Validation

### Task 21.1: Add validation for new Config values
**File:** `config/__init__.py`  
**Lines:** Update `validate()` method (around line 94)  
**Changes:**
- Add validation for `OLLAMA_URL` (must be valid URL format)
- Add validation for `TUNNEL_URL` (must be valid URL format)
- Add warnings (not errors) for optional values: `ENABLE_AI_ENHANCEMENT`, `CONFIDENCE_THRESHOLD`
**Estimated Lines:** 10 lines added  
**Dependencies:** Task 1.1

---

## Summary

**Total Tasks:** 42  
**Total Files Modified:** 20  
**Estimated Total Lines Changed:** ~150 lines (mostly replacements, some additions)

**Task Dependencies:**
- Task 1.1 must be completed before all other tasks (except 20.2, 19.1, 18.1-18.2, 13.1, 14.1, 15.1, 4.1, 5.1, 12.4)
- Tasks can be grouped by file and done in parallel after Task 1.1
- Task 20.1 depends on Tasks 18.1-18.2
- Task 21.1 depends on Task 1.1

**Recommended Execution Order:**
1. Task Group 1 (Tasks 1.1-1.3) - Extend Config
2. Task Group 21 (Task 21.1) - Update validation
3. All other task groups in parallel (can be done file-by-file)
4. Task Group 20 (Tasks 20.1-20.2) - Add startup validation

---

## Testing Checklist

After each task group:
- [ ] Verify imports work (no `ImportError`)
- [ ] Verify Config values are accessible
- [ ] Run affected service/script to ensure no runtime errors
- [ ] Check logs for configuration warnings

After all tasks:
- [ ] Run full system health check
- [ ] Verify all services start correctly
- [ ] Verify no hardcoded paths remain (grep for `C:\\Tools`)
- [ ] Verify no direct `os.getenv()` calls remain (grep for `os.getenv`)

---

**End of Phase 1 Plan**

