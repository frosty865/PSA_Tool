"""
Ollama client service
Handles all Ollama API interactions with runtime configuration support
"""

import requests
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from config import Config
from config.exceptions import ServiceError, FileOperationError

logger = logging.getLogger(__name__)

# Use centralized config for Ollama URL
OLLAMA_HOST = Config.OLLAMA_URL
OLLAMA_URL = Config.OLLAMA_URL  # Backward compatibility

# Engine configuration cache
_engine_config: Optional[Dict[str, Any]] = None

def load_engine_config() -> Dict[str, Any]:
    """
    Load VOFC engine configuration from YAML file or environment variables.
    
    Configuration can be set via:
    1. YAML file at path specified by VOFC_ENGINE_CONFIG env var
    2. Default path: C:/Tools/Ollama/vofc_config.yaml
    3. Environment variables (VOFC_ENGINE_TOPICS_*)
    
    Returns:
        Dictionary with engine configuration
    """
    global _engine_config
    
    if _engine_config is not None:
        return _engine_config
    
    # Default configuration
    default_config = {
        "VOFC_ENGINE_TOPICS": {
            "narrative_risk": True,
            "thematic_expansion": True,
            "target_vulnerabilities_per_doc": 10,
            "target_ofcs_per_vulnerability": 3
        },
        "document_biases": {},  # Document-specific prompt enhancements
        "themes": []  # Global themes to emphasize
    }
    
    # Try to load from YAML file
    config_path = Config.VOFC_ENGINE_CONFIG
    config_file = Path(config_path)
    
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f) or {}
                # Merge with defaults
                _engine_config = {**default_config, **yaml_config}
                logger.info(f"Loaded engine config from {config_path}")
        except (yaml.YAMLError, IOError, OSError) as e:
            logger.warning(f"Failed to load config from {config_path}: {e}, using defaults")
            _engine_config = default_config
        except Exception as e:
            logger.error(f"Unexpected error loading config from {config_path}: {e}", exc_info=True)
            _engine_config = default_config
    else:
        logger.info(f"Config file not found at {config_path}, using defaults")
        _engine_config = default_config
    
    return _engine_config


def get_document_bias(file_path: str) -> str:
    """
    Get document-specific prompt bias based on filename patterns.
    
    Args:
        file_path: Path or filename of the document
    
    Returns:
        Additional prompt instructions to append
    """
    config = load_engine_config()
    biases = config.get("document_biases", {})
    
    # Check for pattern matches
    file_lower = file_path.lower()
    bias_prompts = []
    
    for pattern, bias_config in biases.items():
        if pattern.lower() in file_lower:
            if isinstance(bias_config, dict):
                prompts = bias_config.get("prompts", [])
                if isinstance(prompts, list):
                    bias_prompts.extend(prompts)
                elif isinstance(prompts, str):
                    bias_prompts.append(prompts)
            elif isinstance(bias_config, str):
                bias_prompts.append(bias_config)
    
    # Hard-coded patterns (can be moved to config)
    if "usss" in file_lower or "averting" in file_lower:
        bias_prompts.append("Focus on systemic and behavioral vulnerabilities, not IT or cyber.")
        bias_prompts.append("Look for narrative findings and recommended actions.")
    
    return "\n".join(bias_prompts) if bias_prompts else ""


def get_enrichment_context(file_path: str) -> str:
    """
    Get enrichment context from learning events for a document.
    
    This retrieves themes and examples from past corrections to inform prompts.
    
    Args:
        file_path: Path or filename of the document
    
    Returns:
        Additional prompt context based on past corrections
    """
    try:
        from services.learning_feedback import get_enrichment_themes, get_enrichment_examples
        
        filename = Path(file_path).name
        themes = get_enrichment_themes(filename, limit=5)
        examples = get_enrichment_examples(filename, limit=3)
        
        context_parts = []
        
        if themes:
            context_parts.append(f"Emphasize these themes: {', '.join(themes)}")
        
        if examples:
            context_parts.append("\nExample patterns to look for:")
            for ex in examples[:2]:  # Limit to 2 examples to avoid prompt bloat
                vuln = ex.get("vulnerability", "")
                ofcs = ex.get("ofcs", [])
                if vuln and ofcs:
                    context_parts.append(f"- Vulnerability: {vuln}")
                    context_parts.append(f"  OFCs: {', '.join(ofcs[:2])}")  # Limit OFCs
        
        return "\n".join(context_parts) if context_parts else ""
        
    except (FileNotFoundError, PermissionError, OSError) as e:
        logger.debug(f"Could not load enrichment context: {e}")
        return ""
    except Exception as e:
        logger.warning(f"Unexpected error loading enrichment context: {e}", exc_info=True)
        return ""


