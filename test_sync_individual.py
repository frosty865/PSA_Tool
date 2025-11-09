"""
Test script to manually test individual record sync
"""
import sys
from pathlib import Path
from services.supabase_sync_individual import sync_individual_records

# Find the largest phase1_parser.json file in review/temp
review_temp = Path(r"C:\Tools\Ollama\Data\review\temp")
files = list(review_temp.glob("*_phase1_parser.json"))

if not files:
    print("No phase1_parser.json files found in review/temp")
    sys.exit(1)

# Get the largest file
largest_file = max(files, key=lambda f: f.stat().st_size)
print(f"Testing sync with: {largest_file.name} ({largest_file.stat().st_size} bytes)")

try:
    submission_ids = sync_individual_records(str(largest_file), submitter_email="system@psa.local")
    print(f"\n✅ Successfully created {len(submission_ids)} submissions")
    print(f"Submission IDs: {submission_ids[:5]}..." if len(submission_ids) > 5 else f"Submission IDs: {submission_ids}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

