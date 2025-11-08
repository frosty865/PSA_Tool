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
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Import PyMuPDF for page-based PDF extraction
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logging.warning("PyMuPDF (fitz) not available. Install with: pip install PyMuPDF")

# Import processing modules
from services.preprocess import preprocess_document, normalize_text, chunk_text
from services.ollama_client import run_model_on_chunks, run_model
from services.postprocess import postprocess_results
from services.supabase_client import get_supabase_client, insert_library_record, check_review_approval

# Import watchdog for folder monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError as e:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
    # Don't use logging here as it may not be initialized yet
    import sys
    print(f"WARNING: watchdog import failed: {e}", file=sys.stderr)

# ============================================================================
# Directory Configuration
# ============================================================================

# Explicitly set to C:\Tools\Ollama\Data\incoming to ensure correct path
BASE_DIR = Path(os.getenv("VOFC_BASE_DIR", r"C:\Tools\Ollama\Data"))

# ============================================================================
# Processed Files Tracking (Prevent Duplicate Processing)
# ============================================================================

# Flag to enable/disable processed file tracking
# Set to False to disable tracking (useful for testing)
ENABLE_PROCESSED_TRACKING = os.getenv("ENABLE_PROCESSED_TRACKING", "false").lower() == "true"

# Global dict to track processed files with timestamps (path -> timestamp) for time-based debouncing
processed_files = {}

# Global dict to track file hashes (path -> hash) for content-based deduplication
processed_file_hashes = {}

def file_hash(path: Path) -> str:
    """Calculate MD5 hash of file contents for duplicate detection."""
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logging.warning(f"Could not calculate hash for {path.name}: {e}")
        return ""
INCOMING_DIR = BASE_DIR / "incoming"

# Ensure INCOMING_DIR is explicitly set to the correct path
# Override any environment variable issues by using absolute path
if not str(INCOMING_DIR).startswith(r"C:\Tools\Ollama\Data\incoming"):
    # Force the correct path
    INCOMING_DIR = Path(r"C:\Tools\Ollama\Data\incoming")
    BASE_DIR = INCOMING_DIR.parent

PROCESSED_DIR = BASE_DIR / "processed"
LIBRARY_DIR = BASE_DIR / "library"
ERROR_DIR = BASE_DIR / "errors"
REVIEW_DIR = BASE_DIR / "review"
REVIEW_TEMP_DIR = REVIEW_DIR / "temp"  # Intermediate outputs between phases
AUTOMATION_DIR = BASE_DIR / "automation"
PROGRESS_FILE = AUTOMATION_DIR / "progress.json"
LOG_FILE = AUTOMATION_DIR / "vofc_auto_processor.log"

# Global watcher observer instance for status checking
_watcher_observer = None

# ============================================================================
# Setup
# ============================================================================

def ensure_dirs():
    """Create all required directories if they don't exist"""
    processing_dir = BASE_DIR / "processing"  # Temporary processing directory
    for d in [INCOMING_DIR, PROCESSED_DIR, LIBRARY_DIR, ERROR_DIR, REVIEW_DIR, REVIEW_TEMP_DIR, AUTOMATION_DIR, processing_dir]:
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

# Log watchdog availability (after logging is set up)
if not WATCHDOG_AVAILABLE:
    logging.warning("watchdog not installed. Install with: pip install watchdog")
else:
    logging.info("watchdog is available and ready")

# ============================================================================
# Progress Tracking
# ============================================================================

def get_watcher_status() -> str:
    """
    Check if watcher is currently running
    
    Returns:
        'running' if watcher observer is alive, 'stopped' otherwise
    """
    global _watcher_observer
    
    # Method 1: Check global observer instance
    if _watcher_observer is not None:
        try:
            if _watcher_observer.is_alive():
                return "running"
        except Exception:
            pass
    
    # Method 2: Check active threads for watcher thread
    try:
        for thread in threading.enumerate():
            thread_name = thread.name.lower()
            # Check if it's a watcher-related thread
            if 'watcher' in thread_name or 'observer' in thread_name:
                if thread.is_alive():
                    return "running"
            # Also check if thread is running start_folder_watcher function
            # by checking if the thread's target function name contains 'watcher'
            if hasattr(thread, '_target') and thread._target:
                target_name = str(thread._target).lower()
                if 'start_folder_watcher' in target_name or 'watcher' in target_name:
                    if thread.is_alive():
                        return "running"
    except Exception:
        pass
    
    # Method 3: Check progress.json for recent activity (within last 2 minutes)
    try:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r", encoding="utf-8-sig") as f:
                progress_data = json.load(f)
                watcher_status_from_file = progress_data.get("watcher_status", "stopped")
                timestamp_str = progress_data.get("timestamp", "")
                
                # If file says running and timestamp is recent, trust it
                if watcher_status_from_file == "running" and timestamp_str:
                    try:
                        from datetime import datetime
                        file_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        time_diff = (datetime.now() - file_time).total_seconds()
                        # If updated within last 2 minutes, consider it running
                        if time_diff < 120:
                            return "running"
                    except Exception:
                        pass
    except Exception:
        pass
    
    return "stopped"

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
        
        # Get watcher status
        watcher_status = get_watcher_status()
        
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "incoming": incoming_count,
            "processed": processed_count,
            "library": library_count,
            "errors": errors_count,
            "review": review_count,
            "status": "running" if incoming_count > 0 else "idle",
            "watcher_status": watcher_status
        }
        
        with open(PROGRESS_FILE, "w", encoding="utf-8-sig") as pf:
            json.dump(data, pf, indent=2, ensure_ascii=False)
        
        return data
    except Exception as e:
        logging.error(f"Failed to update progress: {e}")
        return {}

# ============================================================================
# File Processing
# ============================================================================

def extract_text_with_pages(pdf_path: Path):
    """Return a list of (page_num, text) tuples from a PDF."""
    if not PYMUPDF_AVAILABLE:
        logging.warning("PyMuPDF not available, falling back to standard extraction")
        return None
    
    pages = []
    try:
        with fitz.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if text:
                    pages.append((i + 1, text))
        return pages
    except Exception as e:
        logging.error(f"Error extracting pages from PDF: {e}")
        return None

# ============================================================================
# 3-Phase Processing Pipeline
# ============================================================================

