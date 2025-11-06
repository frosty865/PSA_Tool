# Workflow Diagnostic Script
# Checks each step of the processing workflow to find breaks

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Processing Workflow Diagnostic" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if incoming directory exists and has files
Write-Host "Step 1: Check incoming directory" -ForegroundColor Yellow
$incomingDir = "C:\Tools\Ollama\Data\incoming"
if (Test-Path $incomingDir) {
    Write-Host "  ✓ Directory exists: $incomingDir" -ForegroundColor Green
    $files = Get-ChildItem -Path $incomingDir -File -ErrorAction SilentlyContinue | Where-Object {$_.Extension -match '\.(pdf|docx|txt|xlsx)$'}
    Write-Host "  Files found: $($files.Count)" -ForegroundColor $(if ($files.Count -gt 0) { "Green" } else { "Yellow" })
    if ($files.Count -gt 0) {
        foreach ($f in $files | Select-Object -First 3) {
            $sizeKB = [math]::Round($f.Length/1KB, 2)
            Write-Host "    - $($f.Name) - $sizeKB KB" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  ✗ Directory does not exist: $incomingDir" -ForegroundColor Red
}
Write-Host ""

# Step 2: Check Flask is running
Write-Host "Step 2: Check Flask API" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/api/system/health" -Method GET -TimeoutSec 5
    Write-Host "  ✓ Flask is running" -ForegroundColor Green
    Write-Host "    Flask: $($health.flask)" -ForegroundColor Gray
    Write-Host "    Ollama: $($health.ollama)" -ForegroundColor Gray
    Write-Host "    Supabase: $($health.supabase)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Flask is not responding: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Test the control endpoint
Write-Host "Step 3: Test control endpoint" -ForegroundColor Yellow
try {
    $body = @{action='process_existing'} | ConvertTo-Json
    Write-Host "  Sending request..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "http://localhost:8080/api/system/control" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
    Write-Host "  ✓ Request successful" -ForegroundColor Green
    Write-Host "    Response: $($response.message)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Request failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "    Error details: $responseBody" -ForegroundColor Red
    }
}
Write-Host ""

# Step 4: Check logs
Write-Host "Step 4: Check recent logs" -ForegroundColor Yellow
$logFile = "C:\Tools\Ollama\Data\automation\vofc_auto_processor.log"
if (Test-Path $logFile) {
    Write-Host "  ✓ Log file exists" -ForegroundColor Green
    $lastLines = Get-Content $logFile -Tail 20 -ErrorAction SilentlyContinue
    if ($lastLines) {
        Write-Host "  Last 5 log entries:" -ForegroundColor Cyan
        $lastLines | Select-Object -Last 5 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Log file is empty" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⚠ Log file does not exist: $logFile" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Check Flask logs
Write-Host "Step 5: Check Flask logs" -ForegroundColor Yellow
$flaskLog = "C:\Tools\nssm\logs\vofc_flask.log"
if (Test-Path $flaskLog) {
    Write-Host "  ✓ Flask log exists" -ForegroundColor Green
    $lastLines = Get-Content $flaskLog -Tail 10 -ErrorAction SilentlyContinue
    if ($lastLines) {
        Write-Host "  Last 3 Flask log entries:" -ForegroundColor Cyan
        $lastLines | Select-Object -Last 3 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  ⚠ Flask log not found: $flaskLog" -ForegroundColor Yellow
}
Write-Host ""

# Step 6: Check if files were processed
Write-Host "Step 6: Check processing results" -ForegroundColor Yellow
$processedDir = "C:\Tools\Ollama\Data\processed"
$libraryDir = "C:\Tools\Ollama\Data\library"
$errorDir = "C:\Tools\Ollama\Data\errors"
$reviewDir = "C:\Tools\Ollama\Data\review"

if (Test-Path $processedDir) {
    $processed = (Get-ChildItem $processedDir -Filter "*_vofc.json" -ErrorAction SilentlyContinue).Count
    Write-Host "  Processed JSON files: $processed" -ForegroundColor $(if ($processed -gt 0) { "Green" } else { "Yellow" })
}
if (Test-Path $libraryDir) {
    $library = (Get-ChildItem $libraryDir -File -ErrorAction SilentlyContinue).Count
    Write-Host "  Library files: $library" -ForegroundColor Gray
}
if (Test-Path $errorDir) {
    $errors = (Get-ChildItem $errorDir -File -ErrorAction SilentlyContinue).Count
    Write-Host "  Error files: $errors" -ForegroundColor $(if ($errors -gt 0) { "Red" } else { "Green" })
    if ($errors -gt 0) {
        Write-Host "  Recent error files:" -ForegroundColor Yellow
        Get-ChildItem $errorDir -File | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object {
            Write-Host "    - $($_.Name) ($($_.LastWriteTime))" -ForegroundColor Red
        }
    }
}
if (Test-Path $reviewDir) {
    $review = (Get-ChildItem $reviewDir -Filter "*_vofc.json" -ErrorAction SilentlyContinue).Count
    Write-Host "  Review files: $review" -ForegroundColor Gray
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Diagnostic Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

