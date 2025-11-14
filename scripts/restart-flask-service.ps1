# Restart Flask Service to Pick Up Code Changes
# Run this script as Administrator

Write-Host "Restarting VOFC Flask Service..." -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run manually:" -ForegroundColor Yellow
    Write-Host "  nssm restart vofc-flask" -ForegroundColor Cyan
    exit 1
}

$ServiceName = "vofc-flask"

# Check if service exists
$nssmPath = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssmPath)) {
    $nssmPath = "nssm"
}

$serviceStatus = & $nssmPath status $ServiceName 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Service $ServiceName not found" -ForegroundColor Red
    exit 1
}

Write-Host "Current service status: $serviceStatus" -ForegroundColor Gray
Write-Host ""

# Stop dependent services first (VOFC-Tunnel depends on Flask)
Write-Host "Stopping dependent services first..." -ForegroundColor Yellow
$dependentServices = @("VOFC-Tunnel")

foreach ($depService in $dependentServices) {
    Write-Host "  Stopping $depService..." -ForegroundColor Gray
    & $nssmPath stop $depService 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ $depService stopped" -ForegroundColor Green
        Start-Sleep -Seconds 2
    } else {
        Write-Host "  ⚠ $depService may already be stopped" -ForegroundColor Yellow
    }
}

Write-Host ""

# Restart service
Write-Host "Restarting Flask service..." -ForegroundColor Yellow
& $nssmPath restart $ServiceName

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Service restarted successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting 5 seconds for service to fully start..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Check status
    $newStatus = & $nssmPath status $ServiceName
    Write-Host "New service status: $newStatus" -ForegroundColor Gray
    
    if ($newStatus -eq "SERVICE_RUNNING") {
        Write-Host ""
        Write-Host "✅ Flask service is running!" -ForegroundColor Green
        Write-Host ""
        
        # Restart dependent services
        Write-Host "Restarting dependent services..." -ForegroundColor Yellow
        foreach ($depService in $dependentServices) {
            Write-Host "  Starting $depService..." -ForegroundColor Gray
            & $nssmPath start $depService 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ $depService started" -ForegroundColor Green
                Start-Sleep -Seconds 2
            } else {
                Write-Host "  ⚠ Failed to start $depService" -ForegroundColor Yellow
            }
        }
        
        Write-Host ""
        Write-Host "✅ All services restarted successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "The health endpoint should now return watcher status." -ForegroundColor Cyan
        Write-Host "Test with: curl http://localhost:8080/api/system/health" -ForegroundColor Gray
    } else {
        Write-Host ""
        Write-Host "⚠️  Service status: $newStatus" -ForegroundColor Yellow
        Write-Host "Check logs: C:\Tools\Ollama\Data\logs\vofc_processor_*.log" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "❌ Failed to restart service" -ForegroundColor Red
    Write-Host "Check service logs for errors" -ForegroundColor Yellow
    exit 1
}

