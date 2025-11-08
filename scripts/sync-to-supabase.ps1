# Manual Supabase Sync Script
# Usage: .\sync-to-supabase.ps1 -FilePath "C:\Tools\Ollama\Data\review\your_file_vofc.json"
# Or: .\sync-to-supabase.ps1 (will sync all files in review/)

param(
    [Parameter(Mandatory=$false)]
    [string]$FilePath = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$AllFiles = $false
)

$REVIEW_DIR = "C:\Tools\Ollama\Data\review"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Manual Supabase Sync" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check environment variables first
$supabaseUrl = $env:SUPABASE_URL
if (-not $supabaseUrl) {
    $supabaseUrl = $env:NEXT_PUBLIC_SUPABASE_URL
}

if (-not $supabaseUrl) {
    Write-Host "❌ SUPABASE_URL not set!" -ForegroundColor Red
    Write-Host "   Set it with: `$env:SUPABASE_URL = 'your-url'" -ForegroundColor Yellow
    exit 1
}

if (-not $env:SUPABASE_SERVICE_ROLE_KEY) {
    Write-Host "❌ SUPABASE_SERVICE_ROLE_KEY not set!" -ForegroundColor Red
    Write-Host "   Set it with: `$env:SUPABASE_SERVICE_ROLE_KEY = 'your-key'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Environment variables set" -ForegroundColor Green
Write-Host ""

# Check if Python is available
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "❌ Python not found in PATH" -ForegroundColor Red
    Write-Host "   Please ensure Python is installed and in your PATH" -ForegroundColor Yellow
    exit 1
}

# Check if venv exists
$venvPython = ".\venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $pythonCmd = $venvPython
    Write-Host "✅ Using virtual environment Python" -ForegroundColor Green
} else {
    Write-Host "⚠️  Virtual environment not found, using system Python" -ForegroundColor Yellow
}

if ($FilePath) {
    # Sync specific file
    if (-not (Test-Path $FilePath)) {
        Write-Host "❌ File not found: $FilePath" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "📤 Syncing file: $FilePath" -ForegroundColor Yellow
    Write-Host ""
    
    $script = @"
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from services.supabase_sync import sync_processed_result

try:
    submission_id = sync_processed_result(r'$FilePath', submitter_email='system@psa.local')
    print(f'✅ Successfully synced! Submission ID: {submission_id}')
    sys.exit(0)
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@
    
    $script | & $pythonCmd
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "`n✅ Sync completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "`n❌ Sync failed. Check error above." -ForegroundColor Red
    }
    
} elseif ($AllFiles -or (-not $FilePath)) {
    # Sync all files in review/
    if (-not (Test-Path $REVIEW_DIR)) {
        Write-Host "❌ Review directory not found: $REVIEW_DIR" -ForegroundColor Red
        exit 1
    }
    
    $jsonFiles = Get-ChildItem -Path $REVIEW_DIR -Filter "*.json" -File
    if ($jsonFiles.Count -eq 0) {
        Write-Host "⚠️  No JSON files found in $REVIEW_DIR" -ForegroundColor Yellow
        exit 0
    }
    
    Write-Host "📁 Found $($jsonFiles.Count) JSON file(s) in review/" -ForegroundColor Cyan
    Write-Host ""
    
    $successCount = 0
    $failCount = 0
    
    foreach ($file in $jsonFiles) {
        Write-Host "📤 Syncing: $($file.Name)..." -ForegroundColor Yellow
        
        $script = @"
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from services.supabase_sync import sync_processed_result

try:
    submission_id = sync_processed_result(r'$($file.FullName)', submitter_email='system@psa.local')
    print(f'✅ Success: {submission_id}')
    sys.exit(0)
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"@
        
        $script | & $pythonCmd
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            $successCount++
            Write-Host "   ✅ Success" -ForegroundColor Green
        } else {
            $failCount++
            Write-Host "   ❌ Failed" -ForegroundColor Red
        }
        Write-Host ""
    }
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  ✅ Successful: $successCount" -ForegroundColor Green
    Write-Host "  ❌ Failed: $failCount" -ForegroundColor Red
    Write-Host "========================================`n" -ForegroundColor Cyan
}

