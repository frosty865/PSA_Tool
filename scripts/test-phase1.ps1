# Phase 1 Validation Script
# Run this after migration to verify everything is working

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 1 Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check service status
Write-Host "1. Checking VOFC-Processor service status..." -ForegroundColor Yellow
$status = nssm status VOFC-Processor 2>&1
if ($status -match "SERVICE_RUNNING") {
    Write-Host "   ✓ Service is running" -ForegroundColor Green
} else {
    Write-Host "   ✗ Service is not running: $status" -ForegroundColor Red
    Write-Host "   Start it with: nssm start VOFC-Processor" -ForegroundColor Yellow
}
Write-Host ""

# Check for recent processing
Write-Host "2. Checking recent processor logs..." -ForegroundColor Yellow
$logFiles = Get-ChildItem "C:\Tools\Ollama\Data\logs\vofc_processor*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($logFiles) {
    $recentLogs = Get-Content $logFiles.FullName -Tail 30 -ErrorAction SilentlyContinue
    $hasErrors = $recentLogs | Select-String -Pattern "column.*does not exist|ERROR|column.*not found" -CaseSensitive:$false
    if ($hasErrors) {
        Write-Host "   ⚠️  Found potential column errors in logs:" -ForegroundColor Yellow
        $hasErrors | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
    } else {
        Write-Host "   ✓ No column errors found in recent logs" -ForegroundColor Green
    }
    
    $hasSuccess = $recentLogs | Select-String -Pattern "Inserted new vulnerability|Uploaded to Supabase|Processing complete" -CaseSensitive:$false
    if ($hasSuccess) {
        Write-Host "   ✓ Recent successful processing found" -ForegroundColor Green
    }
} else {
    Write-Host "   ⚠️  No log files found" -ForegroundColor Yellow
}
Write-Host ""

# Check incoming directory
Write-Host "3. Checking incoming directory..." -ForegroundColor Yellow
$incomingDir = "C:\Tools\Ollama\Data\incoming"
if (Test-Path $incomingDir) {
    $pdfFiles = Get-ChildItem $incomingDir -Filter "*.pdf" -ErrorAction SilentlyContinue
    if ($pdfFiles) {
        Write-Host "   ✓ Found $($pdfFiles.Count) PDF file(s) waiting to be processed" -ForegroundColor Green
        $pdfFiles | ForEach-Object { Write-Host "      - $($_.Name)" -ForegroundColor Gray }
    } else {
        Write-Host "   ℹ️  No PDF files in incoming directory" -ForegroundColor Gray
        Write-Host "      Place a PDF here to test processing" -ForegroundColor Gray
    }
} else {
    Write-Host "   ⚠️  Incoming directory not found: $incomingDir" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Verify columns in Supabase:" -ForegroundColor White
Write-Host "   Run: sql/verify-phase1.sql" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Test processing:" -ForegroundColor White
Write-Host "   Place a PDF in C:\Tools\Ollama\Data\incoming\" -ForegroundColor Gray
Write-Host "   Wait 30 seconds and check logs" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Verify data in Supabase:" -ForegroundColor White
Write-Host "   SELECT dedupe_key, confidence, impact_level FROM vulnerabilities LIMIT 5;" -ForegroundColor Gray
Write-Host ""

