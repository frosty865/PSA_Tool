# start-services-ordered.ps1
# Starts all VOFC services in the correct order
# Run as Administrator

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting VOFC Services in Order" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

# Service startup order (dependencies first)
$startupOrder = @(
    "VOFC-Ollama",        # 1. Core infrastructure
    "VOFC-Flask",         # 2. API server (depends on Ollama)
    "VOFC-Processor",     # 3. Processing service (depends on Ollama)
    "VOFC-ModelManager",  # 4. Model management (depends on Ollama)
    "VOFC-AutoRetrain",   # 5. Auto-retrain (depends on Ollama)
    "VOFC-Tunnel"         # 6. Tunnel (depends on Flask)
)

# Delays between service starts (in seconds)
$startupDelays = @{
    "VOFC-Ollama" = 0
    "VOFC-Flask" = 5
    "VOFC-Processor" = 3
    "VOFC-ModelManager" = 3
    "VOFC-AutoRetrain" = 3
    "VOFC-Tunnel" = 5
}

Write-Host "Starting services in order..." -ForegroundColor Yellow
Write-Host ""

$successCount = 0
$failCount = 0
$skippedCount = 0

foreach ($service in $startupOrder) {
    Write-Host "[$service]" -ForegroundColor Cyan
    
    # Check if service exists
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ⚠️  Service not installed, skipping" -ForegroundColor Yellow
        $skippedCount++
        continue
    }
    
    # Check current status
    if ($status -eq "SERVICE_RUNNING") {
        Write-Host "  ✓ Already running" -ForegroundColor Green
        $successCount++
    } elseif ($status -eq "SERVICE_PAUSED") {
        Write-Host "  ⚠️  Service is paused, resuming..." -ForegroundColor Yellow
        nssm continue $service 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        $newStatus = nssm status $service 2>&1
        if ($newStatus -eq "SERVICE_RUNNING") {
            Write-Host "  ✓ Resumed successfully" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  ✗ Failed to resume" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "  Starting..." -ForegroundColor Gray
        nssm start $service 2>&1 | Out-Null
        
        # Wait a bit and check status
        Start-Sleep -Seconds 2
        $newStatus = nssm status $service 2>&1
        
        if ($newStatus -eq "SERVICE_RUNNING") {
            Write-Host "  ✓ Started successfully" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "  ✗ Failed to start (status: $newStatus)" -ForegroundColor Red
            $failCount++
        }
    }
    
    # Wait before starting next service
    $delay = $startupDelays[$service]
    if ($delay -gt 0) {
        Write-Host "  Waiting ${delay}s for dependencies..." -ForegroundColor DarkGray
        Start-Sleep -Seconds $delay
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Startup Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results:" -ForegroundColor White
Write-Host "  Started: $successCount" -ForegroundColor Green
Write-Host "  Failed: $failCount" -ForegroundColor $(if ($failCount -gt 0) { 'Red' } else { 'Gray' })
Write-Host "  Skipped: $skippedCount" -ForegroundColor $(if ($skippedCount -gt 0) { 'Yellow' } else { 'Gray' })
Write-Host ""

# Show final status
Write-Host "Service Status:" -ForegroundColor Yellow
foreach ($service in $startupOrder) {
    $status = nssm status $service 2>&1
    if ($LASTEXITCODE -eq 0) {
        $color = if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Yellow" }
        Write-Host "  $service : $status" -ForegroundColor $color
    }
}
Write-Host ""

