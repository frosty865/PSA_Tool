"""
Document Post-Processing Module
Cleans, normalizes, deduplicates, and maps parsed model outputs to Supabase taxonomy.
"""

import re
import logging
from difflib import SequenceMatcher
from services.supabase_client import (
    get_discipline_record,
    get_sector_id,
    get_subsector_id
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def normalize_text(s: str) -> str:
    """
    Normalize text for comparison (lowercase, strip, collapse whitespace).
    
    Args:
        s: Input string
        
    Returns:
        Normalized string
    """
    if not s:
        return ''
    return re.sub(r'\s+', ' ', s.strip().lower())


def dedupe_results(results):
    """
    Remove duplicate results based on normalized vulnerability text.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        List of unique results
    """
    seen = set()
    unique = []
    
    for r in results:
        # Use vulnerability text as deduplication key
        vuln_text = r.get("vulnerability", "")
        key = normalize_text(vuln_text)
        
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
        elif key:
            logger.debug(f"Skipping duplicate vulnerability: {vuln_text[:50]}...")
    
    logger.info(f"Deduplication: {len(results)} -> {len(unique)} unique records")
    return unique


def resolve_discipline(name: str):
    """
    Resolve discipline name to (discipline_id, category) using Supabase lookup.
    Uses fuzzy matching as fallback if exact match not found.
    
    Args:
        name: Discipline name to resolve
        
    Returns:
        Tuple of (discipline_id, category) or (None, None) if not found
    """
    if not name:
        return None, None
    
    # Try exact match first
    record = get_discipline_record(name)
    if record:
        logger.debug(f"Found exact discipline match: {name} -> {record.get('id')}")
        return record.get('id'), record.get('category')
    
    # Try fuzzy match fallback
    logger.info(f"No exact match for discipline '{name}', trying fuzzy match...")
    all_discs = get_discipline_record(all=True)
    
    if not all_discs:
        logger.warning(f"No disciplines available for fuzzy matching")
        return None, None
    
    best = None
    best_score = 0.0
    normalized_name = normalize_text(name)
    
    for d in all_discs:
        disc_name = d.get('name', '')
        if not disc_name:
            continue
        
        normalized_disc = normalize_text(disc_name)
        score = SequenceMatcher(None, normalized_disc, normalized_name).ratio()
        
        if score > best_score:
            best = d
            best_score = score
    
    if best_score >= 0.7:  # 70% similarity threshold
        logger.info(f"Fuzzy match found: '{name}' -> '{best.get('name')}' (score: {best_score:.2f})")
        return best.get('id'), best.get('category')
    
    logger.warning(f"Unknown discipline: '{name}' (best match score: {best_score:.2f})")
    return None, None


def postprocess_results(model_results):
    """
    Post-process model results: clean, normalize, resolve taxonomy, and deduplicate.
    
    Args:
        model_results: List of raw model result dictionaries
        
    Returns:
        List of cleaned and validated records ready for Supabase insertion
    """
    logger.info(f"Starting post-processing for {len(model_results)} model results")
    
    cleaned = []
    skipped = 0
    
    for idx, r in enumerate(model_results, start=1):
        try:
            # Extract vulnerability text
            vuln = r.get("vulnerability") or r.get("vulnerabilities")
            
            # Handle both single vulnerability string and array
            if isinstance(vuln, list):
                if vuln:
                    vuln = vuln[0]  # Take first vulnerability if array
                else:
                    vuln = None
            
            if not vuln or not vuln.strip():
                logger.warning(f"Record {idx}: Skipping - no vulnerability text")
                skipped += 1
                continue
            
            # Extract OFCs - handle multiple formats
            ofcs_raw = r.get("options_for_consideration") or r.get("ofcs") or r.get("options") or []
            if isinstance(ofcs_raw, str):
                # If OFC is a string, split by newlines or commas
                ofcs_raw = [o.strip() for o in re.split(r'[,\n]', ofcs_raw) if o.strip()]
            elif not isinstance(ofcs_raw, list):
                ofcs_raw = []
            
            ofcs = [o.strip() for o in ofcs_raw if o and o.strip()]
            
            if not ofcs:
                logger.warning(f"Record {idx}: Skipping - no OFCs found")
                skipped += 1
                continue
            
            # Resolve discipline
            discipline_name = r.get("discipline") or r.get("disciplines")
            if isinstance(discipline_name, list):
                discipline_name = discipline_name[0] if discipline_name else None
            
            disc_id, category = resolve_discipline(discipline_name)
            
            # Resolve sector
            sector_name = r.get("sector") or r.get("sectors")
            if isinstance(sector_name, list):
                sector_name = sector_name[0] if sector_name else None
            
            sector_id = get_sector_id(sector_name) if sector_name else None
            
            # Resolve subsector
            subsector_name = r.get("subsector") or r.get("subsectors")
            if isinstance(subsector_name, list):
                subsector_name = subsector_name[0] if subsector_name else None
            
            subsector_id = get_subsector_id(subsector_name) if subsector_name else None
            
            # Build cleaned record - preserve ALL fields from input
            cleaned_record = {
                "vulnerability": vuln.strip(),
                "options_for_consideration": ofcs,
                "discipline_id": disc_id,
                "category": category,
                "sector_id": sector_id,
                "subsector_id": subsector_id,
                "source": r.get("source") or r.get("source_file") or r.get("chunk_id"),
                "page_ref": r.get("page_ref") or r.get("page_range"),
                "chunk_id": r.get("chunk_id"),
                "source_file": r.get("source_file"),
            }
            
            # Preserve all additional fields from input record
            # These fields may come from Phase 2/3 and should be preserved
            additional_fields = [
                "discipline", "sector", "subsector",  # Resolved names
                "confidence_score", "confidence",  # Confidence scores
                "intent",  # Intent classification
                "source_context",  # Source context
                "description",  # Description
                "recommendations",  # Recommendations
                "severity_level",  # Severity level
                "audit_status",  # Audit status
                "review_reason",  # Review reason
                "rejection_reason",  # Rejection reason
                "audit_confidence_adjusted",  # Adjusted confidence
                "audit_notes",  # Audit notes
                "citations",  # Citations
                "source_title", "source_url",  # Source metadata
            ]
            
            for field in additional_fields:
                if field in r and r[field] is not None:
                    cleaned_record[field] = r[field]
            
            cleaned.append(cleaned_record)
            
        except Exception as e:
            logger.error(f"Error processing record {idx}: {str(e)}")
            skipped += 1
            continue
    
    # Deduplicate results
    unique_records = dedupe_results(cleaned)
    
    logger.info(f"Post-processing complete: {len(unique_records)} unique records (skipped: {skipped})")
    return unique_records


if __name__ == "__main__":
    """
    CLI interface for testing post-processing.
    Usage: python postprocess.py <path-to-results-json>
    """
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python postprocess.py <path-to-results-json>")
        print("Example: python postprocess.py results.json")
        sys.exit(1)
    
    results_file = sys.argv[1]
    
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            model_results = json.load(f)
        
        print(f"\n{'='*60}")
        print(f"Post-processing: {results_file}")
        print(f"{'='*60}\n")
        
        # Post-process results
        cleaned = postprocess_results(model_results)
        
        # Print summary
        print(f"✓ Post-processing complete!")
        print(f"  Input records: {len(model_results)}")
        print(f"  Output records: {len(cleaned)}")
        print(f"  Unique vulnerabilities: {len(set(r.get('vulnerability', '') for r in cleaned))}")
        
        # Save cleaned results
        output_file = results_file.replace('.json', '_cleaned.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Cleaned results saved to: {output_file}")
        print(f"\nSample records:")
        for i, record in enumerate(cleaned[:3], 1):
            print(f"\n{i}. Vulnerability: {record.get('vulnerability', '')[:60]}...")
            print(f"   Discipline ID: {record.get('discipline_id')}")
            print(f"   Category: {record.get('category')}")
            print(f"   OFCs: {len(record.get('options_for_consideration', []))}")
        
        if len(cleaned) > 3:
            print(f"\n... and {len(cleaned) - 3} more records")
        
        print(f"\n{'='*60}\n")
        
    except FileNotFoundError:
        print(f"✗ Error: File not found - {results_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Error: Invalid JSON - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.exception("CLI post-processing failed")
        sys.exit(1)

