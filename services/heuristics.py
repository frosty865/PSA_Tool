"""
Heuristics Service
Manages confidence thresholds and other heuristic parameters that adapt based on learning feedback.
"""

import logging
import json
import os
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default confidence thresholds
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.85

# Heuristics config file path
HEURISTICS_CONFIG_PATH = Path(__file__).parent.parent / "data" / "heuristics_config.json"


def load_heuristics_config():
    """
    Load heuristics configuration from file or return defaults.
    
    Returns:
        Dictionary with heuristic parameters
    """
    if HEURISTICS_CONFIG_PATH.exists():
        try:
            with open(HEURISTICS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"Loaded heuristics config from {HEURISTICS_CONFIG_PATH}")
                return config
        except Exception as e:
            logger.warning(f"Failed to load heuristics config: {e}, using defaults")
    
    # Return default configuration
    return {
        "confidence_threshold": DEFAULT_CONFIDENCE_THRESHOLD,
        "high_confidence_threshold": DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
        "last_updated": None,
        "accept_rate": None,
        "adjustment_history": []
    }


def save_heuristics_config(config):
    """
    Save heuristics configuration to file.
    
    Args:
        config: Dictionary with heuristic parameters
    """
    try:
        # Ensure directory exists
        HEURISTICS_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(HEURISTICS_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved heuristics config to {HEURISTICS_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"Failed to save heuristics config: {e}")


def adjust_confidence_thresholds(accept_rate, stats=None):
    """
    Adjust confidence thresholds based on acceptance rate.
    
    Logic:
    - High accept rate (>0.8): Lower threshold (model is too conservative)
    - Low accept rate (<0.5): Raise threshold (model is too permissive)
    - Medium accept rate (0.5-0.8): Keep threshold stable
    
    Args:
        accept_rate: Float between 0.0 and 1.0 representing acceptance rate
        stats: Optional dictionary with additional statistics
    """
    try:
        config = load_heuristics_config()
        current_threshold = config.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)
        current_high_threshold = config.get("high_confidence_threshold", DEFAULT_HIGH_CONFIDENCE_THRESHOLD)
        
        # Adjustment parameters
        ADJUSTMENT_STEP = 0.05  # How much to adjust per cycle
        TARGET_ACCEPT_RATE = 0.65  # Target acceptance rate
        
        # Calculate adjustment
        rate_diff = accept_rate - TARGET_ACCEPT_RATE
        
        # Adjust threshold based on acceptance rate
        if accept_rate > 0.8:
            # Too many acceptances - model is too conservative, lower threshold
            new_threshold = max(0.5, current_threshold - ADJUSTMENT_STEP)
            adjustment_reason = f"High accept rate ({accept_rate:.2f}) - lowering threshold"
        elif accept_rate < 0.5:
            # Too few acceptances - model is too permissive, raise threshold
            new_threshold = min(0.95, current_threshold + ADJUSTMENT_STEP)
            adjustment_reason = f"Low accept rate ({accept_rate:.2f}) - raising threshold"
        else:
            # Acceptable range - make small adjustments toward target
            if abs(rate_diff) > 0.1:  # Only adjust if significantly off target
                new_threshold = current_threshold - (rate_diff * ADJUSTMENT_STEP)
                new_threshold = max(0.5, min(0.95, new_threshold))  # Clamp to valid range
                adjustment_reason = f"Adjusting toward target ({accept_rate:.2f} vs {TARGET_ACCEPT_RATE:.2f})"
            else:
                new_threshold = current_threshold
                adjustment_reason = "Within acceptable range - no adjustment"
        
        # Adjust high confidence threshold proportionally
        threshold_ratio = new_threshold / current_threshold if current_threshold > 0 else 1.0
        new_high_threshold = current_high_threshold * threshold_ratio
        new_high_threshold = max(new_threshold + 0.1, min(0.99, new_high_threshold))  # Keep at least 0.1 above base
        
        # Only update if threshold actually changed
        if abs(new_threshold - current_threshold) > 0.01:
            config["confidence_threshold"] = round(new_threshold, 3)
            config["high_confidence_threshold"] = round(new_high_threshold, 3)
            config["last_updated"] = datetime.utcnow().isoformat()
            config["accept_rate"] = accept_rate
            
            # Record adjustment history
            if "adjustment_history" not in config:
                config["adjustment_history"] = []
            
            config["adjustment_history"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "old_threshold": round(current_threshold, 3),
                "new_threshold": round(new_threshold, 3),
                "accept_rate": accept_rate,
                "reason": adjustment_reason,
                "stats": stats
            })
            
            # Keep only last 50 adjustments
            if len(config["adjustment_history"]) > 50:
                config["adjustment_history"] = config["adjustment_history"][-50:]
            
            save_heuristics_config(config)
            logger.info(f"Adjusted confidence threshold: {current_threshold:.3f} → {new_threshold:.3f} ({adjustment_reason})")
        else:
            logger.debug(f"No threshold adjustment needed (current: {current_threshold:.3f}, accept_rate: {accept_rate:.3f})")
        
        return {
            "confidence_threshold": config["confidence_threshold"],
            "high_confidence_threshold": config["high_confidence_threshold"],
            "accept_rate": accept_rate
        }
        
    except Exception as e:
        logger.error(f"Error adjusting confidence thresholds: {e}", exc_info=True)
        return None


def get_confidence_threshold():
    """
    Get current confidence threshold.
    
    Returns:
        Float representing current confidence threshold
    """
    config = load_heuristics_config()
    return config.get("confidence_threshold", DEFAULT_CONFIDENCE_THRESHOLD)


def get_high_confidence_threshold():
    """
    Get current high confidence threshold.
    
    Returns:
        Float representing current high confidence threshold
    """
    config = load_heuristics_config()
    return config.get("high_confidence_threshold", DEFAULT_HIGH_CONFIDENCE_THRESHOLD)

