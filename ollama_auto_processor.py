"""
Ollama Auto Processor
Automated document processing script for VOFC Engine
Monitors incoming directory, processes documents, and manages file lifecycle
"""

import os
import shutil
import json
import time
import logging
import traceback
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Import processing modules
from services.preprocess import preprocess_document
from services.ollama_client import run_model_on_chunks
from services.postprocess import postprocess_results
from services.supabase_client import get_supabase_client, insert_library_record, check_review_approval

# Import watchdog for folder monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# ============================================================================
# Directory Configuration
# ============================================================================

BASE_DIR = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))
INCOMING_DIR = BASE_DIR / "incoming"
PROCESSED_DIR = BASE_DIR / "processed"
LIBRARY_DIR = BASE_DIR / "library"
ERROR_DIR = BASE_DIR / "errors"
REVIEW_DIR = BASE_DIR / "review"
AUTOMATION_DIR = BASE_DIR / "automation"
PROGRESS_FILE = AUTOMATION_DIR / "progress.json"
LOG_FILE = AUTOMATION_DIR / "vofc_auto_processor.log"

# ============================================================================
# Setup
# ============================================================================

def ensure_dirs():
    """Create all required directories if they don't exist"""
    for d in [INCOMING_DIR, PROCESSED_DIR, LIBRARY_DIR, ERROR_DIR, REVIEW_DIR, AUTOMATION_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    logging.info(f"Ensured all directories exist in {BASE_DIR}")

# Setup logging
AUTOMATION_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True  # Override any existing configuration
)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logging.getLogger().addHandler(console_handler)

# Log watchdog availability
if not WATCHDOG_AVAILABLE:
    logging.warning("watchdog not installed. Install with: pip install watchdog")

# ============================================================================
# Progress Tracking
# ============================================================================

def update_progress() -> Dict[str, Any]:
    """
    Update progress.json with current file counts across all directories
    
    Returns:
        Dictionary with file counts and timestamp
    """
    try:
        # Count files in each directory
        incoming_count = len([f for f in INCOMING_DIR.glob("*.*") if f.is_file()])
        processed_count = len([f for f in PROCESSED_DIR.glob("*.json") if f.is_file()])
        library_count = len([f for f in LIBRARY_DIR.glob("*.*") if f.is_file()])
        errors_count = len([f for f in ERROR_DIR.glob("*.*") if f.is_file()])
        review_count = len([f for f in REVIEW_DIR.glob("*.json") if f.is_file()])
        
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "incoming": incoming_count,
            "processed": processed_count,
            "library": library_count,
            "errors": errors_count,
            "review": review_count,
            "status": "running" if incoming_count > 0 else "idle"
        }
        
        with open(PROGRESS_FILE, "w", encoding="utf-8") as pf:
            json.dump(data, pf, indent=2)
        
        return data
    except Exception as e:
        logging.error(f"Failed to update progress: {e}")
        return {}

# ============================================================================
# File Processing
# ============================================================================

