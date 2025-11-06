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

# Add more Ollama functions as needed from your old implementation

