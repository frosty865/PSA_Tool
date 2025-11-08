# Reset Document for Testing/Reprocessing
# Usage: .\reset-document.ps1 -DocumentName "your-document.pdf"

param(
    [Parameter(Mandatory=$true)]
    [string]$DocumentName,
    
    [Parameter(Mandatory=$false)]
    [switch]$ClearDatabase = $false
)

$BASE_DIR = "C:\Tools\Ollama\Data"
$libraryPath = Join-Path $BASE_DIR "library\$DocumentName"
$incomingPath = Join-Path $BASE_DIR "incoming\$DocumentName"
$processingPath = Join-Path $BASE_DIR "processing\$DocumentName"

# Get base filename without extension for JSON files
$baseName = [System.IO.Path]::GetFileNameWithoutExtension($DocumentName)
$processedPath = Join-Path $BASE_DIR "processed\${baseName}_vofc.json"
$reviewPath = Join-Path $BASE_DIR "review\${baseName}_vofc.json"
$reviewTempPath = Join-Path $BASE_DIR "review\temp\${baseName}_phase3_auditor.json"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Resetting Document for Testing" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
Write-Host "Document: $DocumentName" -ForegroundColor Yellow

# 1. Check where file is and move to incoming
$fileFound = $false

if (Test-Path $processingPath) {
    Write-Host "⚠️  File found in processing/ directory (may be stuck)" -ForegroundColor Yellow
    Move-Item $processingPath $incomingPath -Force
    Write-Host "✅ Moved from processing to incoming" -ForegroundColor Green
    $fileFound = $true
} elseif (Test-Path $libraryPath) {
    Move-Item $libraryPath $incomingPath -Force
    Write-Host "✅ Moved from library to incoming" -ForegroundColor Green
    $fileFound = $true
} elseif (Test-Path $incomingPath) {
    Write-Host "✅ File already in incoming directory" -ForegroundColor Green
    $fileFound = $true
} else {
    Write-Host "❌ File not found in library, processing, or incoming!" -ForegroundColor Red
    Write-Host "   Searched:" -ForegroundColor Gray
    Write-Host "     - $libraryPath" -ForegroundColor Gray
    Write-Host "     - $processingPath" -ForegroundColor Gray
    Write-Host "     - $incomingPath" -ForegroundColor Gray
}

# 2. Remove JSON outputs
$removedCount = 0

if (Test-Path $processedPath) {
    Remove-Item $processedPath -Force
    Write-Host "✅ Removed processed JSON: $processedPath" -ForegroundColor Green
    $removedCount++
}

if (Test-Path $reviewPath) {
    Remove-Item $reviewPath -Force
    Write-Host "✅ Removed review JSON: $reviewPath" -ForegroundColor Green
    $removedCount++
}

if (Test-Path $reviewTempPath) {
    Remove-Item $reviewTempPath -Force
    Write-Host "✅ Removed review temp JSON: $reviewTempPath" -ForegroundColor Green
    $removedCount++
}

if ($removedCount -eq 0) {
    Write-Host "ℹ️  No JSON outputs found to remove" -ForegroundColor Gray
}

# 3. Database cleanup (if requested)
if ($ClearDatabase) {
    Write-Host "`n🗄️  Database cleanup requested..." -ForegroundColor Yellow
    Write-Host "   Note: You'll need to manually delete from Supabase:" -ForegroundColor Yellow
    Write-Host "   1. Find submission: SELECT id FROM submissions WHERE data->>'source_file' LIKE '%$baseName%'" -ForegroundColor Gray
    Write-Host "   2. Delete related records from:" -ForegroundColor Gray
    Write-Host "      - submission_vulnerability_ofc_links" -ForegroundColor Gray
    Write-Host "      - submission_vulnerabilities" -ForegroundColor Gray
    Write-Host "      - submission_options_for_consideration" -ForegroundColor Gray
    Write-Host "      - submission_sources" -ForegroundColor Gray
    Write-Host "   3. Delete submission: DELETE FROM submissions WHERE data->>'source_file' LIKE '%$baseName%'" -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Reset Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

if ($fileFound) {
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. RESTART the watcher service to clear in-memory tracking:" -ForegroundColor Yellow
    Write-Host "     .\scripts\restart-flask.ps1" -ForegroundColor White
    Write-Host "`n   OR wait 5+ seconds for in-memory tracking to expire" -ForegroundColor White
    Write-Host "`n  2. The document will be reprocessed automatically" -ForegroundColor White
    Write-Host "`n  Note: If file was in processing/, restart is REQUIRED" -ForegroundColor Yellow
} else {
    Write-Host "⚠️  File not found - cannot reset" -ForegroundColor Red
}

Write-Host "`n" -ForegroundColor White

