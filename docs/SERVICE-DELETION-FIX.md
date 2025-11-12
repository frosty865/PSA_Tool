# Fix: "Service Marked for Deletion" Error

## Problem

When installing the VOFC-Processor service, you may see this error:

```
Error creating service!
CreateService(): The specified service has been marked for deletion.
```

## Cause

This happens when:
1. A service with the same name was recently removed
2. Windows hasn't finished cleaning up the service registry entry
3. The service is in a "pending deletion" state

## Solution 1: Use the Fix Script (Recommended)

Run the automated fix script:

```powershell
# Run as Administrator
cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\scripts
.\fix-service-deletion.ps1
```

This script will:
- Check if service exists
- Force remove it
- Wait for Windows to clean up
- Verify it's gone
- Tell you when it's safe to install

## Solution 2: Wait and Retry

1. **Wait 30-60 seconds** after removing the old service
2. **Check if service is gone:**
   ```powershell
   nssm status VOFC-Processor
   sc.exe query VOFC-Processor
   ```
3. **If both show "does not exist", try installing again:**
   ```powershell
   cd tools\vofc_processor
   .\install_service.ps1
   ```

## Solution 3: Restart Computer

If the service is stuck in deletion state:

1. **Restart your computer**
2. **After restart, try installation again:**
   ```powershell
   cd tools\vofc_processor
   .\install_service.ps1
   ```

## Solution 4: Use Different Service Name

If you need to install immediately without restarting:

1. **Edit `tools/vofc_processor/install_service.ps1`:**
   ```powershell
   # Change line 5 from:
   $ServiceName = "VOFC-Processor"
   
   # To:
   $ServiceName = "VOFC-Processor-V2"
   ```

2. **Run installation:**
   ```powershell
   cd tools\vofc_processor
   .\install_service.ps1
   ```

3. **Later, after restart, you can:**
   - Remove the V2 service
   - Install with the original name

## Solution 5: Manual Registry Cleanup (Advanced)

**⚠️ WARNING: Only if you're comfortable editing the registry**

1. **Open Registry Editor:**
   - Press `Windows Key + R`
   - Type: `regedit`
   - Press Enter

2. **Navigate to:**
   ```
   HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\VOFC-Processor
   ```

3. **If the key exists:**
   - Right-click the `VOFC-Processor` key
   - Select **Delete**
   - Confirm deletion

4. **Restart computer** (required after registry edit)

5. **Install service:**
   ```powershell
   cd tools\vofc_processor
   .\install_service.ps1
   ```

## Verification

After using any solution, verify the service is gone:

```powershell
# Check via NSSM
nssm status VOFC-Processor

# Check via Windows Service Control
sc.exe query VOFC-Processor

# Both should show "does not exist" or error
```

## Prevention

To avoid this issue in the future:

1. **Always stop service before removing:**
   ```powershell
   nssm stop VOFC-Processor
   Start-Sleep -Seconds 3
   nssm remove VOFC-Processor confirm
   ```

2. **Wait 10-15 seconds** after removal before installing new service

3. **Use the migration script** which handles this automatically:
   ```powershell
   .\scripts\migrate-services.ps1
   ```

## Quick Reference

### Check Service Status
```powershell
nssm status VOFC-Processor
sc.exe query VOFC-Processor
```

### Force Remove Service
```powershell
nssm stop VOFC-Processor
Start-Sleep -Seconds 3
nssm remove VOFC-Processor confirm
sc.exe delete VOFC-Processor
Start-Sleep -Seconds 5
```

### Wait and Check
```powershell
# Wait 30 seconds
Start-Sleep -Seconds 30

# Check if gone
nssm status VOFC-Processor
```

