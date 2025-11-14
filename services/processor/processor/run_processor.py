"""
Main Processor Pipeline
Orchestrates the complete extraction pipeline: extract → chunk → model → merge → dedupe → export
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Import modular components
from ..extractors.pdf_extractor import extract_structured_pdf
from ..extractors.chunker import chunk_pages
from ..model.vofc_client import extract_from_chunk
from ..normalization.merge import merge_all
from ..normalization.dedupe import dedupe_records
from ..normalization.classify import normalize_records


def process_pdf(
    path: str,
    output_dir: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """
    Process a PDF through the complete extraction pipeline.
    
    Pipeline:
    1. Extract structured pages from PDF
    2. Chunk pages into manageable sizes
    3. Extract from each chunk via model
    4. Merge all chunk results
    5. Deduplicate records
    6. Normalize fields
    7. Export to JSON
    
    Args:
        path: Path to PDF file
        output_dir: Optional output directory (defaults to same as PDF)
        model: Optional model name override
        
    Returns:
        Path to output JSON file
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    
    logging.info(f"Starting processing pipeline for: {pdf_path.name}")
    
    # Validate model availability before processing
    if model:
        model_to_check = model
    else:
        from ..model.vofc_client import MODEL
        model_to_check = MODEL
    
    logging.info(f"Checking if model '{model_to_check}' is available...")
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        if not ollama_url.startswith(('http://', 'https://')):
            ollama_url = f"http://{ollama_url}"
        ollama_url = ollama_url.rstrip('/')
        
        # Check available models
        tags_response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if tags_response.status_code == 200:
            tags_data = tags_response.json()
            # Handle both formats: {"models": [...]} and direct array
            if isinstance(tags_data, list):
                available_models = tags_data
            else:
                available_models = tags_data.get("models", [])
            model_names = [m.get("name", "") if isinstance(m, dict) else str(m) for m in available_models]
            
            if not model_names:
                error_msg = f"❌ CRITICAL: No models installed in Ollama. Please install a model first:\n  ollama pull {model_to_check}\n  Or set VOFC_MODEL or OLLAMA_MODEL environment variable to an installed model."
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            # Check if requested model is available
            if model_to_check not in model_names:
                # Try without :latest tag
                model_base = model_to_check.split(':')[0]
                matching_models = [m for m in model_names if m.startswith(model_base)]
                
                if matching_models:
                    suggested_model = matching_models[0]
                    logging.warning(f"Model '{model_to_check}' not found. Using '{suggested_model}' instead.")
                    model_to_check = suggested_model
                    # Update model parameter for this processing run
                    model = suggested_model
                else:
                    error_msg = f"❌ Model '{model_to_check}' not found. Available models: {', '.join(model_names) if model_names else 'none'}\n  Please install the model: ollama pull {model_to_check}\n  Or set VOFC_MODEL environment variable to one of the available models."
                    logging.error(error_msg)
                    raise ValueError(error_msg)
            
            logging.info(f"✓ Model '{model_to_check}' is available")
        else:
            logging.warning(f"Could not verify model availability (Ollama returned {tags_response.status_code})")
    except requests.RequestException as e:
        error_msg = f"❌ Cannot connect to Ollama server at {ollama_url}. Please ensure Ollama is running."
        logging.error(error_msg)
        raise ConnectionError(error_msg) from e
    except Exception as e:
        if "CRITICAL" in str(e) or "not found" in str(e).lower():
            raise  # Re-raise validation errors
        logging.warning(f"Could not verify model availability: {e}")
    
    # Step 1: Extract structured pages
    logging.info("Step 1: Extracting structured pages...")
    pages = extract_structured_pdf(str(pdf_path))
    if not pages:
        raise ValueError(f"No pages extracted from {path}")
    
    # Step 2: Chunk pages
    logging.info("Step 2: Chunking pages...")
    chunks = chunk_pages(pages, max_chars=5000)
    if not chunks:
        raise ValueError("No chunks created from pages")
    
    # Step 3: Extract from each chunk
    logging.info(f"Step 3: Extracting from {len(chunks)} chunks...")
    all_results = []
    for i, chunk in enumerate(chunks, 1):
        logging.debug(f"Processing chunk {i}/{len(chunks)}...")
        result = extract_from_chunk(chunk, model=model)
        all_results.append(result)
        
        # Log chunk results
        chunk_records = result.get("records", [])
        if chunk_records:
            logging.info(f"  Chunk {i}: {len(chunk_records)} records extracted")
        else:
            logging.warning(f"  Chunk {i}: No records extracted")
    
    # Step 4: Merge all results
    logging.info("Step 4: Merging chunk results...")
    merged = merge_all(all_results)
    logging.info(f"Merged {len(merged)} total records")
    
    # Step 5: Deduplicate
    logging.info("Step 5: Deduplicating records...")
    deduped = dedupe_records(merged)
    logging.info(f"After deduplication: {len(deduped)} unique records")
    
    # Step 6: Normalize
    logging.info("Step 6: Normalizing records...")
    # Extract document title from PDF filename (remove extension and clean)
    document_title = pdf_path.stem.replace("_", " ").replace("-", " ")
    normalized = normalize_records(deduped, document_title=document_title)
    
    # Step 7: Export to JSON
    logging.info("Step 7: Exporting to JSON...")
    output = {
        "source": pdf_path.name,
        "processed_at": datetime.now().isoformat(),
        "total_records": len(normalized),
        "records": normalized
    }
    
    # Determine output path
    if output_dir:
        output_path = Path(output_dir) / f"{pdf_path.stem}_vofc.json"
    else:
        output_path = pdf_path.parent / f"{pdf_path.stem}_vofc.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logging.info(f"✅ Processing complete: {len(normalized)} records exported to {output_path}")
    return str(output_path)