def process_document_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Process a single document file through the full pipeline:
    1. Preprocess (extract, normalize, chunk)
    2. Run Ollama model on chunks
    3. Post-process (clean, deduplicate, resolve taxonomy)
    
    Args:
        filepath: Path to the document file
        
    Returns:
        Post-processed results dictionary or None on failure
    """
    try:
        logging.info(f"Starting processing for {filepath.name}")
        
        # Step 1: Preprocess document
        logging.info(f"Preprocessing {filepath.name}...")
        chunks = preprocess_document(str(filepath))
        
        if not chunks:
            raise ValueError(f"No chunks extracted from {filepath.name}")
        
        logging.info(f"Extracted {len(chunks)} chunks from {filepath.name}")
        
        # Step 2: Run Ollama model on chunks
        logging.info(f"Running Ollama model on {len(chunks)} chunks...")
        model_results = run_model_on_chunks(chunks, model="psa-engine:latest")
        
        if not model_results:
            raise ValueError(f"No results from Ollama model for {filepath.name}")
        
        logging.info(f"Model returned {len(model_results)} results")
        
        # Step 3: Post-process results
        # Ensure model_results are in the correct format for postprocessing
        # run_model_on_chunks returns results with chunk metadata already attached
        logging.info(f"Post-processing {len(model_results)} model results...")
        final_results = postprocess_results(model_results)
        
        if not final_results:
            raise ValueError(f"No valid records after post-processing for {filepath.name}")
        
        logging.info(f"Post-processing complete: {len(final_results)} unique records")
        
        # Prepare result structure
        result = {
            "source_file": filepath.name,
            "processed_at": datetime.now().isoformat(),
            "chunks_processed": len(chunks),
            "model_results": len(model_results),
            "final_records": len(final_results),
            "vulnerabilities": [
                {
                    "vulnerability": r.get("vulnerability", ""),
                    "discipline_id": r.get("discipline_id"),
                    "category": r.get("category"),
                    "sector_id": r.get("sector_id"),
                    "subsector_id": r.get("subsector_id"),
                    "page_ref": r.get("page_ref"),
                    "chunk_id": r.get("chunk_id")
                }
                for r in final_results
            ],
            "options_for_consideration": [
                {
                    "option_text": ofc,
                    "vulnerability": r.get("vulnerability", ""),
                    "discipline_id": r.get("discipline_id"),
                    "sector_id": r.get("sector_id"),
                    "subsector_id": r.get("subsector_id")
                }
                for r in final_results
                for ofc in r.get("options_for_consideration", [])
            ],
            "summary": f"Processed {filepath.name}: {len(final_results)} vulnerabilities, {sum(len(r.get('options_for_consideration', [])) for r in final_results)} OFCs"
        }
        
        logging.info(f"Successfully processed {filepath.name}")
        return result
        
    except Exception as e:
        logging.error(f"Error processing {filepath.name}: {e}")
        logging.error(traceback.format_exc())
        raise

# ============================================================================
# File Management
# ============================================================================

def handle_successful_processing(filepath: Path, result: Dict[str, Any]) -> None:
    """
    Handle successful document processing:
    1. Save JSON output to processed/
    2. Move original to library/
    3. Copy JSON to review/ for admin validation
    
    Args:
        filepath: Path to original document
        result: Processing result dictionary
    """
    try:
        filename = filepath.stem
        
        # Save JSON output to processed/
        json_out = PROCESSED_DIR / f"{filename}_vofc.json"
        with open(json_out, "w", encoding="utf-8") as jf:
            json.dump(result, jf, indent=2)
        
        logging.info(f"Saved JSON output to {json_out}")
        
        # Move original document to library/
        library_path = LIBRARY_DIR / filepath.name
        shutil.move(str(filepath), str(library_path))
        logging.info(f"Moved {filepath.name} to library/")
        
        # Copy JSON output to review/ for admin validation
        review_path = REVIEW_DIR / json_out.name
        shutil.copy(str(json_out), str(review_path))
        logging.info(f"Copied JSON to review/ for admin validation")
        
    except Exception as e:
        logging.error(f"Error handling successful processing for {filepath.name}: {e}")
        raise

def handle_failed_processing(filepath: Path, error: Exception) -> None:
    """
    Handle failed document processing:
    1. Write error log to errors/
    2. Move failed document to errors/
    
    Args:
        filepath: Path to failed document
        error: Exception that occurred
    """
    try:
        filename = filepath.stem
        
        # Write error log
        error_txt = ERROR_DIR / f"{filename}_error.txt"
        with open(error_txt, "w", encoding="utf-8") as ef:
            ef.write(f"Processing failed for {filepath.name}\n\n")
            ef.write(f"Error: {str(error)}\n\n")
            ef.write(f"Traceback:\n{traceback.format_exc()}\n")
        
        logging.error(f"Wrote error log to {error_txt}")
        
        # Move failed document to errors/
        error_path = ERROR_DIR / filepath.name
        shutil.move(str(filepath), str(error_path))
        logging.info(f"Moved {filepath.name} to errors/")
        
    except Exception as e:
        logging.error(f"Error handling failed processing for {filepath.name}: {e}")
        # Last resort - try to move to errors without log
        try:
            error_path = ERROR_DIR / filepath.name
            shutil.move(str(filepath), str(error_path))
        except:
            pass

# ============================================================================
# Folder Watcher
# ============================================================================

class IncomingWatcher(FileSystemEventHandler):
    """Monitors incoming folder for new files and triggers processing."""
    
    def __init__(self):
        super().__init__()
        self.processing_files = set()  # Track files being processed to avoid duplicates
    
    def _process_file_if_supported(self, path: Path):
        """Helper method to process a file if it's supported"""
        # Check if file is supported
        supported_extensions = {'.pdf', '.docx', '.txt', '.xlsx'}
        if path.suffix.lower() not in supported_extensions:
            return
        
        # Avoid processing the same file multiple times
        if path.name in self.processing_files:
            logging.debug(f"Skipping {path.name} - already processing")
            return
        
        # Wait a moment for file to be fully written
        time.sleep(1)
        
        # Check if file still exists and is readable
        if not path.exists():
            logging.warning(f"File {path.name} no longer exists after wait")
            return
        
        logging.info(f"📂 New file detected: {path.name}")
        
        try:
            self.processing_files.add(path.name)
            process_file(path)
        except Exception as e:
            logging.error(f"❌ Auto-processing failed for {path.name}: {e}")
            logging.error(traceback.format_exc())
        finally:
            # Remove from processing set after a delay
            threading.Timer(60.0, lambda: self.processing_files.discard(path.name)).start()
    
    def on_created(self, event):
        """Handle new file creation events"""
        if event.is_directory:
            return
        
        path = Path(event.src_path)
        self._process_file_if_supported(path)
    
    def on_moved(self, event):
        """Handle file move/copy events (some file operations trigger moved instead of created)"""
        if event.is_directory:
            return
        
        # When a file is moved/copied, event.dest_path contains the new location
        path = Path(event.dest_path) if hasattr(event, 'dest_path') and event.dest_path else Path(event.src_path)
        self._process_file_if_supported(path)

