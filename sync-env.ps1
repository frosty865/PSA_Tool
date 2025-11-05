<#
.SYNOPSIS
Synchronize PSA Tool environment configuration between Flask service directory
(C:\Tools\VOFC-Flask) and the local Next.js frontend project.

.DESCRIPTION
- Copies the unified .env configuration from this project to C:\Tools\VOFC-Flask
- Ensures required Supabase, Ollama, and JWT variables exist
- Optionally creates backups before overwriting
- Verifies file integrity after copy
#>

# ================================
# Configuration
# ================================
$projectPath = "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool"
$flaskPath   = "C:\Tools\VOFC-Flask"
$envFile     = "$projectPath\.env"
$flaskEnv    = "$flaskPath\.env"
$timestamp   = (Get-Date).ToString("yyyyMMdd-HHmmss")
$backupFile  = "$flaskPath\.env.backup.$timestamp"

# ================================
# Helper Functions
# ================================
function Test-KeyValue($file, $key) {
    $pattern = "^\s*$key="
    return Select-String -Path $file -Pattern $pattern -Quiet
}

function Require-Key($file, $key) {
    if (-not (Test-KeyValue $file $key)) {
        Write-Host "❌  Missing required key: $key in $file" -ForegroundColor Red
        $script:missing += $key
    }
}

# ================================
# Step 1: Validate Source
# ================================
if (-not (Test-Path $envFile)) {
    Write-Host "❌  Missing source .env file at $envFile" -ForegroundColor Red
    exit 1
}

Write-Host "🔍 Validating .env file..."
$missing = @()
Require-Key $envFile "SUPABASE_URL"
Require-Key $envFile "SUPABASE_SERVICE_ROLE_KEY"
Require-Key $envFile "OLLAMA_HOST"
Require-Key $envFile "JWT_SECRET"

if ($missing.Count -gt 0) {
    Write-Host "⚠️  Please edit $envFile and add missing keys: $($missing -join ', ')" -ForegroundColor Yellow
    exit 1
}

# ================================
# Step 2: Backup and Copy
# ================================
if (Test-Path $flaskEnv) {
    Write-Host "📦  Backing up existing .env to $backupFile" -ForegroundColor Yellow
    Copy-Item $flaskEnv $backupFile -Force
}

Write-Host "📂  Copying $envFile → $flaskEnv" -ForegroundColor Cyan
Copy-Item $envFile $flaskEnv -Force

# ================================
# Step 3: Verify Copy
# ================================
if (Compare-Object (Get-Content $envFile) (Get-Content $flaskEnv)) {
    Write-Host "✅  .env successfully synchronized to Flask service directory" -ForegroundColor Green
} else {
    Write-Host "⚠️  Copy verification mismatch – please check manually" -ForegroundColor Yellow
}

# ================================
# Step 4: Optional Restart
# ================================
$restart = Read-Host "Do you want to restart the VOFC-Flask service now? (y/n)"
if ($restart -eq "y") {
    Write-Host "🔁 Restarting Flask service..." -ForegroundColor Cyan
    Start-Process -FilePath "nssm" -ArgumentList "restart VOFC-Flask" -Verb RunAs
    Start-Sleep -Seconds 5
    Write-Host "✅  Service restart requested. Check status with 'nssm status VOFC-Flask'."
} else {
    Write-Host "ℹ️  Service restart skipped."
}
