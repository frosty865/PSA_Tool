# Complete Phase 1 Implementation Script
# This script guides you through completing Phase 1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 1 Implementation Checklist" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if migration has been run
Write-Host "Step 1: Database Migration" -ForegroundColor Yellow
Write-Host "  [ ] Run sql/phase1-migration.sql in Supabase SQL Editor" -ForegroundColor Gray
Write-Host "  [ ] Verify with sql/verify-phase1.sql" -ForegroundColor Gray
Write-Host "  Expected: 7 columns, 6 indexes, 1 constraint, 1 trigger" -ForegroundColor Gray
Write-Host ""
$migrated = Read-Host "  Have you run the migration? (y/n)"
if ($migrated -eq "y" -or $migrated -eq "Y") {
    Write-Host "  ✓ Migration completed" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Please run the migration first" -ForegroundColor Yellow
    Write-Host "     Open Supabase SQL Editor and run: sql/phase1-migration.sql" -ForegroundColor Gray
    exit
}
Write-Host ""

# Step 2: Restart service
Write-Host "Step 2: Restart VOFC-Processor Service" -ForegroundColor Yellow
Write-Host "  Checking current status..." -ForegroundColor Gray
$status = nssm status VOFC-Processor 2>&1
if ($status -match "SERVICE_RUNNING") {
    Write-Host "  Current status: Running" -ForegroundColor Green
} else {
    Write-Host "  Current status: $status" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  Restarting service (requires Administrator privileges)..." -ForegroundColor Gray
Write-Host "  If you see 'Access is denied', run PowerShell as Administrator" -ForegroundColor Yellow
Write-Host ""
$restart = Read-Host "  Ready to restart? (y/n)"
if ($restart -eq "y" -or $restart -eq "Y") {
    try {
        nssm restart VOFC-Processor
        Start-Sleep -Seconds 3
        $newStatus = nssm status VOFC-Processor 2>&1
        if ($newStatus -match "SERVICE_RUNNING") {
            Write-Host "  ✓ Service restarted successfully" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Service status: $newStatus" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ✗ Could not restart service: $_" -ForegroundColor Red
        Write-Host "  Please restart manually as Administrator" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠️  Please restart manually: nssm restart VOFC-Processor" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Check logs
Write-Host "Step 3: Verify Logs" -ForegroundColor Yellow
Start-Sleep -Seconds 5
$logFiles = Get-ChildItem "C:\Tools\Ollama\Data\logs\vofc_processor*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($logFiles) {
    Write-Host "  Checking recent logs..." -ForegroundColor Gray
    $recentLogs = Get-Content $logFiles.FullName -Tail 30 -ErrorAction SilentlyContinue
    
    $columnErrors = $recentLogs | Select-String -Pattern "column.*does not exist|42703" -CaseSensitive:$false
    if ($columnErrors) {
        Write-Host "  ⚠️  Still seeing column errors:" -ForegroundColor Yellow
        $columnErrors | Select-Object -First 2 | ForEach-Object { Write-Host "      $_" -ForegroundColor Gray }
        Write-Host "  → Service may need restart or migration not complete" -ForegroundColor Yellow
    } else {
        Write-Host "  ✓ No column errors found" -ForegroundColor Green
    }
    
    $refLoaded = $recentLogs | Select-String -Pattern "Loaded.*reference|Fetched.*vulnerabilities" -CaseSensitive:$false
    if ($refLoaded) {
        Write-Host "  ✓ Reference data loading successfully" -ForegroundColor Green
    }
} else {
    Write-Host "  ⚠️  No log files found" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Test processing
Write-Host "Step 4: Test Processing" -ForegroundColor Yellow
$incomingDir = "C:\Tools\Ollama\Data\incoming"
if (Test-Path $incomingDir) {
    $pdfFiles = Get-ChildItem $incomingDir -Filter "*.pdf" -ErrorAction SilentlyContinue
    if ($pdfFiles) {
        Write-Host "  ✓ Found $($pdfFiles.Count) PDF file(s) in incoming directory" -ForegroundColor Green
        $pdfFiles | ForEach-Object { Write-Host "      - $($_.Name)" -ForegroundColor Gray }
        Write-Host ""
        Write-Host "  The processor will automatically process these files every 30 seconds" -ForegroundColor Gray
        Write-Host "  Wait 30-60 seconds, then check logs and Supabase" -ForegroundColor Gray
    } else {
        Write-Host "  ℹ️  No PDF files in incoming directory" -ForegroundColor Gray
        Write-Host "  To test: Place a PDF in $incomingDir" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⚠️  Incoming directory not found: $incomingDir" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Validation queries
Write-Host "Step 5: Validate in Supabase" -ForegroundColor Yellow
Write-Host "  Run these queries in Supabase SQL Editor:" -ForegroundColor Gray
Write-Host ""
Write-Host "  1. Check columns exist:" -ForegroundColor White
Write-Host "     sql/verify-phase1.sql" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Check data population:" -ForegroundColor White
Write-Host "     sql/test-phase1-data.sql" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Quick check:" -ForegroundColor White
Write-Host "     SELECT dedupe_key, confidence, impact_level FROM vulnerabilities LIMIT 5;" -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 1 Implementation Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Verify migration in Supabase (if not done)" -ForegroundColor White
Write-Host "  2. Restart service (if not done)" -ForegroundColor White
Write-Host "  3. Test with a document" -ForegroundColor White
Write-Host "  4. Validate data in Supabase" -ForegroundColor White
Write-Host ""
Write-Host "Success Criteria:" -ForegroundColor Yellow
Write-Host "  ✓ No 'column does not exist' errors in logs" -ForegroundColor White
Write-Host "  ✓ Reference data loads successfully" -ForegroundColor White
Write-Host "  ✓ New records have dedupe_key, confidence, impact_level" -ForegroundColor White
Write-Host "  ✓ Deduplication working (no duplicate dedupe_keys)" -ForegroundColor White
Write-Host ""
Write-Host "When Phase 1 is validated, proceed to Phase 2!" -ForegroundColor Green
Write-Host ""

