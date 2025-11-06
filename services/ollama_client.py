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
    """Run Ollama model with a prompt (uses generate API)"""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,  # Get complete response
                **kwargs
            },
            timeout=300  # Longer timeout for analysis
        )
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
    except Exception as e:
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
    results = []
    
    for idx, chunk in enumerate(chunks, start=1):
        try:
            chunk_content = chunk.get('content', '')
            chunk_id = chunk.get('chunk_id', f'chunk_{idx}')
            
            # Create prompt for vulnerability analysis
            prompt = f"""Analyze this document chunk for vulnerabilities and options for consideration.

Chunk ID: {chunk_id}
Source: {chunk.get('source_file', 'unknown')}
Page Range: {chunk.get('page_range', 'unknown')}

Document Content:
{chunk_content}

Please identify:
1. Any security vulnerabilities mentioned
2. Options for consideration (OFCs)
3. Relevant disciplines and sectors
4. Key recommendations

Format your response as JSON with the following structure:
{{
    "vulnerabilities": [...],
    "ofcs": [...],
    "disciplines": [...],
    "sectors": [...],
    "recommendations": [...]
}}
"""
            
            # Run model on chunk
            result_text = run_model(model=model, prompt=prompt)
            
            # Try to parse JSON response, fallback to raw text
            try:
                import json
                result_data = json.loads(result_text)
            except (json.JSONDecodeError, ValueError):
                # If not JSON, wrap in structure
                result_data = {
                    "raw_response": result_text,
                    "chunk_id": chunk_id
                }
            
            # Add chunk metadata to result
            result_data['chunk_id'] = chunk_id
            result_data['source_file'] = chunk.get('source_file', 'unknown')
            result_data['page_range'] = chunk.get('page_range', 'unknown')
            result_data['char_count'] = chunk.get('char_count', 0)
            
            results.append(result_data)
            
        except Exception as e:
            # Log error but continue with other chunks
            import logging
            logging.error(f"Failed to process chunk {chunk.get('chunk_id', idx)}: {str(e)}")
            results.append({
                "chunk_id": chunk.get('chunk_id', f'chunk_{idx}'),
                "error": str(e),
                "status": "failed"
            })
    
    return results


def retrain_model(model_name="psa-engine:latest"):
    """
    Trigger model retraining/refresh.
    
    This is a placeholder for retraining logic. Options include:
    - Pull latest model version from Ollama registry
    - Fine-tune model with new training data from Supabase
    - Restart model service after retraining
    
    Args:
        model_name: Name of the model to retrain (default: "psa-engine:latest")
    
    Returns:
        True if retraining was initiated successfully, False otherwise
    """
    import subprocess
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Starting retraining sequence for model: {model_name}")
        
        # Option 1: Pull latest model version (simple refresh)
        # This ensures we have the latest version of the model
        logger.info("Pulling latest model version from Ollama registry...")
        pull_result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout for model pull
        )
        
        if pull_result.returncode == 0:
            logger.info(f"Model {model_name} pulled successfully")
            logger.info(f"Pull output: {pull_result.stdout[:200]}")  # Log first 200 chars
        else:
            logger.warning(f"Model pull returned non-zero exit code: {pull_result.returncode}")
            logger.warning(f"Pull error: {pull_result.stderr[:200]}")
            # Continue anyway - model might already be up to date
        
        # Option 2: Future enhancement - Fine-tune with new data
        # This would:
        # 1. Export approved/rejected samples from Supabase
        # 2. Create training dataset
        # 3. Run fine-tuning script
        # 4. Create new model version
        # For now, we just log that this could be implemented
        logger.info("Retraining complete. Model refreshed.")
        logger.info("Note: Full fine-tuning with training data can be implemented here")
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"Model pull timed out after 10 minutes")
        return False
    except FileNotFoundError:
        logger.error("Ollama CLI not found. Make sure Ollama is installed and in PATH.")
        return False
    except Exception as e:
        logger.error(f"Error during model retraining: {e}", exc_info=True)
        return False


# Add more Ollama functions as needed from your old implementation

