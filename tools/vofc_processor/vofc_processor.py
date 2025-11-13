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
    logging.warning("watchdog not available - will use polling mode instead of file watching")

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
        script_dir.parent.parent / ".env",
        script_dir / ".env",
        Path(r"C:\Tools\PSA_Tool\.env"),
        Path(r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\.env"),
    ]
    
    env_loaded = False
    for env_path in possible_env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=False)
            logging.info(f"Loaded environment variables from {env_path}")
            env_loaded = True
            break
    
    if not env_loaded:
        logging.debug("No .env file found in standard locations")
except ImportError:
    logging.warning("python-dotenv not installed - .env file will not be loaded automatically")
except Exception as e:
    logging.warning(f"Failed to load .env file: {e}")

# Base data directory
DATA_DIR = os.getenv("VOFC_DATA_DIR", r"C:\Tools\Ollama\Data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = r"C:\Tools\VOFC\Data"
    if not os.path.exists(DATA_DIR):
        DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
        os.makedirs(DATA_DIR, exist_ok=True)

INCOMING_DIR = os.path.join(DATA_DIR, "incoming")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
LIBRARY_DIR = os.path.join(DATA_DIR, "library")
TEMP_DIR = os.path.join(DATA_DIR, "temp")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

# Ensure directories exist
for dir_path in [INCOMING_DIR, PROCESSED_DIR, LIBRARY_DIR, TEMP_DIR, LOGS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==========================================================
# LOGGING SETUP
# ==========================================================

LOG_FILE = os.path.join(LOGS_DIR, f"vofc_processor_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ==========================================================
# SUPABASE INITIALIZATION
# ==========================================================

supabase = init_supabase()
if supabase:
    logger.info("✓ Supabase client initialized")
else:
    logger.warning("⚠ Supabase not configured - uploads will be skipped")


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
    
    try:
        # Step 1: Process PDF through chunk-based pipeline
        logger.info("[1/4] Extracting and processing chunks...")
        output_path = process_pdf_chunked(
            path=str(pdf_path),
            output_dir=PROCESSED_DIR,
            model=os.getenv("VOFC_MODEL", "vofc-unified:latest")
        )
        
        # Load results to verify
        with open(output_path, "r", encoding="utf-8") as f:
            result_data = json.load(f)
        
        records = result_data.get("records", [])
        if not records:
            logger.warning(f"⚠️  No records extracted from {pdf_path_obj.name}")
            logger.warning("File will be moved to temp for manual review")
            # Move to temp/errors
            error_dest = os.path.join(TEMP_DIR, "errors", f"{base_name}_{int(time.time())}.pdf")
            os.makedirs(os.path.dirname(error_dest), exist_ok=True)
            try:
                shutil.move(str(pdf_path), error_dest)
                logger.info(f"Moved to: {error_dest}")
            except Exception as e:
                logger.error(f"Failed to move file: {e}")
            return False
        
        logger.info(f"✓ Extracted {len(records)} records")
        logger.info(f"✓ Saved JSON to: {output_path}")
        
        # Step 2: Copy JSON to review directory
        logger.info("[2/4] Copying JSON to review directory...")
        review_dir = os.path.join(DATA_DIR, "review")
        os.makedirs(review_dir, exist_ok=True)
        review_path = os.path.join(review_dir, f"{base_name}_vofc.json")
        shutil.copy2(output_path, review_path)
        logger.info(f"✓ Copied to review: {review_path}")
        
        # Step 3: Upload to Supabase (optional)
        logger.info("[3/4] Uploading to Supabase...")
        submission_id = upload_to_supabase(
            file_path=str(pdf_path),
            records=records,
            supabase=supabase
        )
        if submission_id:
            logger.info(f"✓ Uploaded to Supabase (submission_id={submission_id})")
        else:
            logger.warning("⚠️  Supabase upload skipped or failed")
        
        # Step 4: Move PDF to library
        logger.info("[4/4] Archiving to library...")
        dest = os.path.join(LIBRARY_DIR, pdf_path_obj.name)
        if os.path.exists(dest):
            # Add timestamp to avoid overwrite
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join(LIBRARY_DIR, f"{base_name}_{timestamp}.pdf")
        
        # Move file with error handling
        try:
            shutil.move(str(pdf_path), dest)
            logger.info(f"✓ Moved to library: {os.path.basename(dest)}")
        except Exception as move_error:
            logger.warning(f"Move failed, trying copy: {move_error}")
            try:
                shutil.copy2(str(pdf_path), dest)
                os.remove(pdf_path)
                logger.info(f"✓ Moved to library (via copy): {os.path.basename(dest)}")
            except Exception as copy_error:
                logger.error(f"✗ Copy fallback also failed: {copy_error}")
                raise Exception(f"Failed to move file from incoming to library: {move_error}")
        
        logger.info(f"✅ Completed: {pdf_path_obj.name}")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error processing {pdf_path_obj.name}: {e}", exc_info=True)
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
    
    for file in pdf_files:
        pdf_path = os.path.join(INCOMING_DIR, file)
        if process_pdf_file(pdf_path):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info("=" * 60)
    logger.info(f"Processing cycle complete: {success_count} succeeded, {fail_count} failed")
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
        
        # Avoid duplicate processing
        file_key = str(file_path)
        with self.processing_lock:
            if file_key in self.processed_files:
                return
            self.processed_files.add(file_key)
        
        logger.info(f"🚀 NEW FILE DETECTED: {file_path.name} - Processing immediately...")
        
        # Process in background thread to avoid blocking watcher
        def process_file():
            try:
                # Wait a moment for file to be fully written
                time.sleep(0.5)
                
                # Verify file exists and is readable
                if not file_path.exists():
                    logger.warning(f"File {file_path.name} no longer exists, skipping")
                    return
                
                # Check if file is still being written (size changes)
                last_size = file_path.stat().st_size
                time.sleep(1)
                if file_path.exists() and file_path.stat().st_size != last_size:
                    logger.info(f"File {file_path.name} is still being written, waiting...")
                    time.sleep(2)
                
                # Process the file
                if process_pdf_file(str(file_path)):
                    logger.info(f"✅ Successfully processed {file_path.name}")
                else:
                    logger.warning(f"⚠️  Processing failed for {file_path.name}")
            except Exception as e:
                logger.error(f"Error processing {file_path.name}: {e}", exc_info=True)
        
        # Start processing in background thread
        thread = threading.Thread(target=process_file, daemon=True)
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
                logger.info(f"✓ Incoming directory exists: {INCOMING_DIR}")
                
                # Create event handler
                event_handler = PDFFileHandler()
                
                # Create observer
                observer = Observer()
                observer.schedule(event_handler, str(INCOMING_DIR), recursive=False)
                observer.start()
                
                logger.info("✅ File system watcher started - ready for immediate processing")
                logger.info(f"Watching for new PDF files in: {INCOMING_DIR}")
                
                # Keep service running
                try:
                    while True:
                        time.sleep(1)
                        # Log heartbeat every 5 minutes to confirm watcher is alive
                        if int(time.time()) % 300 == 0:
                            logger.debug("Watcher heartbeat - still monitoring...")
                except KeyboardInterrupt:
                    logger.info("Service interrupted by user")
                    observer.stop()
                finally:
                    observer.stop()
                    observer.join(timeout=5)
                    logger.info("File system watcher stopped")
                    
        except Exception as e:
            logger.error(f"Error in file watcher: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.warning("Falling back to polling mode...")
            # Fall through to polling mode
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
        except Exception as e:
            logger.error(f"Error in service loop: {e}", exc_info=True)
            logger.info(f"Waiting {check_interval} seconds before retry...")
            time.sleep(check_interval)


if __name__ == "__main__":
    # Run as continuous service loop
    run_service_loop()
