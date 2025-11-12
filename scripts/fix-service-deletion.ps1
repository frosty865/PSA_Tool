# Fix Service Deletion Issue
# Handles "service has been marked for deletion" error

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing Service Deletion Issue" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$serviceName = "VOFC-Processor"

Write-Host "Service: $serviceName" -ForegroundColor White
Write-Host ""

# Step 1: Check current status
Write-Host "Step 1: Checking service status..." -ForegroundColor Yellow
$status = nssm status $serviceName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Service exists with status:" -ForegroundColor White
    Write-Host $status -ForegroundColor Gray
    
    # Try to stop it first
    Write-Host "  Attempting to stop service..." -ForegroundColor Gray
    nssm stop $serviceName | Out-Null
    Start-Sleep -Seconds 3
} else {
    Write-Host "  Service does not exist or is marked for deletion" -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Force remove if it exists
Write-Host "Step 2: Force removing service (if exists)..." -ForegroundColor Yellow
try {
    # Try to remove via NSSM
    nssm remove $serviceName confirm 2>&1 | Out-Null
    
    # Also try via sc.exe (Windows Service Control)
    $scResult = sc.exe delete $serviceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Service removal command sent" -ForegroundColor Green
    } else {
        Write-Host "  Service removal attempted (may already be gone)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  Removal attempted" -ForegroundColor Gray
}
Write-Host ""

# Step 3: Wait for Windows to clean up
Write-Host "Step 3: Waiting for Windows to clean up service registry..." -ForegroundColor Yellow
Write-Host "  This may take 10-30 seconds..." -ForegroundColor Gray

$maxWait = 30
$waited = 0
$cleaned = $false

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 2
    $waited += 2
    
    # Check if service still exists
    $checkStatus = nssm status $serviceName 2>&1
    if ($LASTEXITCODE -ne 0) {
        # Service is gone - check via sc.exe too
        $scCheck = sc.exe query $serviceName 2>&1
        if ($scCheck -match "does not exist" -or $LASTEXITCODE -ne 0) {
            Write-Host "  ✓ Service fully removed after $waited seconds" -ForegroundColor Green
            $cleaned = $true
            break
        }
    }
    
    Write-Host "  Waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
}

if (-not $cleaned) {
    Write-Host "  ⚠️  Service may still be marked for deletion" -ForegroundColor Yellow
    Write-Host "  You may need to restart the computer" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Alternative: Use a different service name temporarily" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "  Continue anyway? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "  Aborted. Please restart your computer and try again." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host ""

# Step 4: Verify service is gone
Write-Host "Step 4: Verifying service is removed..." -ForegroundColor Yellow
$finalCheck = nssm status $serviceName 2>&1
$scFinalCheck = sc.exe query $serviceName 2>&1

if ($LASTEXITCODE -ne 0 -and ($scFinalCheck -match "does not exist" -or $LASTEXITCODE -ne 0)) {
    Write-Host "  ✓ Service is fully removed" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Ready to Install!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now run the installation script:" -ForegroundColor White
    Write-Host "  cd tools\vofc_processor" -ForegroundColor Gray
    Write-Host "  .\install_service.ps1" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "  ⚠️  Service may still exist in registry" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Service Still Marked for Deletion" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  1. Restart your computer (recommended)" -ForegroundColor White
    Write-Host "  2. Wait 5-10 minutes and try again" -ForegroundColor White
    Write-Host "  3. Use a different service name (e.g., VOFC-Processor-V2)" -ForegroundColor White
    Write-Host ""
    Write-Host "To use a different service name, edit install_service.ps1:" -ForegroundColor Gray
    Write-Host "  Change: `$ServiceName = `"VOFC-Processor`"" -ForegroundColor Gray
    Write-Host "  To:     `$ServiceName = `"VOFC-Processor-V2`"" -ForegroundColor Gray
    Write-Host ""
}

