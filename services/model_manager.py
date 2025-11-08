"""
VOFC Model Manager
------------------
Autonomous maintenance service that monitors model performance,
checks learning event metrics, and triggers conditional retraining
when thresholds are met.

Usage:
  python services/model_manager.py

Run as an NSSM service or scheduled nightly.
"""

from datetime import datetime, timedelta
import os
import subprocess
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# -------------------------------
# CONFIGURATION
# -------------------------------

MODEL_NAME = "vofc-engine"
OLLAMA_PATH = r"C:\Tools\Ollama"  # adjust if different
TRAINING_PATH = r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\training_data"
TRAINING_CONFIG = os.path.join(TRAINING_PATH, "vofc_engine_training.yaml")
LOG_FILE = r"C:\Tools\VOFC_Logs\model_manager.log"

# Retrain thresholds
MIN_VULN_YIELD = 80.0      # minimum acceptable vuln yield %
MIN_DELTA_SCORE = 0       # if below, retraining candidate
MIN_NEW_EVENTS = 3        # minimum new learning events since last retrain

# -------------------------------
# LOGGING (Set up early so we can log .env loading)
# -------------------------------

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    filemode='a'  # Append mode
)

# Check if Supabase credentials are already available from NSSM/system environment
supabase_url_available = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
supabase_key_available = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')

# Only load .env file if credentials are not already set (NSSM/system vars take precedence)
if not (supabase_url_available and supabase_key_available):
    try:
        from dotenv import load_dotenv
        # Try to load .env from project root
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"
        if env_file.exists():
            # Don't override existing environment variables (system vars take precedence)
            load_dotenv(env_file, override=False)
            logging.info(f"Loaded environment variables from {env_file} (system vars take precedence)")
        else:
            logging.warning(f".env file not found at {env_file}")
    except ImportError:
        # python-dotenv not installed, skip .env loading
        logging.warning("python-dotenv not installed - .env file will not be loaded automatically")
    except Exception as e:
        logging.warning(f"Failed to load .env file: {e}")
else:
    logging.info("Using Supabase credentials from NSSM/system environment variables")

# Verify credentials are available after loading
final_supabase_url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
final_supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')

if final_supabase_url and final_supabase_key:
    # Log first few chars of key for verification (don't log full key)
    key_preview = final_supabase_key[:20] + "..." if len(final_supabase_key) > 20 else final_supabase_key
    logging.info(f"Supabase credentials verified - URL: {final_supabase_url[:30]}..., Key: {key_preview} (length: {len(final_supabase_key)})")
else:
    logging.error("Supabase credentials not available after environment loading!")
    logging.error(f"  SUPABASE_URL: {'SET' if final_supabase_url else 'NOT SET'}")
    logging.error(f"  SUPABASE_SERVICE_ROLE_KEY: {'SET' if final_supabase_key else 'NOT SET'}")

from services.supabase_client import get_supabase_client

def log(msg: str):
    """Log message to both console and file"""
    print(msg)
    logging.info(msg)


# -------------------------------
# FUNCTIONS
# -------------------------------

def get_summary():
    """Pull model performance summary from Supabase view."""
    try:
        supabase = get_supabase_client()
        # Query the view as a table (Supabase views are queryable like tables)
        res = supabase.table("view_model_performance_summary").select("*").execute()
        
        if not res.data:
            log("[WARN] No summary data found.")
            return []
        
        return res.data
    except Exception as e:
        log(f"[ERROR] Failed to get summary: {e}")
        # If view doesn't exist, return empty list (non-critical)
        if "does not exist" in str(e) or "PGRST" in str(e):
            log("[INFO] Performance summary view not available - skipping evaluation")
        return []


def get_recent_learning_events(days: int = 7):
    """Get recent learning events to see if enough new data exists."""
    try:
        supabase = get_supabase_client()
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        query = (
            supabase.table("learning_events")
            .select("id, model_version, event_type, created_at")
            .gte("created_at", since)
            .order("created_at", desc=True)
        ).execute()
        
        return query.data or []
    except Exception as e:
        log(f"[ERROR] Failed to get learning events: {e}")
        return []


