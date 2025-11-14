"""
Flask Server Entry Point for Production
Used by waitress/NSSM service: -m waitress --listen=0.0.0.0:8080 server:app

This file imports the Flask app from app.py to maintain separation
between development (app.py) and production (server.py) entry points.
"""

from app import app

# Export app for waitress
__all__ = ['app']

