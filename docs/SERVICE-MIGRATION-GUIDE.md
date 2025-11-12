# Service Migration Guide - Step by Step

## Overview

This guide provides line-by-line instructions for removing old phase-based services and installing the new unified VOFC Processor service.

---

## Part 1: Remove Old Services

### Step 1: Open PowerShell as Administrator

1. Press `Windows Key + X`
2. Select **"Windows PowerShell (Admin)"** or **"Terminal (Admin)"**
3. Click **"Yes"** when prompted by User Account Control

### Step 2: Check Current Services

Run these commands to see which old services are installed:

```powershell
# Check if VOFC-Phase1 exists
nssm status VOFC-Phase1

# Check if VOFC-AutoProcessor exists
nssm status VOFC-AutoProcessor

# Check if VOFC-Auditor exists
nssm status VOFC-Auditor
```

**Expected Result:**
- If service exists: Shows status (RUNNING, STOPPED, etc.)
- If service doesn't exist: Shows error "The specified service does not exist"

### Step 3: Stop Old Services (if running)

For each service that exists, stop it:

```powershell
# Stop VOFC-Phase1 (if it exists)
nssm stop VOFC-Phase1

# Stop VOFC-AutoProcessor (if it exists)
nssm stop VOFC-AutoProcessor

# Stop VOFC-Auditor (if it exists)
nssm stop VOFC-Auditor
```

**Wait 5 seconds** after each stop command to allow the service to fully shut down.

### Step 4: Remove Old Services

Remove each service that exists:

```powershell
# Remove VOFC-Phase1
nssm remove VOFC-Phase1 confirm

# Remove VOFC-AutoProcessor
nssm remove VOFC-AutoProcessor confirm

# Remove VOFC-Auditor
nssm remove VOFC-Auditor confirm
```

**Expected Result:** Each command should show "Service removed successfully" or similar.

### Step 5: Verify Old Services Are Removed

Verify they're gone:

```powershell
# These should all show "does not exist" errors
nssm status VOFC-Phase1
nssm status VOFC-AutoProcessor
nssm status VOFC-Auditor
```

---

## Part 2: Install New Service

### Step 1: Navigate to Service Directory

```powershell
# Change to the service directory
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\tools\vofc_processor
```

**Verify you're in the right place:**
```powershell
# List files - you should see:
# - vofc_processor.py
# - requirements.txt
# - install_service.ps1
# - __init__.py
dir
```

### Step 2: Install Python Dependencies

```powershell
# Install required packages
pip install -r requirements.txt
```

**Expected Output:**
```
Requirement already satisfied: pandas
Requirement already satisfied: PyMuPDF
Requirement already satisfied: requests
Requirement already satisfied: supabase
```

If any packages are missing, they will be installed automatically.

### Step 3: Set Environment Variables

Set Supabase credentials (replace with your actual values):

```powershell
# Set Supabase URL
$env:SUPABASE_URL = "https://your-project.supabase.co"

# Set Supabase Key
$env:SUPABASE_KEY = "your-service-role-key-here"
```

**Note:** These are session-only. For permanent setup, see "Permanent Environment Variables" section below.

### Step 4: Verify Ollama Server

Check that Ollama server is running and model is available:

```powershell
# Check if Ollama is running (should return list of models)
ollama list
```

**Expected Output:** Should show `vofc-engine:latest` in the list.

**If Ollama is not running:**
```powershell
# Start Ollama (if installed as service)
Start-Service Ollama

# OR if running manually, start it in another terminal
```

### Step 5: Verify Ollama Server URL (Optional)

If your Ollama server is not on localhost:11434, set the URL:

```powershell
# Only if Ollama is on a different host/port
$env:OLLAMA_BASE_URL = "http://your-ollama-server:11434"
```

**Default:** `http://localhost:11434` (no need to set if using default)

### Step 6: Run Installation Script

```powershell
# Run the installation script
.\install_service.ps1
```

**Expected Output:**
```
Installing VOFC-Processor...
  Python: C:\Program Files\Python311\python.exe
  Script: C:\Tools\VOFC\tools\vofc_processor\vofc_processor.py
Service installed. Starting now...
Service installation complete!
  Service Name: VOFC-Processor
  Status: Check with 'nssm status VOFC-Processor'
  Logs: C:\Tools\Ollama\Data\logs\
```

### Step 7: Verify Service is Running

```powershell
# Check service status
nssm status VOFC-Processor
```

**Expected Output:** Should show `SERVICE_RUNNING` or status information.

**If service failed to start:**
```powershell
# Check service logs
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_err.log -Tail 50
```

### Step 8: Test the Service

Drop a test PDF in the incoming directory:

```powershell
# Check incoming directory exists
Test-Path C:\Tools\Ollama\Data\incoming

# If it doesn't exist, create it
New-Item -ItemType Directory -Path C:\Tools\Ollama\Data\incoming -Force
```

