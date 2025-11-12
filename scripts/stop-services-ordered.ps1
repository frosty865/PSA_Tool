# stop-services-ordered.ps1
# Stops all VOFC services in reverse dependency order
# Run as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stopping VOFC Services in Order" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

# Service stop order (reverse of startup - dependents first)
$stopOrder = @(
    "VOFC-Tunnel",         # 1. Stop dependents first
    "VOFC-AutoRetrain",    # 2.
    "VOFC-ModelManager",   # 3.
    "VOFC-Processor",      # 4.
    "VOFC-Flask",          # 5.
    "VOFC-Ollama"          # 6. Stop core services last
)

Write-Host "Stopping services in reverse dependency order..." -ForegroundColor Yellow
Write-Host ""

$stoppedCount = 0
$failCount = 0
$skippedCount = 0

foreach ($service in $stopOrder) {
    Write-Host "[$service]" -ForegroundColor Cyan
    
    # Check if service exists
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Service not installed, skipping" -ForegroundColor Yellow
        $skippedCount++
        continue
    }
    
    # Check current status
    if ($status -eq "SERVICE_STOPPED") {
        Write-Host "  ✓ Already stopped" -ForegroundColor Gray
        $stoppedCount++
    } else {
        Write-Host "  Stopping..." -ForegroundColor Gray
        nssm stop $service 2>&1 | Out-Null
        
        # Wait a bit and check status
        Start-Sleep -Seconds 3
        $newStatus = nssm status $service 2>&1
        
        if ($newStatus -eq "SERVICE_STOPPED") {
            Write-Host "  ✓ Stopped successfully" -ForegroundColor Green
            $stoppedCount++
        } else {
            Write-Host "  ✗ Failed to stop (status: $newStatus)" -ForegroundColor Red
            $failCount++
        }
    }
    
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stop Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results:" -ForegroundColor White
Write-Host "  Stopped: $stoppedCount" -ForegroundColor Green
Write-Host "  Failed: $failCount" -ForegroundColor $(if ($failCount -gt 0) { 'Red' } else { 'Gray' })
Write-Host "  Skipped: $skippedCount" -ForegroundColor $(if ($skippedCount -gt 0) { 'Yellow' } else { 'Gray' })
Write-Host ""

