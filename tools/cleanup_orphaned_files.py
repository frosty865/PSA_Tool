"""
Clean Orphaned Files in VOFC Processing Pipeline

Identifies and removes:
- Files stuck in processing/ directory
- Temporary files (.tmp, .lock, etc.)
- Orphaned JSON files without corresponding PDFs
- Files without corresponding Supabase submissions (optional)
- Old temporary phase files

Usage:
    python tools/cleanup_orphaned_files.py [--dry-run] [--check-db] [--age-days N]
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Dict

# Add project directory to Python path
PROJECT_DIR = Path(__file__).parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Data directories
BASE_DIR = Path(r"C:\Tools\Ollama\Data")
INCOMING_DIR = BASE_DIR / "incoming"
PROCESSING_DIR = BASE_DIR / "processing"
PROCESSED_DIR = BASE_DIR / "processed"
LIBRARY_DIR = BASE_DIR / "library"
ERROR_DIR = BASE_DIR / "errors"
REVIEW_DIR = BASE_DIR / "review"
REVIEW_TEMP_DIR = REVIEW_DIR / "temp"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("cleanup_orphaned")


def get_file_age_hours(file_path: Path) -> float:
    """Get file age in hours."""
    try:
        mtime = file_path.stat().st_mtime
        age_seconds = time.time() - mtime
        return age_seconds / 3600.0
    except Exception:
        return 0.0


def find_orphaned_files(
    age_hours: float = 24.0,
    check_db: bool = False
) -> Dict[str, List[Path]]:
    """
    Find orphaned files across all directories.
    
    Excludes project files (files in project directory).
    
    Returns:
        Dictionary with categories of orphaned files
    """
    orphaned = {
        "stuck_processing": [],      # Files stuck in processing/
        "temp_files": [],            # .tmp, .lock, etc.
        "orphaned_json": [],         # JSON without corresponding PDF
        "old_phase_files": [],       # Old phase output files
        "small_json": [],            # JSON files under 2KB (likely corrupted)
        "duplicate_outputs": [],     # Multiple outputs for same source
        "orphaned_scripts": [],      # Orphaned .py scripts in data dirs
        "orphaned_ps1": []          # Orphaned .ps1 scripts in data dirs
    }
    
    # Exclude project directory from cleanup
    project_dirs = [
        PROJECT_DIR,
        Path(r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool")
    ]
    
    # Helper to check if file is in project directory
    def is_project_file(file_path: Path) -> bool:
        """Check if file is in project directory (should not be cleaned)."""
        try:
            return any(file_path.is_relative_to(proj_dir) for proj_dir in project_dirs)
        except (ValueError, AttributeError):
            # Python < 3.9 compatibility
            try:
                return any(str(file_path).startswith(str(proj_dir)) for proj_dir in project_dirs)
            except:
                return False
    
    # 1. Find files stuck in processing/ (older than age_hours)
    if PROCESSING_DIR.exists():
        for file_path in PROCESSING_DIR.glob("*"):
            if file_path.is_file() and not is_project_file(file_path):
                age = get_file_age_hours(file_path)
                if age > age_hours:
                    orphaned["stuck_processing"].append(file_path)
    
    # 2. Find temporary files
    temp_patterns = ["*.tmp", "*.lock", "*.temp", "*.bak", "*.old", "*~"]
    for directory in [PROCESSING_DIR, PROCESSED_DIR, REVIEW_TEMP_DIR, ERROR_DIR]:
        if directory.exists() and not is_project_file(directory):
            for pattern in temp_patterns:
                for temp_file in directory.glob(pattern):
                    if not is_project_file(temp_file):
                        orphaned["temp_files"].append(temp_file)
                for temp_file in directory.glob(f"**/{pattern}"):
                    if not is_project_file(temp_file):
                        orphaned["temp_files"].append(temp_file)
    
    # 3. Find orphaned JSON files (no corresponding PDF in library)
    if PROCESSED_DIR.exists() and not is_project_file(PROCESSED_DIR):
        library_pdfs = {f.stem.lower(): f for f in LIBRARY_DIR.glob("*.pdf")} if LIBRARY_DIR.exists() else {}
        
        for json_file in PROCESSED_DIR.glob("*_vofc.json"):
            if is_project_file(json_file):
                continue
            
            # Extract base name (remove _vofc suffix)
            base_name = json_file.stem.replace("_vofc", "").lower()
            
            # Check if corresponding PDF exists
            if base_name not in library_pdfs:
                # Check if it's old (older than age_hours)
                age = get_file_age_hours(json_file)
                if age > age_hours:
                    orphaned["orphaned_json"].append(json_file)
    
    # 4. Find old phase files in review/temp
    if REVIEW_TEMP_DIR.exists() and not is_project_file(REVIEW_TEMP_DIR):
        phase_patterns = ["*_phase1_parser.json", "*_phase2_engine.json", "*_phase2_normalized.json", "*_phase3_auditor.json"]
        for pattern in phase_patterns:
            for phase_file in REVIEW_TEMP_DIR.glob(pattern):
                if not is_project_file(phase_file):
                    age = get_file_age_hours(phase_file)
                    if age > age_hours:
                        orphaned["old_phase_files"].append(phase_file)
    
    # 5. Find small JSON files (likely corrupted or empty)
    for directory in [PROCESSED_DIR, REVIEW_TEMP_DIR]:
        if directory.exists() and not is_project_file(directory):
            for json_file in directory.glob("*.json"):
                if is_project_file(json_file):
                    continue
                try:
                    size = json_file.stat().st_size
                    if size < 2048:  # Under 2KB
                        orphaned["small_json"].append(json_file)
                except Exception:
                    pass
    
    # 6. Find duplicate outputs (same base name, multiple JSON files)
    if PROCESSED_DIR.exists() and not is_project_file(PROCESSED_DIR):
        base_names = {}
        for json_file in PROCESSED_DIR.glob("*_vofc.json"):
            if is_project_file(json_file):
                continue
            base = json_file.stem.replace("_vofc", "").lower()
            if base not in base_names:
                base_names[base] = []
            base_names[base].append(json_file)
        
        for base, files in base_names.items():
            if len(files) > 1:
                # Keep the newest, mark others as duplicates
                files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                orphaned["duplicate_outputs"].extend(files[1:])  # All except newest
    
    # 7. Find orphaned Python scripts in data directories
    # (scripts that shouldn't be in data dirs, only in project/tools)
    script_dirs = [PROCESSING_DIR, PROCESSED_DIR, REVIEW_TEMP_DIR, ERROR_DIR, INCOMING_DIR, LIBRARY_DIR]
    for directory in script_dirs:
        if directory.exists() and not is_project_file(directory):
            for py_file in directory.glob("*.py"):
                # Skip if it's in a project directory
                if is_project_file(py_file):
                    continue
                
                # Check if it's old or looks orphaned
                age = get_file_age_hours(py_file)
                if age > age_hours:
                    # Check if it's a known utility script (keep those)
                    if py_file.name not in ["__init__.py", "utils.py", "helpers.py"]:
                        orphaned["orphaned_scripts"].append(py_file)
    
    # 8. Find orphaned PowerShell scripts in data directories
    for directory in script_dirs:
        if directory.exists() and not is_project_file(directory):
            for ps1_file in directory.glob("*.ps1"):
                # Skip if it's in a project directory
                if is_project_file(ps1_file):
                    continue
                
                # Check if it's old or looks orphaned
                age = get_file_age_hours(ps1_file)
                if age > age_hours:
                    # Check if it's a known utility script (keep those)
                    if ps1_file.name not in ["setup.ps1", "config.ps1"]:
                        orphaned["orphaned_ps1"].append(ps1_file)
    
    return orphaned


def check_supabase_orphans(file_paths: List[Path]) -> List[Path]:
    """
    Check which files don't have corresponding Supabase submissions.
    
    Returns:
        List of file paths without submissions
    """
    try:
        from services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
    except Exception as e:
        logger.warning(f"Could not connect to Supabase: {e}")
        return []
    
    orphaned = []
    
    for file_path in file_paths:
        try:
            # Extract filename
            filename = file_path.name
            
            # Query submissions table for this filename
            result = supabase.table("submissions").select("id").eq("source", "psa_tool_auto").execute()
            
            # Check if filename appears in any submission's data JSONB
            found = False
            for submission in result.data:
                # Get full submission to check data field
                full_sub = supabase.table("submissions").select("data").eq("id", submission["id"]).single().execute()
                if full_sub.data and full_sub.data.get("data"):
                    data = full_sub.data["data"]
                    if isinstance(data, dict) and data.get("source_file") == filename:
                        found = True
                        break
            
            if not found:
                orphaned.append(file_path)
        except Exception as e:
            logger.debug(f"Error checking {file_path.name}: {e}")
            # If we can't check, assume it's orphaned to be safe
            orphaned.append(file_path)
    
    return orphaned


def cleanup_orphaned_files(
    dry_run: bool = True,
    age_hours: float = 24.0,
    check_db: bool = False,
    move_to_errors: bool = True
) -> Dict[str, int]:
    """
    Clean up orphaned files.
    
    Args:
        dry_run: If True, only report what would be deleted
        age_hours: Minimum age in hours for files to be considered orphaned
        check_db: If True, verify against Supabase before deleting
        move_to_errors: If True, move files to errors/ instead of deleting
    
    Returns:
        Dictionary with counts of files processed
    """
    logger.info("=" * 70)
    logger.info("VOFC Orphaned Files Cleanup")
    logger.info("=" * 70)
    logger.info(f"Dry run: {dry_run}")
    logger.info(f"Minimum age: {age_hours} hours")
    logger.info(f"Check database: {check_db}")
    logger.info(f"Move to errors: {move_to_errors}")
    logger.info("")
    
    # Find orphaned files
    logger.info("Scanning for orphaned files...")
    orphaned = find_orphaned_files(age_hours=age_hours, check_db=check_db)
    
    # Summary
    total_files = sum(len(files) for files in orphaned.values())
    total_size = 0
    
    logger.info("")
    logger.info("Orphaned Files Found:")
    logger.info("-" * 70)
    
    for category, files in orphaned.items():
        if files:
            category_size = sum(f.stat().st_size for f in files if f.exists())
            total_size += category_size
            logger.info(f"{category:20s}: {len(files):4d} files ({category_size:,} bytes)")
    
    logger.info("-" * 70)
    logger.info(f"{'TOTAL':20s}: {total_files:4d} files ({total_size:,} bytes / {total_size / 1024 / 1024:.2f} MB)")
    logger.info("")
    
    if total_files == 0:
        logger.info("✅ No orphaned files found!")
        return {category: 0 for category in orphaned.keys()}
    
    if dry_run:
        logger.info("🔍 DRY RUN: Files would be cleaned up. Run without --dry-run to proceed.")
        return {category: len(files) for category, files in orphaned.items()}
    
    # Actually clean up
    logger.info("🗑️  Cleaning up orphaned files...")
    logger.info("")
    
    counts = {}
    ERROR_DIR.mkdir(parents=True, exist_ok=True)
    
    for category, files in orphaned.items():
        if not files:
            counts[category] = 0
            continue
        
        cleaned = 0
        for file_path in files:
            try:
                if move_to_errors and category in ["stuck_processing", "orphaned_json"]:
                    # Move important files to errors/ for review
                    error_path = ERROR_DIR / f"orphaned_{file_path.name}"
                    if error_path.exists():
                        error_path = ERROR_DIR / f"orphaned_{int(time.time())}_{file_path.name}"
                    shutil.move(str(file_path), str(error_path))
                    logger.debug(f"  Moved {file_path.name} → errors/")
                else:
                    # Delete temporary/small files
                    file_path.unlink()
                    logger.debug(f"  Deleted {file_path.name}")
                cleaned += 1
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to clean {file_path.name}: {e}")
        
        counts[category] = cleaned
        logger.info(f"✅ {category}: Cleaned {cleaned}/{len(files)} files")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"✅ Cleanup complete: Processed {sum(counts.values())} files")
    logger.info("=" * 70)
    
    return counts


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clean orphaned files in VOFC processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/cleanup_orphaned_files.py --dry-run
    Preview what would be cleaned (safe, no changes)
  
  python tools/cleanup_orphaned_files.py
    Clean files older than 24 hours (default)
  
  python tools/cleanup_orphaned_files.py --age-days 7
    Clean files older than 7 days
  
  python tools/cleanup_orphaned_files.py --check-db
    Also verify against Supabase submissions
  
  python tools/cleanup_orphaned_files.py --no-move-to-errors
    Delete files instead of moving to errors/
        """
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be cleaned without making changes")
    parser.add_argument("--age-days", type=float, default=1.0, help="Minimum age in days for files to be considered orphaned (default: 1.0)")
    parser.add_argument("--age-hours", type=float, help="Minimum age in hours (overrides --age-days)")
    parser.add_argument("--check-db", action="store_true", help="Verify files against Supabase before cleaning")
    parser.add_argument("--no-move-to-errors", action="store_true", help="Delete files instead of moving to errors/")
    
    args = parser.parse_args()
    
    age_hours = args.age_hours if args.age_hours else (args.age_days * 24.0)
    
    try:
        cleanup_orphaned_files(
            dry_run=args.dry_run,
            age_hours=age_hours,
            check_db=args.check_db,
            move_to_errors=not args.no_move_to_errors
        )
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Cleanup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

