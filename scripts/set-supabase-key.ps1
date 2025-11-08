# Set Supabase Service Role Key
# Usage: .\set-supabase-key.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$Key = ""
)

if ($Key) {
    $env:SUPABASE_SERVICE_ROLE_KEY = $Key
    Write-Host "✅ Service role key set for current session" -ForegroundColor Green
    Write-Host ""
    Write-Host "To make it permanent, run:" -ForegroundColor Yellow
    Write-Host "[System.Environment]::SetEnvironmentVariable('SUPABASE_SERVICE_ROLE_KEY', '$Key', 'User')" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or add it to your .env.local file for Next.js" -ForegroundColor Yellow
} else {
    Write-Host "Usage: .\set-supabase-key.ps1 -Key 'your-key-here'" -ForegroundColor Yellow
}

