#!/usr/bin/env python3
"""
Test Log Reading
Quick test to verify log file can be read and filtered correctly
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from datetime import datetime

log_file = Config.LOGS_DIR / "vofc_processor.log"

print("=" * 60)
print("Log File Reading Test")
print("=" * 60)
print()

print(f"Log file path: {log_file}")
print(f"Exists: {log_file.exists()}")
print()

if log_file.exists():
    print(f"File size: {log_file.stat().st_size} bytes")
    print(f"Last modified: {datetime.fromtimestamp(log_file.stat().st_mtime)}")
    print()
    
    print("Last 20 lines:")
    print("-" * 60)
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        for line in lines[-20:]:
            print(line.rstrip())
    print("-" * 60)
    print()
    
    # Test the filtering logic
    today_date_str = datetime.now().strftime("%Y-%m-%d")
    print(f"Today's date: {today_date_str}")
    print()
    
    today_lines = []
    all_lines = []
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            all_lines.append(cleaned)
            if cleaned.startswith(today_date_str):
                today_lines.append(cleaned)
    
    print(f"Total lines: {len(all_lines)}")
    print(f"Lines starting with today's date: {len(today_lines)}")
    print()
    
    if today_lines:
        print("Last 5 lines from today:")
        for line in today_lines[-5:]:
            print(f"  {line[:80]}...")
    else:
        print("⚠️  No lines found starting with today's date")
        print("Last 5 lines (all):")
        for line in all_lines[-5:]:
            print(f"  {line[:80]}...")
else:
    print("❌ Log file does not exist!")
    print()
    print("The processor may not be running or logs are being written elsewhere.")
    print(f"Expected location: {log_file}")

print("=" * 60)

