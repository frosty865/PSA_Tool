"""
VOFC Model Client
Handles single-chunk extraction calls to Ollama.
"""
import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from .vofc_prompt import BASE_PROMPT

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("VOFC_MODEL", os.getenv("OLLAMA_MODEL", "vofc-unified:latest"))


def extract_from_chunk(chunk_text: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract vulnerabilities and OFCs from a single chunk.
    
    Args:
        chunk_text: Text chunk to process
        model: Optional model name override (defaults to MODEL constant)
        
    Returns:
        Dictionary with 'records' list containing extracted vulnerabilities
    """
    if not model:
        model = MODEL
    
    prompt = f"{BASE_PROMPT}\n\nCHUNK:\n{chunk_text}\n\nJSON:"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 2048
        }
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
        
        raw = response.json().get("response", "").strip()
        
        # Attempt direct JSON parse
        try:
            result = json.loads(raw)
            if "records" not in result:
                logging.warning("Model response missing 'records' key, wrapping result")
                result = {"records": [result]} if result else {"records": []}
            return result
        except json.JSONDecodeError as e:
            logging.error(f"Malformed JSON from model: {e}")
            logging.debug(f"Raw response: {raw[:500]}")
            return {"records": []}
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Ollama API error: {e}")
        return {"records": []}
    except Exception as e:
        logging.error(f"Unexpected error in extract_from_chunk: {e}", exc_info=True)
        return {"records": []}

