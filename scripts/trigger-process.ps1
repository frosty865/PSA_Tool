# Trigger File Processing Script
# Processes all existing files in C:\Tools\Ollama\Data\incoming

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Triggering File Processing" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if files exist in incoming directory
$incomingDir = "C:\Tools\Ollama\Data\incoming"
Write-Host "Checking incoming directory: $incomingDir" -ForegroundColor Yellow

if (-not (Test-Path $incomingDir)) {
    Write-Host "❌ Incoming directory does not exist: $incomingDir" -ForegroundColor Red
    Write-Host "   Creating directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $incomingDir -Force | Out-Null
}

$files = Get-ChildItem -Path $incomingDir -File -Filter "*.pdf","*.docx","*.txt","*.xlsx" -ErrorAction SilentlyContinue

if ($files.Count -eq 0) {
    Write-Host "⚠️  No files found in incoming directory" -ForegroundColor Yellow
    Write-Host "   Supported formats: PDF, DOCX, TXT, XLSX" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Place files in: $incomingDir" -ForegroundColor Cyan
    exit 0
}

Write-Host "✓ Found $($files.Count) file(s) to process:" -ForegroundColor Green
foreach ($file in $files) {
    $sizeKB = [math]::Round($file.Length / 1KB, 2)
    Write-Host "   - $($file.Name) - $sizeKB KB" -ForegroundColor Gray
}
Write-Host ""

# Try to trigger processing via Flask API
Write-Host "Triggering processing via Flask API..." -ForegroundColor Yellow

try {
    # Try localhost first
    $flaskUrl = "http://localhost:8080"
    
    Write-Host "Testing Flask connection: $flaskUrl/api/system/health" -ForegroundColor Cyan
    $healthCheck = Invoke-WebRequest -Uri "$flaskUrl/api/system/health" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✓ Flask is reachable" -ForegroundColor Green
    Write-Host ""
    
    # Trigger processing
    Write-Host "Sending process request to: $flaskUrl/api/system/control" -ForegroundColor Cyan
    $body = @{
        action = "process_existing"
    } | ConvertTo-Json
    
    $response = Invoke-WebRequest -Uri "$flaskUrl/api/system/control" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30 -ErrorAction Stop
    
    $result = $response.Content | ConvertFrom-Json
    
    Write-Host "✓ Processing triggered successfully!" -ForegroundColor Green
    Write-Host "  Response: $($result.message)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Monitor progress at:" -ForegroundColor Cyan
    Write-Host "  - Logs: C:\Tools\Ollama\Data\automation\vofc_auto_processor.log" -ForegroundColor White
    Write-Host "  - Admin Panel: http://localhost:3000/admin/processing" -ForegroundColor White
    
} catch {
    Write-Host "❌ Failed to trigger processing" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    
    # Check if Flask is running
    try {
        $service = Get-Service -Name "VOFC-Flask" -ErrorAction Stop
        if ($service.Status -ne "Running") {
            Write-Host "   → Flask service is not running. Start it with:" -ForegroundColor Yellow
            Write-Host "     nssm start `"VOFC-Flask`"" -ForegroundColor White
        } else {
            Write-Host "   → Flask service is running but not responding" -ForegroundColor Yellow
            Write-Host "     Check logs: Get-Content `"C:\Tools\nssm\logs\vofc_flask.log`" -Tail 50" -ForegroundColor White
        }
    } catch {
        Write-Host "   -> Flask service not found" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Alternative: Process files manually using Python" -ForegroundColor Cyan
    Write-Host "  python ollama_auto_processor.py" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Processing triggered!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