def phase1_parser(chunks: list, filepath: Path) -> Dict[str, Any]:
    """
    Phase 1: Parsing/Extraction
    Model: vofc-parser:latest
    Purpose: Extract raw vulnerabilities and OFCs from text chunks
    
    Args:
        chunks: List of text chunks with metadata
        filepath: Path to source document
        
    Returns:
        Dictionary with parser output (raw structured JSON)
    """
    import threading
    model_name = "vofc-parser:latest"
    thread_id = threading.current_thread().ident
    thread_name = threading.current_thread().name
    
    logging.info(f"🔍 Phase 1: Running parser ({model_name}) on {len(chunks)} chunks...")
    logging.info(f"   Thread: {thread_name} (ID: {thread_id})")
    logging.info(f"   File: {filepath.name}")
    logging.info(f"   Chunk processing: Starting chunk 1/{len(chunks)}")
    
    parser_results = []
    start_time = time.time()
    successful_chunks = 0
    failed_chunks = 0
    
    for idx, chunk_data in enumerate(chunks, start=1):
        chunk_start_time = time.time()
        chunk_text = chunk_data.get("content") or chunk_data.get("text", "")
        page_num = chunk_data.get("page", 1)
        chunk_id = chunk_data.get("chunk_id", f"chunk_{idx:03d}")
        chunk_size = len(chunk_text)
        
        logging.info(f"   [Phase 1] Processing chunk {idx}/{len(chunks)} ({chunk_id})")
        logging.info(f"      - Page: {page_num}")
        logging.info(f"      - Chunk size: {chunk_size} characters")
        logging.info(f"      - Model: {model_name}")
        
        prompt = f"""You are a document parser for security assessments.

Extract vulnerabilities and options for consideration from the following text.

CRITICAL: Respond ONLY in valid JSON. No markdown, no explanations, no code blocks.

Required JSON structure (array format):
[
  {{
    "category": "Perimeter Security",
    "vulnerability": "The facility lacks perimeter fencing...",
    "options_for_consideration": [
      "Install fencing appropriate for facility type...",
      "Use CPTED principles..."
    ],
    "citations": ["Section {page_num}"]
  }}
]

If you have no data, return: []

Document: {chunk_data.get("filename", filepath.name)}
Page: {page_num}

Text:
{chunk_text}

Remember: Return ONLY valid JSON, nothing else."""
        
        prompt_size = len(prompt)
        logging.info(f"      - Prompt size: {prompt_size} characters")
        logging.info(f"      - Calling model API...")
        
        try:
            model_call_start = time.time()
            result_text = run_model(model=model_name, prompt=prompt)
            model_call_duration = time.time() - model_call_start
            
            if not result_text or not result_text.strip():
                logging.warning(f"      - ⚠️  Empty response from model (duration: {model_call_duration:.2f}s)")
                failed_chunks += 1
                continue
            
            response_size = len(result_text)
            logging.info(f"      - ✅ Model response received (duration: {model_call_duration:.2f}s, size: {response_size} chars)")
            logging.info(f"      - Parsing JSON response...")
            
            # Clean and parse JSON
            json_text = result_text.strip()
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join([l for l in lines if not l.strip().startswith("```")])
                logging.info(f"      - Removed markdown code blocks from response")
            
            parsed = json.loads(json_text)
            records_found = 0
            
            if isinstance(parsed, list):
                records_found = len(parsed)
                for record in parsed:
                    record["source_file"] = chunk_data.get("filename", filepath.name)
                    record["source_page"] = page_num
                    record["page_range"] = str(page_num)
                    record["chunk_id"] = chunk_id
                    parser_results.append(record)
                logging.info(f"      - ✅ Parsed {records_found} records from array response")
            elif isinstance(parsed, dict):
                records_found = 1
                parsed["source_file"] = chunk_data.get("filename", filepath.name)
                parsed["source_page"] = page_num
                parsed["page_range"] = str(page_num)
                parsed["chunk_id"] = chunk_id
                parser_results.append(parsed)
                logging.info(f"      - ✅ Parsed 1 record from object response")
            else:
                logging.warning(f"      - ⚠️  Unexpected response type: {type(parsed)}")
                failed_chunks += 1
                continue
            
            successful_chunks += 1
            chunk_duration = time.time() - chunk_start_time
            logging.info(f"      - ✅ Chunk {idx}/{len(chunks)} complete ({chunk_duration:.2f}s, {records_found} records)")
                
        except json.JSONDecodeError as je:
            chunk_duration = time.time() - chunk_start_time
            logging.error(f"      - ❌ JSON parse error on chunk {idx}: {je}")
            logging.error(f"      - Response preview: {result_text[:200] if 'result_text' in locals() else 'N/A'}...")
            logging.error(f"      - Duration: {chunk_duration:.2f}s")
            failed_chunks += 1
        except Exception as e:
            chunk_duration = time.time() - chunk_start_time
            logging.error(f"      - ❌ Model call failed on chunk {idx}: {type(e).__name__}: {e}")
            logging.error(f"      - Duration: {chunk_duration:.2f}s")
            logging.error(f"      - Traceback: {traceback.format_exc()}")
            failed_chunks += 1
        
        # Progress update every 10 chunks
        if idx % 10 == 0:
            elapsed = time.time() - start_time
            remaining_chunks = len(chunks) - idx
            avg_time_per_chunk = elapsed / idx
            estimated_remaining = remaining_chunks * avg_time_per_chunk
            logging.info(f"   [Phase 1] Progress: {idx}/{len(chunks)} chunks ({elapsed:.1f}s elapsed, ~{estimated_remaining:.1f}s remaining)")
    
    total_duration = time.time() - start_time
    logging.info(f"   [Phase 1] COMPLETE: {len(parser_results)} raw records extracted")
    logging.info(f"      - Successful chunks: {successful_chunks}/{len(chunks)}")
    logging.info(f"      - Failed chunks: {failed_chunks}/{len(chunks)}")
    logging.info(f"      - Total duration: {total_duration:.2f}s")
    logging.info(f"      - Average time per chunk: {total_duration/len(chunks):.2f}s")
    
    return {"records": parser_results, "phase": "parser", "count": len(parser_results)}


def phase2_engine(parser_output: Dict[str, Any], filepath: Path) -> Dict[str, Any]:
    """
    Phase 2: Normalization/Semantic Engine
    Model: vofc-engine:latest
    Purpose: Normalize, deduplicate, and validate parser output
    
    Args:
        parser_output: Output from Phase 1
        filepath: Path to source document
        
    Returns:
        Dictionary with normalized, validated JSON
    """
    import threading
    model_name = "vofc-engine:latest"
    thread_id = threading.current_thread().ident
    thread_name = threading.current_thread().name
    
    start_time = time.time()
    input_count = parser_output.get("count", 0)
    
    logging.info(f"🧠 Phase 2: Running engine ({model_name}) on {input_count} parser records...")
    logging.info(f"   Thread: {thread_name} (ID: {thread_id})")
    logging.info(f"   File: {filepath.name}")
    
    records = parser_output.get("records", [])
    if not records:
        logging.warning("   ⚠️  Phase 2: No records from parser, skipping")
        return {"records": [], "phase": "engine", "count": 0}
    
    logging.info(f"   - Input records: {len(records)}")
    
    # Prepare input for engine (consolidate all records)
    input_json = json.dumps(records, indent=2)
    input_size = len(input_json)
    logging.info(f"   - Input JSON size: {input_size} characters")
    
    prompt = f"""You are a normalization and validation engine for security assessments.

Normalize and validate the following parser output:
- Consolidate duplicate vulnerabilities
- Standardize categories and classifications
- Link OFCs to vulnerabilities
- Apply confidence scores
- Ensure citation consistency

CRITICAL: Respond ONLY in valid JSON. No markdown, no explanations, no code blocks.

Input (parser output):
{input_json}

Output format (array):
[
  {{
    "category": "standardized category",
    "vulnerability": "normalized vulnerability text",
    "options_for_consideration": ["normalized OFC 1", "normalized OFC 2"],
    "citations": ["Section X"],
    "confidence_score": 0.95,
    "source_file": "{filepath.name}",
    "page_range": "X-Y"
  }}
]

Return normalized, deduplicated records. If no valid data, return: []"""
    
    prompt_size = len(prompt)
    logging.info(f"   - Prompt size: {prompt_size} characters")
    logging.info(f"   - Calling model API...")
    
    try:
        model_call_start = time.time()
        result_text = run_model(model=model_name, prompt=prompt)
        model_call_duration = time.time() - model_call_start
        
        if not result_text or not result_text.strip():
            logging.warning(f"   ⚠️  Phase 2: Empty response from engine (duration: {model_call_duration:.2f}s)")
            return {"records": [], "phase": "engine", "count": 0}
        
        response_size = len(result_text)
        logging.info(f"   - ✅ Model response received (duration: {model_call_duration:.2f}s, size: {response_size} chars)")
        logging.info(f"   - Parsing JSON response...")
        
        # Clean and parse JSON
        json_text = result_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join([l for l in lines if not l.strip().startswith("```")])
            logging.info(f"   - Removed markdown code blocks from response")
        
        parsed = json.loads(json_text)
        engine_records = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
        
        total_duration = time.time() - start_time
        logging.info(f"   [Phase 2] COMPLETE: {len(engine_records)} normalized records")
        logging.info(f"      - Input: {input_count} records")
        logging.info(f"      - Output: {len(engine_records)} records")
        logging.info(f"      - Reduction: {input_count - len(engine_records)} records (deduplication)")
        logging.info(f"      - Total duration: {total_duration:.2f}s")
        
        return {"records": engine_records, "phase": "engine", "count": len(engine_records)}
        
    except json.JSONDecodeError as je:
        total_duration = time.time() - start_time
        logging.error(f"   ❌ Phase 2: Failed to parse JSON from engine: {je}")
        logging.error(f"      - Response preview: {result_text[:200] if 'result_text' in locals() else 'N/A'}...")
        logging.error(f"      - Duration: {total_duration:.2f}s")
        logging.warning(f"   - Using parser output as fallback (no normalization)")
        # Fallback: return parser output as-is
        return {"records": records, "phase": "engine", "count": len(records), "error": "engine_parse_failed"}
    except Exception as e:
        total_duration = time.time() - start_time
        logging.error(f"   ❌ Phase 2: Engine failed: {type(e).__name__}: {e}")
        logging.error(f"      - Duration: {total_duration:.2f}s")
        logging.error(f"      - Traceback: {traceback.format_exc()}")
        logging.warning(f"   - Using parser output as fallback (no normalization)")
        # Fallback: return parser output as-is
        return {"records": records, "phase": "engine", "count": len(records), "error": str(e)}


