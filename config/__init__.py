"""
Centralized Configuration Module
Single source of truth for all configuration with validation
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails"""
    pass


class Config:
    """Single source of truth for all configuration"""
    
    # ============================================================
    # DATA PATHS
    # ============================================================
    
    # Base data directory - standardize on VOFC_DATA_DIR
    _DATA_DIR = os.getenv("VOFC_DATA_DIR") or os.getenv("VOFC_BASE_DIR") or r"C:\Tools\Ollama\Data"
    DATA_DIR = Path(_DATA_DIR)
    
    # Subdirectories
    INCOMING_DIR = DATA_DIR / "incoming"
    PROCESSED_DIR = DATA_DIR / "processed"
    LIBRARY_DIR = DATA_DIR / "library"
    ERRORS_DIR = DATA_DIR / "errors"
    REVIEW_DIR = DATA_DIR / "review"
    LOGS_DIR = DATA_DIR / "logs"
    TEMP_DIR = DATA_DIR / "temp"
    AUTOMATION_DIR = DATA_DIR / "automation"
    
    # Specific files
    PROGRESS_FILE = AUTOMATION_DIR / "progress.json"
    
    # ============================================================
    # SERVICE NAMES
    # ============================================================
    
    FLASK_SERVICE = "vofc-flask"
    PROCESSOR_SERVICE = "VOFC-Processor"
    OLLAMA_SERVICE = "VOFC-Ollama"
    TUNNEL_SERVICE = "VOFC-Tunnel"
    MODEL_MANAGER_SERVICE = "VOFC-ModelManager"
    
    # Service name variants (for compatibility)
    SERVICE_VARIANTS = {
        'flask': ['vofc-flask', 'VOFC-Flask', 'PSA-Flask'],
        'processor': ['VOFC-Processor', 'vofc-processor', 'PSA-Processor'],
        'ollama': ['VOFC-Ollama', 'vofc-ollama'],
        'tunnel': ['VOFC-Tunnel', 'vofc-tunnel'],
        'model_manager': ['VOFC-ModelManager', 'vofc-modelmanager']
    }
    
    # ============================================================
    # API CONFIGURATION
    # ============================================================
    
    FLASK_PORT = int(os.getenv("FLASK_PORT", "8080"))
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
    
    # Flask URL resolution (handled by server-utils.js in Next.js)
    # This is for reference only - actual resolution happens in frontend
    FLASK_URL_LOCAL = f"http://localhost:{FLASK_PORT}"
    OLLAMA_URL_LOCAL = f"http://localhost:{OLLAMA_PORT}"
    
    # ============================================================
    # MODEL CONFIGURATION
    # ============================================================
    
    DEFAULT_MODEL = os.getenv("VOFC_MODEL") or os.getenv("OLLAMA_MODEL") or "vofc-unified:latest"
    MIN_RECORDS_FOR_LIBRARY = int(os.getenv("MIN_RECORDS_FOR_LIBRARY", "5"))
    
    # ============================================================
    # SUPABASE CONFIGURATION
    # ============================================================
    
    SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    
    # ============================================================
    # VALIDATION
    # ============================================================
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate all configuration at startup.
        Raises ConfigurationError if validation fails.
        """
        errors = []
        warnings = []
        
        # Validate required environment variables
        required_vars = {
            'VOFC_DATA_DIR': cls._DATA_DIR,
        }
        
        # Validate paths exist or can be created
        required_dirs = [
            ('DATA_DIR', cls.DATA_DIR),
            ('INCOMING_DIR', cls.INCOMING_DIR),
            ('PROCESSED_DIR', cls.PROCESSED_DIR),
            ('LIBRARY_DIR', cls.LIBRARY_DIR),
            ('ERRORS_DIR', cls.ERRORS_DIR),
            ('REVIEW_DIR', cls.REVIEW_DIR),
            ('LOGS_DIR', cls.LOGS_DIR),
            ('TEMP_DIR', cls.TEMP_DIR),
            ('AUTOMATION_DIR', cls.AUTOMATION_DIR),
        ]
        
        for name, path in required_dirs:
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {name} = {path}")
                except Exception as e:
                    errors.append(f"{name} ({path}) cannot be created: {e}")
        
        # Validate Supabase configuration (warn if missing, don't fail)
        if not cls.SUPABASE_URL:
            warnings.append("SUPABASE_URL not set - Supabase features will be disabled")
        if not cls.SUPABASE_ANON_KEY:
            warnings.append("SUPABASE_ANON_KEY not set - Supabase features will be disabled")
        
        # Validate services exist (warn if missing, don't fail - services may be on different machines)
        # This is informational only
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"Configuration warning: {warning}")
        
        # Raise error if critical issues
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ConfigurationError(error_msg)
        
        logger.info("Configuration validation passed")
        return True
    
    @classmethod
    def get_service_name(cls, service_type: str) -> Optional[str]:
        """
        Get the actual service name for a service type.
        Tries variants until one is found.
        
        Args:
            service_type: One of 'flask', 'processor', 'ollama', 'tunnel', 'model_manager'
        
        Returns:
            Service name if found, None otherwise
        """
        variants = cls.SERVICE_VARIANTS.get(service_type, [])
        for variant in variants:
            if cls._service_exists(variant):
                return variant
        return None
    
    @staticmethod
    def _service_exists(service_name: str) -> bool:
        """Check if a Windows service exists"""
        try:
            result = subprocess.run(
                ['sc', 'query', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            'data_dir': str(cls.DATA_DIR),
            'incoming_dir': str(cls.INCOMING_DIR),
            'processed_dir': str(cls.PROCESSED_DIR),
            'library_dir': str(cls.LIBRARY_DIR),
            'errors_dir': str(cls.ERRORS_DIR),
            'review_dir': str(cls.REVIEW_DIR),
            'logs_dir': str(cls.LOGS_DIR),
            'flask_service': cls.FLASK_SERVICE,
            'processor_service': cls.PROCESSOR_SERVICE,
            'ollama_service': cls.OLLAMA_SERVICE,
            'default_model': cls.DEFAULT_MODEL,
            'min_records_for_library': cls.MIN_RECORDS_FOR_LIBRARY,
            'supabase_configured': bool(cls.SUPABASE_URL and cls.SUPABASE_ANON_KEY),
        }


# Validate configuration on import
try:
    Config.validate()
except ConfigurationError as e:
    # Log but don't fail on import - let the application decide
    logger.error(f"Configuration validation failed: {e}")