**Test Processing:**
1. Copy a test PDF to `C:\Tools\Ollama\Data\incoming\`
2. Wait 30-60 seconds
3. Check if file was processed:

```powershell
# Check if PDF was moved to library
dir C:\Tools\Ollama\Data\library

# Check if JSON output was created
dir C:\Tools\Ollama\Data\processed

# Check service logs
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 20
```

---

## Part 3: Permanent Environment Variables (Optional)

If you want environment variables to persist across reboots:

### Option A: System Environment Variables (Recommended)

1. Press `Windows Key + R`
2. Type: `sysdm.cpl` and press Enter
3. Click **"Advanced"** tab
4. Click **"Environment Variables"** button
5. Under **"System variables"**, click **"New"**
6. Add each variable:
   - Variable name: `SUPABASE_URL`
   - Variable value: `https://your-project.supabase.co`
   - Click **"OK"**
7. Repeat for `SUPABASE_KEY`
8. Click **"OK"** to close all dialogs
9. **Restart PowerShell** for changes to take effect

### Option B: User Environment Variables

Same as Option A, but add to **"User variables"** instead of **"System variables"**.

---

## Part 4: Service Management Commands

### Start Service
```powershell
nssm start VOFC-Processor
```

### Stop Service
```powershell
nssm stop VOFC-Processor
```

### Restart Service
```powershell
nssm restart VOFC-Processor
```

### Check Service Status
```powershell
nssm status VOFC-Processor
```

### View Service Logs
```powershell
# View output log (last 50 lines)
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 50

# View error log (last 50 lines)
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_err.log -Tail 50

# Follow log in real-time
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Wait -Tail 20
```

### Edit Service Configuration
```powershell
# Open NSSM GUI to edit service settings
nssm edit VOFC-Processor
```

---

## Troubleshooting

### Service Won't Start

1. **Check Python path:**
   ```powershell
   # Verify Python exists
   python --version
   
   # If not found, update install_service.ps1 with correct path
   ```

2. **Check script path:**
   ```powershell
   # Verify script exists
   Test-Path C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\tools\vofc_processor\vofc_processor.py
   ```

3. **Check environment variables:**
   ```powershell
   # Verify Supabase credentials are set
   $env:SUPABASE_URL
   $env:SUPABASE_KEY
   ```

4. **Check Ollama server:**
   ```powershell
   # Test Ollama connection
   curl http://localhost:11434/api/tags
   ```

### Service Starts But Doesn't Process Files

1. **Check incoming directory:**
   ```powershell
   # Verify directory exists and is accessible
   Test-Path C:\Tools\Ollama\Data\incoming
   dir C:\Tools\Ollama\Data\incoming
   ```

2. **Check service logs:**
   ```powershell
   Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 100
   ```

3. **Check for errors:**
   ```powershell
   Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_err.log -Tail 100
   ```

### Service Processes But Files Don't Appear in Supabase

1. **Verify Supabase credentials:**
   ```powershell
   # Check if credentials are set
   $env:SUPABASE_URL
   $env:SUPABASE_KEY
   ```

2. **Test Supabase connection:**
   ```powershell
   # Try a simple Python test
   python -c "from supabase import create_client; print('Supabase import OK')"
   ```

3. **Check processed directory:**
   ```powershell
   # Verify JSON files are being created
   dir C:\Tools\Ollama\Data\processed
   ```

---

## Verification Checklist

After installation, verify everything is working:

- [ ] Old services removed (VOFC-Phase1, VOFC-AutoProcessor, VOFC-Auditor)
- [ ] New service installed (VOFC-Processor)
- [ ] Service is running (`nssm status VOFC-Processor` shows RUNNING)
- [ ] Environment variables set (SUPABASE_URL, SUPABASE_KEY)
- [ ] Ollama server accessible (`ollama list` works)
- [ ] Test PDF processed (file moved to library, JSON in processed)
- [ ] Submission appears in Supabase (check submissions table)

---

## Quick Reference

### Remove All Old Services (One Command)
```powershell
nssm stop VOFC-Phase1; nssm remove VOFC-Phase1 confirm
nssm stop VOFC-AutoProcessor; nssm remove VOFC-AutoProcessor confirm
nssm stop VOFC-Auditor; nssm remove VOFC-Auditor confirm
```

### Install New Service (One Command)
```powershell
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\tools\vofc_processor; .\install_service.ps1
```

### Check Everything
```powershell
# Check old services (should all fail)
nssm status VOFC-Phase1; nssm status VOFC-AutoProcessor; nssm status VOFC-Auditor

# Check new service (should show RUNNING)
nssm status VOFC-Processor

# Check logs
Get-Content C:\Tools\Ollama\Data\logs\vofc_processor_out.log -Tail 10
```