def phase3_auditor(engine_output: Dict[str, Any], filepath: Path) -> Dict[str, Any]:
    """
    Phase 3: Validation/Audit
    Model: vofc-auditor:latest
    Purpose: Quality check and flag issues
    
    Args:
        engine_output: Output from Phase 2
        filepath: Path to source document
        
    Returns:
        Dictionary with audited JSON + metadata (accepted/rejected/needs_review)
    """
    import threading
    model_name = "vofc-auditor:latest"
    thread_id = threading.current_thread().ident
    thread_name = threading.current_thread().name
    
    start_time = time.time()
    input_count = engine_output.get("count", 0)
    
    logging.info(f"🔍 Phase 3: Running auditor ({model_name}) on {input_count} engine records...")
    logging.info(f"   Thread: {thread_name} (ID: {thread_id})")
    logging.info(f"   File: {filepath.name}")
    
    records = engine_output.get("records", [])
    if not records:
        logging.warning("   ⚠️  Phase 3: No records from engine, skipping")
        return {"records": [], "phase": "auditor", "count": 0, "metadata": {"status": "empty"}}
    
    logging.info(f"   - Input records: {len(records)}")
    
    # Prepare input for auditor
    input_json = json.dumps(records, indent=2)
    input_size = len(input_json)
    logging.info(f"   - Input JSON size: {input_size} characters")
    
    prompt = f"""You are a quality assurance auditor for security assessments.

Review and validate the following normalized records:
- Flag low-confidence mappings
- Identify missing categories or citations
- Suggest corrections or merges
- Mark records as: accepted, rejected, or needs_review

CRITICAL: Respond ONLY in valid JSON. No markdown, no explanations, no code blocks.

Input (engine output):
{input_json}

Output format:
{{
  "records": [
    {{
      "category": "...",
      "vulnerability": "...",
      "options_for_consideration": [...],
      "citations": [...],
      "confidence_score": 0.95,
      "audit_status": "accepted" | "rejected" | "needs_review",
      "audit_notes": "optional notes",
      "source_file": "{filepath.name}"
    }}
  ],
  "metadata": {{
    "total_records": 10,
    "accepted": 8,
    "rejected": 1,
    "needs_review": 1,
    "accuracy_score": 0.85
  }}
}}

Return audited records with status. If no valid data, return: {{"records": [], "metadata": {{"status": "empty"}}}}"""
    
    prompt_size = len(prompt)
    logging.info(f"   - Prompt size: {prompt_size} characters")
    logging.info(f"   - Calling model API...")
    
    try:
        model_call_start = time.time()
        result_text = run_model(model=model_name, prompt=prompt)
        model_call_duration = time.time() - model_call_start
        
        if not result_text or not result_text.strip():
            logging.warning(f"   ⚠️  Phase 3: Empty response from auditor (duration: {model_call_duration:.2f}s)")
            logging.warning("   - Marking all records as accepted (fallback)")
            # Fallback: mark all as accepted
            return {
                "records": records,
                "phase": "auditor",
                "count": len(records),
                "metadata": {"status": "accepted_all", "total": len(records), "accepted": len(records)}
            }
        
        response_size = len(result_text)
        logging.info(f"   - ✅ Model response received (duration: {model_call_duration:.2f}s, size: {response_size} chars)")
        logging.info(f"   - Parsing JSON response...")
        
        # Clean and parse JSON
        json_text = result_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join([l for l in lines if not l.strip().startswith("```")])
            logging.info(f"   - Removed markdown code blocks from response")
        
        parsed = json.loads(json_text)
        
        # Handle both formats: direct array or object with records/metadata
        if isinstance(parsed, list):
            auditor_records = parsed
            metadata = {"status": "accepted_all", "total": len(auditor_records), "accepted": len(auditor_records)}
            logging.info(f"   - Parsed list response: {len(auditor_records)} records")
        elif isinstance(parsed, dict):
            auditor_records = parsed.get("records", records)
            metadata = parsed.get("metadata", {"status": "accepted_all", "total": len(auditor_records)})
            logging.info(f"   - Parsed dict response: {len(auditor_records)} records, metadata: {metadata}")
        else:
            auditor_records = records
            metadata = {"status": "error", "total": len(records)}
            logging.warning(f"   - ⚠️  Unexpected response type: {type(parsed)}")
        
        total_duration = time.time() - start_time
        logging.info(f"   [Phase 3] COMPLETE: {len(auditor_records)} audited records")
        logging.info(f"      - Input: {input_count} records")
        logging.info(f"      - Output: {len(auditor_records)} records")
        if metadata:
            accepted = metadata.get("accepted", 0)
            rejected = metadata.get("rejected", 0)
            needs_review = metadata.get("needs_review", 0)
            logging.info(f"      - Audit status: {accepted} accepted, {rejected} rejected, {needs_review} needs_review")
        logging.info(f"      - Total duration: {total_duration:.2f}s")
        
        return {"records": auditor_records, "phase": "auditor", "count": len(auditor_records), "metadata": metadata}
        
    except json.JSONDecodeError as je:
        total_duration = time.time() - start_time
        logging.error(f"   ❌ Phase 3: Failed to parse JSON from auditor: {je}")
        logging.error(f"      - Response preview: {result_text[:200] if 'result_text' in locals() else 'N/A'}...")
        logging.error(f"      - Duration: {total_duration:.2f}s")
        logging.warning(f"   - Marking all records as accepted (fallback)")
        # Fallback: mark all as accepted
        return {
            "records": records,
            "phase": "auditor",
            "count": len(records),
            "metadata": {"status": "auditor_parse_failed", "total": len(records), "accepted": len(records), "error": str(je)}
        }
    except Exception as e:
        total_duration = time.time() - start_time
        logging.error(f"   ❌ Phase 3: Auditor failed: {type(e).__name__}: {e}")
        logging.error(f"      - Duration: {total_duration:.2f}s")
        logging.error(f"      - Traceback: {traceback.format_exc()}")
        logging.warning(f"   - Marking all records as accepted (fallback)")
        # Fallback: mark all as accepted
        return {
            "records": records,
            "phase": "auditor",
            "count": len(records),
            "metadata": {"status": "auditor_error", "total": len(records), "accepted": len(records)}
        }


