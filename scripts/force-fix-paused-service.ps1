# Force Fix Paused Service
# More aggressive approach to fix stuck paused services
# MUST be run as Administrator

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceName
)

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor Yellow
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "  3. Run this script again" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Force Fixing Paused Service: $ServiceName" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check current status
Write-Host "Step 1: Checking service status..." -ForegroundColor Yellow
$status = sc.exe query $ServiceName 2>&1
$statusString = if ($status -is [Array]) { $status -join "`n" } else { $status.ToString() }
Write-Host $statusString -ForegroundColor Gray

if ($statusString -match "STATE.*1.*STOPPED") {
    Write-Host "  ✓ Service is already stopped" -ForegroundColor Green
    Write-Host "  Proceeding to start..." -ForegroundColor Yellow
} elseif ($statusString -match "STATE.*7.*PAUSED") {
    Write-Host "  ⚠️  Service is PAUSED - attempting to resume..." -ForegroundColor Yellow
    
    # Step 2: Try to resume
    Write-Host ""
    Write-Host "Step 2: Resuming service..." -ForegroundColor Yellow
    $resumeResult = sc.exe continue $ServiceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Resume command sent" -ForegroundColor Green
        Start-Sleep -Seconds 3
    } else {
        Write-Host "  ⚠️  Resume failed: $resumeResult" -ForegroundColor Yellow
    }
    
    # Step 3: Stop the service
    Write-Host ""
    Write-Host "Step 3: Stopping service..." -ForegroundColor Yellow
    $stopResult = sc.exe stop $ServiceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Stop command sent" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Stop failed: $stopResult" -ForegroundColor Yellow
    }
    
    # Wait for stop
    $waited = 0
    $maxWait = 30
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 2
        $waited += 2
        $checkStatus = sc.exe query $ServiceName 2>&1
        $checkString = if ($checkStatus -is [Array]) { $checkStatus -join "`n" } else { $checkStatus.ToString() }
        if ($checkString -match "STATE.*1.*STOPPED") {
            Write-Host "  ✓ Service stopped after $waited seconds" -ForegroundColor Green
            break
        }
        Write-Host "  Waiting for stop... ($waited/$maxWait seconds)" -ForegroundColor Gray
    }
    
    if ($waited -ge $maxWait) {
        Write-Host "  ⚠️  Service did not stop within $maxWait seconds" -ForegroundColor Yellow
        Write-Host "  Attempting force stop..." -ForegroundColor Yellow
        
        # Try to kill the process
        $processName = nssm get $ServiceName Application 2>&1
        if ($processName -match "python\.exe") {
            Write-Host "  Attempting to kill Python processes for this service..." -ForegroundColor Yellow
            Get-Process python -ErrorAction SilentlyContinue | Where-Object {
                $_.Path -like "*Tools\python*"
            } | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3
        }
    }
} else {
    Write-Host "  Service status: $statusString" -ForegroundColor Yellow
}

# Step 4: Verify stopped
Write-Host ""
Write-Host "Step 4: Verifying service is stopped..." -ForegroundColor Yellow
$finalCheck = sc.exe query $ServiceName 2>&1
$finalString = if ($finalCheck -is [Array]) { $finalCheck -join "`n" } else { $finalCheck.ToString() }
if ($finalString -match "STATE.*1.*STOPPED") {
    Write-Host "  ✓ Service is stopped" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Service status: $finalString" -ForegroundColor Yellow
    Write-Host "  Will attempt to start anyway..." -ForegroundColor Yellow
}

# Step 5: Start the service
Write-Host ""
Write-Host "Step 5: Starting service..." -ForegroundColor Yellow
try {
    $startResult = nssm start $ServiceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Start command sent" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  nssm start failed, trying sc.exe..." -ForegroundColor Yellow
        sc.exe start $ServiceName 2>&1 | Out-Null
        Write-Host "  ✓ Start command sent via sc.exe" -ForegroundColor Green
    }
    
    # Wait for service to start
    $waited = 0
    $maxWait = 30
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 2
        $waited += 2
        $currentStatus = nssm status $ServiceName 2>&1
        if ($currentStatus -eq "SERVICE_RUNNING") {
            Write-Host "  ✓ Service started after $waited seconds" -ForegroundColor Green
            break
        }
        Write-Host "  Waiting for start... ($waited/$maxWait seconds) - Status: $currentStatus" -ForegroundColor Gray
    }
    
    $finalStatus = nssm status $ServiceName 2>&1
    if ($finalStatus -eq "SERVICE_RUNNING") {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Service Fixed and Running!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Service Name: $ServiceName" -ForegroundColor White
        Write-Host "Status: $finalStatus" -ForegroundColor Green
        Write-Host ""
        Write-Host "Check logs:" -ForegroundColor Yellow
        Write-Host "  Get-Content 'C:\Tools\Ollama\Data\logs\vofc_processor*.log' -Tail 20" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "Service Status: $finalStatus" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "The service may need manual intervention." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Check:" -ForegroundColor Yellow
        Write-Host "  1. Service configuration: nssm edit $ServiceName" -ForegroundColor Cyan
        Write-Host "  2. Python path: nssm get $ServiceName Application" -ForegroundColor Cyan
        Write-Host "  3. Script path: nssm get $ServiceName AppParameters" -ForegroundColor Cyan
        Write-Host "  4. Working directory: nssm get $ServiceName AppDirectory" -ForegroundColor Cyan
        Write-Host ""
    }
} catch {
    Write-Host "  ✗ Error starting service: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Failed to Start Service" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    exit 1
}