def trigger_retrain(current_version: str, reason: str):
    """Run Ollama retraining process."""
    try:
        # Extract version number and increment
        version_str = current_version.replace("v", "").replace(":", "")
        try:
            version_number = int(version_str) + 1
        except ValueError:
            # If version is "latest" or invalid, start at v2
            version_number = 2
        
        new_version = f"v{version_number}"
        
        # Use Modelfile (Ollama doesn't support YAML training configs natively)
        modelfile_path = os.path.join(TRAINING_PATH, "Modelfile")
        
        if not os.path.exists(modelfile_path):
            log(f"[ERROR] Modelfile not found at {modelfile_path}")
            log(f"[INFO] Expected path: {modelfile_path}")
            return None
        
        # Use absolute path for Modelfile
        abs_modelfile = os.path.abspath(modelfile_path)
        
        # Use explicit Ollama executable path
        OLLAMA_EXE = os.path.join(OLLAMA_PATH, "ollama.exe")
        if not os.path.exists(OLLAMA_EXE):
            # Fallback to system PATH if not in OLLAMA_PATH
            OLLAMA_EXE = "ollama.exe"
        
        cmd = f'"{OLLAMA_EXE}" create {MODEL_NAME}:{new_version} -f "{abs_modelfile}"'
        
        log(f"[ACTION] Retraining {MODEL_NAME}:{new_version} due to {reason}")
        log(f"[INFO] Running command: {cmd}")
        
        result = subprocess.run(
            cmd,
            cwd=OLLAMA_PATH if os.path.exists(OLLAMA_PATH) else os.getcwd(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode != 0:
            log(f"[ERROR] Retraining failed: {result.stderr}")
            return None
        
        log(f"[SUCCESS] Model {MODEL_NAME}:{new_version} created successfully")
        
        # Register retrain event in Supabase
        try:
            supabase = get_supabase_client()
            # Create learning event record (use minimal fields to avoid schema issues)
            event_data = {
                "event_type": "auto_parse",  # Use existing event type (auto_retrain may not be in check constraint)
                "model_version": f"{MODEL_NAME}:{new_version}",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Add metadata if schema supports it (will fail gracefully if not)
            try:
                event_data["metadata"] = {
                    "reason": reason,
                    "previous_version": current_version,
                    "triggered_by": "model_manager",
                    "training_config": TRAINING_CONFIG,
                    "retrain_type": "automatic"
                }
            except:
                pass  # Metadata is optional
            
            # Try to insert, but don't fail if it doesn't work
            try:
                supabase.table("learning_events").insert(event_data).execute()
                log(f"[SUCCESS] Registered retrain event for {MODEL_NAME}:{new_version}")
            except Exception as insert_error:
                log(f"[WARN] Could not register retrain event: {insert_error}")
                log("   This is not critical - retraining completed successfully")
        except Exception as e:
            log(f"[WARN] Failed to register retrain event: {e}")
        
        return new_version
        
    except subprocess.TimeoutExpired:
        log(f"[ERROR] Retraining timed out after 10 minutes")
        return None
    except Exception as e:
        log(f"[ERROR] Retraining failed: {e}")
        logging.exception("Full traceback:")
        return None


def evaluate_models():
    """Core decision logic."""
    summaries = get_summary()
    if not summaries:
        log("[INFO] No summaries available to evaluate.")
        return
    
    for m in summaries:
        model_id = m.get("model_id", MODEL_NAME)
        version = m.get("model_version", "v1")
        vuln_yield = float(m.get("vuln_yield_pct") or 0)
        delta = float(m.get("avg_delta_score") or 0)
        
        log(f"[CHECK] {model_id}:{version} | yield={vuln_yield:.1f}% delta={delta}")
        
        # Check for recent learning events
        new_events = get_recent_learning_events()
        new_count = len(new_events)
        log(f"[INFO] Recent learning events (last 7 days): {new_count}")
        
        # Retrain decision logic
        should_retrain = False
        reason_parts = []
        
        if vuln_yield < MIN_VULN_YIELD:
            should_retrain = True
            reason_parts.append(f"yield={vuln_yield:.1f}%<{MIN_VULN_YIELD}%")
        
        if delta < MIN_DELTA_SCORE:
            should_retrain = True
            reason_parts.append(f"delta={delta}<{MIN_DELTA_SCORE}")
        
        if new_count >= MIN_NEW_EVENTS:
            should_retrain = True
            reason_parts.append(f"new_events={new_count}>={MIN_NEW_EVENTS}")
        
        if should_retrain:
            reason = ", ".join(reason_parts)
            log(f"[DECISION] Retraining triggered: {reason}")
            new_version = trigger_retrain(version, reason)
            if new_version:
                log(f"[SUCCESS] Retraining completed: {MODEL_NAME}:{new_version}")
            else:
                log(f"[ERROR] Retraining failed for {MODEL_NAME}:{version}")
        else:
            log(f"[SKIP] {model_id}:{version} meets thresholds (yield={vuln_yield:.1f}%, delta={delta}, events={new_count}).")


# -------------------------------
# MAIN
# -------------------------------

if __name__ == "__main__":
    log("=== VOFC Model Manager Run Start ===")
    
    # Keep service running even after errors
    while True:
        try:
            evaluate_models()
            log("[INFO] Sleeping for 6 hours before next check...")
            time.sleep(21600)  # 6 hours
        except KeyboardInterrupt:
            log("[INFO] Received interrupt signal, shutting down...")
            break
        except Exception as e:
            logging.exception(f"[ERROR] ModelManager error in evaluation cycle: {e}")
            log(f"[ERROR] ModelManager error in evaluation cycle: {e}")
            log("[INFO] Will retry in 1 hour...")
            # Sleep for 1 hour before retrying after an error (instead of 6 hours)
            time.sleep(3600)  # 1 hour
    
    log("=== VOFC Model Manager Run End ===")