def process_document_file(filepath: Path) -> Optional[Dict[str, Any]]:
    """
    Process a single document file through the 3-phase pipeline:
    1. Phase 1 - Parser (vofc-parser:latest): Extract raw vulnerabilities/OFCs
    2. Phase 2 - Engine (vofc-engine:latest): Normalize and validate
    3. Phase 3 - Auditor (vofc-auditor:latest): Quality check and flag issues
    
    Args:
        filepath: Path to the document file
        
    Returns:
        Final processed results dictionary or None on failure
    """
    temp_outputs = {}  # Store intermediate outputs for debugging
    
    try:
        import threading
        thread_id = threading.current_thread().ident
        thread_name = threading.current_thread().name
        process_start_time = time.time()
        
        logging.info(f"🚀 Starting 3-phase processing for {filepath.name}")
        logging.info(f"   Thread: {thread_name} (ID: {thread_id})")
        logging.info(f"   File path: {filepath.resolve()}")
        logging.info(f"   File size: {filepath.stat().st_size if filepath.exists() else 0} bytes")
        logging.info(f"   Timestamp: {datetime.now().isoformat()}")
        
        # Step 1: Extract text per page for full source traceability
        # Try page-based extraction first (for PDFs)
        pages = None
        if filepath.suffix.lower() == '.pdf' and PYMUPDF_AVAILABLE:
            logging.info(f"   [Step 1] Extracting text with page numbers from {filepath.name}...")
            extract_start = time.time()
            pages = extract_text_with_pages(filepath)
            extract_duration = time.time() - extract_start
            if pages:
                logging.info(f"   ✅ Extracted {len(pages)} pages ({extract_duration:.2f}s)")
            else:
                logging.warning(f"   ⚠️  No pages extracted ({extract_duration:.2f}s)")
        
        all_chunks = []
        results = []
        
        if pages:
            # Page-based extraction (PDF with PyMuPDF)
            # Step 1: Deduplicate pages by text (preserve order, keep first page number for duplicates)
            seen_texts = {}
            unique_pages = []
            for page_num, page_text in pages:
                if page_text not in seen_texts:
                    seen_texts[page_text] = page_num
                    unique_pages.append((page_num, page_text))
                # If duplicate text, we still track it but use the first page number
            
            # Step 2: Concatenate all unique page texts (before normalization)
            all_text = " ".join([page_text for _, page_text in unique_pages])
            
            # Step 3: Normalize once (after concatenation, not per page)
            normalized = normalize_text(all_text)
            
            # Step 4: Chunk once (not per page)
            # Reduced chunk size to 1500 to prevent timeout/token overflow
            chunks = chunk_text(normalized, max_chars=1500)
            
            # Step 5: Map chunks back to pages for metadata
            # Build page boundaries from original unique pages (approximate mapping)
            # Since normalization changes text length, we use proportional mapping
            original_length = len(all_text)
            normalized_length = len(normalized)
            length_ratio = normalized_length / original_length if original_length > 0 else 1.0
            
            page_boundaries = []
            current_pos = 0
            for page_num, page_text in unique_pages:
                # Calculate approximate position in normalized text
                page_start = int(current_pos * length_ratio)
                page_length = int(len(page_text) * length_ratio)
                page_end = page_start + page_length
                page_boundaries.append((page_num, page_start, page_end))
                current_pos += len(page_text) + 1  # +1 for space separator
            
            # Create chunk metadata with page tracking
            chunk_pos = 0
            for idx, chunk_text_content in enumerate(chunks, start=1):
                chunk_start = chunk_pos
                chunk_end = chunk_pos + len(chunk_text_content)
                
                # Find which page this chunk belongs to
                page_num = 1  # Default to first page
                for pnum, pstart, pend in page_boundaries:
                    if chunk_start >= pstart and chunk_start < pend:
                        page_num = pnum
                        break
                    # Also check if chunk spans page boundary
                    elif chunk_start < pend and chunk_end > pend:
                        page_num = pnum
                        break
                
                all_chunks.append({
                    "content": chunk_text_content,
                    "text": chunk_text_content,  # Alias for compatibility
                    "page": page_num,
                    "excerpt": chunk_text_content[:300].replace("\n", " "),
                    "filename": filepath.name,
                    "source_file": filepath.name,
                    "page_range": str(page_num),
                    "chunk_id": f"{filepath.stem}_chunk_{idx:03d}"
                })
                
                chunk_pos = chunk_end + 1  # Move to next chunk position
            
            # Log once per file (reduced noise)
            logging.info(f"Created {len(all_chunks)} chunks for {filepath.name}")
            
            # Convert chunks to format expected by phase1_parser
            chunks_for_parser = all_chunks
        else:
            # Fallback to standard preprocessing (for non-PDF or if PyMuPDF unavailable)
            logging.info(f"Using standard preprocessing for {filepath.name}...")
            chunks = preprocess_document(str(filepath), max_chars=1500)
            
            if not chunks:
                logging.error(f"[DEBUG] No chunks extracted from {filepath.name}")
                raise ValueError(f"No chunks extracted from {filepath.name}")
            
            logging.info(f"Extracted {len(chunks)} chunks from {filepath.name}")
            
            # Convert chunks to format expected by phase1_parser
            chunks_for_parser = []
            for idx, chunk in enumerate(chunks, start=1):
                chunks_for_parser.append({
                    "content": chunk.get("content", ""),
                    "text": chunk.get("content", ""),
                    "page": 1,
                    "excerpt": chunk.get("content", "")[:300].replace("\n", " "),
                    "filename": filepath.name,
                    "source_file": filepath.name,
                    "page_range": "1",
                    "chunk_id": chunk.get("chunk_id", f"{filepath.stem}_chunk_{idx:03d}")
                })
        
        if not chunks_for_parser:
            raise ValueError(f"No chunks created for {filepath.name}")
        
        prep_duration = time.time() - process_start_time
        logging.info(f"   [Preparation] COMPLETE: {len(chunks_for_parser)} chunks prepared ({prep_duration:.2f}s)")
        logging.info(f"   ========================================")
        logging.info(f"   Starting 3-phase pipeline...")
        logging.info(f"   ========================================")
        
        # ========================================================================
        # 3-PHASE PIPELINE
        # ========================================================================
        
        # Phase 1: Parser
        parser_output = None
        try:
            parser_output = phase1_parser(chunks_for_parser, filepath)
            temp_outputs["phase1_parser"] = parser_output
            
            # Save Phase 1 output to temp directory
            temp_file = REVIEW_TEMP_DIR / f"{filepath.stem}_phase1_parser.json"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(parser_output, f, indent=2, default=str)
            logging.info(f"💾 Saved Phase 1 output to {temp_file}")
        except Exception as phase1_err:
            logging.error(f"Phase 1 (parser) failed: {phase1_err}")
            logging.warning("Continuing to Phase 2 with empty parser output...")
            parser_output = {"records": [], "phase": "parser", "count": 0, "error": str(phase1_err)}
            temp_outputs["phase1_parser"] = parser_output
        
        # If Phase 1 failed or returned no records, try using vofc-engine directly as fallback
        if not parser_output.get("records"):
            logging.warning(f"Phase 1 returned no records, trying fallback to vofc-engine:latest...")
            try:
                # Fallback: Use vofc-engine directly on chunks
                model_name = "vofc-engine:latest"
                all_chunk_text = "\n\n".join([chunk.get("content", "") or chunk.get("text", "") for chunk in chunks_for_parser])
                # Limit chunk text to prevent overflow
                limited_text = all_chunk_text[:5000]
                fallback_prompt = f"""Extract vulnerabilities and options for consideration from this document.

CRITICAL: Respond ONLY in valid JSON array format. No markdown, no explanations.

Required format:
[{{"vulnerability": "...", "options_for_consideration": ["..."], "category": "...", "confidence_score": 0.9}}]

Document: {filepath.name}

Text:
{limited_text}

Return ONLY valid JSON array."""
                
                result_text = run_model(model=model_name, prompt=fallback_prompt)
                if result_text and result_text.strip():
                    json_text = result_text.strip()
                    if json_text.startswith("```"):
                        lines = json_text.split("\n")
                        json_text = "\n".join([l for l in lines if not l.strip().startswith("```")])
                    parsed = json.loads(json_text)
                    fallback_records = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
                    if fallback_records:
                        parser_output = {"records": fallback_records, "phase": "parser_fallback", "count": len(fallback_records)}
                        logging.info(f"Fallback to {model_name} succeeded: {len(fallback_records)} records")
            except Exception as fallback_err:
                logging.error(f"Fallback to vofc-engine also failed: {fallback_err}")
        
        # Phase 2: Engine
        engine_output = None
        try:
            if parser_output and parser_output.get("records"):
                engine_output = phase2_engine(parser_output, filepath)
                temp_outputs["phase2_engine"] = engine_output
                
                # Save Phase 2 output to temp directory
                temp_file = REVIEW_TEMP_DIR / f"{filepath.stem}_phase2_engine.json"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(engine_output, f, indent=2, default=str)
                logging.info(f"💾 Saved Phase 2 output to {temp_file}")
            else:
                logging.warning("Skipping Phase 2 - no parser output")
                engine_output = parser_output  # Use parser output as-is
        except Exception as phase2_err:
            logging.error(f"Phase 2 (engine) failed: {phase2_err}")
            logging.warning("Using Phase 1 output as fallback for Phase 2...")
            engine_output = parser_output if parser_output else {"records": [], "phase": "engine", "count": 0, "error": str(phase2_err)}
            temp_outputs["phase2_engine"] = engine_output
        
        if not engine_output or not engine_output.get("records"):
            logging.warning(f"Phase 2 returned no records, using Phase 1 output")
            engine_output = parser_output if parser_output else {"records": [], "phase": "engine", "count": 0}
        
        # Phase 3: Auditor
        auditor_output = None
        try:
            if engine_output and engine_output.get("records"):
                auditor_output = phase3_auditor(engine_output, filepath)
                temp_outputs["phase3_auditor"] = auditor_output
                
                # Save Phase 3 output to temp directory for debugging (intermediate step)
                # The final output will be saved to review/ via handle_successful_processing
                temp_file = REVIEW_TEMP_DIR / f"{filepath.stem}_phase3_auditor.json"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(auditor_output, f, indent=2, default=str)
                logging.info(f"💾 Saved Phase 3 output to {temp_file}")
            else:
                logging.warning("Skipping Phase 3 - no engine output")
                # Create minimal auditor output
                auditor_output = {
                    "records": [],
                    "phase": "auditor",
                    "count": 0,
                    "metadata": {"status": "skipped", "reason": "no_engine_output"}
                }
        except Exception as phase3_err:
            logging.error(f"Phase 3 (auditor) failed: {phase3_err}")
            logging.warning("Using Phase 2 output as fallback for Phase 3...")
            # Fallback: mark all as accepted
            auditor_output = {
                "records": engine_output.get("records", []) if engine_output else [],
                "phase": "auditor",
                "count": len(engine_output.get("records", [])) if engine_output else 0,
                "metadata": {"status": "accepted_all_fallback", "total": len(engine_output.get("records", [])) if engine_output else 0, "accepted": len(engine_output.get("records", [])) if engine_output else 0, "error": str(phase3_err)}
            }
            temp_outputs["phase3_auditor"] = auditor_output
        
        # Final post-processing (clean, deduplicate, resolve taxonomy)
        final_records = auditor_output.get("records", []) if auditor_output else []
        
        # If still no records after all phases, create a minimal result to prevent file from getting stuck
        if not final_records:
            logging.warning(f"All phases completed but no records extracted for {filepath.name}")
            logging.warning("Creating minimal result to allow file to complete processing...")
            # Create a minimal valid result structure
            final_records = [{
                "vulnerability": f"Document processed but no vulnerabilities extracted from {filepath.name}",
                "category": "Unknown",
                "options_for_consideration": ["Review document manually"],
                "confidence_score": 0.0,
                "audit_status": "needs_review",
                "source_file": filepath.name
            }]
        
        logging.info(f"Post-processing {len(final_records)} final records...")
        postprocessed = postprocess_results(final_records)
        
        if not postprocessed:
            raise ValueError(f"No valid records after post-processing for {filepath.name}")
        
        # Prepare final result structure
        result = {
            "source_file": filepath.name,
            "processed_at": datetime.now().isoformat(),
            "chunks_processed": len(chunks_for_parser),
            "phase1_parser_count": parser_output.get("count", 0),
            "phase2_engine_count": engine_output.get("count", 0),
            "phase3_auditor_count": auditor_output.get("count", 0),
            "final_records": len(postprocessed),
            "audit_metadata": auditor_output.get("metadata", {}),
            "vulnerabilities": [
                {
                    "vulnerability": r.get("vulnerability", ""),
                    "discipline_id": r.get("discipline_id"),
                    "category": r.get("category"),
                    "sector_id": r.get("sector_id"),
                    "subsector_id": r.get("subsector_id"),
                    "page_ref": r.get("page_ref"),
                    "chunk_id": r.get("chunk_id"),
                    "audit_status": r.get("audit_status", "accepted")
                }
                for r in postprocessed
            ],
            "options_for_consideration": [
                {
                    "option_text": ofc,
                    "vulnerability": r.get("vulnerability", ""),
                    "discipline_id": r.get("discipline_id"),
                    "sector_id": r.get("sector_id"),
                    "subsector_id": r.get("subsector_id"),
                    "audit_status": r.get("audit_status", "accepted")
                }
                for r in postprocessed
                for ofc in r.get("options_for_consideration", [])
            ],
            "summary": f"Processed {filepath.name}: {len(postprocessed)} vulnerabilities, {sum(len(r.get('options_for_consideration', [])) for r in postprocessed)} OFCs"
        }
        
        logging.info(f"✅ Successfully processed {filepath.name} through 3-phase pipeline")
        return result
        
    except Exception as e:
        logging.error(f"❌ Error processing {filepath.name}: {e}")
        logging.error(traceback.format_exc())
        
        # Save error output to temp directory for debugging
        error_output = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "temp_outputs": temp_outputs
        }
        try:
            error_file = REVIEW_TEMP_DIR / f"{filepath.stem}_error.json"
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(error_output, f, indent=2, default=str)
            logging.info(f"💾 Saved error output to {error_file}")
        except:
            pass
        
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
        
        # Move original document to library/ (removes from incoming, prevents re-trigger)
        library_path = LIBRARY_DIR / filepath.name
        shutil.move(str(filepath), str(library_path))
        logging.info(f"✅ File processing complete, moved to {LIBRARY_DIR}")
        
        # Copy JSON output to review/ for admin validation
        review_path = REVIEW_DIR / json_out.name
        shutil.copy(str(json_out), str(review_path))
        logging.info(f"Copied JSON to {review_path} for admin validation")
        
        # Sync to submissions table as pending_review
        try:
            from services.supabase_sync import sync_processed_result
            logging.info(f"📤 Syncing {review_path.name} to Supabase...")
            submission_id = sync_processed_result(str(review_path), submitter_email="system@psa.local")
            logging.info(f"✅ Created submission {submission_id} for review")
        except Exception as sync_err:
            logging.error(f"❌ Failed to create submission for {filepath.name}: {sync_err}")
            logging.error(f"   Error type: {type(sync_err).__name__}")
            import traceback
            logging.error(f"   Traceback: {traceback.format_exc()}")
            # Don't fail the whole process if sync fails, but log the error clearly
        
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

