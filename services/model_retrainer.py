"""
Automated Model Retraining Trigger
Monitors learning metrics and triggers retraining when performance declines.
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from services.supabase_client import get_recent_learning_stats, record_retrain_event
from services.ollama_client import retrain_model

# Setup logging
logging.basicConfig(
    filename='logs/model_retrainer.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
THRESHOLD = 0.6  # Default accept rate threshold (60%)
WINDOW = 5  # Check last 5 learning cycles
CHECK_INTERVAL_MIN = 60  # Check every hour
MIN_STATS_REQUIRED = 3  # Minimum stats needed before triggering (to avoid false positives)


def check_retrain_condition():
    """
    Check if retraining conditions are met based on recent learning stats.
    
    Returns:
        bool: True if retraining was triggered, False otherwise
    """
    try:
        stats = get_recent_learning_stats(WINDOW)
        
        if not stats or len(stats) < MIN_STATS_REQUIRED:
            logger.info(f"Not enough data for retrain evaluation. Have {len(stats) if stats else 0}, need {MIN_STATS_REQUIRED}")
            return False
        
        # Calculate average accept rate from recent stats
        accept_rates = [s.get("accept_rate", 0) for s in stats if s.get("accept_rate") is not None]
        
        if not accept_rates:
            logger.warning("No accept_rate data found in learning stats")
            return False
        
        avg_accept = sum(accept_rates) / len(accept_rates)
        
        logger.info(f"Retrain check: Average accept rate = {avg_accept:.3f} (threshold = {THRESHOLD})")
        
        if avg_accept < THRESHOLD:
            logger.warning(
                f"Average accept rate {avg_accept:.3f} below threshold {THRESHOLD}. "
                f"Triggering retrain. Stats window: {len(stats)} cycles"
            )
            
            # Record retrain event
            try:
                record_retrain_event(avg_accept, len(stats))
            except Exception as e:
                logger.error(f"Failed to record retrain event: {e}")
            
            # Trigger retraining
            try:
                retrain_model()
                logger.info("Model retraining triggered successfully")
            except Exception as e:
                logger.error(f"Failed to trigger model retraining: {e}")
                raise
            
            return True
        else:
            logger.info(f"Average accept rate healthy: {avg_accept:.3f} >= {THRESHOLD}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking retrain condition: {e}", exc_info=True)
        return False


def start_retrain_monitor(interval_minutes=CHECK_INTERVAL_MIN):
    """
    Start background thread to monitor learning metrics and trigger retraining.
    
    Args:
        interval_minutes: How often to check (default: 60 minutes)
    """
    def monitor():
        logger.info(f"Model retrain monitor started (checking every {interval_minutes} minutes)")
        while True:
            try:
                check_retrain_condition()
            except Exception as e:
                logger.error(f"Retrain monitor error: {e}", exc_info=True)
            
            # Sleep for the specified interval
            time.sleep(interval_minutes * 60)
    
    # Start the monitor thread as a daemon so it exits with the main program
    thread = threading.Thread(target=monitor, daemon=True, name="ModelRetrainMonitor")
    thread.start()
    logger.info("Model retrain monitor thread started")


if __name__ == "__main__":
    # CLI mode for testing
    print("Running model retrainer in CLI mode (single check)...")
    result = check_retrain_condition()
    print(f"Retrain condition check result: {result}")

