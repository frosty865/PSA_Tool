#!/usr/bin/env python3
"""
Comprehensive Backend Diagnostic Tool
Checks all services, connections, configurations, and logs
"""
import sys
import subprocess
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("BACKEND DIAGNOSTIC TOOL")
print("=" * 80)
print()

# ============================================================
# 1. SERVICE STATUS
# ============================================================
print("🔧 SERVICE STATUS")
print("-" * 80)

services = {
    "Flask": "vofc-flask",
    "Processor": "VOFC-Processor",
    "Tunnel": "VOFC-Tunnel",
    "Ollama": "VOFC-Ollama",
    "Auto Retrain": "VOFC-AutoRetrain"
}

service_status = {}
for name, service_name in services.items():
    try:
        result = subprocess.run(
            ['sc', 'query', service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            if 'RUNNING' in result.stdout:
                service_status[name] = "✅ RUNNING"
            elif 'STOPPED' in result.stdout:
                service_status[name] = "❌ STOPPED"
            else:
                service_status[name] = "⚠️  " + result.stdout.split('\n')[3].strip()
        else:
            service_status[name] = "❌ NOT FOUND"
    except Exception as e:
        service_status[name] = f"❌ ERROR: {e}"

for name, status in service_status.items():
    print(f"  {name:20} {status}")

print()

# ============================================================
# 2. CONFIGURATION
# ============================================================
print("⚙️  CONFIGURATION")
print("-" * 80)

try:
    from config import Config
    
    print(f"  Data Directory:     {Config.DATA_DIR}")
    print(f"  Logs Directory:     {Config.LOGS_DIR}")
    print(f"  Flask Port:          {Config.FLASK_PORT}")
    print(f"  Ollama URL:          {Config.OLLAMA_URL}")
    print(f"  Default Model:       {Config.DEFAULT_MODEL}")
    print(f"  Tunnel URL:          {Config.TUNNEL_URL}")
    print()
    
    # Supabase
    print("  Supabase:")
    print(f"    URL:               {'✅ SET' if Config.SUPABASE_URL else '❌ NOT SET'}")
    if Config.SUPABASE_URL:
        print(f"    Value:             {Config.SUPABASE_URL[:50]}...")
    print(f"    Service Role Key:  {'✅ SET' if Config.SUPABASE_SERVICE_ROLE_KEY else '❌ NOT SET'}")
    print(f"    Anon Key:          {'✅ SET' if Config.SUPABASE_ANON_KEY else '❌ NOT SET'}")
    print(f"    Offline Mode:      {'⚠️  ENABLED' if Config.SUPABASE_OFFLINE_MODE else '✅ DISABLED'}")
    print()
    
    # Paths
    print("  Critical Paths:")
    paths_to_check = {
        "Incoming": Config.INCOMING_DIR,
        "Processed": Config.PROCESSED_DIR,
        "Library": Config.LIBRARY_DIR,
        "Logs": Config.LOGS_DIR,
        "Errors": Config.ERRORS_DIR
    }
    for name, path in paths_to_check.items():
        exists = path.exists()
        if exists:
            try:
                size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
                file_count = len(list(path.rglob('*')))
                print(f"    {name:15} ✅ {path} ({file_count} files, {size/1024/1024:.1f} MB)")
            except:
                print(f"    {name:15} ✅ {path} (exists)")
        else:
            print(f"    {name:15} ❌ {path} (NOT FOUND)")
    
except Exception as e:
    print(f"  ❌ Configuration error: {e}")
    import traceback
    traceback.print_exc()

print()

# ============================================================
# 3. CONNECTIONS
# ============================================================
print("🔌 CONNECTIONS")
print("-" * 80)

# Flask
try:
    import requests
    flask_url = f"http://localhost:{Config.FLASK_PORT}"
    try:
        response = requests.get(f"{flask_url}/api/system/health", timeout=5)
        if response.status_code == 200:
            print(f"  Flask API:           ✅ {flask_url} (Status: {response.status_code})")
        else:
            print(f"  Flask API:           ⚠️  {flask_url} (Status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"  Flask API:           ❌ {flask_url} (Connection refused)")
    except Exception as e:
        print(f"  Flask API:           ❌ {flask_url} (Error: {e})")
except Exception as e:
    print(f"  Flask API:           ❌ Cannot test (Error: {e})")

# Ollama
try:
    ollama_url = Config.OLLAMA_URL
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print(f"  Ollama:              ✅ {ollama_url} (Status: {response.status_code})")
        else:
            print(f"  Ollama:              ⚠️  {ollama_url} (Status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f"  Ollama:              ❌ {ollama_url} (Connection refused)")
    except Exception as e:
        print(f"  Ollama:              ❌ {ollama_url} (Error: {e})")
except Exception as e:
    print(f"  Ollama:              ❌ Cannot test (Error: {e})")

# Supabase
try:
    from services.supabase_client import test_supabase
    result = test_supabase()
    if result == "ok":
        print(f"  Supabase:            ✅ Connection successful")
    else:
        print(f"  Supabase:            ❌ Connection failed ({result})")
except Exception as e:
    print(f"  Supabase:            ❌ Cannot test (Error: {e})")

print()

# ============================================================
# 4. LOG FILES
# ============================================================
print("📋 LOG FILES")
print("-" * 80)

log_files = {
    "Processor": Config.LOGS_DIR / "vofc_processor.log",
    "Flask (NSSM)": Path(r"C:\Tools\nssm\logs\vofc_flask_err.log"),
    "Flask (NSSM Out)": Path(r"C:\Tools\nssm\logs\vofc_flask_out.log"),
    "Processor (NSSM)": Path(r"C:\Tools\Ollama\Data\logs\vofc_processor_out.log"),
    "Tunnel": Path(r"C:\Tools\nssm\logs\vofc_tunnel_err.log")
}

for name, log_path in log_files.items():
    if log_path.exists():
        try:
            stat = log_path.stat()
            size_kb = stat.st_size / 1024
            modified = datetime.fromtimestamp(stat.st_mtime)
            age = datetime.now() - modified
            
            # Get last few lines
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    last_line = lines[-1].strip() if lines else "(empty)"
                    if len(last_line) > 60:
                        last_line = last_line[:60] + "..."
            except:
                last_line = "(cannot read)"
            
            status = "✅" if age.total_seconds() < 3600 else "⚠️ "
            print(f"  {name:20} {status} {log_path}")
            print(f"    Size: {size_kb:.1f} KB | Modified: {age.total_seconds()/60:.1f} min ago")
            print(f"    Last: {last_line}")
        except Exception as e:
            print(f"  {name:20} ⚠️  {log_path} (Error: {e})")
    else:
        print(f"  {name:20} ❌ {log_path} (NOT FOUND)")

print()

# ============================================================
# 5. RECENT ERRORS
# ============================================================
print("🚨 RECENT ERRORS")
print("-" * 80)

error_keywords = ["ERROR", "CRITICAL", "Exception", "Traceback", "Failed", "Error:"]

for name, log_path in log_files.items():
    if log_path.exists():
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                # Check last 100 lines for errors
                recent_lines = lines[-100:]
                errors = [line.strip() for line in recent_lines if any(kw in line.upper() for kw in error_keywords)]
                if errors:
                    print(f"  {name}:")
                    for error in errors[-3:]:  # Show last 3 errors
                        if len(error) > 100:
                            error = error[:100] + "..."
                        print(f"    - {error}")
        except Exception as e:
            pass

print()

# ============================================================
# 6. FILE SYSTEM
# ============================================================
print("📁 FILE SYSTEM")
print("-" * 80)

# Check incoming directory
incoming = Config.INCOMING_DIR
if incoming.exists():
    pdfs = list(incoming.glob("*.pdf"))
    print(f"  Incoming PDFs:       {len(pdfs)} files")
    if pdfs:
        for pdf in pdfs[:3]:
            size_mb = pdf.stat().st_size / 1024 / 1024
            age = datetime.now() - datetime.fromtimestamp(pdf.stat().st_mtime)
            print(f"    - {pdf.name} ({size_mb:.1f} MB, {age.total_seconds()/3600:.1f} hours ago)")
        if len(pdfs) > 3:
            print(f"    ... and {len(pdfs) - 3} more")
else:
    print(f"  Incoming PDFs:       ❌ Directory not found: {incoming}")

# Check processed directory
processed = Config.PROCESSED_DIR
if processed.exists():
    jsons = list(processed.glob("*.json"))
    print(f"  Processed JSONs:     {len(jsons)} files")
else:
    print(f"  Processed JSONs:     ❌ Directory not found: {processed}")

# Check library directory
library = Config.LIBRARY_DIR
if library.exists():
    pdfs = list(library.glob("*.pdf"))
    print(f"  Library PDFs:        {len(pdfs)} files")
else:
    print(f"  Library PDFs:        ❌ Directory not found: {library}")

print()

# ============================================================
# 7. PYTHON ENVIRONMENT
# ============================================================
print("🐍 PYTHON ENVIRONMENT")
print("-" * 80)

print(f"  Python Version:      {sys.version.split()[0]}")
print(f"  Python Path:         {sys.executable}")

# Check critical imports
critical_modules = [
    ("supabase", "Supabase client"),
    ("flask", "Flask"),
    ("requests", "HTTP requests"),
    ("watchdog", "File watching"),
]

for module_name, description in critical_modules:
    try:
        __import__(module_name)
        print(f"  {description:20} ✅ Installed")
    except ImportError:
        print(f"  {description:20} ❌ NOT INSTALLED")

print()

# ============================================================
# 8. SUMMARY & RECOMMENDATIONS
# ============================================================
print("=" * 80)
print("SUMMARY & RECOMMENDATIONS")
print("=" * 80)

issues = []
warnings = []

# Check service status
for name, status in service_status.items():
    if "STOPPED" in status or "NOT FOUND" in status:
        issues.append(f"{name} service is not running")
    elif "ERROR" in status:
        warnings.append(f"{name} service has errors")

# Check critical paths
if not Config.INCOMING_DIR.exists():
    issues.append(f"Incoming directory not found: {Config.INCOMING_DIR}")
if not Config.LOGS_DIR.exists():
    issues.append(f"Logs directory not found: {Config.LOGS_DIR}")

# Check Supabase
if not Config.SUPABASE_URL:
    issues.append("SUPABASE_URL not configured")
if not Config.SUPABASE_SERVICE_ROLE_KEY and not Config.SUPABASE_ANON_KEY:
    issues.append("No Supabase keys configured")

# Filter out Model Manager and Auto Retrain if they're not critical
critical_issues = [i for i in issues if "Model Manager" not in i and "Auto Retrain" not in i]
non_critical_warnings = [w for w in warnings if "Model Manager" not in w and "Auto Retrain" not in w]

if critical_issues:
    print("❌ CRITICAL ISSUES:")
    for issue in critical_issues:
        print(f"  - {issue}")
    print()

if non_critical_warnings:
    print("⚠️  WARNINGS:")
    for warning in non_critical_warnings:
        print(f"  - {warning}")
    print()

if not critical_issues and not non_critical_warnings:
    print("✅ No critical issues found!")
    print()
    print("All systems appear to be functioning correctly.")
else:
    print("🔧 RECOMMENDED ACTIONS:")
    if any("service" in issue.lower() for issue in critical_issues):
        print("  1. Check service status: sc query <service-name>")
        print("  2. Restart services: nssm restart <service-name>")
        print("  3. Check service logs in C:\\Tools\\nssm\\logs\\")
    if any("directory" in issue.lower() for issue in critical_issues):
        print("  1. Create missing directories")
        print("  2. Check file permissions")
    if any("supabase" in issue.lower() for issue in critical_issues):
        print("  1. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment")
        print("  2. Or set SUPABASE_OFFLINE_MODE=true to disable Supabase")

print("=" * 80)