if WATCHDOG_AVAILABLE and FileSystemEventHandler:
    class IncomingWatcher(FileSystemEventHandler):
        """Monitors incoming folder for new files and triggers processing."""
        
        def __init__(self):
            super().__init__()
            self.processing_files = set()  # Track files being processed to avoid duplicates
        
        def _process_file_if_supported(self, path: Path):
            """Helper method to process a file if it's supported"""
            # Resolve to absolute path for logging and tracking
            abs_path = path.resolve()
            logging.info(f"🔍 Checking file: {path.name}")
            logging.info(f"   Absolute path: {abs_path}")
            
            # Check if file is supported
            supported_extensions = {'.pdf', '.docx', '.txt', '.xlsx'}
            file_ext = path.suffix.lower()
            if file_ext not in supported_extensions:
                logging.info(f"   ⏭️  Skipping {path.name} - unsupported extension: {file_ext}")
                logging.info(f"   Supported: {', '.join(supported_extensions)}")
                return
            
            # Check if file is a log file (should always be processed)
            filename_lower = path.name.lower()
            is_log_file = (
                '.log' in filename_lower or 
                'log' in filename_lower or
                (file_ext == '.txt' and 'log' in filename_lower)
            )
            
            if is_log_file:
                logging.info(f"   📋 Detected log file: {path.name} - will process regardless of library status")
            
            # Check if file exists in library directory
            library_path = LIBRARY_DIR / path.name
            file_in_library = library_path.exists()
            
            # Process if: NOT in library OR it's a log file
            if file_in_library and not is_log_file:
                logging.info(f"   ⏭️  Skipping {path.name} - already in library (not a log file)")
                return
            
            if not file_in_library:
                logging.info(f"   ✅ File {path.name} not in library - will process")
            elif is_log_file:
                logging.info(f"   ✅ File {path.name} is a log file - will process even though in library")
            
            # Check if already processing (by filename) - THIS IS THE PRIMARY CHECK
            # The processing_files set is checked FIRST and is the source of truth
            if path.name in self.processing_files:
                logging.info(f"   ⏭️  Skipping {path.name} - already processing")
                return
            
            # Only check processed_files if tracking is enabled
            if ENABLE_PROCESSED_TRACKING:
                # Only check processed_files for files that are >5 seconds old (to allow retries)
                # Don't check for very recent entries (0.0s) as that causes false positives
                now = time.time()
                original_incoming_path = (BASE_DIR / "incoming" / path.name).resolve()
                
                # Check current path (processing/ path) - only skip if >5s old
                if abs_path in processed_files:
                    time_since = now - processed_files[abs_path]
                    if time_since > 5:  # Only skip if processed more than 5 seconds ago
                        logging.info(f"   ⏭️  Skipping {path.name} - already processed ({time_since:.1f}s ago)")
                        return
                    # If <5s, remove the entry (likely from a failed/stuck attempt)
                    logging.debug(f"   ℹ️  Removing recent processed entry ({time_since:.1f}s old) - allowing retry")
                    del processed_files[abs_path]
                
                # Check original incoming path - only skip if >5s old
                if original_incoming_path in processed_files and original_incoming_path != abs_path:
                    time_since = now - processed_files[original_incoming_path]
                    if time_since > 5:  # Only skip if processed more than 5 seconds ago
                        logging.info(f"   ⏭️  Skipping {path.name} - already processed from incoming ({time_since:.1f}s ago)")
                        return
                    # If <5s, remove the entry
                    logging.debug(f"   ℹ️  Removing recent processed entry from incoming path ({time_since:.1f}s old)")
                    del processed_files[original_incoming_path]
            else:
                logging.debug(f"   ℹ️  Processed file tracking is DISABLED (ENABLE_PROCESSED_TRACKING=false)")
            
            # Optional: Check file hash to skip unchanged files
            # Skip hash check for log files or files not in library (they should be processed)
            if not is_log_file and file_in_library:
                try:
                    current_hash = file_hash(abs_path)
                    if current_hash and abs_path in processed_file_hashes:
                        if processed_file_hashes[abs_path] == current_hash:
                            logging.info(f"   ⏭️  Skipping {path.name} - file content unchanged (hash match)")
                            return
                except Exception as e:
                    logging.debug(f"   Could not check file hash: {e}")
            else:
                logging.debug(f"   ℹ️  Skipping hash check - file is log or not in library")
            
            # Debounce: Wait for file to be fully written (avoid partial writes)
            logging.info(f"   ⏳ Debouncing (waiting for file to be fully written)...")
            time.sleep(0.5)
            
            # Check if file still exists and is readable
            if not path.exists():
                logging.warning(f"   ⚠️  File {path.name} no longer exists after debounce")
                return
            
            # Verify file is in the correct directory
            expected_dir = Path(r"C:\Tools\Ollama\Data\incoming")
            if path.parent.resolve() != expected_dir.resolve():
                logging.warning(f"   ⚠️  File is not in expected directory!")
                logging.warning(f"   Expected: {expected_dir.resolve()}")
                logging.warning(f"   Actual: {path.parent.resolve()}")
                # Still try to process it if it's a valid file
            
            logging.info(f"   ✅ File validated: {path.name} ({path.stat().st_size} bytes)")
            import threading
            thread_id = threading.current_thread().ident
            thread_name = threading.current_thread().name
            
            logging.info(f"📂 Processing new file: {path.name}")
            logging.info(f"   Thread: {thread_name} (ID: {thread_id})")
            logging.info(f"   File path: {abs_path}")
            logging.info(f"   Current processing files: {list(self.processing_files)}")
            logging.info(f"   Already in processed_files: {abs_path in processed_files}")
            
            # Check if another thread is already processing this file
            if path.name in self.processing_files:
                logging.warning(f"   ⚠️  File {path.name} is already being processed by another thread!")
                logging.warning(f"   - Skipping to prevent duplicate processing")
                return
            
            try:
                # Add to processing set FIRST (prevents race condition)
                self.processing_files.add(path.name)
                logging.info(f"   ✅ Added {path.name} to processing_files set")
                
                # Mark as processed with timestamp AFTER adding to processing set (only if tracking enabled)
                # This prevents duplicate processing but allows the check above to work
                if ENABLE_PROCESSED_TRACKING:
                    processed_files[abs_path] = time.time()
                    # Also mark original incoming path if different
                    original_incoming_path = (BASE_DIR / "incoming" / path.name).resolve()
                    if original_incoming_path != abs_path:
                        processed_files[original_incoming_path] = time.time()
                    logging.info(f"   ✅ Marked {path.name} in processed_files dict")
                else:
                    logging.debug(f"   ℹ️  Skipping processed_files tracking (ENABLE_PROCESSED_TRACKING=false)")
                # Store file hash
                try:
                    current_hash = file_hash(abs_path)
                    if current_hash:
                        processed_file_hashes[abs_path] = current_hash
                except Exception:
                    pass
                
                # CRITICAL: Move file IMMEDIATELY to processing/ before calling process_file()
                # This prevents watcher from seeing it again
                processing_dir = BASE_DIR / "processing"
                processing_dir.mkdir(parents=True, exist_ok=True)
                temp_path = processing_dir / path.name
                
                try:
                    if path.exists():
                        shutil.move(str(path), str(temp_path))
                        logging.info(f"✅ Moved {path.name} to processing/ immediately")
                        path = temp_path  # Update path to new location
                        # Remove from tracking since file is now moved
                        if abs_path in processed_files:
                            del processed_files[abs_path]
                    else:
                        logging.warning(f"File {path.name} no longer exists")
                        return
                except Exception as move_err:
                    logging.error(f"Failed to move file to processing/: {move_err}")
                    # Continue anyway, but file may be re-triggered
                
                process_file(path)
            except Exception as e:
                logging.error(f"❌ Auto-processing failed for {path.name}: {e}")
                logging.error(traceback.format_exc())
                # Remove from processed dict on failure (allow retry after 5s)
                if abs_path in processed_files:
                    del processed_files[abs_path]
            finally:
                # Remove from processing set after a delay
                threading.Timer(60.0, lambda: self.processing_files.discard(path.name)).start()
        
        def on_created(self, event):
            """Handle new file creation events with time-based debouncing"""
            if event.is_directory:
                return
            
            path = Path(event.src_path)
            
            # Process supported file types in incoming directory
            supported_extensions = {'.pdf', '.docx', '.txt', '.xlsx'}
            if (
                path.suffix.lower() in supported_extensions
                and "incoming" in path.parts
                and "processed" not in path.parts
                and "library" not in path.parts
                and "processing" not in path.parts
            ):
                # Check if file still exists (may have been moved already)
                if not path.exists():
                    logging.debug(f"⏭️  Skipping {path.name} - file no longer exists")
                    return
                
                abs_path = path.resolve()
                
                # CRITICAL: Move file IMMEDIATELY to prevent re-triggering
                # Do this BEFORE any processing checks
                processing_dir = BASE_DIR / "processing"
                processing_dir.mkdir(parents=True, exist_ok=True)
                temp_path = processing_dir / path.name
                
                try:
                    # Try to move file immediately
                    if path.exists():
                        shutil.move(str(path), str(temp_path))
                        logging.info(f"✅ Moved {path.name} to processing/ immediately (prevents re-trigger)")
                        path = temp_path  # Update path to new location
                        abs_path = path.resolve()  # Update absolute path
                    else:
                        logging.debug(f"⏭️  Skipping {path.name} - file no longer exists")
                        return
                except Exception as move_err:
                    # If move fails, check if it's because file was already moved
                    if not path.exists():
                        logging.debug(f"⏭️  Skipping {path.name} - file already moved")
                        return
                    logging.error(f"Failed to move file to processing/: {move_err}")
                    # Continue with original path, but file may be re-triggered
                
                # Check if already processing (by filename, not path, since path changed)
                if path.name in self.processing_files:
                    logging.info(f"⏭️  Skipping {path.name} - already processing")
                    return
                
                logging.info(f"📄 Detected new file: {path.name}")
                # Don't mark as processed yet - let _process_file_if_supported handle it
                # It will check and mark appropriately
                self._process_file_if_supported(path)
        
        def on_moved(self, event):
            """Handle file move/copy events (some file operations trigger moved instead of created)"""
            if event.is_directory:
                return
            
            # When a file is moved/copied, event.dest_path contains the new location
            dest_path = Path(event.dest_path) if hasattr(event, 'dest_path') and event.dest_path else None
            src_path = Path(event.src_path) if hasattr(event, 'src_path') and event.src_path else None
            
            # Ignore moves TO processing/ directory (handled by on_created)
            if dest_path and "processing" in dest_path.parts:
                logging.debug(f"🔔 Ignoring move to processing/: {dest_path.name} (handled by on_created)")
                return
            
            # Only process if file is being moved INTO incoming/ directory
            if dest_path and "incoming" in dest_path.parts:
                # File is being moved/copied into incoming/
                logging.info(f"🔔 File system event: MOVED INTO incoming - {dest_path.name}")
                logging.info(f"   Full path: {dest_path.resolve()}")
                # Check if already processing to avoid duplicate
                if dest_path.name not in self.processing_files:
                    self._process_file_if_supported(dest_path)
                else:
                    logging.info(f"   ⏭️  Skipping {dest_path.name} - already processing")
            else:
                # Other moves - log but don't process
                logging.debug(f"🔔 File system event: MOVED - {dest_path or src_path} (not processing)")
