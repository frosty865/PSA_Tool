<# 
VOFC Dependency Repair Tool
Fixes corrupt, stale, or phantom Windows service dependency entries
and rebuilds the correct VOFC service chain.

Safe to run multiple times.
#>

Write-Host "=== VOFC Dependency Repair Tool ===" -ForegroundColor Cyan

# --- CONFIGURE YOUR SERVICE NAMES ---
$services = @{
    "VOFC-Ollama"      = @()                         # Top-level service
    "VOFC-Processor"   = @("VOFC-Ollama")
    "VOFC-ModelManager"= @("VOFC-Processor")
    "VOFC-AutoRetrain" = @("VOFC-ModelManager")
    "VOFC-Flask"       = @("VOFC-Processor")
    "VOFC-Tunnel"      = @("VOFC-Flask")
}

# Backup location
$backupPath = "C:\VOFC_DependencyBackup"
if (!(Test-Path $backupPath)) {
    New-Item -ItemType Directory -Path $backupPath | Out-Null
}

# Function: Backup registry keys
function Backup-ServiceKey($svcName) {
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$svcName"
    $exportPath = "$backupPath\$svcName.reg"

    if (Test-Path $regPath) {
        reg export "HKLM\SYSTEM\CurrentControlSet\Services\$svcName" $exportPath /y | Out-Null
        Write-Host "Backed up $svcName to $exportPath"
    }
}

# Function: Clear corrupt dependency keys
function Clear-Dependencies($svcName) {
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$svcName"
    $depKey = "$regPath\DependOnService"

    if (Test-Path $depKey) {
        Write-Host "  Removing stale dependency key from $svcName" -ForegroundColor Yellow
        reg delete "HKLM\SYSTEM\CurrentControlSet\Services\$svcName" /v DependOnService /f | Out-Null
    }
}

# Function: Apply correct dependencies
function Apply-Dependencies($svcName, $deps) {
    if ($deps.Count -eq 0) {
        Write-Host "  $svcName: No dependencies to apply (top-level)" -ForegroundColor Green
        return
    }

    $depString = ($deps -join "/")
    Write-Host "  Setting dependencies for $svcName → $depString" -ForegroundColor Green

    sc.exe config $svcName depend= $depString | Out-Null
}

# --- START REPAIR PROCESS ---
Write-Host "`nBacking up service registry keys..." -ForegroundColor Cyan
foreach ($svc in $services.Keys) {
    Backup-ServiceKey $svc
}

Write-Host "`nDetecting and clearing corrupt dependency keys..." -ForegroundColor Cyan
foreach ($svc in $services.Keys) {
    Clear-Dependencies $svc
}

Write-Host "`nRebuilding correct VOFC dependency chain..." -ForegroundColor Cyan
foreach ($svc in $services.Keys) {
    Apply-Dependencies $svc $services[$svc]
}

Write-Host "`nVerifying rebuilt dependency tree..." -ForegroundColor Cyan
foreach ($svc in $services.Keys) {
    Write-Host "Dependencies for $svc:"
    sc.exe enumdepend $svc
    Write-Host ""
}

Write-Host "=== VOFC Dependency Repair Complete ===" -ForegroundColor Cyan
Write-Host "You may now stop/start VOFC-Ollama safely." -ForegroundColor Green
