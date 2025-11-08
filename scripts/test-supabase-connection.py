#!/usr/bin/env python3
"""
Test Supabase Connection and Sync
This script tests if Supabase is accessible and can insert data
"""

import sys
import os
from pathlib import Path
import json

# Add project root to path
# Handle both running from scripts/ and from project root
script_dir = Path(__file__).parent
if script_dir.name == "scripts":
    project_root = script_dir.parent
else:
    project_root = script_dir
sys.path.insert(0, str(project_root))

print("=" * 60)
print("Supabase Connection Test")
print("=" * 60)
print()

# 1. Check environment variables
print("1. Checking environment variables...")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL:
    print("[ERROR] SUPABASE_URL not set!")
    print("   Set it with: $env:SUPABASE_URL = 'your-url'")
    sys.exit(1)
else:
    print(f"[OK] SUPABASE_URL: {SUPABASE_URL[:30]}...")

if not SUPABASE_SERVICE_ROLE_KEY:
    print("[ERROR] SUPABASE_SERVICE_ROLE_KEY not set!")
    print("   Set it with: $env:SUPABASE_SERVICE_ROLE_KEY = 'your-key'")
    sys.exit(1)
else:
    key_length = len(SUPABASE_SERVICE_ROLE_KEY)
    key_start = SUPABASE_SERVICE_ROLE_KEY[:10]
    print(f"[OK] SUPABASE_SERVICE_ROLE_KEY: {key_start}... (length: {key_length})")
    
    # Validate key format
    if key_length < 100:
        print("[WARNING] Service role key seems too short (should be 200+ characters)")
    if not SUPABASE_SERVICE_ROLE_KEY.startswith("eyJ"):
        print("[WARNING] Service role key should start with 'eyJ' (JWT format)")
        print("   You might be using the anon key instead of the service role key")

print()

# 2. Test Supabase client creation
print("2. Testing Supabase client creation...")
try:
    from supabase import create_client, Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    print("[OK] Supabase client created successfully")
except Exception as e:
    print(f"[ERROR] Failed to create Supabase client: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# 3. Test connection by querying a table
print("3. Testing connection by querying submissions table...")
try:
    result = supabase.table("submissions").select("id").limit(1).execute()
    print(f"[OK] Connection successful! Found {len(result.data)} existing submission(s)")
except Exception as e:
    print(f"[ERROR] Failed to query submissions table: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# 4. Test inserting a simple submission
print("4. Testing insert into submissions table...")
import uuid
from datetime import datetime

# Test with minimal required fields first
# Note: type must be 'vulnerability' or 'ofc' per check constraint
test_submission = {
    "id": str(uuid.uuid4()),
    "type": "vulnerability",  # Must be 'vulnerability' or 'ofc' per check constraint
    "status": "pending_review",
    "source": "psa_tool_auto",
    "data": {
        "test": True,
        "message": "This is a test submission",
        "submitter_email": "test@psa.local",  # Store in data if column doesn't exist
        "document_type": "document"  # Store actual type in data JSONB
    },
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat()
}

try:
    result = supabase.table("submissions").insert(test_submission).execute()
    if result.data:
        print(f"[OK] Successfully inserted test submission: {test_submission['id']}")
        print(f"   Response data: {result.data}")
        
        # Clean up - delete the test submission
        print("   Cleaning up test submission...")
        supabase.table("submissions").delete().eq("id", test_submission["id"]).execute()
        print("   [OK] Test submission deleted")
    else:
        print("[WARNING] Insert returned no data (but may have succeeded)")
        print(f"   Response: {result}")
except Exception as e:
    print(f"[ERROR] Failed to insert test submission: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    print()
    print("   This is the actual error preventing sync!")
    sys.exit(1)

print()

# 5. Test sync function with a sample file
print("5. Testing sync_processed_result function...")
print("   Looking for JSON files in review/ directory...")

review_dir = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data")) / "review"
if not review_dir.exists():
    print(f"[WARNING] Review directory not found: {review_dir}")
    print("   Creating a test JSON file...")
    review_dir.mkdir(parents=True, exist_ok=True)
    test_file = review_dir / "test_sync.json"
    test_data = {
        "source_file": "test_document.pdf",
        "processed_at": datetime.utcnow().isoformat(),
        "vulnerabilities": [
            {
                "vulnerability": "Test vulnerability",
                "discipline": "Physical Security",
                "sector": "Energy"
            }
        ],
        "options_for_consideration": [
            {
                "option_text": "Test OFC",
                "vulnerability": "Test vulnerability",  # Link to parent vulnerability
                "discipline": "Physical Security"
            }
        ],
        "sources": [
            {
                "source_title": "test_document.pdf",
                "source_text": "Test document source",
                "source_type": "guidance_doc"
            }
        ],
        "summary": "Test submission for sync verification"
    }
    with open(test_file, "w") as f:
        json.dump(test_data, f, indent=2)
    print(f"   [OK] Created test file: {test_file}")
else:
    json_files = list(review_dir.glob("*.json"))
    if json_files:
        test_file = json_files[0]
        print(f"   [OK] Found {len(json_files)} JSON file(s), using: {test_file.name}")
    else:
        print(f"   [WARNING] No JSON files found in {review_dir}")
        print("   Creating a test JSON file...")
        test_file = review_dir / "test_sync.json"
        test_data = {
            "source_file": "test_document.pdf",
            "processed_at": datetime.utcnow().isoformat(),
            "vulnerabilities": [
                {
                    "vulnerability": "Test vulnerability",
                    "discipline": "Physical Security",
                    "sector": "Energy"
                }
            ],
            "options_for_consideration": [
                {
                    "option_text": "Test OFC",
                    "discipline": "Physical Security"
                }
            ],
            "summary": "Test submission for sync verification"
        }
        with open(test_file, "w") as f:
            json.dump(test_data, f, indent=2)
        print(f"   [OK] Created test file: {test_file}")

print()
print("   Attempting to sync test file...")
try:
    from services.supabase_sync import sync_processed_result
    submission_id = sync_processed_result(str(test_file), submitter_email="test@psa.local")
    print(f"   [OK] Sync successful! Submission ID: {submission_id}")
    
    # Verify it was created
    verify = supabase.table("submissions").select("id, status").eq("id", submission_id).execute()
    if verify.data:
        print(f"   [OK] Verified submission exists in database")
        print(f"      Status: {verify.data[0]['status']}")
    else:
        print(f"   [WARNING] Submission not found after creation")
        
except Exception as e:
    print(f"   [ERROR] Sync failed: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("[OK] All tests passed! Supabase sync should be working.")
print("=" * 60)
print()
print("If tables are still empty, check:")
print("  1. Are files being processed? (Check processed/ directory)")
print("  2. Are files being copied to review/?")
print("  3. Is sync_processed_result being called? (Check logs)")
print("  4. Are there any errors in the logs?")

