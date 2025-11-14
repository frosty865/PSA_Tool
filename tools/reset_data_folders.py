"""
Reset VOFC Data Folders to Base State

This script clears all processed files, temp files, and review files
while preserving the folder structure.

Usage:
    python tools/reset_data_folders.py [--dry-run] [--keep-library]
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Add project directory to Python path
PROJECT_DIR = Path(__file__).parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Data directories - use centralized config
from config import Config
BASE_DIR = Config.DATA_DIR
INCOMING_DIR = Config.INCOMING_DIR
REVIEW_DIR = Config.REVIEW_DIR
REVIEW_TEMP_DIR = REVIEW_DIR / "temp"
PROCESSED_DIR = Config.PROCESSED_DIR
LIBRARY_DIR = Config.LIBRARY_DIR
ERROR_DIR = Config.ERRORS_DIR
# Training data can be in either location
TRAINING_PARSED_DIR = Path(r"C:\Tools\VOFC-Flask\training_data\parsed") if Path(r"C:\Tools\VOFC-Flask\training_data\parsed").exists() else Path(r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\training_data\parsed")

# Directories to clean (with descriptions)
CLEANUP_DIRS = {
    REVIEW_TEMP_DIR: "Review temp files (phase outputs, sync files)",
    REVIEW_DIR: "Review folder (approved/rejected files)",
    PROCESSED_DIR: "Processed files (final outputs)",
    ERROR_DIR: "Error logs and failed files",
    TRAINING_PARSED_DIR: "Training parsed data",
    # Note: INCOMING_DIR and LIBRARY_DIR are preserved by default
}

def reset_folders(dry_run=False, keep_library=False, keep_incoming=True):
    """
    Reset data folders to base state.
    
    Args:
        dry_run: If True, only show what would be deleted without actually deleting
        keep_library: If True, preserve files in library directory
        keep_incoming: If True, preserve files in incoming directory
    """
    print("=" * 70)
    print("VOFC Data Folders Reset Script")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Dry run: {dry_run}")
    print(f"Keep library: {keep_library}")
    print(f"Keep incoming: {keep_incoming}")
    print()
    
    total_files = 0
    total_size = 0
    
    # Clean up each directory
    for dir_path, description in CLEANUP_DIRS.items():
        if not dir_path.exists():
            print(f"⏭️  {dir_path.name}: Directory doesn't exist, skipping")
            continue
        
        # Count files and size
        files_to_delete = []
        dir_size = 0
        
        for item in dir_path.rglob("*"):
            if item.is_file():
                files_to_delete.append(item)
                dir_size += item.stat().st_size
        
        total_files += len(files_to_delete)
        total_size += dir_size
        
        if dry_run:
            print(f"📋 {dir_path.name}: Would delete {len(files_to_delete)} files ({dir_size:,} bytes)")
            if files_to_delete:
                print(f"   {description}")
        else:
            if files_to_delete:
                print(f"🗑️  {dir_path.name}: Deleting {len(files_to_delete)} files ({dir_size:,} bytes)...")
                for file_path in files_to_delete:
                    try:
                        file_path.unlink()
                    except Exception as e:
                        print(f"   ⚠️  Failed to delete {file_path.name}: {e}")
                
                # Remove empty subdirectories
                for subdir in sorted(dir_path.rglob("*"), reverse=True):
                    if subdir.is_dir() and not any(subdir.iterdir()):
                        try:
                            subdir.rmdir()
                        except Exception:
                            pass
                
                print(f"   ✅ Cleaned {dir_path.name}")
            else:
                print(f"✅ {dir_path.name}: Already empty")
    
    # Handle library directory
    if not keep_library and LIBRARY_DIR.exists():
        library_files = list(LIBRARY_DIR.glob("*"))
        library_size = sum(f.stat().st_size for f in library_files if f.is_file())
        
        if dry_run:
            print(f"📋 {LIBRARY_DIR.name}: Would delete {len(library_files)} files ({library_size:,} bytes)")
        else:
            if library_files:
                print(f"🗑️  {LIBRARY_DIR.name}: Deleting {len(library_files)} files ({library_size:,} bytes)...")
                for file_path in library_files:
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"   ⚠️  Failed to delete {file_path.name}: {e}")
                print(f"   ✅ Cleaned {LIBRARY_DIR.name}")
            else:
                print(f"✅ {LIBRARY_DIR.name}: Already empty")
    
    # Handle incoming directory
    if not keep_incoming and INCOMING_DIR.exists():
        incoming_files = list(INCOMING_DIR.glob("*"))
        incoming_size = sum(f.stat().st_size for f in incoming_files if f.is_file())
        
        if dry_run:
            print(f"📋 {INCOMING_DIR.name}: Would delete {len(incoming_files)} files ({incoming_size:,} bytes)")
        else:
            if incoming_files:
                print(f"🗑️  {INCOMING_DIR.name}: Deleting {len(incoming_files)} files ({incoming_size:,} bytes)...")
                for file_path in incoming_files:
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"   ⚠️  Failed to delete {file_path.name}: {e}")
                print(f"   ✅ Cleaned {INCOMING_DIR.name}")
            else:
                print(f"✅ {INCOMING_DIR.name}: Already empty")
    
    print()
    print("=" * 70)
    if dry_run:
        print(f"DRY RUN: Would delete {total_files} files ({total_size:,} bytes / {total_size / 1024 / 1024:.2f} MB)")
        print("Run without --dry-run to actually delete files")
    else:
        print(f"✅ Reset complete: Deleted {total_files} files ({total_size:,} bytes / {total_size / 1024 / 1024:.2f} MB)")
    print("=" * 70)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reset VOFC data folders to base state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/reset_data_folders.py --dry-run
    Preview what would be deleted
  
  python tools/reset_data_folders.py
    Reset all folders (clears library, keeps incoming by default)
  
  python tools/reset_data_folders.py --clear-library
    Also clear library folder
  
  python tools/reset_data_folders.py --clear-incoming
    Also clear incoming folder
  
  python tools/reset_data_folders.py --clear-library --clear-incoming
    Clear everything including library and incoming
        """
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--keep-library", action="store_true", help="Preserve files in library directory (default: library is cleared)")
    parser.add_argument("--keep-incoming", action="store_true", help="Preserve files in incoming directory (default: incoming is preserved)")
    parser.add_argument("--clear-incoming", action="store_true", help="Also clear incoming directory")
    parser.add_argument("--clear-library", action="store_true", help="Also clear library directory (this is the default, flag is for clarity)")
    
    args = parser.parse_args()
    
    # Determine keep_incoming: --clear-incoming overrides --keep-incoming
    if args.clear_incoming:
        keep_incoming = False
    else:
        keep_incoming = args.keep_incoming
    
    # Determine keep_library: --clear-library means don't keep (default behavior)
    # --keep-library means keep it
    keep_library = args.keep_library
    
    try:
        reset_folders(
            dry_run=args.dry_run,
            keep_library=args.keep_library,
            keep_incoming=keep_incoming
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Reset cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during reset: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

