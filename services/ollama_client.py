"""
Ollama client service
Handles all Ollama API interactions
"""

import requests
import os

# Use OLLAMA_HOST environment variable (managed by NSSM service)
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://127.0.0.1:11434')
OLLAMA_URL = OLLAMA_HOST  # Backward compatibility

def test_ollama():
    """Test Ollama connection (assumes Ollama is running as NSSM service)"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            return "ok"
        return "error"
    except Exception:
        return "offline"

def generate_text(prompt, model="llama2", **kwargs):
    """Generate text using Ollama"""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                **kwargs
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Ollama generation failed: {str(e)}")

def chat(messages, model="llama2", **kwargs):
    """Chat with Ollama model"""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": model,
                "messages": messages,
                **kwargs
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Ollama chat failed: {str(e)}")

def run_model(model="psa-engine:latest", prompt="", **kwargs):
    """
    Run Ollama model with a prompt.
    
    Uses /api/chat with format='json' to enforce JSON output (like old VOFC Engine).
    Falls back to /api/generate if chat fails.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Try /api/chat first with format='json' (like old VOFC Engine)
    # This forces Ollama to return valid JSON
    chat_url = f"{OLLAMA_HOST}/api/chat"
    chat_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "format": "json",  # CRITICAL: Forces JSON output
        "stream": False,
        **kwargs
    }
    
    try:
        # Try chat API first (enforces JSON format)
        response = requests.post(chat_url, json=chat_payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        
        # Extract content from chat response
        if isinstance(result, dict):
            # Chat API returns: {"message": {"content": "..."}, ...}
            if 'message' in result and 'content' in result['message']:
                return result['message']['content']
            # Fallback to 'response' field
            elif 'response' in result:
                return result['response']
        
        # If we got here, try generate API as fallback
        logger.warning("Chat API returned unexpected format, falling back to generate API")
        raise ValueError("Unexpected chat response format")
        
    except (requests.exceptions.RequestException, ValueError) as e:
        # Fallback to /api/generate if chat fails
        logger.debug(f"Chat API failed ({e}), falling back to generate API")
        generate_url = f"{OLLAMA_HOST}/api/generate"
        generate_payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        
        try:
            response = requests.post(generate_url, json=generate_payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            
            # Extract the generated text from the response
            if isinstance(result, dict):
                if 'response' in result:
                    return result['response']
                elif 'text' in result:
                    return result['text']
                else:
                    return result
            return result
        except requests.exceptions.RequestException as gen_e:
            logger.error(f"Both chat and generate APIs failed. Generate error: {gen_e}")
            raise Exception(f"Ollama model execution failed: {str(gen_e)}")
    except Exception as e:
        logger.error(f"Unexpected error in Ollama model execution: {e}")
        raise Exception(f"Ollama model execution failed: {str(e)}")

def run_model_on_chunks(chunks, model="psa-engine:latest"):
    """
    Run Ollama model on a list of document chunks.
    
    Args:
        chunks: List of chunk dictionaries with 'content' field
        model: Ollama model name (default: "psa-engine:latest")
    
    Returns:
        List of results, one per chunk
    """
    import json
    import logging
    
    results = []
    
    for idx, chunk in enumerate(chunks, start=1):
        try:
            chunk_content = chunk.get('content', '')
            chunk_id = chunk.get('chunk_id', f'chunk_{idx}')
            
            # Create prompt for vulnerability analysis with schema wrapper
            # This ensures the model returns structured, parseable JSON
            # Include chunk metadata for context
            chunk_meta = {
                "chunk_id": chunk_id,
                "page_range": chunk.get('page_range', 'unknown'),
                "source_title": chunk.get('source_title', chunk.get('source_file', 'unknown')),
                "filename": chunk.get('source_file', chunk.get('filename', 'unknown'))
            }
            
            prompt = f"""Document: {chunk_meta['filename']}
Section: pages {chunk_meta['page_range']}
Extract vulnerabilities and mitigations from this section.

CRITICAL: Respond ONLY in valid JSON. No markdown, no explanations, no code blocks.

Required JSON structure (array format):

[{{"vulnerability":"...","option_for_consideration":"...","confidence_score":<float>,"page_range":"{chunk_meta['page_range']}","source_file":"{chunk_meta['filename']}"}}]

If you have no data, return: []

Text:

{chunk_content}

Remember: Return ONLY valid JSON, nothing else."""
            
            # Run model on chunk
            result_text = run_model(model=model, prompt=prompt)
            
            # Try to parse JSON response
            # Expected format: [{"vulnerability": "...", "option_for_consideration": "...", "confidence_score": <float>}]
            try:
                parsed = json.loads(result_text)
                
                # Handle array response (new schema format)
                if isinstance(parsed, list):
                    # Each item in the array is a vulnerability-OFC pair
                    # Preserve metadata from chunk
                    result_data = {
                        "vulnerabilities": [item.get("vulnerability", "") for item in parsed if item.get("vulnerability")],
                        "ofcs": [item.get("option_for_consideration", "") for item in parsed if item.get("option_for_consideration")],
                        "vulnerability_ofc_pairs": parsed,  # Keep original pairs for reference
                        "chunk_id": chunk_id,
                        "source_file": chunk.get('source_file') or chunk.get('filename', 'unknown'),
                        "filename": chunk.get('filename') or chunk.get('source_file', 'unknown'),
                        "page_range": chunk.get('page_range', 'unknown'),
                        "source_title": chunk.get('source_title'),
                        "file_hash": chunk.get('file_hash'),
                        "char_count": chunk.get('char_count', 0)
                    }
                # Handle object response (legacy format)
                elif isinstance(parsed, dict):
                    result_data = parsed
                    result_data['chunk_id'] = chunk_id
                    result_data['source_file'] = chunk.get('source_file') or chunk.get('filename', 'unknown')
                    result_data['filename'] = chunk.get('filename') or chunk.get('source_file', 'unknown')
                    result_data['page_range'] = chunk.get('page_range', 'unknown')
                    result_data['source_title'] = chunk.get('source_title')
                    result_data['file_hash'] = chunk.get('file_hash')
                    result_data['char_count'] = chunk.get('char_count', 0)
                else:
                    # Unexpected format, wrap it
                    result_data = {
                        "raw_response": result_text,
                        "chunk_id": chunk_id,
                        "source_file": chunk.get('source_file') or chunk.get('filename', 'unknown'),
                        "filename": chunk.get('filename') or chunk.get('source_file', 'unknown'),
                        "page_range": chunk.get('page_range', 'unknown'),
                        "source_title": chunk.get('source_title'),
                        "file_hash": chunk.get('file_hash'),
                        "char_count": chunk.get('char_count', 0)
                    }
            except (json.JSONDecodeError, ValueError):
                # If not JSON, wrap in structure
                result_data = {
                    "raw_response": result_text,
                    "chunk_id": chunk_id,
                    "source_file": chunk.get('source_file') or chunk.get('filename', 'unknown'),
                    "filename": chunk.get('filename') or chunk.get('source_file', 'unknown'),
                    "page_range": chunk.get('page_range', 'unknown'),
                    "source_title": chunk.get('source_title'),
                    "file_hash": chunk.get('file_hash'),
                    "char_count": chunk.get('char_count', 0)
                }
            
            results.append(result_data)
            
        except Exception as e:
            # Log error but continue with other chunks
            logging.error(f"Failed to process chunk {chunk.get('chunk_id', idx)}: {str(e)}")
            results.append({
                "chunk_id": chunk.get('chunk_id', f'chunk_{idx}'),
                "error": str(e),
                "status": "failed"
            })
    
    return results

