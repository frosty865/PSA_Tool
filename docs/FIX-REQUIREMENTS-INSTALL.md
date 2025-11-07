# Fixing Requirements Installation Issues

## Problem

When installing from `requirements.txt`, you may encounter:

1. **`pdf-parse==1.3.11` doesn't exist** - This package name is invalid
2. **Pandas build errors** - Requires C compiler (Visual Studio Build Tools) on Windows
3. **NLTK not found** - Needs to be installed before downloading punkt data

## Solution

### Step 1: Install VOFC Parser Dependencies Only

For the VOFC parser, you only need `nltk` and `pyyaml`:

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install VOFC parser dependencies
pip install nltk pyyaml

# Download NLTK punkt tokenizer data
python -m nltk.downloader punkt
```

### Step 2: Verify Installation

```powershell
python -c "import yaml; import nltk; from nltk import sent_tokenize; print('Success')"
```

### Step 3: Install Other Dependencies (Optional)

If you need other packages from `requirements.txt`, install them individually:

```powershell
# Core Flask dependencies
pip install Flask==3.0.0 flask-cors==4.0.0

# Database
pip install supabase==2.0.0 psycopg2-binary==2.9.9

# File processing (skip pandas if you don't need it)
pip install python-docx==1.1.0 PyPDF2==3.0.1 pdfplumber==0.10.3 PyMuPDF==1.23.8

# Other utilities
pip install requests==2.31.0 python-dotenv==1.0.0 python-dateutil==2.8.2 watchdog==3.0.0
```

### Step 4: Fix Pandas (If Needed)

If you need pandas but don't have Visual Studio Build Tools:

**Option A: Use pre-built wheel**
```powershell
pip install pandas --only-binary :all:
```

**Option B: Install Visual Studio Build Tools**
1. Download from: https://visualstudio.microsoft.com/downloads/
2. Install "Desktop development with C++" workload
3. Then: `pip install pandas==2.1.4`

**Option C: Skip pandas** (if not needed for your use case)
- Remove `pandas==2.1.4` from `requirements.txt`
- Remove `openpyxl==3.1.2` if you only use it with pandas

## Fixed Requirements.txt

The `pdf-parse==1.3.11` line has been removed from `requirements.txt`. The file now contains only valid packages.

## Production Environment

For the production Flask service at `C:\Tools\VOFC-Flask\`:

```powershell
cd C:\Tools\VOFC-Flask

# Activate venv (if exists)
.\venv\Scripts\Activate.ps1

# Install VOFC parser dependencies
pip install nltk pyyaml
python -m nltk.downloader punkt

# Restart Flask
nssm restart "VOFC-Flask"
```

## Quick Install Script

Save as `install-vofc-only.ps1`:

```powershell
# Install only VOFC parser dependencies
Write-Host "Installing VOFC parser dependencies..." -ForegroundColor Green

if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}

pip install nltk pyyaml
python -m nltk.downloader punkt

Write-Host "VOFC parser dependencies installed!" -ForegroundColor Green
```