def start_folder_watcher():
    """Start the folder watcher to monitor incoming directory"""
    if not WATCHDOG_AVAILABLE:
        logging.error("Cannot start folder watcher: watchdog not installed")
        return
    
    event_handler = IncomingWatcher()
    observer = Observer()
    observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
    observer.start()
    
    logging.info(f"📂 Folder watcher started for {INCOMING_DIR}")
    logging.info("Monitoring for new files (PDF, DOCX, TXT, XLSX)...")
    
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logging.info("Folder watcher interrupted by user")
        observer.stop()
    
    observer.join()
    logging.info("Folder watcher stopped")

# ============================================================================
# File Processing (Refactored)
# ============================================================================

def process_file(filepath: Path) -> None:
    """
    Complete file processing workflow:
    1. Ensure directories exist
    2. Process document (preprocess → model → postprocess)
    3. Handle success (save JSON, move to library, copy to review)
    4. Handle failure (error log, move to errors)
    5. Update progress
    
    Args:
        filepath: Path to the document file to process
    """
    ensure_dirs()
    
    try:
        # Process document through pipeline
        result = process_document_file(filepath)
        
        # Handle successful processing
        handle_successful_processing(filepath, result)
        
        logging.info(f"✅ Successfully processed {filepath.name}")
        
    except Exception as e:
        # Handle failed processing
        handle_failed_processing(filepath, e)
        logging.error(f"❌ Failed to process {filepath.name}: {e}")
    
    finally:
        # Update progress after processing
        update_progress()

# ============================================================================
# Supabase Sync
# ============================================================================

# Note: check_review_approval and insert_library_record are imported from services.supabase_client

