# Watcher Migration Status

## Current Situation

The **watcher** is a feature within Flask that monitors the `incoming` directory for new files. However, it has a dependency issue:

### Problem

`routes/system.py` line 470 imports from the decommissioned module:
```python
from ollama_auto_processor import start_folder_watcher
```

But `ollama_auto_processor.py` was deleted as part of the pipeline rebuild.

## Is Watcher Still Needed?

### Option 1: Watcher is Redundant (Recommended)

**VOFC-Processor service** already runs continuously and processes files from `C:\Tools\Ollama\Data\incoming\` automatically. The watcher functionality is **duplicated**.

**Recommendation:** Remove watcher functionality from Flask since VOFC-Processor handles it.

### Option 2: Keep Watcher for Flask-Only Processing

If you want Flask to handle file watching separately (e.g., for different processing logic), you need to:

1. **Create a new watcher module** in `services/folder_watcher.py`
2. **Update Flask imports** to use the new module
3. **Migrate watcher code** from old `ollama_auto_processor.py` (if you have a backup)

## Migration Options

### Option A: Remove Watcher (Recommended)

Since VOFC-Processor service handles automatic processing:

1. **Remove watcher endpoints** from `routes/system.py`:
   - Remove `start_watcher` action
   - Remove `stop_watcher` action
   - Keep other control actions

2. **Update frontend** to remove watcher buttons (or disable them)

3. **Update documentation** to reflect that VOFC-Processor handles automatic processing

### Option B: Create New Watcher Module

If watcher is still needed:

1. **Create** `services/folder_watcher.py` with watcher functionality
2. **Update** `routes/system.py` to import from new module:
   ```python
   from services.folder_watcher import start_folder_watcher
   ```
3. **Ensure** watcher code is in `C:\Tools\py_scripts\flask\` (or wherever Flask runs from)

## Current Watcher Status

- **Location**: Part of Flask (`routes/system.py`)
- **Dependency**: `ollama_auto_processor` (decommissioned) ❌
- **Functionality**: Monitors `C:\Tools\Ollama\Data\incoming\`
- **Replacement**: VOFC-Processor service (already handles this) ✅

## Recommendation

**Remove the watcher** since:
1. ✅ VOFC-Processor service already monitors and processes files
2. ✅ No need for duplicate functionality
3. ✅ Simpler architecture
4. ✅ Less code to maintain

If you need the watcher for other purposes, we should create a new implementation that doesn't depend on the old processor.

## Action Required

**If removing watcher:**
1. Update `routes/system.py` to remove watcher actions
2. Update frontend to remove/disable watcher buttons
3. Document that VOFC-Processor handles automatic processing

**If keeping watcher:**
1. Create new `services/folder_watcher.py` module
2. Update imports in `routes/system.py`
3. Ensure it's migrated to `C:\Tools\py_scripts\` with Flask

