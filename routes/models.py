"""
Model information and analytics routes
Routes: /api/models/info, /api/system/events
"""

import os
import subprocess
import requests
from flask import Blueprint, jsonify
from services.supabase_client import get_supabase_client
from config import Config

models_bp = Blueprint('models', __name__)

# Supabase client - lazy loaded (only when needed)
def get_supabase():
    """Get Supabase client, handling configuration errors gracefully."""
    try:
        return get_supabase_client()
    except Exception as e:
        import logging
        logging.debug(f"Supabase client not available: {e}")
        return None

@models_bp.route('/api/models/info', methods=['GET'])
def get_model_info():
    """Get information about the current Ollama model"""
    try:
        # Get Ollama URL from centralized config (already normalized)
        ollama_base = Config.OLLAMA_URL
        
        # Get model name from centralized config
        model_name = Config.DEFAULT_MODEL
        
        # Try to get model info from Ollama API
        try:
            # Get list of models
            response = requests.get(f"{ollama_base}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json()
                models = models_data.get('models', [])
                
                # Find the PSA/VOFC model
                target_model = None
                for model in models:
                    model_name_lower = model.get('name', '').lower()
                    if 'psa-engine' in model_name_lower or 'vofc-engine' in model_name_lower:
                        target_model = model
                        break
                
                if target_model:
                    # Extract model info
                    name = target_model.get('name', model_name)
                    size_bytes = target_model.get('size', 0)
                    size_gb = round(size_bytes / (1024**3), 2) if size_bytes else None
                    
                    # Try to get more details from model show
                    try:
                        show_response = requests.post(
                            f"{ollama_base}/api/show",
                            json={"name": name},
                            timeout=5
                        )
                        if show_response.status_code == 200:
                            show_data = show_response.json()
                            # Extract version/modified info if available
                            modified_at = show_data.get('modified_at')
                            version = 'latest'  # Default
                            if modified_at:
                                # Could parse date for version info
                                pass
                    except:
                        pass  # Non-critical, continue with basic info
                    
                    return jsonify({
                        "name": name,
                        "version": "latest",
                        "size_gb": size_gb,
                        "size_bytes": size_bytes,
                        "status": "available"
                    })
        except requests.RequestException:
            pass  # Fall through to default response
        
        # Fallback: try using ollama CLI command
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                for line in lines:
                    if 'psa-engine' in line.lower() or 'vofc-engine' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[0]
                            # Try to extract size (usually in format like "3.8GB")
                            size_str = None
                            for part in parts[1:]:
                                if 'GB' in part.upper() or 'MB' in part.upper():
                                    size_str = part
                                    break
                            
                            size_gb = None
                            if size_str:
                                try:
                                    # Extract number from string like "3.8GB"
                                    import re
                                    match = re.search(r'(\d+\.?\d*)', size_str)
                                    if match:
                                        num = float(match.group(1))
                                        if 'MB' in size_str.upper():
                                            num = num / 1024
                                        size_gb = round(num, 2)
                                except:
                                    pass
                            
                            return jsonify({
                                "name": name,
                                "version": "latest",
                                "size_gb": size_gb,
                                "status": "available"
                            })
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass  # Fall through to default
        
        # Default response if we can't get model info
        return jsonify({
            "name": model_name,
            "version": "unknown",
            "size_gb": None,
            "status": "unknown"
        })
        
    except Exception as e:
        import logging
        logging.error(f"Error getting model info: {e}")
        return jsonify({
            "name": Config.DEFAULT_MODEL,
            "version": "unknown",
            "size_gb": None,
            "status": "error",
            "error": str(e)
        }), 500

@models_bp.route('/api/system/events', methods=['GET'])
def get_system_events():
    """Get system events (retraining, etc.) from Supabase"""
    try:
        # Query system_events table
        supabase_client = get_supabase()
        if not supabase_client:
            return jsonify([])  # Return empty array if Supabase not configured
        result = supabase_client.table("system_events").select("*").order("timestamp", desc=True).limit(50).execute()
        
        if result.data:
            return jsonify(result.data)
        else:
            return jsonify([])
            
    except Exception as e:
        import logging
        logging.error(f"Error getting system events: {e}")
        # Return empty array on error to prevent frontend crashes
        return jsonify([])

@models_bp.route("/api/models/performance", methods=["GET"])
def model_performance_summary():
    """Get model performance summary from Supabase view"""
    try:
        supabase_client = get_supabase()
        if not supabase_client:
            return jsonify([])  # Return empty array if Supabase not configured
        res = supabase_client.table("view_model_performance_summary").select("*").execute()
        return jsonify(res.data)
    except Exception as e:
        import logging
        logging.error(f"Error getting model performance summary: {e}")
        # Return empty array on error to prevent frontend crashes
        return jsonify([])

