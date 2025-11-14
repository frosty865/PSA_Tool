# PowerShell script to restart services with dependency management
# Usage: .\restart-services-with-deps.ps1 -ServiceName "ollama"
#        .\restart-services-with-deps.ps1 -ServiceName "vofc-flask"
#        .\restart-services-with-deps.ps1 -All

param(
    [Parameter(Mandatory=$false)]
    [string]$ServiceName,
    
    [Parameter(Mandatory=$false)]
    [switch]$All
)

# Service dependencies
$ServiceDependencies = @{
    'ollama' = @('vofc-flask', 'VOFC-Processor', 'VOFC-ModelManager')
    'vofc-flask' = @('VOFC-Tunnel')
    'VOFC-Processor' = @()
    'VOFC-ModelManager' = @()
    'VOFC-Tunnel' = @()
}

# Service startup order (dependencies first)
$StartupOrder = @(
    'ollama',
    'VOFC-Processor',
    'VOFC-ModelManager',
    'vofc-flask',
    'VOFC-Tunnel'
)

# Service shutdown order (reverse - dependents first)
$ShutdownOrder = $StartupOrder | Sort-Object -Descending

# Service name variations
$ServiceNameVariants = @{
    'ollama' = @('Ollama', 'ollama')
    'vofc-flask' = @('vofc-flask', 'VOFC-Flask', 'PSA-Flask')
    'VOFC-Processor' = @('VOFC-Processor', 'vofc-processor', 'PSA-Processor')
    'VOFC-ModelManager' = @('VOFC-ModelManager', 'vofc-modelmanager', 'VOFC-Model-Manager', 'PSA-ModelManager', 'ModelManager')
    'VOFC-Tunnel' = @('VOFC-Tunnel', 'vofc-tunnel', 'VOFC-Tunnel-Service', 'PSA-Tunnel', 'Cloudflare-Tunnel')
}

function Find-ServiceName {
    param([string]$CanonicalName)
    
    $variants = $ServiceNameVariants[$CanonicalName]
    if (-not $variants) {
        $variants = @($CanonicalName)
    }
    
    foreach ($variant in $variants) {
        try {
            $result = sc.exe query $variant 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Found service $CanonicalName as $variant" -ForegroundColor Green
                return $variant
            }
        } catch {
            continue
        }
    }
    
    Write-Warning "Service $CanonicalName not found with any variant"
    return $null
}

function Stop-ServiceWithNSSM {
    param([string]$ServiceName)
    
    $actualName = Find-ServiceName -CanonicalName $ServiceName
    if (-not $actualName) {
        return $false, "Service $ServiceName not found"
    }
    
    try {
        Write-Host "Stopping $actualName..." -ForegroundColor Yellow
        $result = nssm.exe stop $actualName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $actualName stopped" -ForegroundColor Green
            return $true, "Service $actualName stopped"
        } else {
            $errorMsg = $result -join "`n"
            Write-Host "  ✗ Failed to stop $actualName : $errorMsg" -ForegroundColor Red
            return $false, "Failed to stop $actualName : $errorMsg"
        }
    } catch {
        Write-Host "  ✗ Error stopping $actualName : $_" -ForegroundColor Red
        return $false, "Error stopping $actualName : $_"
    }
}

function Start-ServiceWithNSSM {
    param([string]$ServiceName)
    
    $actualName = Find-ServiceName -CanonicalName $ServiceName
    if (-not $actualName) {
        return $false, "Service $ServiceName not found"
    }
    
    try {
        Write-Host "Starting $actualName..." -ForegroundColor Yellow
        $result = nssm.exe start $actualName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ $actualName started" -ForegroundColor Green
            return $true, "Service $actualName started"
        } else {
            $errorMsg = $result -join "`n"
            Write-Host "  ✗ Failed to start $actualName : $errorMsg" -ForegroundColor Red
            return $false, "Failed to start $actualName : $errorMsg"
        }
    } catch {
        Write-Host "  ✗ Error starting $actualName : $_" -ForegroundColor Red
        return $false, "Error starting $actualName : $_"
    }
}

