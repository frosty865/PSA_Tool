# Phase 1 Complete Validation Script
# Run this after migration and processor restart

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 1 Complete Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check service status
Write-Host "1. Service Status" -ForegroundColor Yellow
$status = nssm status VOFC-Processor 2>&1
if ($status -match "SERVICE_RUNNING") {
    Write-Host "   ✓ VOFC-Processor is running" -ForegroundColor Green
} else {
    Write-Host "   ✗ Service status: $status" -ForegroundColor Red
    Write-Host "   Run: nssm start VOFC-Processor" -ForegroundColor Yellow
}
Write-Host ""

# 2. Check for column errors in logs
Write-Host "2. Checking for Column Errors" -ForegroundColor Yellow
$logFiles = Get-ChildItem "C:\Tools\Ollama\Data\logs\vofc_processor*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($logFiles) {
    $recentLogs = Get-Content $logFiles.FullName -Tail 50 -ErrorAction SilentlyContinue
    $columnErrors = $recentLogs | Select-String -Pattern "column.*does not exist|column.*not found|42703" -CaseSensitive:$false
    if ($columnErrors) {
        Write-Host "   ⚠️  Found column errors:" -ForegroundColor Red
        $columnErrors | Select-Object -First 3 | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
        Write-Host "   → Migration may not have completed successfully" -ForegroundColor Yellow
    } else {
        Write-Host "   ✓ No column errors found" -ForegroundColor Green
    }
    
    # Check for successful reference loading
    $refLoaded = $recentLogs | Select-String -Pattern "Loaded.*reference.*from Supabase|Fetched.*vulnerabilities from Supabase" -CaseSensitive:$false
    if ($refLoaded) {
        Write-Host "   ✓ Reference data loading successfully" -ForegroundColor Green
        $refLoaded | Select-Object -First 1 | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
    }
} else {
    Write-Host "   ⚠️  No log files found" -ForegroundColor Yellow
}
Write-Host ""

# 3. Check for successful processing
Write-Host "3. Recent Processing Activity" -ForegroundColor Yellow
if ($logFiles) {
    $processing = $recentLogs | Select-String -Pattern "Inserted new vulnerability|Uploaded to Supabase|Processing complete|dedupe_key" -CaseSensitive:$false
    if ($processing) {
        Write-Host "   ✓ Recent processing activity found:" -ForegroundColor Green
        $processing | Select-Object -First 3 | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
    } else {
        Write-Host "   ℹ️  No recent processing activity" -ForegroundColor Gray
        Write-Host "      Place a PDF in C:\Tools\Ollama\Data\incoming\ to test" -ForegroundColor Gray
    }
}
Write-Host ""

# 4. Check incoming directory
Write-Host "4. Incoming Directory" -ForegroundColor Yellow
$incomingDir = "C:\Tools\Ollama\Data\incoming"
if (Test-Path $incomingDir) {
    $pdfFiles = Get-ChildItem $incomingDir -Filter "*.pdf" -ErrorAction SilentlyContinue
    if ($pdfFiles) {
        Write-Host "   ✓ Found $($pdfFiles.Count) PDF file(s) to process" -ForegroundColor Green
    } else {
        Write-Host "   ℹ️  No PDF files waiting" -ForegroundColor Gray
    }
} else {
    Write-Host "   ⚠️  Directory not found: $incomingDir" -ForegroundColor Yellow
}
Write-Host ""

# 5. Summary and next steps
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To verify database migration:" -ForegroundColor White
Write-Host "  1. Open Supabase SQL Editor" -ForegroundColor Gray
Write-Host "  2. Run: sql/verify-phase1.sql" -ForegroundColor Gray
Write-Host "  3. Should see 7 columns, 6 indexes, 1 constraint" -ForegroundColor Gray
Write-Host ""
Write-Host "To test processing:" -ForegroundColor White
Write-Host "  1. Place a PDF in C:\Tools\Ollama\Data\incoming\" -ForegroundColor Gray
Write-Host "  2. Wait 30 seconds" -ForegroundColor Gray
Write-Host "  3. Check logs: Get-Content C:\Tools\Ollama\Data\logs\vofc_processor*.log -Tail 50" -ForegroundColor Gray
Write-Host "  4. Verify in Supabase:" -ForegroundColor Gray
Write-Host "     SELECT dedupe_key, confidence, impact_level FROM vulnerabilities LIMIT 5;" -ForegroundColor Gray
Write-Host ""

