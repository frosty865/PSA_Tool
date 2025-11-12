# Fix Paused Service
# Handles SERVICE_PAUSED state by stopping and restarting the service

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
Write-Host "Fixing Paused Service: $ServiceName" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check current status
Write-Host "Step 1: Checking service status..." -ForegroundColor Yellow
$status = nssm status $ServiceName 2>&1
Write-Host "  Current status: $status" -ForegroundColor Gray

if ($status -eq "SERVICE_RUNNING") {
    Write-Host "  ✓ Service is already running" -ForegroundColor Green
    exit 0
}

# Step 2: Handle paused state - resume first, then stop
Write-Host ""
Write-Host "Step 2: Handling paused state..." -ForegroundColor Yellow
if ($status -eq "SERVICE_PAUSED") {
    Write-Host "  Service is paused - resuming first..." -ForegroundColor Yellow
    try {
        $resumeResult = sc.exe continue $ServiceName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Resume command sent" -ForegroundColor Green
            Start-Sleep -Seconds 2
        } else {
            Write-Host "  ⚠️  Resume failed, trying stop directly..." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠️  Resume error: $_" -ForegroundColor Yellow
    }
}

# Step 3: Stop the service
Write-Host ""
Write-Host "Step 3: Stopping service..." -ForegroundColor Yellow
try {
    # Try nssm stop first
    $stopResult = nssm stop $ServiceName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Stop command sent via nssm" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  nssm stop failed, trying sc.exe..." -ForegroundColor Yellow
        sc.exe stop $ServiceName 2>&1 | Out-Null
        Write-Host "  ✓ Stop command sent via sc.exe" -ForegroundColor Green
    }
    
    # Wait for service to stop
    $waited = 0
    $maxWait = 30
    while ($waited -lt $maxWait) {
        Start-Sleep -Seconds 2
        $waited += 2
        $currentStatus = nssm status $ServiceName 2>&1
        if ($currentStatus -eq "SERVICE_STOPPED" -or $currentStatus -match "not exist") {
            Write-Host "  ✓ Service stopped after $waited seconds" -ForegroundColor Green
            break
        }
        Write-Host "  Waiting for stop... ($waited/$maxWait seconds) - Status: $currentStatus" -ForegroundColor Gray
    }
    
    if ($waited -ge $maxWait) {
        Write-Host "  ⚠️  Service did not stop within $maxWait seconds" -ForegroundColor Yellow
        Write-Host "  Current status: $(nssm status $ServiceName 2>&1)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠️  Error stopping service: $_" -ForegroundColor Yellow
}

# Step 4: Verify stopped
Write-Host ""
Write-Host "Step 4: Verifying service is stopped..." -ForegroundColor Yellow
$finalStatus = nssm status $ServiceName 2>&1
if ($finalStatus -eq "SERVICE_STOPPED") {
    Write-Host "  ✓ Service is stopped" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Service status: $finalStatus" -ForegroundColor Yellow
    Write-Host "  Will attempt to start anyway..." -ForegroundColor Yellow
}

# Step 5: Start the service
Write-Host ""
Write-Host "Step 5: Starting service..." -ForegroundColor Yellow
try {
    nssm start $ServiceName 2>&1 | Out-Null
    Write-Host "  ✓ Start command sent" -ForegroundColor Green
    
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
        Write-Host "  Waiting for start... ($waited/$maxWait seconds)" -ForegroundColor Gray
    }
    
    $finalStatus = nssm status $ServiceName 2>&1
    if ($finalStatus -eq "SERVICE_RUNNING") {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "Service Fixed Successfully!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Service Name: $ServiceName" -ForegroundColor White
        Write-Host "Status: $finalStatus" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "Service Status: $finalStatus" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "The service may need manual intervention." -ForegroundColor Yellow
        Write-Host "Check logs: C:\Tools\Ollama\Data\logs\" -ForegroundColor Yellow
        Write-Host ""
    }
} catch {
    Write-Host "  ✗ Error starting service: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Failed to Start Service" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check:" -ForegroundColor Yellow
    Write-Host "  1. Service configuration: nssm edit $ServiceName" -ForegroundColor Yellow
    Write-Host "  2. Service logs: C:\Tools\Ollama\Data\logs\" -ForegroundColor Yellow
    Write-Host "  3. Python path: nssm get $ServiceName Application" -ForegroundColor Yellow
    Write-Host "  4. Script path: nssm get $ServiceName AppParameters" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

