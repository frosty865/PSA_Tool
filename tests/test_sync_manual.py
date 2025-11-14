"""Manual test script for sync_individual_records"""
import sys
import os
from pathlib import Path

# Add project directory to path
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

# Load environment variables from .env if it exists
from dotenv import load_dotenv
load_dotenv()

print(f"SUPABASE_URL: {'SET' if os.getenv('SUPABASE_URL') else 'NOT SET'}")
print(f"SUPABASE_SERVICE_ROLE_KEY: {'SET' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'NOT SET'}")

if len(sys.argv) < 2:
    print("Usage: python test_sync_manual.py <phase2_file.json>")
    sys.exit(1)

phase2_file = sys.argv[1]

if not Path(phase2_file).exists():
    print(f"Error: File not found: {phase2_file}")
    sys.exit(1)

print(f"\nTesting sync for: {phase2_file}")
print("=" * 60)

try:
    from services.supabase_sync_individual_v2 import sync_individual_records
    
    print("Calling sync_individual_records...")
    submission_ids = sync_individual_records(phase2_file, submitter_email="system@psa.local")
    
    print(f"\nSuccess! Created {len(submission_ids)} submissions")
    if submission_ids:
        print(f"First submission ID: {submission_ids[0]}")
    
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

