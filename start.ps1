# PSA Tool Startup Script for PowerShell
# Starts the Flask backend server

Write-Host "Starting PSA Tool Flask Server..." -ForegroundColor Green

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Install/update dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
pip install -q -r requirements.txt

# Load environment variables
if (Test-Path ".env") {
    Write-Host "Loading .env file..." -ForegroundColor Yellow
} else {
    Write-Host "Warning: .env file not found. Copy .env.example to .env and configure." -ForegroundColor Red
}

# Start Flask server
Write-Host "Starting Flask server on http://localhost:8080" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Cyan
python app.py

