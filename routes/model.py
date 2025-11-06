"""
Model routes for running Ollama models directly
Routes: /api/run_model
"""

from flask import Blueprint, request, jsonify
import requests

model_bp = Blueprint("model", __name__)

@model_bp.route("/api/run_model", methods=["POST", "OPTIONS"])
def run_model():
    """Send text to Ollama and return the model's response."""
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json() or {}
    text = (data.get("text") or "")[:4000]
    
    if not text:
        return jsonify({
            "error": "text field is required",
            "service": "PSA Processing Server"
        }), 400
    
    try:
        res = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "vofc-engine:latest", "prompt": text, "stream": False},
            timeout=120
        )
        res.raise_for_status()
        return jsonify(res.json()), 200
        
    except requests.RequestException as e:
        return jsonify({
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500
    except Exception as e:
        return jsonify({
            "error": str(e),
            "service": "PSA Processing Server"
        }), 500

