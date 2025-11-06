"""
Learning Engine Service
Processes learning events and updates system heuristics based on analyst feedback.
"""

import logging
import time
from datetime import datetime, timedelta
from services.supabase_client import get_learning_events, insert_learning_stats
from services.heuristics import adjust_confidence_thresholds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_learning_cycle(interval_minutes=60):
    """
    Process new learning events and update learning statistics.
    
    Args:
        interval_minutes: Time window to look back for events (default: 60 minutes)
    
    Returns:
        Dictionary with learning statistics
    """
    logger.info(f"Starting learning engine cycle (looking back {interval_minutes} minutes)...")
    
    try:
        # Calculate time window
        since = datetime.utcnow() - timedelta(minutes=interval_minutes)
        
        # Get learning events from the time window
        events = get_learning_events(since)
        
        if not events:
            logger.info("No new learning events in the last cycle.")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "window_minutes": interval_minutes,
                "total_events": 0,
                "message": "No events found"
            }
        
        # Categorize events by type
        accepted = [e for e in events if e.get("approved") is True or e.get("event_type") == "approval"]
        rejected = [e for e in events if e.get("approved") is False or e.get("event_type") == "rejection"]
        edited = [e for e in events if e.get("event_type") == "correction" or e.get("event_type") == "edited"]
        
        # Calculate statistics
        total_events = len(events)
        accepted_count = len(accepted)
        rejected_count = len(rejected)
        edited_count = len(edited)
        
        # Calculate acceptance rate
        review_events = accepted_count + rejected_count
        accept_rate = round(accepted_count / max(review_events, 1), 3) if review_events > 0 else 0.0
        
        # Calculate average confidence scores
        accepted_confidences = [float(e.get("confidence_score", 0)) for e in accepted if e.get("confidence_score")]
        rejected_confidences = [float(e.get("confidence_score", 0)) for e in rejected if e.get("confidence_score")]
        
        avg_accepted_confidence = round(sum(accepted_confidences) / len(accepted_confidences), 3) if accepted_confidences else 0.0
        avg_rejected_confidence = round(sum(rejected_confidences) / len(rejected_confidences), 3) if rejected_confidences else 0.0
        
        # Build statistics dictionary
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "window_minutes": interval_minutes,
            "total_events": total_events,
            "accepted": accepted_count,
            "rejected": rejected_count,
            "edited": edited_count,
            "accept_rate": accept_rate,
            "avg_accepted_confidence": avg_accepted_confidence,
            "avg_rejected_confidence": avg_rejected_confidence,
            "confidence_gap": round(avg_accepted_confidence - avg_rejected_confidence, 3)
        }
        
        # Insert learning statistics (optional - if learning_stats table exists)
        try:
            insert_learning_stats(stats)
        except Exception as e:
            logger.warning(f"Could not insert learning stats (table may not exist): {e}")
        
        # Adjust confidence thresholds based on acceptance rate
        try:
            adjust_confidence_thresholds(accept_rate, stats)
        except Exception as e:
            logger.warning(f"Could not adjust confidence thresholds: {e}")
        
        logger.info(f"Learning cycle complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error in learning cycle: {e}", exc_info=True)
        raise


def start_learning_monitor(interval_minutes=60):
    """
    Start background learning monitor thread.
    
    Args:
        interval_minutes: How often to run the learning cycle (default: 60 minutes)
    """
    def monitor():
        logger.info(f"Learning monitor started (interval: {interval_minutes} minutes)")
        while True:
            try:
                run_learning_cycle(interval_minutes)
            except Exception as e:
                logger.error(f"Learning cycle error: {e}", exc_info=True)
            
            # Sleep for the interval
            time.sleep(interval_minutes * 60)
    
    import threading
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    logger.info(f"✅ Learning monitor thread started (checking every {interval_minutes} minutes)")