else:
    # Fallback class when watchdog is not available
    class IncomingWatcher:
        """Dummy watcher class when watchdog is not available"""
        pass

def start_folder_watcher():
    """Start the folder watcher to monitor incoming directory"""
    if not WATCHDOG_AVAILABLE:
        logging.error("Cannot start folder watcher: watchdog not installed")
        return
    
    # Explicitly ensure we're watching the correct directory
    watch_dir = Path(r"C:\Tools\Ollama\Data\incoming")
    
    # Verify directory exists
    if not watch_dir.exists():
        logging.error(f"❌ Incoming directory does not exist: {watch_dir}")
        logging.info(f"Creating directory: {watch_dir}")
        watch_dir.mkdir(parents=True, exist_ok=True)
    
    # Log the exact path being watched
    watch_path = str(watch_dir.resolve())
    logging.info("=" * 60)
    logging.info(f"📂 Starting folder watcher")
    logging.info(f"   Watching directory: {watch_path}")
    logging.info(f"   Directory exists: {watch_dir.exists()}")
    logging.info(f"   Directory is readable: {os.access(watch_dir, os.R_OK)}")
    
    # List existing files in the directory
    existing_files = list(watch_dir.glob("*.*"))
    logging.info(f"   Existing files in directory: {len(existing_files)}")
    if existing_files:
        for f in existing_files[:5]:  # Show first 5 files
            logging.info(f"     - {f.name}")
        if len(existing_files) > 5:
            logging.info(f"     ... and {len(existing_files) - 5} more")
    logging.info("=" * 60)
    
    # Process existing files before starting watcher
    if existing_files:
        logging.info(f"📄 Processing {len(existing_files)} existing file(s) before starting watcher...")
        supported_extensions = {'.pdf', '.docx', '.txt', '.xlsx'}
        files_to_process = [f for f in existing_files if f.is_file() and f.suffix.lower() in supported_extensions]
        
        for filepath in files_to_process:
            try:
                abs_path = filepath.resolve()
                # Mark as processed with timestamp before processing (prevents watcher from re-processing)
                processed_files[abs_path] = time.time()
                # Store file hash
                try:
                    current_hash = file_hash(abs_path)
                    if current_hash:
                        processed_file_hashes[abs_path] = current_hash
                except Exception:
                    pass
                
                logging.info(f"🔄 Processing existing file: {filepath.name}")
                process_file(filepath)
                logging.info(f"✅ Successfully processed existing file: {filepath.name}")
            except Exception as e:
                logging.error(f"❌ Error processing existing file {filepath.name}: {e}")
                logging.error(traceback.format_exc())
                # Remove from processed dict on failure (allow retry after 5s)
                if abs_path in processed_files:
                    del processed_files[abs_path]
    
    event_handler = IncomingWatcher()
    global _watcher_observer
    _watcher_observer = Observer()
    _watcher_observer.schedule(event_handler, watch_path, recursive=False)
    _watcher_observer.start()
    
    logging.info(f"✅ Folder watcher started successfully")
    logging.info(f"   Monitoring: {watch_path}")
    logging.info("   Supported formats: PDF, DOCX, TXT, XLSX")
    
    try:
        while True:
            time.sleep(5)
            # Periodic health check - verify watcher is still running
            if not _watcher_observer.is_alive():
                logging.error("❌ Observer thread died unexpectedly!")
                break
            # Update progress.json periodically to indicate watcher is alive
            update_progress()
    except KeyboardInterrupt:
        logging.info("Folder watcher interrupted by user")
        _watcher_observer.stop()
    except Exception as e:
        logging.error(f"❌ Watcher error: {e}")
        logging.error(traceback.format_exc())
    finally:
        if _watcher_observer is not None:
            _watcher_observer.stop()
            _watcher_observer.join()
        _watcher_observer = None
        # Update progress to reflect stopped status
        update_progress()
        logging.info("Folder watcher stopped")