def build_enhanced_prompt(base_prompt: str, file_path: str = "", text: str = "") -> str:
    """
    Build an enhanced prompt with configuration-based enhancements.
    
    Args:
        base_prompt: Base prompt text
        file_path: Path to source document (for bias detection)
        text: Document text (for context)
    
    Returns:
        Enhanced prompt with configuration and enrichment context
    """
    config = load_engine_config()
    topics = config.get("VOFC_ENGINE_TOPICS", {})
    
    enhancements = []
    
    # Add document-specific bias
    if file_path:
        bias = get_document_bias(file_path)
        if bias:
            enhancements.append(bias)
    
    # Add enrichment context from learning events
    if file_path:
        enrichment = get_enrichment_context(file_path)
        if enrichment:
            enhancements.append(enrichment)
    
    # Add configuration-based instructions
    if topics.get("narrative_risk", False):
        enhancements.append("Focus on narrative risk patterns and behavioral indicators.")
    
    if topics.get("thematic_expansion", False):
        target_vulns = topics.get("target_vulnerabilities_per_doc", 10)
        target_ofcs = topics.get("target_ofcs_per_vulnerability", 3)
        enhancements.append(
            f"Aim to extract approximately {target_vulns} vulnerabilities per document, "
            f"with {target_ofcs} options for consideration per vulnerability."
        )
    
    # Add global themes
    themes = config.get("themes", [])
    if themes:
        enhancements.append(f"Emphasize these themes: {', '.join(themes)}")
    
    # Combine enhancements
    if enhancements:
        enhancement_text = "\n".join(enhancements)
        return f"{base_prompt}\n\n{enhancement_text}"
    
    return base_prompt


