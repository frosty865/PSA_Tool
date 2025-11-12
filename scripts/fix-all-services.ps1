# fix-all-services.ps1
# Fixes all paused services and sets missing environment variables
# Run as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing All VOFC Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Services that need environment variables
$servicesNeedingEnv = @(
    "VOFC-ModelManager",
    "VOFC-AutoRetrain",
    "VOFC-Flask"
)

# Step 1: Fix paused services
Write-Host "Step 1: Fixing paused services..." -ForegroundColor Yellow
Write-Host ""

$pausedServices = @()
$allServices = @("VOFC-Ollama", "VOFC-Flask", "VOFC-Processor", "VOFC-ModelManager", "VOFC-AutoRetrain", "VOFC-Tunnel")

foreach ($svc in $allServices) {
    $status = nssm status $svc 2>&1
    if ($LASTEXITCODE -eq 0 -and $status -eq "SERVICE_PAUSED") {
        $pausedServices += $svc
        Write-Host "  Found paused service: $svc" -ForegroundColor Yellow
    }
}

if ($pausedServices.Count -gt 0) {
    foreach ($svc in $pausedServices) {
        Write-Host ""
        Write-Host "  Fixing $svc..." -ForegroundColor Cyan
        & "$PSScriptRoot\fix-paused-service.ps1" -ServiceName $svc
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $svc fixed" -ForegroundColor Green
        } else {
            Write-Host "  ✗ Failed to fix $svc" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  ✓ No paused services found" -ForegroundColor Green
}

Write-Host ""

# Step 2: Set environment variables
Write-Host "Step 2: Setting environment variables..." -ForegroundColor Yellow
Write-Host ""

foreach ($svc in $servicesNeedingEnv) {
    # Check if service exists
    $status = nssm status $svc 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  $svc not found, skipping..." -ForegroundColor Yellow
        continue
    }
    
    # Check if environment variables are already set
    $env = nssm get $svc AppEnvironmentExtra 2>&1
    if ($env -notmatch "not exist" -and $env -ne "") {
        Write-Host "  ✓ $svc already has environment variables set" -ForegroundColor Green
        continue
    }
    
    Write-Host "  Setting environment variables for $svc..." -ForegroundColor Cyan
    
    switch ($svc) {
        "VOFC-ModelManager" {
            & "$PSScriptRoot\set-model-manager-env.ps1" -ServiceName $svc
        }
        "VOFC-AutoRetrain" {
            & "$PSScriptRoot\set-autoretrain-env.ps1"
        }
        "VOFC-Flask" {
            Write-Host "    ⚠️  Flask environment variables may need manual configuration" -ForegroundColor Yellow
            Write-Host "    Check if Flask needs specific environment variables" -ForegroundColor Gray
        }
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ $svc environment variables set" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Failed to set environment variables for $svc" -ForegroundColor Red
    }
    Write-Host ""
}

# Step 3: Restart services that were fixed
Write-Host "Step 3: Restarting services..." -ForegroundColor Yellow
Write-Host ""

$servicesToRestart = $pausedServices + @("VOFC-ModelManager", "VOFC-AutoRetrain")

foreach ($svc in $servicesToRestart) {
    $status = nssm status $svc 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Restarting $svc..." -ForegroundColor Cyan
        nssm restart $svc 2>&1 | Out-Null
        Start-Sleep -Seconds 3
        
        $newStatus = nssm status $svc 2>&1
        if ($newStatus -eq "SERVICE_RUNNING") {
            Write-Host "  ✓ $svc is running" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  $svc status: $newStatus" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fix Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Run the check script to verify:" -ForegroundColor Yellow
Write-Host "  .\scripts\check-all-services.ps1" -ForegroundColor Cyan
Write-Host ""

