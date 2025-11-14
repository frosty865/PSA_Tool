"""
Flask Server Entry Point for Production
Used by waitress/NSSM service: -m waitress --listen=0.0.0.0:8080 server:app

This file imports the Flask app from app.py to maintain separation
between development (app.py) and production (server.py) entry points.
"""

import logging
import sys

# Setup logging before imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Validate configuration before starting
try:
    from config import Config, ConfigurationError
    
    logger.info("Validating configuration...")
    Config.validate()
    logger.info("Configuration validation passed")
    logger.info(f"Configuration summary: {Config.get_summary()}")
except ConfigurationError as e:
    logger.error(f"Configuration validation failed: {e}")
    logger.error("Server will not start with invalid configuration")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error during configuration validation: {e}")
    logger.warning("Continuing with potentially invalid configuration...")

# Import app after validation
from app import app

# Export app for waitress
__all__ = ['app']

