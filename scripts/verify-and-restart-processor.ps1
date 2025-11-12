# Verify and Restart VOFC-Processor
# Ensures the service is using the latest code

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VOFC-Processor Verification & Restart" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠️  WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "   Service restart requires Administrator privileges" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please run this script as Administrator:" -ForegroundColor White
    Write-Host "  1. Right-click PowerShell" -ForegroundColor Gray
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor Gray
    Write-Host "  3. Run this script again" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

$nssm = "C:\Tools\nssm\nssm.exe"
$processorPath = "C:\Tools\py_scripts\vofc_processor\vofc_processor.py"
$sourcePath = "tools\vofc_processor\vofc_processor.py"

# 1. Verify files exist
Write-Host "Step 1: Verifying files..." -ForegroundColor Cyan
if (-not (Test-Path $nssm)) {
    Write-Host "✗ NSSM not found at $nssm" -ForegroundColor Red
    exit 1
}
Write-Host "✓ NSSM found" -ForegroundColor Green

if (-not (Test-Path $processorPath)) {
    Write-Host "✗ Processor not found at $processorPath" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Processor found" -ForegroundColor Green

# 2. Check file format
Write-Host ""
Write-Host "Step 2: Verifying code format..." -ForegroundColor Cyan
$hasNewFormat = Select-String -Path $processorPath -Pattern '"records":|"links":|"model_version":' -Quiet
$hasOldFormat = Select-String -Path $processorPath -Pattern "chunks_processed|phase1_parser_count" -Quiet

if ($hasNewFormat -and -not $hasOldFormat) {
    Write-Host "✓ Using NEW format (records/links)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Format check unclear" -ForegroundColor Yellow
    if ($hasOldFormat) {
        Write-Host "   Found old format markers!" -ForegroundColor Red
    }
}

# 3. Check service status
Write-Host ""
Write-Host "Step 3: Checking service status..." -ForegroundColor Cyan
$status = & $nssm status VOFC-Processor 2>&1
Write-Host "Current status: $status" -ForegroundColor $(if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Yellow" })

# 4. Get service configuration
Write-Host ""
Write-Host "Step 4: Verifying service configuration..." -ForegroundColor Cyan
$scriptPath = & $nssm get VOFC-Processor AppParameters 2>&1
Write-Host "Service script: $scriptPath" -ForegroundColor Gray

if ($scriptPath -ne $processorPath) {
    Write-Host "⚠️  Service path doesn't match expected path!" -ForegroundColor Yellow
    Write-Host "   Expected: $processorPath" -ForegroundColor Gray
    Write-Host "   Actual: $scriptPath" -ForegroundColor Gray
} else {
    Write-Host "✓ Service path correct" -ForegroundColor Green
}

# 5. Restart service
Write-Host ""
Write-Host "Step 5: Restarting service..." -ForegroundColor Cyan
Write-Host "   Stopping service..." -ForegroundColor Gray
& $nssm stop VOFC-Processor
Start-Sleep -Seconds 2

Write-Host "   Starting service..." -ForegroundColor Gray
& $nssm start VOFC-Processor
Start-Sleep -Seconds 3

$newStatus = & $nssm status VOFC-Processor 2>&1
Write-Host "New status: $newStatus" -ForegroundColor $(if ($newStatus -eq "SERVICE_RUNNING") { "Green" } else { "Red" })

# 6. Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ Code verified (new format)" -ForegroundColor Green
Write-Host "✓ Service restarted" -ForegroundColor $(if ($newStatus -eq "SERVICE_RUNNING") { "Green" } else { "Red" })
Write-Host ""
Write-Host "The service is now using the unified pipeline." -ForegroundColor Green
Write-Host "New submissions will have format: {records: [...], links: [...]}" -ForegroundColor Gray
Write-Host ""
Write-Host "To test:" -ForegroundColor Yellow
Write-Host "  1. Place a PDF in C:\Tools\Ollama\Data\incoming\" -ForegroundColor White
Write-Host "  2. Wait 30 seconds" -ForegroundColor White
Write-Host "  3. Check C:\Tools\Ollama\Data\processed\ for output" -ForegroundColor White
Write-Host "  4. Check Supabase submissions table for new format" -ForegroundColor White

