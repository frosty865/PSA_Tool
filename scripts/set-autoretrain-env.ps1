# Set environment variables for VOFC-AutoRetrain service from .env file
# Run this after installing the service to configure environment variables

$SERVICE_NAME = "VOFC-AutoRetrain"
# Try multiple possible project root locations
$POSSIBLE_ROOTS = @(
    (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool",
    "C:\Tools\PSA_Tool"
)

$PROJECT_ROOT = $null
foreach ($root in $POSSIBLE_ROOTS) {
    $envTest = Join-Path $root ".env"
    if (Test-Path $envTest) {
        $PROJECT_ROOT = $root
        break
    }
}

if (-not $PROJECT_ROOT) {
    Write-Host "ERROR: Could not find .env file in any of these locations:" -ForegroundColor Red
    foreach ($root in $POSSIBLE_ROOTS) {
        Write-Host "  $root\.env" -ForegroundColor Yellow
    }
    exit 1
}

$ENV_FILE = Join-Path $PROJECT_ROOT ".env"

if (-not (Test-Path $ENV_FILE)) {
    Write-Host "ERROR: .env file not found at: $ENV_FILE" -ForegroundColor Red
    exit 1
}

Write-Host "Reading environment variables from: $ENV_FILE" -ForegroundColor Green

$envVars = @()

Get-Content $ENV_FILE | ForEach-Object {
    # Skip comments and empty lines
    if ($_ -match '^\s*#') {
        return
    }
    if ($_ -match '^\s*$') {
        return
    }
    
    # Match KEY=VALUE format
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim().Trim('"').Trim("'")
        
        # Only include Supabase and other relevant variables
        if ($key -match '^(SUPABASE_|NEXT_PUBLIC_SUPABASE_|OLLAMA_|FLASK_)' -or 
            $key -match '^(VOFC_|TUNNEL_|AUTH_)') {
            if ($key -and $value -and $value -ne 'your-service-role-key' -and $value -ne 'your-anon-key') {
                $envVars += "$key=$value"
                Write-Host "  Found: $key" -ForegroundColor Gray
            }
        }
    }
}

if ($envVars.Count -eq 0) {
    Write-Host "WARNING: No valid environment variables found in .env file" -ForegroundColor Yellow
    Write-Host "Make sure your .env file contains SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY" -ForegroundColor Yellow
    exit 1
}

# Get existing environment variables to preserve them
Write-Host "Checking for existing environment variables..." -ForegroundColor Yellow
$currentEnvRaw = nssm get $SERVICE_NAME AppEnvironmentExtra 2>&1
$existingVars = @{}

if ($currentEnvRaw -notmatch "not exist" -and $currentEnvRaw -ne "") {
    # Parse existing environment variables
    # NSSM returns them as newline-separated KEY=VALUE pairs
    $currentEnvRaw -split "`n" | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1]
            $value = $matches[2]
            $existingVars[$key] = $value
        }
    }
    if ($existingVars.Count -gt 0) {
        Write-Host "  Found $($existingVars.Count) existing variable(s), will preserve them" -ForegroundColor Gray
    }
}

# Merge new variables with existing ones (new values override existing)
foreach ($var in $envVars) {
    if ($var -match '^([^=]+)=(.*)$') {
        $key = $matches[1]
        $value = $matches[2]
        $existingVars[$key] = $value
    }
}

# Build environment string (NSSM expects newline-separated KEY=VALUE pairs)
$envString = ($existingVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"

Write-Host "`nSetting $($existingVars.Count) environment variables for service: $SERVICE_NAME" -ForegroundColor Green

# Set environment variables in NSSM
nssm set $SERVICE_NAME AppEnvironmentExtra $envString

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Environment variables configured successfully!" -ForegroundColor Green
    Write-Host "`nRestart the service to apply changes:" -ForegroundColor Yellow
    Write-Host "  nssm restart $SERVICE_NAME" -ForegroundColor White
} else {
    Write-Host "`n❌ Failed to set environment variables" -ForegroundColor Red
    exit 1
}

