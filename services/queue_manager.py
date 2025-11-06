"""
Job Queue System
Manages file processing queue with background worker thread
"""

import threading
import json
import time
import os
import traceback
from pathlib import Path

# Import processor after it's defined to avoid circular imports
# from services.processor import process_file

# Queue and directory paths
QUEUE_PATH = Path(__file__).parent.parent / "data" / "queue.json"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
ERROR_DIR = Path(__file__).parent.parent / "data" / "errors"
INCOMING_DIR = Path(__file__).parent.parent / "data" / "incoming"

# Ensure directories exist
for dir_path in [PROCESSED_DIR, ERROR_DIR, INCOMING_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

def load_queue():
    """Load queue from JSON file"""
    if not QUEUE_PATH.exists():
        return []
    
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_queue(queue):
    """Save queue to JSON file"""
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)

def add_job(filename):
    """Add a job to the processing queue"""
    queue = load_queue()
    if filename not in [job.get("filename") for job in queue]:
        queue.append({"filename": filename, "status": "pending"})
        save_queue(queue)

def worker_loop():
    """Background worker that processes jobs from the queue"""
    while True:
        queue = load_queue()
        changed = False
        
        for job in queue:
            if job.get("status") != "pending":
                continue
            
            try:
                print(f"⚙️  Processing {job['filename']}")
                job["status"] = "running"
                save_queue(queue)
                
                # Import here to avoid circular import
                from services.processor import process_file
                
                path = INCOMING_DIR / job["filename"]
                
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                
                result = process_file(str(path))
                
                # Save result to processed directory
                out_path = PROCESSED_DIR / f"{job['filename']}.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)
                
                job["status"] = "done"
                job["result_path"] = str(out_path)
                
                # Send to Supabase
                try:
                    from services.supabase_sync import sync_processed_result
                    from services.learning_logger import log_learning_event
                    
                    submission_id = sync_processed_result(str(out_path))
                    job["supabase_submission_id"] = submission_id
                    print(f"✅ Synced to Supabase: submission {submission_id}")
                    
                    # Log the learning event
                    try:
                        log_learning_event(submission_id, str(out_path), model_version="psa-engine:latest")
                    except Exception as learning_err:
                        # Don't fail if learning event logging fails
                        print(f"⚠️  Warning: Learning event logging failed: {str(learning_err)}")
                        job["learning_event_error"] = str(learning_err)
                    
                except Exception as sync_err:
                    # Don't fail the job if Supabase sync fails - log it but mark job as done
                    job["supabase_sync_error"] = str(sync_err)
                    print(f"⚠️  Warning: Supabase sync failed: {str(sync_err)}")
                    # Job is still marked as "done" since processing succeeded
                
            except Exception as e:
                job["status"] = "error"
                job["error"] = str(e)
                
                # Save error log
                error_log_path = ERROR_DIR / f"{job['filename']}.log"
                with open(error_log_path, "w", encoding="utf-8") as log:
                    log.write(traceback.format_exc())
                
                print(f"❌ Error processing {job['filename']}: {str(e)}")
            
            changed = True
            save_queue(queue)
        
        if not changed:
            time.sleep(5)  # Idle wait when no jobs

def start_worker():
    """Start the background worker thread"""
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    print("✅ Queue worker started")