# ============================================================================
# File Processing (Refactored)
# ============================================================================

def process_file(filepath: Path) -> Path:
    """
    Simplified file processing workflow:
    1. Extract and parse (with page numbers for PDFs)
    2. Send to model and write JSON output
    3. Move original PDF to library folder
    
    Note: Callers should check processed_files dict before calling this function
    to avoid duplicate processing. This function does not check itself.
    
    Args:
        filepath: Path to the document file to process (should be a PDF)
    
    Returns:
        Path to the generated JSON output file
    """
    abs_path = filepath.resolve()
    ensure_dirs()
    
    logging.info(f"Starting processing for {filepath.name}")
    
    # CRITICAL: Check if file exists
    if not filepath.exists():
        logging.warning(f"File {filepath.name} no longer exists, skipping")
        return None
    
    # Check if file is already in processing/ directory (moved by watcher)
    processing_dir = BASE_DIR / "processing"
    is_in_processing = filepath.parent.resolve() == processing_dir.resolve()
    
    # If file is still in incoming/, move it to processing/ immediately
    # (This handles manual calls to process_file() that bypass the watcher)
    expected_incoming = Path(r"C:\Tools\Ollama\Data\incoming")
    if not is_in_processing and filepath.parent.resolve() == expected_incoming.resolve():
        processing_dir.mkdir(parents=True, exist_ok=True)
        temp_path = processing_dir / filepath.name
        try:
            shutil.move(str(filepath), str(temp_path))
            logging.info(f"✅ Moved {filepath.name} to processing/ to prevent re-triggering")
            filepath = temp_path  # Update filepath to point to new location
            is_in_processing = True
        except Exception as e:
            logging.error(f"Failed to move file to processing/: {e}")
            # Continue anyway, but file may be re-triggered
    
    # If file is not in incoming/ or processing/, skip it
    if not is_in_processing and filepath.parent.resolve() != expected_incoming.resolve():
        logging.warning(f"File {filepath.name} is not in incoming/ or processing/ ({filepath.parent}), skipping")
        return None
    
    try:
        # 1️⃣ Extract and parse
        # For PDFs, use page-based extraction; for others, use standard preprocessing
        if filepath.suffix.lower() == '.pdf' and PYMUPDF_AVAILABLE:
            pages = extract_text_with_pages(filepath)
            if pages:
                # Deduplicate and concatenate
                seen_texts = {}
                unique_pages = []
                for page_num, page_text in pages:
                    if page_text not in seen_texts:
                        seen_texts[page_text] = page_num
                        unique_pages.append((page_num, page_text))
                
                all_text = " ".join([page_text for _, page_text in unique_pages])
                normalized = normalize_text(all_text)
                # Reduced chunk size to 1500 to prevent timeout/token overflow
                chunks = chunk_text(normalized, max_chars=1500)
            else:
                # Fallback to standard preprocessing
                chunks = preprocess_document(str(filepath), max_chars=1500)
                chunks = [chunk.get('content', '') if isinstance(chunk, dict) else chunk for chunk in chunks]
        else:
            # Non-PDF or PyMuPDF unavailable - use standard preprocessing
            chunks = preprocess_document(str(filepath), max_chars=1500)
            chunks = [chunk.get('content', '') if isinstance(chunk, dict) else chunk for chunk in chunks]
        
        logging.info(f"Created {len(chunks)} chunks for {filepath.name}")
        
        # 2️⃣ Send to model and write JSON output
        result = process_document_file(filepath)  # This handles the full pipeline
        
        # Validate JSON before writing (completion guard)
        output_json_valid = False
        try:
            # Test if result can be serialized to JSON
            json_str = json.dumps(result, indent=2, ensure_ascii=False, default=str)
            # Validate it can be parsed back
            json.loads(json_str)
            output_json_valid = True
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            logging.warning(f"Invalid JSON output for {filepath.name}: {e}")
            logging.warning("Skipping file write, moving to errors")
            output_json_valid = False
        
        # Completion guard: Only proceed if JSON is valid
        if output_json_valid:
            # Use handle_successful_processing to:
            # 1. Save JSON to processed/
            # 2. Move file to library/
            # 3. Copy JSON to review/ for admin validation
            # 4. Sync to Supabase submissions table
            handle_successful_processing(filepath, result)
            
            # Update progress
            update_progress()
            
            # Return path to processed JSON
            json_path = PROCESSED_DIR / f"{filepath.stem}_vofc.json"
            return json_path
        else:
            # Move to errors if JSON is invalid (file already moved to processing/)
            error_path = ERROR_DIR / filepath.name
            if filepath.exists():
                shutil.move(str(filepath), str(error_path))
                logging.error(f"Moved {filepath.name} to errors/ (invalid JSON output)")
            else:
                logging.warning(f"File {filepath.name} already moved, skipping error move")
            update_progress()
            raise ValueError(f"Invalid JSON output for {filepath.name}")
        
    except Exception as e:
        # Handle failed processing
        logging.error(f"Error processing {filepath.name}: {e}")
        logging.error(traceback.format_exc())
        
        # CRITICAL: Ensure file is ALWAYS moved out of processing/ directory
        # Try multiple times if needed
        max_retries = 3
        moved = False
        for attempt in range(max_retries):
            try:
                if filepath.exists():
                    error_path = ERROR_DIR / filepath.name
                    # Ensure error directory exists
                    ERROR_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(filepath), str(error_path))
                    logging.info(f"✅ Moved {filepath.name} to errors/ after failure (attempt {attempt + 1})")
                    moved = True
                    break
                else:
                    # File already moved or doesn't exist
                    logging.info(f"File {filepath.name} no longer exists in processing/, may have been moved already")
                    moved = True
                    break
            except Exception as move_err:
                logging.warning(f"Attempt {attempt + 1} failed to move file to errors/: {move_err}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait 1 second before retry
                else:
                    logging.error(f"❌ CRITICAL: Failed to move {filepath.name} after {max_retries} attempts. File may be stuck in processing/")
                    # Try to at least copy it to errors/ so we don't lose it
                    try:
                        error_path = ERROR_DIR / f"stuck_{filepath.name}"
                        shutil.copy(str(filepath), str(error_path))
                        logging.error(f"Copied stuck file to {error_path} as backup")
                    except:
                        pass
        
        update_progress()
        
        # Don't raise if we successfully moved the file - let it complete
        if not moved:
            raise  # Only raise if we couldn't move the file

# ============================================================================
# Supabase Sync
# ============================================================================

# Note: check_review_approval and insert_library_record are imported from services.supabase_client

def sync_review_files_to_submissions() -> None:
    """
    Sync review JSON files from review/ folder to Supabase submissions table as pending_review.
    This makes files available for admin review in the dashboard.
    Only creates submissions for files that don't already have a submission record.
    """
    try:
        from services.supabase_sync import sync_processed_result
        
        review_files = list(REVIEW_DIR.glob("*.json"))
        
        if not review_files:
            return
        
        logging.info(f"Checking {len(review_files)} review file(s) for submission sync...")
        
        synced_count = 0
        skipped_count = 0
        
        for review_file in review_files:
            try:
                # Check if a submission already exists for this file
                filename_stem = review_file.stem.replace('_vofc', '').replace('_phase3_auditor', '')
                
                # Check if submission already exists by checking source_file in data JSONB column
                client = get_supabase_client()
                # Query all recent submissions and filter in Python (JSONB queries can be tricky)
                all_results = client.table('submissions').select('id, data').order('created_at', desc=True).limit(100).execute()
                
                submission_exists = False
                if all_results.data:
                    import json
                    for sub in all_results.data:
                        sub_data = sub.get('data', {})
                        if isinstance(sub_data, str):
                            try:
                                sub_data = json.loads(sub_data)
                            except:
                                continue
                        source_file = sub_data.get('source_file', '')
                        document_name = sub_data.get('document_name', '')
                        if filename_stem.lower() in str(source_file).lower() or filename_stem.lower() in str(document_name).lower():
                            submission_exists = True
                            break
                
                result = type('obj', (object,), {'data': [] if not submission_exists else [{'id': 'found'}]})()
                
                if result.data and len(result.data) > 0:
                    logging.debug(f"⏭️  Skipping {review_file.name} - submission already exists")
                    skipped_count += 1
                    continue
                
                logging.info(f"📤 Creating submission for review file: {review_file.name}")
                
                # Sync to submissions table as pending_review
                try:
                    logging.info(f"📤 Syncing {review_file.name} to Supabase...")
                    submission_id = sync_processed_result(str(review_file), submitter_email="system@psa.local")
                    logging.info(f"✅ Created submission {submission_id} for {review_file.name}")
                    synced_count += 1
                except Exception as sync_err:
                    logging.error(f"❌ Failed to create submission for {review_file.name}: {sync_err}")
                    logging.error(f"   Error type: {type(sync_err).__name__}")
                    import traceback
                    logging.error(f"   Traceback: {traceback.format_exc()}")
                    # Continue processing other files
                    continue
                    
            except Exception as e:
                logging.error(f"❌ Error processing {review_file.name}: {e}")
                logging.error(traceback.format_exc())
                continue
        
        if synced_count > 0:
            logging.info(f"📊 Created {synced_count} submission(s) from review files")
        if skipped_count > 0:
            logging.info(f"⏭️  Skipped {skipped_count} file(s) (already have submissions)")
        
    except Exception as e:
        logging.error(f"Error in sync_review_files_to_submissions: {e}")
        logging.error(traceback.format_exc())

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
                with open(review_file, "r", encoding="utf-8-sig") as jf:
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
        # Explicitly use the correct directory
        incoming_dir = Path(r"C:\Tools\Ollama\Data\incoming")
        
        if not incoming_dir.exists():
            logging.warning(f"Incoming directory does not exist: {incoming_dir}")
            return []
        
        # Get all files (exclude subdirectories and hidden files)
        files = [
            f for f in incoming_dir.iterdir()
            if f.is_file() and not f.name.startswith('.')
        ]
        
        # Filter by supported extensions
        supported_extensions = {'.pdf', '.docx', '.txt', '.xlsx'}
        files = [f for f in files if f.suffix.lower() in supported_extensions]
        
        logging.debug(f"Found {len(files)} files in {incoming_dir}")
        return sorted(files, key=lambda x: x.stat().st_mtime)  # Process oldest first
    except Exception as e:
        logging.error(f"Error getting incoming files: {e}")
        logging.error(traceback.format_exc())
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
        
        # Initialize progress.json if it doesn't exist
        if not PROGRESS_FILE.exists():
            logging.info("Initializing progress.json...")
            update_progress()
        
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
        
        # Main loop: periodic Supabase sync and progress updates
        sync_interval = 600  # 10 minutes
        progress_interval = 30  # Update progress every 30 seconds
        logging.info(f"Starting Supabase sync loop (every {sync_interval} seconds)...")
        logging.info(f"Progress updates every {progress_interval} seconds...")
        
        last_sync = time.time()
        last_progress = time.time()
        
        while True:
            try:
                current_time = time.time()
                
                # Update progress more frequently (every 30 seconds)
                if current_time - last_progress >= progress_interval:
                    update_progress()
                    last_progress = current_time
                
                # Sync approved review files to Supabase (every 10 minutes)
                if current_time - last_sync >= sync_interval:
                    sync_review_to_supabase()
                    last_sync = current_time
                
                # Sleep for a short interval to allow for responsive updates
                time.sleep(5)  # Check every 5 seconds
                
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

