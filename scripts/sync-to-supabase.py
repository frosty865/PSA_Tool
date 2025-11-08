#!/usr/bin/env python3
"""
Manual Supabase Sync Script
Usage:
    python sync-to-supabase.py <file_path>
    python sync-to-supabase.py --all
    python sync-to-supabase.py --review-dir
"""

import sys
import os
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.supabase_sync import sync_processed_result

def sync_file(file_path: str):
    """Sync a single file to Supabase"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return False
    
    print(f"Syncing: {file_path.name}")
    
    try:
        submission_id = sync_processed_result(str(file_path), submitter_email="system@psa.local")
        print(f"[OK] Successfully synced! Submission ID: {submission_id}")
        return True
    except Exception as e:
        print(f"[ERROR] Error syncing {file_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def sync_all_in_review():
    """Sync all JSON files in the review directory"""
    review_dir = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data")) / "review"
    
    if not review_dir.exists():
        print(f"[ERROR] Review directory not found: {review_dir}")
        return
    
    json_files = list(review_dir.glob("*.json"))
    
    if not json_files:
        print(f"[WARNING] No JSON files found in {review_dir}")
        return
    
    print(f"Found {len(json_files)} JSON file(s) in review/")
    print("")
    
    success_count = 0
    fail_count = 0
    
    for json_file in json_files:
        if sync_file(str(json_file)):
            success_count += 1
        else:
            fail_count += 1
        print("")
    
    print("=" * 50)
    print(f"Summary:")
    print(f"  [OK] Successful: {success_count}")
    print(f"  [ERROR] Failed: {fail_count}")
    print("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Manually sync processed results to Supabase")
    parser.add_argument("file", nargs="?", help="Path to JSON file to sync")
    parser.add_argument("--all", action="store_true", help="Sync all files in review/ directory")
    parser.add_argument("--review-dir", action="store_true", help="Sync all files in review/ directory (alias for --all)")
    
    args = parser.parse_args()
    
    if args.all or args.review_dir:
        sync_all_in_review()
    elif args.file:
        success = sync_file(args.file)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python sync-to-supabase.py path/to/file.json")
        print("  python sync-to-supabase.py --all")
        sys.exit(1)

if __name__ == "__main__":
    main()

