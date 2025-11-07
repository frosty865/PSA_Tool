# Restart Folder Watcher
# Stops and starts the file watcher via Flask API

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Restarting Folder Watcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Flask URL
$flaskUrl = "http://10.0.0.213:8080"

# Step 1: Stop watcher
Write-Host "1. Stopping watcher..." -ForegroundColor Yellow
try {
    $stopBody = @{action='stop_watcher'} | ConvertTo-Json
    $stopResponse = Invoke-RestMethod -Uri "$flaskUrl/api/system/control" -Method POST -Body $stopBody -ContentType "application/json" -ErrorAction Stop
    Write-Host "   $($stopResponse.message)" -ForegroundColor Green
    Start-Sleep -Seconds 2
} catch {
    Write-Host "   Warning: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   (Watcher may not be running)" -ForegroundColor Gray
}

Write-Host ""

# Step 2: Start watcher
Write-Host "2. Starting watcher..." -ForegroundColor Yellow
try {
    $startBody = @{action='start_watcher'} | ConvertTo-Json
    $startResponse = Invoke-RestMethod -Uri "$flaskUrl/api/system/control" -Method POST -Body $startBody -ContentType "application/json" -ErrorAction Stop
    Write-Host "   $($startResponse.message)" -ForegroundColor Green
} catch {
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "   → Check Flask is running: Invoke-RestMethod -Uri '$flaskUrl/api/system/health'" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Watcher Restart Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The watcher is now monitoring:" -ForegroundColor White
Write-Host "  C:\Tools\Ollama\Data\incoming" -ForegroundColor Yellow
Write-Host ""

