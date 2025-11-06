#!/usr/bin/env python3
"""
Test script to trigger processing and check the workflow
"""
import requests
import json
import sys
from pathlib import Path

def test_processing():
    """Test the process_existing endpoint"""
    print("=" * 60)
    print("Testing Processing Workflow")
    print("=" * 60)
    print()
    
    # Step 1: Check incoming directory
    incoming_dir = Path(r"C:\Tools\Ollama\Data\incoming")
    print(f"Step 1: Checking incoming directory: {incoming_dir}")
    if not incoming_dir.exists():
        print(f"  [ERROR] Directory does not exist!")
        return False
    print(f"  [OK] Directory exists")
    
    files = list(incoming_dir.glob("*.*"))
    supported = [f for f in files if f.suffix.lower() in {'.pdf', '.docx', '.txt', '.xlsx'}]
    print(f"  Files found: {len(supported)}")
    if supported:
        for f in supported[:3]:
            print(f"    - {f.name}")
    else:
        print("  [WARN] No supported files found")
        return False
    print()
    
    # Step 2: Test Flask health
    print("Step 2: Testing Flask connection...")
    try:
        health = requests.get("http://localhost:8080/api/system/health", timeout=5)
        if health.status_code == 200:
            print("  [OK] Flask is running")
            data = health.json()
            print(f"    Flask: {data.get('flask')}")
            print(f"    Ollama: {data.get('ollama')}")
        else:
            print(f"  [ERROR] Flask returned status {health.status_code}")
            return False
    except Exception as e:
        print(f"  [ERROR] Flask not reachable: {e}")
        return False
    print()
    
    # Step 3: Trigger processing
    print("Step 3: Triggering processing...")
    try:
        response = requests.post(
            "http://localhost:8080/api/system/control",
            json={"action": "process_existing"},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  [OK] Request successful")
            print(f"    Message: {result.get('message', 'No message')}")
            print()
            print("  Check logs at:")
            print("    C:\\Tools\\Ollama\\Data\\automation\\vofc_auto_processor.log")
            print("    C:\\Tools\\nssm\\logs\\vofc_flask.log")
            return True
        else:
            print(f"  [ERROR] Request failed with status {response.status_code}")
            print(f"    Response: {response.text}")
            return False
    except Exception as e:
        print(f"  [ERROR] Request failed: {e}")
        return False

if __name__ == "__main__":
    success = test_processing()
    sys.exit(0 if success else 1)
