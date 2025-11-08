# Cleanup Review Temp Files
# Removes stuck intermediate files from review/temp and reconstructs final outputs if possible

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup Review Temp Files" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$flaskUrl = "http://10.0.0.213:8080/api/system/control"

Write-Host "Calling cleanup_review_temp action..." -ForegroundColor Yellow

try {
    $body = @{
        action = "cleanup_review_temp"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri $flaskUrl -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
    
    Write-Host "✅ Response: $($response.message)" -ForegroundColor Green
    
    if ($response.success) {
        Write-Host ""
        Write-Host "Cleanup completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Check the logs for details:" -ForegroundColor White
        Write-Host "  C:\Tools\Ollama\Data\automation\vofc_auto_processor.log" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "⚠️  Cleanup may have encountered issues" -ForegroundColor Yellow
        Write-Host "   Check logs for details" -ForegroundColor White
    }
} catch {
    Write-Host "❌ Error calling cleanup: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure Flask is running:" -ForegroundColor Yellow
    Write-Host "  nssm status `"VOFC-Flask`"" -ForegroundColor White
    Write-Host ""
    Write-Host "Or restart Flask:" -ForegroundColor Yellow
    Write-Host "  .\scripts\restart-flask.ps1" -ForegroundColor White
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Done" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

