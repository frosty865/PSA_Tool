"""
PSA Flask App - Complete Route Registration
All blueprints must be registered for production deployment
"""

import sys
import logging

# Runtime diagnostics (optional - comment out for production)
try:
    import diagnostic
except ImportError:
    pass  # diagnostic.py not found, skip

# Validate configuration before starting
try:
    from config import Config, ConfigurationError
    Config.validate()
    logging.info("Configuration validation passed")
except ConfigurationError as e:
    logging.error(f"Configuration validation failed: {e}")
    logging.error("Flask app will not start with invalid configuration")
    sys.exit(1)
except Exception as e:
    logging.error(f"Unexpected error during configuration validation: {e}")
    logging.warning("Continuing with potentially invalid configuration...")

from flask import Flask
from routes.processing import processing_bp
from routes.system import system_bp
from routes.models import models_bp
from routes.learning import learning_bp
from routes.analytics import bp as analytics_bp
from routes.extract import extract_bp
from routes.process import process_bp
from routes.library import library_bp
from routes.files import files_bp
from routes.audit_routes import audit_bp
from routes.disciplines import bp as disciplines_bp

app = Flask(__name__)

# Register all blueprints for production
app.register_blueprint(processing_bp)
app.register_blueprint(system_bp)
app.register_blueprint(models_bp)  # /api/models/info, /api/system/events
app.register_blueprint(learning_bp)  # /api/learning/*
app.register_blueprint(analytics_bp)  # /api/analytics/*
app.register_blueprint(extract_bp)  # /api/documents/extract/*
app.register_blueprint(process_bp)  # /api/process/*
app.register_blueprint(library_bp)  # /api/library/*
app.register_blueprint(files_bp)  # /api/files/*
app.register_blueprint(audit_bp)  # /api/audit/*
app.register_blueprint(disciplines_bp)  # /api/disciplines/*

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

