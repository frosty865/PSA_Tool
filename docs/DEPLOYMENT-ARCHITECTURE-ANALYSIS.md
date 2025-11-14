# Deployment Architecture Analysis

## Current Problem

**Development Location:**
- `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool` (OneDrive synced)
- Code is developed here, committed to git

**Service Runtime Location:**
- `C:\Tools\VOFC-Flask` (Flask service runs from here)
- `C:\Tools\VOFC-Processor` (Processor service runs from here)
- `C:\Tools\Ollama` (Ollama installation)

**Issue:**
- Services run from `C:\Tools\*` but code is in project folder
- Manual sync required (`scripts/sync-flask-code.ps1`)
- OneDrive sync can interfere with running services
- Code changes require manual intervention

## Why Services Are in C:\Tools

**Reasons:**
1. **Stability**: `C:\Tools` is not synced to OneDrive, preventing sync conflicts
2. **Service Isolation**: Services need stable paths that don't change
3. **Production-like**: Mimics production deployment structure
4. **NSSM Requirements**: Windows services need fixed paths

**Problems:**
1. **Manual Sync**: Code must be manually copied after changes
2. **Two Locations**: Code exists in two places (project + Tools)
3. **Sync Scripts**: Requires manual execution of sync scripts
4. **Deployment Friction**: Every code change requires sync + restart

## Proposed Solutions

### Option A: Automated File Watcher Sync (Recommended)
**Approach:** Create a file watcher that automatically syncs changes from project to Tools

**Pros:**
- Services stay in stable `C:\Tools` location
- Automatic sync on file changes
- No OneDrive sync conflicts
- Services remain isolated

**Cons:**
- Requires file watcher service
- Still maintains two copies of code

**Implementation:**
- PowerShell file watcher script
- Watches project folder for changes
- Automatically copies to `C:\Tools\*`
- Optionally restarts services on critical file changes

### Option B: Run Services from Project Folder
**Approach:** Change NSSM services to run directly from project folder

**Pros:**
- Single source of truth
- No sync needed
- Immediate code changes

**Cons:**
- OneDrive sync can interfere with running services
- File locks during sync
- Services may crash if OneDrive syncs while running
- Project folder path may change

### Option C: Git-Based Deployment
**Approach:** Services pull from git repo automatically

**Pros:**
- Version controlled
- Automated deployment
- Can rollback easily

**Cons:**
- Requires git setup in Tools folder
- More complex
- Still requires restart after pull

### Option D: Junction Points / Symlinks
**Approach:** Use Windows junction points to link Tools to project

**Pros:**
- Single source of truth
- Services see project folder directly

**Cons:**
- OneDrive sync issues still apply
- Junction points can be fragile
- May not work well with OneDrive

## Recommendation: Option A (Automated File Watcher)

**Why:**
1. Keeps services in stable `C:\Tools` location
2. Prevents OneDrive sync conflicts
3. Automates the sync process
4. Services remain isolated and stable

**Implementation:**
1. Create `scripts/auto-sync-services.ps1` file watcher
2. Watch for changes in project folder
3. Auto-sync to `C:\Tools\*` on file save
4. Optionally auto-restart services on critical changes
5. Run as background service or scheduled task