function Restart-ServiceWithDependencies {
    param([string]$ServiceName)
    
    Write-Host "`n=== Restarting $ServiceName with dependencies ===" -ForegroundColor Cyan
    
    # Get dependent services
    $dependents = $ServiceDependencies[$ServiceName]
    if (-not $dependents) {
        $dependents = @()
    }
    
    if ($dependents.Count -eq 0) {
        Write-Host "No dependencies for $ServiceName - restarting directly" -ForegroundColor Yellow
        $actualName = Find-ServiceName -CanonicalName $ServiceName
        if ($actualName) {
            Write-Host "Restarting $actualName..." -ForegroundColor Yellow
            nssm.exe restart $actualName
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ $actualName restarted" -ForegroundColor Green
            } else {
                Write-Host "  ✗ Failed to restart $actualName" -ForegroundColor Red
            }
        }
        return
    }
    
    # Step 1: Stop dependent services first (in shutdown order)
    $servicesToStop = $dependents + $ServiceName
    $servicesToStopSorted = @()
    foreach ($svc in $ShutdownOrder) {
        if ($servicesToStop -contains $svc) {
            $servicesToStopSorted += $svc
        }
    }
    # Add any services not in ShutdownOrder
    foreach ($svc in $servicesToStop) {
        if ($servicesToStopSorted -notcontains $svc) {
            $servicesToStopSorted += $svc
        }
    }
    
    Write-Host "`nStopping services in order: $($servicesToStopSorted -join ', ')" -ForegroundColor Yellow
    foreach ($svc in $servicesToStopSorted) {
        Stop-ServiceWithNSSM -ServiceName $svc | Out-Null
        Start-Sleep -Seconds 2  # Brief pause between stops
    }
    
    # Step 2: Start services in startup order
    $servicesToStart = @($ServiceName) + $dependents
    $servicesToStartSorted = @()
    foreach ($svc in $StartupOrder) {
        if ($servicesToStart -contains $svc) {
            $servicesToStartSorted += $svc
        }
    }
    # Add any services not in StartupOrder
    foreach ($svc in $servicesToStart) {
        if ($servicesToStartSorted -notcontains $svc) {
            $servicesToStartSorted += $svc
        }
    }
    
    Write-Host "`nStarting services in order: $($servicesToStartSorted -join ', ')" -ForegroundColor Yellow
    foreach ($svc in $servicesToStartSorted) {
        Start-ServiceWithNSSM -ServiceName $svc | Out-Null
        Start-Sleep -Seconds 3  # Brief pause between starts
    }
    
    Write-Host "`n=== Restart complete ===" -ForegroundColor Green
}

function Restart-AllServices {
    Write-Host "`n=== Restarting all services in dependency order ===" -ForegroundColor Cyan
    
    # Step 1: Stop all services in shutdown order
    Write-Host "`nStopping all services..." -ForegroundColor Yellow
    foreach ($svc in $ShutdownOrder) {
        Stop-ServiceWithNSSM -ServiceName $svc | Out-Null
        Start-Sleep -Seconds 2
    }
    
    # Step 2: Start all services in startup order
    Write-Host "`nStarting all services..." -ForegroundColor Yellow
    foreach ($svc in $StartupOrder) {
        Start-ServiceWithNSSM -ServiceName $svc | Out-Null
        Start-Sleep -Seconds 3
    }
    
    Write-Host "`n=== All services restarted ===" -ForegroundColor Green
}

# Main execution
if ($All) {
    Restart-AllServices
} elseif ($ServiceName) {
    Restart-ServiceWithDependencies -ServiceName $ServiceName
} else {
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\restart-services-with-deps.ps1 -ServiceName 'ollama'" -ForegroundColor Cyan
    Write-Host "  .\restart-services-with-deps.ps1 -ServiceName 'vofc-flask'" -ForegroundColor Cyan
    Write-Host "  .\restart-services-with-deps.ps1 -All" -ForegroundColor Cyan
}