def sync_review_to_supabase() -> None:
    """
    Sync approved review JSON files from review/ folder to Supabase production tables.
    Checks for approval status and moves synced files to processed/.
    """
    try:
        review_files = list(REVIEW_DIR.glob("*.json"))
        
        if not review_files:
            return
        
        logging.info(f"Checking {len(review_files)} review file(s) for Supabase sync...")
        
        synced_count = 0
        
        for review_file in review_files:
            try:
                # Extract filename without extension for approval check
                filename_stem = review_file.stem.replace('_vofc', '')  # Remove _vofc suffix if present
                
                # Check if this review file has been approved
                if not check_review_approval(filename_stem):
                    continue
                
                logging.info(f"📤 Syncing approved review file: {review_file.name}")
                
                # Load JSON data
                with open(review_file, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                
                # Insert into Supabase production tables
                result = insert_library_record(data)
                success = result.get('success', False) if isinstance(result, dict) else bool(result)
                
                if success:
                    # Move to processed/ after successful sync
                    dest = PROCESSED_DIR / review_file.name
                    shutil.move(str(review_file), str(dest))
                    logging.info(f"✅ Synced and moved {review_file.name} to processed/")
                    synced_count += 1
                else:
                    logging.warning(f"⚠️ Failed to insert data for {review_file.name}, keeping in review/")
                    
            except Exception as e:
                logging.error(f"❌ Supabase sync failed for {review_file.name}: {e}")
                logging.error(traceback.format_exc())
                continue
        
        if synced_count > 0:
            logging.info(f"📊 Synced {synced_count} approved review file(s) to Supabase")
        
    except Exception as e:
        logging.error(f"Error in sync_review_to_supabase: {e}")
        logging.error(traceback.format_exc())

# ============================================================================
# Main Processing Loop (Legacy - for batch processing)
# ============================================================================

def get_incoming_files() -> list[Path]:
    """
    Get list of files in incoming/ directory
    
    Returns:
        List of Path objects for files to process
    """
    try:
        # Get all files (exclude subdirectories and hidden files)
        files = [
            f for f in INCOMING_DIR.iterdir()
            if f.is_file() and not f.name.startswith('.')
        ]
        
        # Filter by supported extensions
        supported_extensions = {'.pdf', '.docx', '.txt', '.xlsx'}
        files = [f for f in files if f.suffix.lower() in supported_extensions]
        
        return sorted(files, key=lambda x: x.stat().st_mtime)  # Process oldest first
    except Exception as e:
        logging.error(f"Error getting incoming files: {e}")
        return []

def process_incoming_files() -> None:
    """
    Main processing loop: process all files in incoming/ directory
    """
    logging.info("=" * 60)
    logging.info("Starting document processing cycle")
    logging.info("=" * 60)
    
    # Update progress
    progress = update_progress()
    logging.info(f"Current status: {progress.get('status', 'unknown')}")
    logging.info(f"Incoming files: {progress.get('incoming', 0)}")
    
    # Get files to process
    files = get_incoming_files()
    
    if not files:
        logging.info("No files to process")
        return
    
    logging.info(f"Found {len(files)} file(s) to process")
    
    # Process each file
    for filepath in files:
        try:
            logging.info(f"\n{'=' * 60}")
            logging.info(f"Processing: {filepath.name}")
            logging.info(f"{'=' * 60}")
            
            # Process document
            result = process_document_file(filepath)
            
            # Handle successful processing
            handle_successful_processing(filepath, result)
            
            logging.info(f"✅ Successfully processed {filepath.name}")
            
        except Exception as e:
            # Handle failed processing
            handle_failed_processing(filepath, e)
            logging.error(f"❌ Failed to process {filepath.name}: {e}")
        
        finally:
            # Update progress after each file
            update_progress()
    
    # Final progress update
    final_progress = update_progress()
    logging.info(f"\nProcessing cycle complete")
    logging.info(f"Final status: {final_progress.get('status', 'unknown')}")
    logging.info(f"Remaining incoming files: {final_progress.get('incoming', 0)}")

# ============================================================================
# Cleanup Functions (Future)
# ============================================================================

def cleanup_review_files(days_old: int = 30) -> None:
    """
    Clean up old review files after they've been approved/rejected
    
    Args:
        days_old: Remove review files older than this many days
    """
    try:
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        removed_count = 0
        
        for review_file in REVIEW_DIR.glob("*.json"):
            if review_file.stat().st_mtime < cutoff_time:
                review_file.unlink()
                removed_count += 1
        
        if removed_count > 0:
            logging.info(f"Cleaned up {removed_count} old review file(s)")
    except Exception as e:
        logging.warning(f"Error during cleanup: {e}")

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the auto processor with folder watcher"""
    try:
        # Ensure directories exist
        ensure_dirs()
        
        logging.info("=" * 60)
        logging.info("Starting VOFC Auto-Processor with folder watcher...")
        logging.info("=" * 60)
        
        # Process any existing files in incoming/ first
        existing_files = get_incoming_files()
        if existing_files:
            logging.info(f"Processing {len(existing_files)} existing file(s) in incoming/...")
            for filepath in existing_files:
                try:
                    process_file(filepath)
                except Exception as e:
                    logging.error(f"Error processing existing file {filepath.name}: {e}")
        
        # Start folder watcher in background thread
        if WATCHDOG_AVAILABLE:
            watcher_thread = threading.Thread(target=start_folder_watcher, daemon=True)
            watcher_thread.start()
            logging.info("✅ Folder watcher thread started")
        else:
            logging.warning("⚠️ Folder watcher not available (watchdog not installed)")
            logging.info("Falling back to periodic polling mode...")
        
        # Main loop: periodic Supabase sync
        sync_interval = 600  # 10 minutes
        logging.info(f"Starting Supabase sync loop (every {sync_interval} seconds)...")
        
        while True:
            try:
                # Sync approved review files to Supabase
                sync_review_to_supabase()
                
                # Update progress
                update_progress()
                
                # Sleep until next sync
                time.sleep(sync_interval)
                
            except KeyboardInterrupt:
                logging.info("Main loop interrupted by user")
                break
            except Exception as e:
                logging.error(f"Error in main sync loop: {e}")
                logging.error(traceback.format_exc())
                # Continue running even if sync fails
                time.sleep(sync_interval)
        
    except KeyboardInterrupt:
        logging.info("Processing interrupted by user")
    except Exception as e:
        logging.error(f"Fatal error in main loop: {e}")
        logging.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main()

