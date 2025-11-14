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


# Import exceptions from dedicated module
from config.exceptions import ConfigurationError


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
    
    # Archive directory (for migration fallback detection)
    ARCHIVE_DIR = Path(r"C:\Tools\archive\VOFC\Data")
    
    # Specific files
    PROGRESS_FILE = AUTOMATION_DIR / "progress.json"
    
    # External log directories (NSSM service logs)
    VOFC_LOGS_DIR = Path(r"C:\Tools\nssm\logs")
    TUNNEL_LOG_PATHS = [VOFC_LOGS_DIR / "vofc_tunnel.log"]
    
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
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Explicit offline mode flags
    SUPABASE_OFFLINE_MODE = os.getenv("SUPABASE_OFFLINE_MODE", "false").lower() == "true"
    ANALYTICS_OFFLINE_MODE = os.getenv("ANALYTICS_OFFLINE_MODE", "false").lower() == "true"
    
    # ============================================================
    # TUNNEL CONFIGURATION
    # ============================================================
    
    TUNNEL_URL = os.getenv("TUNNEL_URL", "https://flask.frostech.site")
    
    # ============================================================
    # OLLAMA CONFIGURATION
    # ============================================================
    
    # OLLAMA_HOST supports multiple environment variable names for compatibility
    OLLAMA_HOST = (
        os.getenv("OLLAMA_HOST") or 
        os.getenv("OLLAMA_URL") or 
        os.getenv("OLLAMA_API_BASE_URL") or 
        "http://127.0.0.1:11434"
    )
    # Normalize OLLAMA_URL (ensure no trailing slash)
    OLLAMA_URL = OLLAMA_HOST.rstrip('/')
    VOFC_ENGINE_CONFIG = os.getenv("VOFC_ENGINE_CONFIG", "C:/Tools/Ollama/vofc_config.yaml")
    
    # ============================================================
    # PROCESSING CONFIGURATION
    # ============================================================
    
    ENABLE_AI_ENHANCEMENT = os.getenv("ENABLE_AI_ENHANCEMENT", "false").lower() == "true"
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.3"))
    SUBMITTER_EMAIL = os.getenv("SUBMITTER_EMAIL")
    
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
        
        # Validate Supabase configuration
        if cls.SUPABASE_OFFLINE_MODE:
            logger.info("Supabase offline mode enabled - Supabase features will be disabled")
        elif not cls.SUPABASE_URL:
            warnings.append("SUPABASE_URL not set - Supabase features will be disabled (use SUPABASE_OFFLINE_MODE=true to explicitly enable offline mode)")
        elif not cls.SUPABASE_ANON_KEY:
            warnings.append("SUPABASE_ANON_KEY not set - Supabase features will be disabled (use SUPABASE_OFFLINE_MODE=true to explicitly enable offline mode)")
        
        # Validate Analytics configuration
        if cls.ANALYTICS_OFFLINE_MODE:
            logger.info("Analytics offline mode enabled - Analytics features will be disabled")
        
        # Validate OLLAMA_URL format (warn if invalid, don't fail)
        if cls.OLLAMA_URL and not cls.OLLAMA_URL.startswith(('http://', 'https://')):
            warnings.append(f"OLLAMA_URL ({cls.OLLAMA_URL}) should start with http:// or https://")
        
        # Validate TUNNEL_URL format (warn if invalid, don't fail)
        if cls.TUNNEL_URL and not cls.TUNNEL_URL.startswith(('http://', 'https://')):
            warnings.append(f"TUNNEL_URL ({cls.TUNNEL_URL}) should start with http:// or https://")
        
        # Validate optional processing configuration (warn if unusual values, don't fail)
        if cls.CONFIDENCE_THRESHOLD < 0 or cls.CONFIDENCE_THRESHOLD > 1:
            warnings.append(f"CONFIDENCE_THRESHOLD ({cls.CONFIDENCE_THRESHOLD}) should be between 0 and 1")
        
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
            'supabase_configured': bool(cls.SUPABASE_URL and cls.SUPABASE_ANON_KEY) and not cls.SUPABASE_OFFLINE_MODE,
            'supabase_offline_mode': cls.SUPABASE_OFFLINE_MODE,
            'analytics_offline_mode': cls.ANALYTICS_OFFLINE_MODE,
        }


# Validate configuration on import
try:
    Config.validate()
except ConfigurationError as e:
    # Log but don't fail on import - let the application decide
    logger.error(f"Configuration validation failed: {e}")

