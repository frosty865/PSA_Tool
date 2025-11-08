# Cleanup Rejected Submissions
# Removes rejected submissions from the database
# Optionally filters by age (older than X days)

param(
    [int]$OlderThanDays = 0,  # Only delete rejections older than this many days (0 = all)
    [switch]$DryRun = $false   # If true, just show what would be deleted without actually deleting
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup Rejected Submissions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "⚠️  DRY RUN MODE - No submissions will be deleted" -ForegroundColor Yellow
    Write-Host ""
}

if ($OlderThanDays -gt 0) {
    Write-Host "Filter: Only submissions older than $OlderThanDays days" -ForegroundColor White
    Write-Host ""
}

$flaskUrl = "http://10.0.0.213:8080/api/system/control"

Write-Host "Calling cleanup_rejected_submissions action..." -ForegroundColor Yellow

try {
    $body = @{
        action = "cleanup_rejected_submissions"
        older_than_days = $OlderThanDays
        dry_run = $DryRun.IsPresent
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri $flaskUrl -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
    
    Write-Host "✅ Response: $($response.message)" -ForegroundColor Green
    
    if ($response.success) {
        Write-Host ""
        if ($DryRun) {
            Write-Host "Found $($response.deleted_count) rejected submission(s) that would be deleted" -ForegroundColor Yellow
        } else {
            Write-Host "Cleanup completed successfully!" -ForegroundColor Green
            Write-Host "  - Deleted: $($response.deleted_count)" -ForegroundColor White
            if ($response.error_count -gt 0) {
                Write-Host "  - Errors: $($response.error_count)" -ForegroundColor Red
            }
        }
        Write-Host ""
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

