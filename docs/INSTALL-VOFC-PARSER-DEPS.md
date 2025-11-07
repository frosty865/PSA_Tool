# Installing VOFC Parser Dependencies

## Overview

The VOFC parser requires two additional dependencies:
1. **`pyyaml`** - For loading the YAML ruleset configuration
2. **NLTK data** - For sentence tokenization (NLTK itself is already in requirements.txt)

## Installation Location

You have **two Flask environments** to consider:

### 1. Development Environment (Project Root)
- **Location**: `C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\`
- **Virtual Environment**: `venv\` (in project root)
- **Use for**: Development and testing

### 2. Production Environment (NSSM Service)
- **Location**: `C:\Tools\VOFC-Flask\`
- **Virtual Environment**: Likely `C:\Tools\VOFC-Flask\venv\` or system Python
- **Use for**: Production Flask service (what NSSM runs)

## Installation Steps

### Option A: Development Environment (Recommended First)

1. **Navigate to project root:**
   ```powershell
   cd C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool
   ```

2. **Activate virtual environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Install pyyaml:**
   ```powershell
   pip install pyyaml
   ```

4. **Download NLTK data:**
   ```powershell
   python -m nltk.downloader punkt
   ```

5. **Update requirements.txt (optional, for future installs):**
   ```powershell
   pip freeze > requirements.txt
   ```
   Or manually add `pyyaml==6.0.1` to `requirements.txt`

### Option B: Production Environment (NSSM Service)

Since your Flask service runs from `C:\Tools\VOFC-Flask\`, you need to install dependencies there too:

1. **Navigate to Flask service directory:**
   ```powershell
   cd C:\Tools\VOFC-Flask
   ```

2. **Activate virtual environment (if exists):**
   ```powershell
   # If venv exists:
   .\venv\Scripts\Activate.ps1
   
   # OR if using system Python (check NSSM config):
   # No activation needed
   ```

3. **Install pyyaml:**
   ```powershell
   pip install pyyaml
   ```

4. **Download NLTK data:**
   ```powershell
   python -m nltk.downloader punkt
   ```

5. **Restart Flask service:**
   ```powershell
   nssm restart "VOFC-Flask"
   ```

## Verify Installation

Test that dependencies are installed:

```powershell
python -c "import yaml; import nltk; print('✅ All dependencies installed')"
```

Test NLTK data:
```powershell
python -c "from nltk import sent_tokenize; print('✅ NLTK punkt data available')"
```

## Update requirements.txt

Add `pyyaml` to your `requirements.txt` file:

```txt
# Add this line to requirements.txt
pyyaml==6.0.1
```

Then future installs will include it automatically:
```powershell
pip install -r requirements.txt
```

## Troubleshooting

### "No module named 'yaml'"
- Make sure you activated the virtual environment
- Install: `pip install pyyaml`

### "NLTK punkt data not found"
- Download: `python -m nltk.downloader punkt`
- Or the parser will use a fallback tokenizer (less accurate)

### "Module not found" in production
- Install dependencies in the production environment (`C:\Tools\VOFC-Flask\`)
- Restart Flask service after installing

## Quick Install Script

Save this as `install-vofc-deps.ps1`:

```powershell
# Install VOFC Parser Dependencies
Write-Host "Installing VOFC parser dependencies..." -ForegroundColor Green

# Check if venv exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "No venv found. Using system Python." -ForegroundColor Yellow
}

# Install pyyaml
Write-Host "Installing pyyaml..." -ForegroundColor Yellow
pip install pyyaml

# Download NLTK data
Write-Host "Downloading NLTK punkt data..." -ForegroundColor Yellow
python -m nltk.downloader punkt

Write-Host "✅ Dependencies installed!" -ForegroundColor Green
```

Run it:
```powershell
.\install-vofc-deps.ps1
```

