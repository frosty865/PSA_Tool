# VOFC Services Management Script
# Quick reference for starting/stopping/checking services

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status", "list")]
    [string]$Action = "status",
    
    [Parameter(Position=1)]
    [string]$ServiceName = ""
)

$nssm = "C:\Tools\nssm\nssm.exe"
if (-not (Test-Path $nssm)) {
    Write-Host "NSSM not found at $nssm" -ForegroundColor Red
    exit 1
}

# Required services
$requiredServices = @(
    "VOFC-Ollama",
    "VOFC-Processor",
    "VOFC-Flask"
)

# Optional services
$optionalServices = @(
    "VOFC-Tunnel",
    "VOFC-ModelManager",
    "VOFC-AutoRetrain"
)

# All services
$allServices = $requiredServices + $optionalServices

function Show-Status {
    param([string]$ServiceName)
    $status = & $nssm status $ServiceName 2>&1
    $color = switch ($status) {
        "SERVICE_RUNNING" { "Green" }
        "SERVICE_STOPPED" { "Yellow" }
        "SERVICE_PAUSED" { "Red" }
        default { "Gray" }
    }
    Write-Host "$ServiceName : $status" -ForegroundColor $color
}

function Start-Service {
    param([string]$ServiceName)
    Write-Host "Starting $ServiceName..." -ForegroundColor Cyan
    & $nssm start $ServiceName
    Start-Sleep -Seconds 2
    Show-Status $ServiceName
}

function Stop-Service {
    param([string]$ServiceName)
    Write-Host "Stopping $ServiceName..." -ForegroundColor Cyan
    & $nssm stop $ServiceName
    Start-Sleep -Seconds 2
    Show-Status $ServiceName
}

function Restart-Service {
    param([string]$ServiceName)
    Write-Host "Restarting $ServiceName..." -ForegroundColor Cyan
    & $nssm stop $ServiceName
    Start-Sleep -Seconds 2
    & $nssm start $ServiceName
    Start-Sleep -Seconds 2
    Show-Status $ServiceName
}

# Main logic
switch ($Action) {
    "list" {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "VOFC Services" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Required Services:" -ForegroundColor Yellow
        foreach ($svc in $requiredServices) {
            Show-Status $svc
        }
        Write-Host ""
        Write-Host "Optional Services:" -ForegroundColor Gray
        foreach ($svc in $optionalServices) {
            Show-Status $svc
        }
    }
    
    "status" {
        if ($ServiceName) {
            Show-Status $ServiceName
        } else {
            Write-Host "Service Status:" -ForegroundColor Cyan
            Write-Host ""
            foreach ($svc in $allServices) {
                Show-Status $svc
            }
        }
    }
    
    "start" {
        if ($ServiceName) {
            Start-Service $ServiceName
        } else {
            Write-Host "Starting all required services..." -ForegroundColor Cyan
            foreach ($svc in $requiredServices) {
                Start-Service $svc
            }
        }
    }
    
    "stop" {
        if ($ServiceName) {
            Stop-Service $ServiceName
        } else {
            Write-Host "Stopping all services..." -ForegroundColor Cyan
            foreach ($svc in $allServices) {
                Stop-Service $svc
            }
        }
    }
    
    "restart" {
        if ($ServiceName) {
            Restart-Service $ServiceName
        } else {
            Write-Host "Restarting all required services..." -ForegroundColor Cyan
            foreach ($svc in $requiredServices) {
                Restart-Service $svc
            }
        }
    }
}

Write-Host ""
Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  .\scripts\manage-services.ps1 status              # Check all services" -ForegroundColor Gray
Write-Host "  .\scripts\manage-services.ps1 start               # Start required services" -ForegroundColor Gray
Write-Host "  .\scripts\manage-services.ps1 restart VOFC-Processor  # Restart specific service" -ForegroundColor Gray
Write-Host "  .\scripts\manage-services.ps1 list                # List all services" -ForegroundColor Gray

