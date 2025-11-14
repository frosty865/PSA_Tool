# Fix Cloudflare Tunnel Service Configuration
# Run this script as Administrator

Write-Host "Fixing VOFC-Tunnel service configuration..." -ForegroundColor Yellow

# Stop the service first
Write-Host "Stopping VOFC-Tunnel service..." -ForegroundColor Cyan
Stop-Service -Name "VOFC-Tunnel" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Update the service parameters
# Option 1: Use config file with tunnel name (uses ingress from config file)
Write-Host "Updating service parameters..." -ForegroundColor Cyan
Write-Host "Using: --config C:\Users\frost\cloudflared\config.yml tunnel run ollama-tunnel" -ForegroundColor Yellow
& nssm set VOFC-Tunnel AppParameters "--config C:\Users\frost\cloudflared\config.yml tunnel run ollama-tunnel"

# Verify the change
Write-Host "`nVerifying configuration..." -ForegroundColor Cyan
$params = & nssm get VOFC-Tunnel AppParameters
Write-Host "Current parameters: $params" -ForegroundColor Green

# Start the service
Write-Host "`nStarting VOFC-Tunnel service..." -ForegroundColor Cyan
Start-Service -Name "VOFC-Tunnel"
Start-Sleep -Seconds 3

# Check status
$status = Get-Service -Name "VOFC-Tunnel"
Write-Host "`nService status: $($status.Status)" -ForegroundColor $(if ($status.Status -eq 'Running') { 'Green' } else { 'Red' })

Write-Host "`nDone! The tunnel should now use the correct configuration." -ForegroundColor Green
Write-Host "Test with: curl https://flask.frostech.site/api/system/health" -ForegroundColor Yellow

