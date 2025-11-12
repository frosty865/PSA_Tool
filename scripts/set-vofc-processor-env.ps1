# Set environment variables for VOFC-Processor service from .env file
# Run this after installing the service to configure environment variables
# Must be run as Administrator

param(
    [string]$ServiceName = "VOFC-Processor"
)

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor Yellow
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "  3. Run this script again" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Try multiple possible project root locations
$POSSIBLE_ROOTS = @(
    (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)),
    "C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool",
    "C:\Tools\PSA_Tool",
    "C:\Tools\py_scripts\vofc_processor"
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

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setting Environment Variables for $ServiceName" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Reading from: $ENV_FILE" -ForegroundColor Green
Write-Host ""

$envVars = @{}

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
        
        # Only include relevant variables for processor
        # Map SUPABASE_SERVICE_ROLE_KEY to SUPABASE_KEY for processor compatibility
        if ($key -eq "SUPABASE_SERVICE_ROLE_KEY") {
            $envVars["SUPABASE_KEY"] = $value
            $envVars["SUPABASE_SERVICE_ROLE_KEY"] = $value  # Also keep original
            Write-Host "  Found: $key (mapped to SUPABASE_KEY)" -ForegroundColor Gray
        }
        elseif ($key -match '^(SUPABASE_|OLLAMA_|VOFC_)' -and 
            $value -and $value -ne 'your-service-role-key' -and $value -ne 'your-anon-key' -and
            $value -ne 'your-project-url') {
            $envVars[$key] = $value
            Write-Host "  Found: $key" -ForegroundColor Gray
        }
        
        # Special handling for OLLAMA_MODEL
        if ($key -eq "OLLAMA_MODEL") {
            $envVars["OLLAMA_MODEL"] = $value
            Write-Host "  Found: $key = $value" -ForegroundColor Gray
        }
        
        # Also map NEXT_PUBLIC_SUPABASE_URL to SUPABASE_URL if SUPABASE_URL not found
        if ($key -eq "NEXT_PUBLIC_SUPABASE_URL" -and -not $envVars.ContainsKey("SUPABASE_URL")) {
            $envVars["SUPABASE_URL"] = $value
            Write-Host "  Found: $key (mapped to SUPABASE_URL)" -ForegroundColor Gray
        }
    }
}

if ($envVars.Count -eq 0) {
    Write-Host "WARNING: No relevant environment variables found in .env file" -ForegroundColor Yellow
    Write-Host "Looking for: SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY, OLLAMA_BASE_URL, VOFC_DATA_DIR" -ForegroundColor Yellow
    exit 1
}

# Get existing environment variables to preserve them
Write-Host "Checking for existing environment variables..." -ForegroundColor Yellow
$currentEnvRaw = nssm get $ServiceName AppEnvironmentExtra 2>&1
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
foreach ($key in $envVars.Keys) {
    $existingVars[$key] = $envVars[$key]
}

Write-Host ""
Write-Host "Setting environment variables for service..." -ForegroundColor Yellow

# Build the combined environment string (NSSM expects newline-separated KEY=VALUE pairs)
$envString = ($existingVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "`n"

try {
    nssm set $ServiceName AppEnvironmentExtra $envString 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Set $($existingVars.Count) environment variable(s)" -ForegroundColor Green
        foreach ($key in $envVars.Keys) {
            Write-Host "    - $key" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ✗ Failed to set environment variables" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ✗ Error setting environment variables: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Environment Variables Set" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To verify, run:" -ForegroundColor Yellow
Write-Host "  nssm get $ServiceName AppEnvironmentExtra" -ForegroundColor Cyan
Write-Host ""
Write-Host "To restart the service:" -ForegroundColor Yellow
Write-Host "  nssm restart $ServiceName" -ForegroundColor Cyan
Write-Host ""

