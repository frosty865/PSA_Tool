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
    normalized = normalize_records(deduped)
    
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

