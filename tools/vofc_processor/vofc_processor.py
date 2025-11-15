"""
VOFC Processor - Reliable Extraction Version
Chunk-based processing pipeline for physical security document extraction.

Flow: PDF → structured extraction → chunking → model (per chunk) → merge → dedupe → normalize → Supabase → archive
"""
import os
import sys
import json
import logging
import time
import threading
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from config.exceptions import ServiceError, FileOperationError, DependencyError, ConfigurationError

# ==========================================================
# LOGGING SETUP (MUST BE FIRST - before any other imports that log)
# ==========================================================

# Base data directory - use centralized config (needed for log path)
from config import Config
LOGS_DIR = Config.LOGS_DIR

# Ensure log directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Create log file path - single rolling log file (not date-specific)
LOG_FILE = os.path.join(LOGS_DIR, "vofc_processor.log")

# Configure logging with explicit handlers
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
logger.handlers.clear()

# Create file handler with explicit encoding and immediate flush
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8", delay=False)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
# Ensure immediate flushing for real-time log viewing
file_handler.stream.reconfigure(line_buffering=True) if hasattr(file_handler.stream, 'reconfigure') else None

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Also configure root logger to ensure all logging goes to file
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Only add handlers if root logger doesn't have them (avoid duplicates)
if not root_logger.handlers:
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

# Add services directory to path for imports
# Support both project structure and deployed structure
script_dir = Path(__file__).parent
if (script_dir / "services").exists():
    # Deployed structure: C:\Tools\vofc_processor\services
    sys.path.insert(0, str(script_dir))
else:
    # Project structure: services/processor is at project root
    sys.path.insert(0, str(script_dir.parent.parent))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    logger.warning("watchdog not available - will use polling mode instead of file watching")

# Import new modular processor
from services.processor.processor.run_processor import process_pdf as process_pdf_chunked
from services.processor.normalization.supabase_upload import upload_to_supabase, init_supabase


# ==========================================================
# CONFIGURATION
# ==========================================================

# Load .env file if available
try:
    from dotenv import load_dotenv
    script_dir = Path(__file__).parent
    possible_env_paths = [
        Path(r"C:\Tools\.env"),  # Primary location for shared .env
        script_dir.parent.parent / ".env",
        script_dir / ".env",
        Path(r"C:\Tools\VOFC-Flask\.env"),
        Path(r"C:\Tools\PSA_Tool\.env"),  # Legacy path
        Path(r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env"),  # Legacy path
    ]
    
    env_loaded = False
    for env_path in possible_env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=False)
            logger.info(f"Loaded environment variables from {env_path}")
            env_loaded = True
            break
    
    if not env_loaded:
        logger.debug("No .env file found in standard locations")
except ImportError:
    logger.warning("python-dotenv not installed - .env file will not be loaded automatically")
except (FileNotFoundError, PermissionError, OSError) as e:
    logger.debug(f"Could not load .env file (using environment defaults): {e}")
except Exception as e:
    logger.warning(f"Unexpected error loading .env file: {e}", exc_info=True)

# Get remaining config paths
DATA_DIR = Config.DATA_DIR
INCOMING_DIR = Config.INCOMING_DIR
PROCESSED_DIR = Config.PROCESSED_DIR
LIBRARY_DIR = Config.LIBRARY_DIR
TEMP_DIR = Config.TEMP_DIR