def test_ollama():
    """Test Ollama connection (assumes Ollama is running as NSSM service)"""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            return "ok"
        return "failed"
    except requests.exceptions.ConnectionError:
        logger.debug("Ollama connection failed - service not reachable")
        return "failed"
    except requests.exceptions.Timeout:
        logger.debug("Ollama request timeout")
        return "failed"
    except requests.exceptions.RequestException as e:
        logger.debug(f"Ollama request failed: {e}")
        return "failed"
    except Exception as e:
        logger.error(f"Unexpected error testing Ollama: {e}", exc_info=True)
        return "failed"

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
    except requests.exceptions.HTTPError as e:
        raise ServiceError(f"Ollama generation HTTP error: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise ServiceError(f"Ollama connection failed: {e}") from e
    except requests.exceptions.Timeout as e:
        raise ServiceError(f"Ollama generation timeout: {e}") from e
    except requests.exceptions.RequestException as e:
        raise ServiceError(f"Ollama generation request failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error in Ollama generation: {e}", exc_info=True)
        raise ServiceError(f"Ollama generation failed: {e}") from e

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
    except requests.exceptions.HTTPError as e:
        raise ServiceError(f"Ollama chat HTTP error: {e}") from e
    except requests.exceptions.ConnectionError as e:
        raise ServiceError(f"Ollama connection failed: {e}") from e
    except requests.exceptions.Timeout as e:
        raise ServiceError(f"Ollama chat timeout: {e}") from e
    except requests.exceptions.RequestException as e:
        raise ServiceError(f"Ollama chat request failed: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error in Ollama chat: {e}", exc_info=True)
        raise ServiceError(f"Ollama chat failed: {e}") from e

def run_model(model="psa-engine:latest", prompt="", file_path="", **kwargs):
    """
    Run Ollama model with a prompt.
    
    Uses /api/chat with format='json' to enforce JSON output (like old VOFC Engine).
    Falls back to /api/generate if chat fails.
    
    Args:
        model: Model name (default: "psa-engine:latest")
        prompt: Base prompt text
        file_path: Optional file path for configuration-based prompt enhancement
        **kwargs: Additional arguments to pass to Ollama API
    """
    # Enhance prompt with configuration if file_path provided
    if file_path:
        prompt = build_enhanced_prompt(prompt, file_path=file_path)
    
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
            raise ServiceError(f"Ollama model execution failed: {gen_e}") from gen_e
    except (ServiceError, ValueError):
        # Re-raise ServiceError and ValueError as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Ollama model execution: {e}", exc_info=True)
        raise ServiceError(f"Ollama model execution failed: {e}") from e

def run_model_on_chunks(chunks, model="psa-engine:latest", file_path=""):
    """
    Run Ollama model on a list of document chunks.
    
    Args:
        chunks: List of chunk dictionaries with 'content' field
        model: Ollama model name (default: "psa-engine:latest")
        file_path: Optional file path for configuration-based prompt enhancement
    
    Returns:
        List of results, one per chunk
    """
    import json
    
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
            
            # Load heuristics for design guidance mode
            heuristics_path = Path(r"C:\Tools\Ollama\Data\automation\heuristics_design_guidance.json")
            heuristics = {}
            if heuristics_path.exists():
                try:
                    import json as json_module
                    with open(heuristics_path, "r", encoding="utf-8") as f:
                        heuristics = json_module.load(f)
                except (FileNotFoundError, PermissionError, OSError, json.JSONDecodeError) as e:
                    logger.debug(f"Could not load heuristics: {e}")
                except Exception as e:
                    logger.warning(f"Unexpected error loading heuristics: {e}", exc_info=True)
            
            # Build prompt based on heuristics or default
            if heuristics.get("mode") == "security_guidance":
                base_prompt = f"""You are a structured extraction engine for *design and planning guidance* documents.

Identify every paragraph that indicates a **security concern, weakness, or risk** (vulnerability)
AND every sentence that offers **advice, recommendation, or mitigation** (option for consideration).

Return a JSON array. Each item must include:
{{
  "category": "<Design Process / Perimeter / Access Control / Operations / Community Integration / Sustainability>",
  "vulnerability": "<risk, failure, or issue>",
  "options_for_consideration": ["<recommendation>", "<secondary recommendation>"],
  "citations": ["Page {chunk_meta.get('page_range', 'unknown')}"],
  "confidence_score": 0.7
}}

Guidance verbs such as *should, recommend, consider, integrate, promote* are treated as mitigation.
Warning verbs such as *risk, hazard, conflict, inadequate, failure* are treated as vulnerabilities.
Do NOT summarize; output one record per discrete issue or recommendation pair.

Document: {chunk_meta['filename']}

Text:
{chunk_content}"""
            else:
                # Default prompt (backward compatible)
                base_prompt = f"""Document: {chunk_meta['filename']}
Section: pages {chunk_meta['page_range']}
Extract vulnerabilities and mitigations from this section.

CRITICAL: Respond ONLY in valid JSON. No markdown, no explanations, no code blocks.

Required JSON structure (array format):
[{{"vulnerability":"...","option_for_consideration":"...","confidence_score":<float>,"page_range":"{chunk_meta['page_range']}","source_file":"{chunk_meta['filename']}"}}]

If you have no data, return: []

Text:
{chunk_content}

Remember: Return ONLY valid JSON, nothing else."""
            
            # Enhance prompt with configuration
            prompt = build_enhanced_prompt(base_prompt, file_path=file_path or chunk_meta['filename'])
            
            # Run model on chunk
            result_text = run_model(model=model, prompt=prompt, file_path=file_path or chunk_meta['filename'])
            
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
            
        except ServiceError as e:
            # ServiceError from run_model - log and continue with other chunks
            logger.error(f"Failed to process chunk {chunk.get('chunk_id', idx)}: {e}")
            results.append({
                "chunk_id": chunk.get('chunk_id', f'chunk_{idx}'),
                "error": str(e),
                "status": "failed"
            })
            continue
        except Exception as e:
            # Unexpected error - log with full context and continue
            logger.error(f"Unexpected error processing chunk {chunk.get('chunk_id', idx)}: {e}", exc_info=True)
            results.append({
                "chunk_id": chunk.get('chunk_id', f'chunk_{idx}'),
                "error": f"Unexpected error: {e}",
                "status": "failed"
            })
            continue
    
    return results

