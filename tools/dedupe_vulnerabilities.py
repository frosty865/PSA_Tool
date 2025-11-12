"""
VOFC Engine – Vulnerability Deduplication Module

Purpose:
    Consolidate semantically duplicate vulnerabilities across Phase2 output
    (e.g., repeating "The facility does not have interoperable communications..." variants)
    before insertion into Supabase.

Dependencies:
    pip install rapidfuzz
"""

import json
from pathlib import Path

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    # Fallback to difflib if rapidfuzz not available
    from difflib import SequenceMatcher
    def fuzz_token_sort_ratio(a, b):
        return int(SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100)


def normalize_for_dedup(text):
    """Normalize text for better duplicate detection."""
    if not text:
        return ""
    import re
    # Lowercase and strip
    text = str(text).strip().lower()
    # Remove articles (a, an, the) for better matching
    text = re.sub(r'\b(a|an|the)\s+', '', text)
    # Normalize common word variations
    # Remove trailing 's' for plural normalization (simple approach)
    # This helps match "policy" vs "policies", "vulnerability" vs "vulnerabilities"
    words = text.split()
    normalized_words = []
    for word in words:
        # Remove trailing 's' if word is longer than 3 chars (avoid removing 'is', 'as', etc.)
        if len(word) > 3 and word.endswith('s'):
            word = word[:-1]
        normalized_words.append(word)
    text = ' '.join(normalized_words)
    # Remove punctuation for comparison
    text = re.sub(r'[^\w\s]', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_ofc_text(record):
    """Extract OFC text from record in various formats."""
    ofcs = record.get("options_for_consideration", [])
    if not ofcs:
        # Try other field names
        ofc = record.get("ofc") or record.get("option_text") or ""
        if ofc:
            return str(ofc).strip()
        return ""
    
    # Handle list of OFCs
    if isinstance(ofcs, list):
        # Get first OFC text
        if ofcs and len(ofcs) > 0:
            first_ofc = ofcs[0]
            if isinstance(first_ofc, dict):
                return str(first_ofc.get("option_text") or first_ofc.get("ofc") or "").strip()
            else:
                return str(first_ofc).strip()
    else:
        return str(ofcs).strip()
    
    return ""


def dedupe_vulnerabilities(vuln_records, threshold=85):
    """
    Deduplicate vulnerabilities based on text similarity (fuzzy ratio).
    Improved to also consider OFC text when determining duplicates.
    
    :param vuln_records: list of dicts from Phase2 output
    :param threshold: match score (0–100) above which entries are treated as duplicates (default: 85, lowered for better deduplication)
    :return: list of deduplicated vulnerability records
    """
    if not vuln_records:
        return []
    
    if not RAPIDFUZZ_AVAILABLE:
        # Fallback to simpler deduplication if rapidfuzz not available
        import logging
        logging.warning("rapidfuzz not available, using basic deduplication")
        return _basic_dedupe(vuln_records, threshold)
    
    unique = []
    mapping = []  # optional: map duplicates to their canonical version

    for record in vuln_records:
        text = record.get("vulnerability", "") or record.get("vulnerability_name", "")
        text = str(text).strip()
        if not text:
            continue
        
        # Extract OFC text for comparison
        record_ofc = extract_ofc_text(record)
        record_ofc_norm = normalize_for_dedup(record_ofc)

        matched = None
        best_score = 0
        
        for u in unique:
            u_text = u.get("vulnerability", "") or u.get("vulnerability_name", "")
            u_text = str(u_text).strip()
            if not u_text:
                continue
            
            # Compare vulnerability text
            vuln_score = fuzz.token_sort_ratio(text, u_text)
            
            # Also compare OFC text if available
            u_ofc = extract_ofc_text(u)
            u_ofc_norm = normalize_for_dedup(u_ofc)
            
            if record_ofc_norm and u_ofc_norm:
                ofc_score = fuzz.token_sort_ratio(record_ofc_norm, u_ofc_norm)
                # Combined score: 70% vulnerability, 30% OFC
                combined_score = (vuln_score * 0.7) + (ofc_score * 0.3)
            else:
                # If no OFC text, use only vulnerability score
                combined_score = vuln_score
            
            # Match if combined score meets threshold OR if vulnerability is very similar (>90%)
            if combined_score >= threshold or vuln_score >= 90:
                if combined_score > best_score:
                    best_score = combined_score
                    matched = u

        if matched:
            # merge metadata (page refs, ofcs, sources, etc.)
            matched.setdefault("merged_sources", []).append(record.get("source_file"))
            matched.setdefault("merged_pages", []).append(record.get("page_ref") or record.get("source_page"))
            
            # Merge OFCs with better deduplication
            if record.get("options_for_consideration") or record.get("ofc"):
                existing_ofcs = set()
                existing_ofcs_norm = set()
                
                # Collect existing OFCs
                for o in matched.get("options_for_consideration", []):
                    ofc_text = o.get("option_text") if isinstance(o, dict) else str(o)
                    if not ofc_text:
                        ofc_text = o.get("ofc") if isinstance(o, dict) else ""
                    if isinstance(ofc_text, str) and ofc_text.strip():
                        existing_ofcs.add(ofc_text.strip())
                        existing_ofcs_norm.add(normalize_for_dedup(ofc_text))
                
                # Also check direct ofc field
                if matched.get("ofc"):
                    ofc_text = str(matched.get("ofc")).strip()
                    if ofc_text:
                        existing_ofcs.add(ofc_text)
                        existing_ofcs_norm.add(normalize_for_dedup(ofc_text))
                
                # Add new OFCs if not duplicates
                record_ofcs = record.get("options_for_consideration", [])
                if not record_ofcs and record.get("ofc"):
                    record_ofcs = [record.get("ofc")]
                
                for o in record_ofcs:
                    ofc_text = o.get("option_text") if isinstance(o, dict) else str(o)
                    if not ofc_text:
                        ofc_text = o.get("ofc") if isinstance(o, dict) else ""
                    if isinstance(ofc_text, str) and ofc_text.strip():
                        ofc_norm = normalize_for_dedup(ofc_text)
                        # Check if this OFC is similar to any existing OFC
                        is_duplicate = False
                        for existing_norm in existing_ofcs_norm:
                            if RAPIDFUZZ_AVAILABLE:
                                similarity = fuzz.token_sort_ratio(ofc_norm, existing_norm)
                                if similarity >= 85:  # 85% similarity threshold for OFCs
                                    is_duplicate = True
                                    break
                            else:
                                # Simple exact match fallback
                                if ofc_norm == existing_norm:
                                    is_duplicate = True
                                    break
                        
                        if not is_duplicate:
                            if isinstance(o, dict):
                                matched.setdefault("options_for_consideration", []).append(o)
                            else:
                                matched.setdefault("options_for_consideration", []).append({"option_text": ofc_text})
                            existing_ofcs_norm.add(ofc_norm)
        else:
            record["merged_sources"] = [record.get("source_file")]
            record["merged_pages"] = [record.get("page_ref") or record.get("source_page")]
            unique.append(record)

    return unique


def _basic_dedupe(vuln_records, threshold=85):
    """Fallback deduplication using difflib if rapidfuzz not available."""
    from difflib import SequenceMatcher
    
    unique = []
    threshold_ratio = threshold / 100.0
    
    for record in vuln_records:
        text = record.get("vulnerability", "") or record.get("vulnerability_name", "")
        text = normalize_for_dedup(text)
        if not text:
            continue
        
        # Extract OFC text for comparison
        record_ofc = extract_ofc_text(record)
        record_ofc_norm = normalize_for_dedup(record_ofc)

        matched = None
        best_score = 0
        
        for u in unique:
            u_text = u.get("vulnerability", "") or u.get("vulnerability_name", "")
            u_text = normalize_for_dedup(u_text)
            if not u_text:
                continue
            
            # Compare vulnerability text
            vuln_ratio = SequenceMatcher(None, text, u_text).ratio()
            
            # Also compare OFC text if available
            u_ofc = extract_ofc_text(u)
            u_ofc_norm = normalize_for_dedup(u_ofc)
            
            if record_ofc_norm and u_ofc_norm:
                ofc_ratio = SequenceMatcher(None, record_ofc_norm, u_ofc_norm).ratio()
                # Combined score: 70% vulnerability, 30% OFC
                combined_ratio = (vuln_ratio * 0.7) + (ofc_ratio * 0.3)
            else:
                # If no OFC text, use only vulnerability score
                combined_ratio = vuln_ratio
            
            # Match if combined score meets threshold OR if vulnerability is very similar (>90%)
            if combined_ratio >= threshold_ratio or vuln_ratio >= 0.9:
                if combined_ratio > best_score:
                    best_score = combined_ratio
                    matched = u

        if matched:
            # merge metadata
            matched.setdefault("merged_sources", []).append(record.get("source_file"))
            matched.setdefault("merged_pages", []).append(record.get("page_ref") or record.get("source_page"))
            
            # Merge OFCs with better deduplication
            if record.get("options_for_consideration") or record.get("ofc"):
                existing_ofcs_norm = set()
                
                # Collect existing OFCs
                for o in matched.get("options_for_consideration", []):
                    ofc_text = o.get("option_text") if isinstance(o, dict) else str(o)
                    if not ofc_text:
                        ofc_text = o.get("ofc") if isinstance(o, dict) else ""
                    if isinstance(ofc_text, str) and ofc_text.strip():
                        existing_ofcs_norm.add(normalize_for_dedup(ofc_text))
                
                # Also check direct ofc field
                if matched.get("ofc"):
                    ofc_text = str(matched.get("ofc")).strip()
                    if ofc_text:
                        existing_ofcs_norm.add(normalize_for_dedup(ofc_text))
                
                # Add new OFCs if not duplicates
                record_ofcs = record.get("options_for_consideration", [])
                if not record_ofcs and record.get("ofc"):
                    record_ofcs = [record.get("ofc")]
                
                for o in record_ofcs:
                    ofc_text = o.get("option_text") if isinstance(o, dict) else str(o)
                    if not ofc_text:
                        ofc_text = o.get("ofc") if isinstance(o, dict) else ""
                    if isinstance(ofc_text, str) and ofc_text.strip():
                        ofc_norm = normalize_for_dedup(ofc_text)
                        # Check if this OFC is similar to any existing OFC
                        is_duplicate = False
                        for existing_norm in existing_ofcs_norm:
                            similarity = SequenceMatcher(None, ofc_norm, existing_norm).ratio()
                            if similarity >= 0.85:  # 85% similarity threshold for OFCs
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            if isinstance(o, dict):
                                matched.setdefault("options_for_consideration", []).append(o)
                            else:
                                matched.setdefault("options_for_consideration", []).append({"option_text": ofc_text})
                            existing_ofcs_norm.add(ofc_norm)
        else:
            record["merged_sources"] = [record.get("source_file")]
            record["merged_pages"] = [record.get("page_ref") or record.get("source_page")]
            unique.append(record)

    return unique


def run_deduplication(input_path, output_path=None, threshold=90):
    """
    Load Phase2 JSON, dedupe vulnerabilities, and save cleaned output.
    
    :param input_path: Path to Phase2 engine JSON file
    :param output_path: Path to save deduped output (default = same folder + _deduped.json)
    """
    input_path = Path(input_path)
    if not output_path:
        output_path = input_path.with_name(input_path.stem + "_deduped.json")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("vulnerabilities", [])
    deduped = dedupe_vulnerabilities(records, threshold=threshold)

    data["deduplication_stats"] = {
        "before": len(records),
        "after": len(deduped),
        "reduction_pct": round(100 * (1 - len(deduped) / max(len(records), 1)), 2)
    }
    data["vulnerabilities"] = deduped

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Deduplicated {len(records)} → {len(deduped)} vulnerabilities "
          f"({data['deduplication_stats']['reduction_pct']}% reduction)")
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Deduplicate VOFC vulnerabilities in Phase2 JSON.")
    parser.add_argument("input", help="Path to Phase2 JSON file")
    parser.add_argument("--threshold", type=int, default=90, help="Fuzzy match threshold (default 90)")
    parser.add_argument("--output", help="Optional path to save deduped output")

    args = parser.parse_args()
    run_deduplication(args.input, args.output, args.threshold)