# Ensure directories exist
for dir_path in [INCOMING_DIR, PROCESSED_DIR, LIBRARY_DIR, TEMP_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==========================================================
# STARTUP VALIDATION
# ==========================================================

# Validate configuration before starting
try:
    from config import Config, ConfigurationError
    Config.validate()
    logger.info("Configuration validation passed")
except ConfigurationError as e:
    logger.error(f"Configuration validation failed: {e}")
    logger.error("Processor will not start with invalid configuration")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error during configuration validation: {e}", exc_info=True)
    raise ConfigurationError(f"Configuration validation failed: {e}") from e

# ==========================================================
# SUPABASE INITIALIZATION
# ==========================================================

supabase = init_supabase()
if supabase:
    logger.info("[OK] Supabase client initialized")
else:
    logger.warning("[WARN] Supabase not configured - uploads will be skipped")


# ==========================================================
# PROCESSING FUNCTIONS
# ==========================================================

def process_pdf_file(pdf_path: str) -> bool:
    """
    Process a single PDF file through the complete pipeline.
    
    Pipeline:
    1. Extract structured pages → chunk → model (per chunk) → merge → dedupe → normalize
    2. Save JSON output
    3. Upload to Supabase (optional)
    4. Move PDF to library
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        True if successful, False otherwise
    """
    pdf_path_obj = Path(pdf_path)
    base_name = pdf_path_obj.stem
    
    if not pdf_path_obj.exists():
        logger.error(f"PDF not found: {pdf_path}")
        return False
    
    logger.info("=" * 60)
    logger.info(f"Processing: {pdf_path_obj.name}")
    logger.info("=" * 60)
    # Flush logs immediately for real-time monitoring
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()
    
    try:
        # Step 1: Process PDF through chunk-based pipeline
        logger.info("[1/4] Extracting and processing chunks...")
        output_path = process_pdf_chunked(
            path=str(pdf_path),
            output_dir=PROCESSED_DIR,
            model=Config.DEFAULT_MODEL
        )
        
        # Load results to verify
        with open(output_path, "r", encoding="utf-8") as f:
            result_data = json.load(f)
        
        records = result_data.get("records", [])
        record_count = len(records) if records else 0
        
        # Minimum records threshold for moving to library (allows reprocessing for learning)
        min_records_for_library = Config.MIN_RECORDS_FOR_LIBRARY
        
        if record_count == 0:
            logger.warning(f"[WARN] No records extracted from {pdf_path_obj.name}")
            logger.info("File will remain in incoming for reprocessing (model learning)")
            logger.info("JSON results saved - file can be reprocessed to improve extraction")
            # Don't move file - keep in incoming for reprocessing
            return True  # Return True since processing completed (even with 0 records)
        
        logger.info(f"[OK] Extracted {record_count} records")
        logger.info(f"[OK] Saved JSON to: {output_path}")
        # Flush logs after saving JSON
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
        
        # Step 2: Copy JSON to review directory
        logger.info("[2/4] Copying JSON to review directory...")
        review_dir = os.path.join(DATA_DIR, "review")
        os.makedirs(review_dir, exist_ok=True)
        review_path = os.path.join(review_dir, f"{base_name}_vofc.json")
        shutil.copy2(output_path, review_path)
        logger.info(f"[OK] Copied to review: {review_path}")
        
        # Step 3: Upload to Supabase (optional)
        logger.info("[3/4] Uploading to Supabase...")
        try:
            submission_id = upload_to_supabase(
                file_path=str(pdf_path),
                records=records,
                supabase=supabase
            )
            if submission_id:
                logger.info(f"[OK] Uploaded to Supabase (submission_id={submission_id})")
            else:
                # Check why upload failed
                if not supabase:
                    logger.warning("[WARN] Supabase upload skipped: Supabase client not initialized (check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY environment variables)")
                elif not records:
                    logger.warning("[WARN] Supabase upload skipped: No records to upload")
                else:
                    logger.warning("[WARN] Supabase upload failed: Check logs above for details")
        except ServiceError as upload_error:
            # ServiceError from upload_to_supabase - log but don't fail processing
            logger.error(f"[ERROR] Supabase upload error: {upload_error}", exc_info=True)
        except Exception as e:
            logger.error(f"[ERROR] Unexpected Supabase upload error: {e}", exc_info=True)
        
        # Step 4: Move PDF to library (always move after successful processing, unless 0 records)
        # Only keep files with 0 records in incoming for reprocessing/learning
        if record_count == 0:
            logger.info(f"[4/4] Keeping file in incoming for reprocessing (0 records extracted)")
            logger.info("File will be reprocessed on next cycle to improve extraction quality")
            logger.info(f"[OK] Completed processing: {pdf_path_obj.name} (kept in incoming for learning)")
            return True
        
        # For files with records, always move to library after successful processing
        logger.info("[4/4] Archiving to library...")
        dest = os.path.join(LIBRARY_DIR, pdf_path_obj.name)
        if os.path.exists(dest):
            # Add timestamp to avoid overwrite
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(LIBRARY_DIR, f"{base_name}_{timestamp}.pdf")
        
        # Move file with error handling and verification
        moved_successfully = False
        try:
            # Ensure library directory exists
            os.makedirs(LIBRARY_DIR, exist_ok=True)
            
            # Verify source file still exists before moving
            if not pdf_path_obj.exists():
                logger.warning(f"Source file no longer exists: {pdf_path_obj.name} (may have been moved already)")
                return True  # Consider it successful if already moved
            
            # Attempt move
            shutil.move(str(pdf_path), dest)
            
            # Verify move succeeded
            if os.path.exists(dest) and not pdf_path_obj.exists():
                logger.info(f"[OK] Moved to library: {os.path.basename(dest)}")
                moved_successfully = True
            else:
                raise Exception(f"Move verification failed: dest exists={os.path.exists(dest)}, source exists={pdf_path_obj.exists()}")
                
        except (PermissionError, OSError) as move_error:
            logger.warning(f"Move failed, trying copy+delete: {move_error}")
            try:
                # Ensure library directory exists
                os.makedirs(LIBRARY_DIR, exist_ok=True)
                
                # Verify source file still exists
                if not pdf_path_obj.exists():
                    logger.warning(f"Source file no longer exists during copy fallback: {pdf_path_obj.name}")
                    return True
                
                # Copy file
                shutil.copy2(str(pdf_path), dest)
                
                # Verify copy succeeded before removing source
                if os.path.exists(dest):
                    # Verify file sizes match before deleting source
                    if os.path.getsize(dest) == os.path.getsize(pdf_path):
                        os.remove(str(pdf_path))
                        # Verify source was removed
                        if not pdf_path_obj.exists():
                            logger.info(f"[OK] Moved to library (via copy+delete): {os.path.basename(dest)}")
                            moved_successfully = True
                        else:
                            raise FileOperationError("Source file still exists after copy+delete")
                    else:
                        raise FileOperationError(f"File size mismatch: source={os.path.getsize(pdf_path)}, dest={os.path.getsize(dest)}")
                else:
                    raise FileOperationError("Destination file does not exist after copy")
                    
            except (PermissionError, OSError) as copy_error:
                logger.error(f"[ERROR] Copy fallback also failed: {copy_error}", exc_info=True)
                raise FileOperationError(f"Failed to move file from incoming to library: {move_error}") from move_error
            except Exception as e:
                logger.error(f"[ERROR] Unexpected error during copy fallback: {e}", exc_info=True)
                raise FileOperationError(f"Unexpected error during file move: {e}") from e
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error during file move: {e}", exc_info=True)
            raise FileOperationError(f"Unexpected error moving file: {e}") from e
        
        # Final verification - if move didn't succeed, raise error
        if not moved_successfully:
            raise FileOperationError("File move verification failed - file may still be in incoming directory")
        
        logger.info(f"[OK] Completed: {pdf_path_obj.name}")
        # Flush logs after completion
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.flush()
        return True
        
    except (ServiceError, FileOperationError, DependencyError) as e:
        # Re-raise domain-specific errors as-is
        logger.error(f"[ERROR] Error processing {pdf_path_obj.name}: {e}", exc_info=True)
        # Move failed file to temp for manual review
        error_dest = os.path.join(TEMP_DIR, "errors", f"{base_name}_error_{int(time.time())}.pdf")
        try:
            os.makedirs(os.path.dirname(error_dest), exist_ok=True)
            shutil.move(str(pdf_path), error_dest)
            logger.info(f"Moved failed file to: {error_dest}")
        except Exception as move_err:
            logger.error(f"Failed to move error file: {move_err}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"[ERROR] Unexpected error processing {pdf_path_obj.name}: {e}", exc_info=True)
        # Move failed file to temp for manual review
        error_dest = os.path.join(TEMP_DIR, "errors", f"{base_name}_error_{int(time.time())}.pdf")
        os.makedirs(os.path.dirname(error_dest), exist_ok=True)
        try:
            shutil.move(str(pdf_path), error_dest)
            logger.info(f"Moved failed file to: {error_dest}")
        except:
            pass
        return False


def process_all_pdfs():
    """Process all PDFs in incoming directory."""
    logger.info("=" * 60)
    logger.info("VOFC Processor - Starting processing cycle")
    logger.info("=" * 60)
    
    # Process all PDFs in incoming directory
    pdf_files = [f for f in os.listdir(INCOMING_DIR) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        logger.info("No PDF files found in incoming directory")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) to process")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    # Track retry attempts for files (to prevent infinite retry loops)
    retry_tracking_file = os.path.join(DATA_DIR, "temp", "processing_retries.json")
    os.makedirs(os.path.dirname(retry_tracking_file), exist_ok=True)
    
    # Load retry tracking
    retry_counts = {}
    if os.path.exists(retry_tracking_file):
        try:
            with open(retry_tracking_file, "r", encoding="utf-8") as f:
                retry_counts = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load retry tracking: {e}")
            retry_counts = {}
    
    MAX_RETRIES = 10  # Maximum retries before moving to errors
    
    for file in pdf_files:
        pdf_path = os.path.join(INCOMING_DIR, file)
        
        # Skip if file doesn't exist (may have been moved already)
        if not os.path.exists(pdf_path):
            logger.debug(f"Skipping {file} - file no longer exists")
            skipped_count += 1
            # Clean up retry tracking for moved files
            if file in retry_counts:
                del retry_counts[file]
            continue
        
        # Check retry count - if exceeded, move to errors
        retry_count = retry_counts.get(file, 0)
        if retry_count >= MAX_RETRIES:
            logger.error(f"[ERROR] File {file} has exceeded {MAX_RETRIES} retry attempts - moving to errors")
            error_dest = os.path.join(TEMP_DIR, "errors", f"{Path(file).stem}_max_retries_{int(time.time())}.pdf")
            try:
                os.makedirs(os.path.dirname(error_dest), exist_ok=True)
                shutil.move(pdf_path, error_dest)
                logger.info(f"Moved to errors: {error_dest}")
                # Remove from retry tracking
                if file in retry_counts:
                    del retry_counts[file]
                fail_count += 1
                continue
            except Exception as move_err:
                logger.error(f"Failed to move max-retry file: {move_err}", exc_info=True)
                # Continue processing anyway - maybe this time it will work
        
        # Note: We process files even if they exist in library
        # This allows reprocessing for iterative learning/improvement
        
        try:
            if process_pdf_file(pdf_path):
                success_count += 1
                # Clear retry count on success
                if file in retry_counts:
                    del retry_counts[file]
            else:
                fail_count += 1
                # Increment retry count
                retry_counts[file] = retry_count + 1
                logger.warning(f"[WARN] Processing failed for {file} (retry {retry_counts[file]}/{MAX_RETRIES})")
        except Exception as e:
            fail_count += 1
            # Increment retry count on exception
            retry_counts[file] = retry_count + 1
            logger.error(f"[ERROR] Exception processing {file} (retry {retry_counts[file]}/{MAX_RETRIES}): {e}", exc_info=True)
    
    # Save retry tracking
    try:
        with open(retry_tracking_file, "w", encoding="utf-8") as f:
            json.dump(retry_counts, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save retry tracking: {e}")
    
    logger.info("=" * 60)
    logger.info(f"Processing cycle complete: {success_count} succeeded, {fail_count} failed, {skipped_count} skipped")
    if retry_counts:
        logger.info(f"Files with retry counts: {len(retry_counts)}")
    logger.info("=" * 60)


# ==========================================================
# FILE WATCHER
# ==========================================================

class PDFFileHandler(FileSystemEventHandler):
    """Handler for PDF file events - processes files immediately when detected."""
    
    def __init__(self):
        super().__init__()
        self.processed_files = set()
        self.processing_lock = threading.Lock()
    
    def on_created(self, event: FileSystemEvent):
        """Called when a new file is created - process immediately."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only process PDF files
        if file_path.suffix.lower() != '.pdf':
            return
        
        # Note: We allow reprocessing files even if they exist in library
        # This enables iterative learning where files may need multiple processing attempts
        
        # Avoid duplicate processing
        file_key = str(file_path)
        with self.processing_lock:
            if file_key in self.processed_files:
                logger.debug(f"File {file_path.name} is already being processed, skipping")
                return
            self.processed_files.add(file_key)
        
        logger.info(f"[NEW FILE] {file_path.name} - Processing immediately...")
        
        # Process in background thread to avoid blocking watcher
        def process_file():
            try:
                # Wait a moment for file to be fully written
                time.sleep(0.5)
                
                # Verify file exists and is readable
                if not file_path.exists():
                    logger.warning(f"File {file_path.name} no longer exists, skipping")
                    with self.processing_lock:
                        self.processed_files.discard(file_key)
                    return
                
                # Check if file is still being written (size changes)
                last_size = file_path.stat().st_size
                time.sleep(1)
                if file_path.exists() and file_path.stat().st_size != last_size:
                    logger.info(f"File {file_path.name} is still being written, waiting...")
                    time.sleep(2)
                
                # Double-check file still exists and hasn't been moved
                if not file_path.exists():
                    logger.info(f"File {file_path.name} was moved before processing started, skipping")
                    with self.processing_lock:
                        self.processed_files.discard(file_key)
                    return
                
                # Process the file
                if process_pdf_file(str(file_path)):
                    logger.info(f"[OK] Successfully processed {file_path.name}")
                else:
                    logger.warning(f"[WARN] Processing failed for {file_path.name}")
            except (ServiceError, FileOperationError, DependencyError) as e:
                # Re-raise domain-specific errors
                logger.error(f"Error processing {file_path.name}: {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Unexpected error processing {file_path.name}: {e}", exc_info=True)
                raise ServiceError(f"Unexpected error processing file: {e}") from e
            finally:
                # Remove from processed set after processing completes (success or failure)
                with self.processing_lock:
                    self.processed_files.discard(file_key)
        
        # Start processing in background thread
        # Use explicit daemon parameter to avoid Python 3.13 compatibility issues
        thread = threading.Thread(target=process_file)
        thread.daemon = True
        thread.start()


# ==========================================================
# SERVICE LOOP
# ==========================================================

def run_service_loop():
    """Continuous service loop - uses file watcher for immediate processing."""
    logger.info("=" * 60)
    logger.info("VOFC Processor Service - Reliable Extraction Version")
    logger.info("Chunk-based processing pipeline")
    logger.info("=" * 60)
    
    # Process any existing files first
    logger.info("Processing any existing files in incoming directory...")
    process_all_pdfs()
    
    # Use file system watcher if available, otherwise fall back to polling
    if WATCHDOG_AVAILABLE:
        logger.info("=" * 60)
        logger.info("Starting file system watcher for immediate processing...")
        logger.info(f"Monitoring: {INCOMING_DIR}")
        logger.info("Files will be processed immediately when added to incoming folder")
        logger.info("=" * 60)
        
        try:
            # Verify directory exists
            if not os.path.exists(INCOMING_DIR):
                logger.error(f"Incoming directory does not exist: {INCOMING_DIR}")
                logger.warning("Falling back to polling mode...")
            else:
                logger.info(f"[OK] Incoming directory exists: {INCOMING_DIR}")
                
                # Create event handler
                event_handler = PDFFileHandler()
                
                # Create observer
                observer = Observer()
                observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
                try:
                    observer.start()
                    logger.info("File system watcher started - ready for immediate processing")
                    logger.info(f"Watching for new PDF files in: {INCOMING_DIR}")
                except TypeError as e:
                    # Python 3.13 compatibility issue with watchdog 3.0.0
                    if "'handle' must be a _ThreadHandle" in str(e) or "handle" in str(e).lower():
                        logger.error(f"Watchdog incompatible with Python 3.13: {e}")
                        logger.warning("Falling back to polling mode (more reliable)")
                        try:
                            observer.stop()
                            observer.join(timeout=1)
                        except:
                            pass
                        # Force fallback to polling mode
                        raise Exception("Watchdog incompatible - forcing polling mode")
                    else:
                        raise  # Re-raise other TypeError exceptions
                
                # Keep service running
                try:
                    last_heartbeat = time.time()
                    last_existing_check = time.time()
                    existing_check_interval = 300  # Check for existing files every 5 minutes
                    while True:
                        time.sleep(1)
                        current_time = time.time()
                        
                        # Log heartbeat every 30 seconds to confirm watcher is alive
                        if current_time - last_heartbeat >= 30:
                            logger.info("Watcher heartbeat - still monitoring...")
                            last_heartbeat = current_time
                        
                        # Periodically check for existing files that weren't processed
                        # REDUCED INTERVAL: Check every 60 seconds (was 300) to catch stuck files faster
                        if current_time - last_existing_check >= 60:
                            logger.info("Checking for unprocessed files in incoming directory...")
                            try:
                                process_all_pdfs()
                            except (ServiceError, FileOperationError, DependencyError) as e:
                                # Log but don't re-raise - allow service to continue
                                logger.error(f"Error processing existing files: {e}", exc_info=True)
                                logger.warning("Service will continue and retry on next check")
                            except Exception as e:
                                # Log but don't re-raise - allow service to continue
                                logger.error(f"Unexpected error processing existing files: {e}", exc_info=True)
                                logger.warning("Service will continue and retry on next check")
                            last_existing_check = current_time
                except KeyboardInterrupt:
                    logger.info("Service interrupted by user")
                    observer.stop()
                finally:
                    observer.stop()
                    observer.join(timeout=5)
                    logger.info("File system watcher stopped")
                    
        except (ServiceError, FileOperationError, DependencyError) as e:
            # Re-raise domain-specific errors
            logger.error(f"Error in file watcher: {e}", exc_info=True)
            raise
        except KeyboardInterrupt:
            # Re-raise KeyboardInterrupt
            raise
        except Exception as e:
            # Check if this is a watchdog compatibility error
            error_str = str(e)
            if "Watchdog incompatible" in error_str or "'handle' must be a _ThreadHandle" in error_str or "handle" in error_str.lower():
                logger.warning("Watchdog failed due to Python 3.13 compatibility - falling back to polling mode")
                # Don't re-raise - fall through to polling mode
            else:
                logger.error(f"Unexpected error in file watcher: {e}", exc_info=True)
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.warning("Falling back to polling mode...")
                # Don't re-raise - fall through to polling mode
    else:
        logger.warning("Watchdog library not available - using polling mode")
        logger.warning("Install watchdog for immediate file processing: pip install watchdog")
    
    # Fallback: Polling mode (if watchdog not available or watcher failed)
    logger.info("Using polling mode (watchdog not available or watcher failed)")
    
    cycle_count = 0
    check_interval = 30  # seconds between cycles
    
    while True:
        try:
            cycle_count += 1
            logger.info("")
            logger.info(f"--- Processing Cycle #{cycle_count} ---")
            logger.info(f"Checking for PDFs in: {INCOMING_DIR}")
            
            # Run one processing cycle
            process_all_pdfs()
            
            # Wait before next cycle
            logger.info(f"Waiting {check_interval} seconds before next check...")
            time.sleep(check_interval)
            
        except KeyboardInterrupt:
            logger.info("Service loop interrupted by user")
            break
        except (ServiceError, FileOperationError, DependencyError) as e:
            # Log but don't re-raise - allow service to continue
            logger.error(f"Error in service loop: {e}", exc_info=True)
            logger.warning("Service will continue and retry on next cycle")
            time.sleep(check_interval)
        except Exception as e:
            # Log but don't re-raise - allow service to continue
            logger.error(f"Unexpected error in service loop: {e}", exc_info=True)
            logger.warning("Service will continue and retry on next cycle")
            time.sleep(check_interval)


if __name__ == "__main__":
    # Run as continuous service loop
    run_service_loop()
