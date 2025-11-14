# Cleanup Duplicate Flask Services
# Removes VOFC-Flask and PSA-Flask, keeps only vofc-flask (lowercase)
# Run this script as Administrator

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup Duplicate Flask Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Services to check and remove (duplicates)
$duplicateServices = @("VOFC-Flask", "PSA-Flask")

# Service to keep
$keepService = "vofc-flask"

Write-Host "Checking for duplicate Flask services..." -ForegroundColor Cyan
Write-Host ""

# Check if the service we want to keep exists
$keepExists = $false
try {
    $result = sc query $keepService 2>&1
    if ($LASTEXITCODE -eq 0) {
        $keepExists = $true
        Write-Host "✓ $keepService exists (will keep this one)" -ForegroundColor Green
    } else {
        Write-Host "⚠ $keepService does not exist" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ $keepService does not exist" -ForegroundColor Yellow
}

Write-Host ""

# Remove duplicate services
foreach ($serviceName in $duplicateServices) {
    Write-Host "Checking $serviceName..." -ForegroundColor Cyan
    try {
        $result = sc query $serviceName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Found duplicate service: $serviceName" -ForegroundColor Yellow
            
            # Stop the service first
            Write-Host "  Stopping service..." -ForegroundColor Yellow
            nssm stop $serviceName 2>&1 | Out-Null
            Start-Sleep -Seconds 2
            
            # Remove the service
            Write-Host "  Removing service..." -ForegroundColor Yellow
            nssm remove $serviceName confirm 2>&1 | Out-Null
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ Removed $serviceName" -ForegroundColor Green
            } else {
                Write-Host "  ⚠ Failed to remove $serviceName (may need manual removal)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "  ✓ $serviceName does not exist (no action needed)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "  ✓ $serviceName does not exist (no action needed)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Verify final state
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Final Service Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$allServices = @("vofc-flask", "VOFC-Flask", "PSA-Flask")
foreach ($serviceName in $allServices) {
    try {
        $result = sc query $serviceName 2>&1
        if ($LASTEXITCODE -eq 0) {
            $status = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ($status) {
                $color = if ($serviceName -eq "vofc-flask") { "Green" } else { "Red" }
                Write-Host "  $serviceName : $($status.Status)" -ForegroundColor $color
            }
        }
    } catch {
        # Service doesn't exist, which is fine
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Cleanup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Only 'vofc-flask' (lowercase) should remain." -ForegroundColor Cyan
Write-Host ""

