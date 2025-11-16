"""
Document Post-Processing Module
Cleans, normalizes, deduplicates, and maps parsed model outputs to Supabase taxonomy.
"""

import re
import json
import os
import logging
from difflib import SequenceMatcher
from pathlib import Path
from config import Config
from services.supabase_client import (
    get_discipline_record
)
from services.processor.normalization.discipline_resolver import (
    resolve_discipline_and_subtype,
    get_subtype_id
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


def merge_similar_duplicates(records, similarity_threshold=0.8):
    """
    Merge duplicates if vulnerability text is ≥80% similar and category matches.
    
    Args:
        records: List of cleaned records
        similarity_threshold: Minimum similarity ratio (default: 0.8)
        
    Returns:
        List of merged records
    """
    if not records:
        return records
    
    merged = []
    seen_indices = set()
    
    for i, rec1 in enumerate(records):
        if i in seen_indices:
            continue
        
        # Find similar records
        similar_group = [rec1]
        for j, rec2 in enumerate(records[i+1:], start=i+1):
            if j in seen_indices:
                continue
            
            # Check if categories match
            cat1 = normalize_text(rec1.get("category", ""))
            cat2 = normalize_text(rec2.get("category", ""))
            if cat1 and cat2 and cat1 != cat2:
                continue
            
            # Use AI to determine if records should be merged (with fallback to text similarity)
            should_merge = False
            import os
            use_ai = Config.ENABLE_AI_ENHANCEMENT
            
            if use_ai:
                try:
                    from services.ai_enhancer import ai_should_merge
                    merge_decision = ai_should_merge(rec1, rec2)
                    should_merge = merge_decision.get("should_merge", False)
                    
                    if should_merge and merge_decision.get("merged_suggestion"):
                        # Use AI-suggested merged text
                        rec1["vulnerability"] = merge_decision["merged_suggestion"]
                except Exception as e:
                    logger.debug(f"AI merge decision failed, using text similarity: {e}")
                    use_ai = False
            
            # Fallback to text similarity
            if not use_ai:
                vuln1 = normalize_text(rec1.get("vulnerability", ""))
                vuln2 = normalize_text(rec2.get("vulnerability", ""))
                page1 = rec1.get("page_ref") or rec1.get("source_page") or rec1.get("chunk_id", "")
                page2 = rec2.get("page_ref") or rec2.get("source_page") or rec2.get("chunk_id", "")
                
                if vuln1 and vuln2:
                    similarity = SequenceMatcher(None, vuln1, vuln2).ratio()
                    
                    # Prefer merging records from same page/section (more likely to be true duplicates)
                    # But still allow cross-page merging if similarity is very high (≥0.9)
                    same_location = page1 and page2 and (page1 == page2 or str(page1) == str(page2))
                    location_bonus = 0.1 if same_location else 0.0
                    effective_threshold = similarity_threshold - location_bonus  # Lower threshold for same-page matches
                    
                    should_merge = similarity >= effective_threshold
            
            if should_merge:
                similar_group.append(rec2)
                seen_indices.add(j)
        
        # Merge similar records
        if len(similar_group) > 1:
            # Merge OFCs from all similar records
            all_ofcs = []
            for rec in similar_group:
                ofcs = rec.get("options_for_consideration", [])
                if isinstance(ofcs, list):
                    all_ofcs.extend(ofcs)
                elif ofcs:
                    all_ofcs.append(str(ofcs))
            
            # Deduplicate OFCs
            unique_ofcs = []
            seen_ofcs = set()
            for ofc in all_ofcs:
                ofc_norm = normalize_text(str(ofc))
                if ofc_norm and ofc_norm not in seen_ofcs:
                    seen_ofcs.add(ofc_norm)
                    unique_ofcs.append(ofc)
            
            # Use the first record as base, merge OFCs
            merged_rec = similar_group[0].copy()
            merged_rec["options_for_consideration"] = unique_ofcs
            merged_rec["confidence_score"] = max([r.get("confidence_score", 0.5) for r in similar_group])
            merged.append(merged_rec)
            logger.debug(f"Merged {len(similar_group)} similar records")
        else:
            merged.append(rec1)
        
        seen_indices.add(i)
    
    if len(merged) < len(records):
        logger.info(f"Merged {len(records)} records into {len(merged)} unique records (similarity threshold: {similarity_threshold})")
    
    return merged


def promote_orphaned_ofcs(records):
    """
    Promote OFCs when they appear without a paired vulnerability (turn them into "design considerations").
    
    Args:
        records: List of cleaned records
        
    Returns:
        List of records with orphaned OFCs promoted to design considerations
    """
    promoted = []
    orphaned_ofcs = []
    
    for rec in records:
        vuln = rec.get("vulnerability", "").strip()
        ofcs = rec.get("options_for_consideration", [])
        
        if not vuln and ofcs:
            # This is an orphaned OFC - promote it to a design consideration
            for ofc in ofcs:
                if isinstance(ofc, str) and ofc.strip():
                    orphaned_ofcs.append({
                        "vulnerability": f"Design consideration: {ofc.strip()}",
                        "options_for_consideration": [ofc.strip()],
                        "category": rec.get("category") or "Design Process",
                        "discipline": rec.get("discipline") or "General Security",
                        "confidence_score": rec.get("confidence_score", 0.5),
                        "source": rec.get("source"),
                        "page_ref": rec.get("page_ref"),
                        "chunk_id": rec.get("chunk_id"),
                        "source_file": rec.get("source_file"),
                    })
        else:
            promoted.append(rec)
    
    # Add promoted OFCs
    promoted.extend(orphaned_ofcs)
    
    if orphaned_ofcs:
        logger.info(f"Promoted {len(orphaned_ofcs)} orphaned OFCs to design considerations")
    
    return promoted


def add_domain_defaults(records):
    """
    Add default domains using AI semantic classification (with fallback to keyword matching).
    
    Args:
        records: List of cleaned records
        
    Returns:
        List of records with domain defaults applied
    """
    import os
    
    # Check if AI enhancement is enabled
    use_ai = Config.ENABLE_AI_ENHANCEMENT
    
    if use_ai:
        try:
            from services.ai_enhancer import ai_classify_domain
            
            for rec in records:
                # Skip if category already set with high confidence
                if rec.get("category") and rec.get("category_confidence", 1.0) >= 0.8:
                    continue
                
                vuln_text = normalize_text(rec.get("vulnerability", ""))
                ofcs = rec.get("options_for_consideration", [])
                ofc_text = " ".join([normalize_text(str(o)) for o in ofcs if o])
                source_context = rec.get("source_context", "")[:500]
                
                # Use AI classification
                domain_result = ai_classify_domain(vuln_text, ofc_text, source_context)
                
                if domain_result.get("category"):
                    rec["category"] = domain_result["category"]
                    rec["category_confidence"] = domain_result.get("confidence", 0.5)
                    rec["category_reasoning"] = domain_result.get("reasoning", "")
                    logger.debug(f"AI assigned domain '{rec['category']}' (confidence: {rec['category_confidence']:.2f})")
                else:
                    # Fallback to keyword matching
                    _apply_keyword_domain(rec, vuln_text, ofc_text)
        except Exception as e:
            logger.warning(f"AI domain classification failed, falling back to keywords: {e}")
            use_ai = False
    
    # Fallback to keyword-based classification
    if not use_ai:
        for rec in records:
            if rec.get("category"):
                continue
            
            vuln_text = normalize_text(rec.get("vulnerability", ""))
            ofcs = rec.get("options_for_consideration", [])
            ofc_text = " ".join([normalize_text(str(o)) for o in ofcs if o])
            
            _apply_keyword_domain(rec, vuln_text, ofc_text)
    
    return records


def _apply_keyword_domain(rec, vuln_text, ofc_text):
    """Helper function for keyword-based domain classification (fallback)."""
    domain_keywords = {
        "Perimeter": ["bollard", "barrier", "fence", "perimeter", "standoff", "glazing", "blast", "ram", "vehicular"],
        "Access Control": ["access control", "visitor", "screening", "credential", "badge", "entry", "gate"],
        "Operations": ["inspection", "drill", "exercise", "evacuation", "lockdown", "sop", "procedure", "training"],
        "Design Process": ["design", "planning", "program", "phase", "concept", "schematic"],
        "Community Integration": ["community", "public", "stakeholder", "engagement", "outreach"],
        "Sustainability": ["sustainability", "green", "energy", "environmental", "leed"]
    }
    
    combined_text = f"{vuln_text} {ofc_text}".lower()
    
    for domain, keywords in domain_keywords.items():
        for keyword in keywords:
            if keyword in combined_text:
                rec["category"] = domain
                rec["category_confidence"] = 0.6  # Lower confidence for keyword-based
                logger.debug(f"Keyword assigned domain '{domain}' based on '{keyword}'")
                return
    
    # Default to "Design Process" if no match
    if not rec.get("category"):
        rec["category"] = "Design Process"
        rec["category_confidence"] = 0.5


def dedupe_results(results):
    """
    Remove duplicate results based on normalized vulnerability text and OFC text.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        List of unique results
    """
    seen = set()
    unique = []
    
    for r in results:
        # Extract vulnerability text - handle dict/list safely
        vuln_text = r.get("vulnerability", "")
        if isinstance(vuln_text, dict):
            vuln_text = str(vuln_text)
        elif not isinstance(vuln_text, str):
            vuln_text = str(vuln_text) if vuln_text else ""
        
        # Extract OFC text - handle dict/list safely
        ofc_text = r.get("ofc") or r.get("options_for_consideration")
        if isinstance(ofc_text, list) and ofc_text:
            ofc_text = ofc_text[0] if isinstance(ofc_text[0], str) else str(ofc_text[0])
        elif isinstance(ofc_text, dict):
            ofc_text = str(ofc_text)
        elif not isinstance(ofc_text, str):
            ofc_text = str(ofc_text) if ofc_text else ""
        
        # Create deduplication key from both vulnerability and OFC
        if vuln_text and ofc_text:
            key = (normalize_text(vuln_text), normalize_text(ofc_text))
            if key not in seen:
                seen.add(key)
                unique.append(r)
            else:
                logger.debug(f"Skipping duplicate vulnerability+OFC pair: {vuln_text[:50]}... / {ofc_text[:50]}...")
        elif vuln_text:
            # Fallback to vulnerability-only deduplication
            key = normalize_text(vuln_text)
            if key and key not in seen:
                seen.add(key)
                unique.append(r)
            elif key:
                logger.debug(f"Skipping duplicate vulnerability: {vuln_text[:50]}...")
        else:
            logger.warning(f"Skipping record with no vulnerability text: {r}")
    
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


def postprocess_results(model_results, source_filepath=None, min_confidence=0.4):
    """
    Post-process model results: clean, normalize, resolve taxonomy, and deduplicate.
    
    Args:
        model_results: List of raw model result dictionaries
        source_filepath: Optional path to source file (for heuristic mode detection)
        min_confidence: Minimum confidence score threshold (default: 0.4)
        
    Returns:
        List of cleaned and validated records ready for Supabase insertion
    """
    import os
    # Get confidence threshold from environment or use default (LOWERED to 0.3 to capture more)
    min_confidence = Config.CONFIDENCE_THRESHOLD
    
    logger.info(f"Starting post-processing for {len(model_results)} model results (min_confidence={min_confidence})")
    
    # Load expanded heuristics if available
    heuristics = {}
    heur_path = os.path.join(
        Config.DATA_DIR,
        "automation",
        "heuristics_design_guidance.json"
    )
    
    # Check if we should use design guidance mode based on filename
    use_design_guidance = False
    if source_filepath:
        filename = str(source_filepath).lower()
        if "design guide" in filename or "cpted" in filename or "planning" in filename:
            use_design_guidance = True
            os.environ["VOFC_HEURISTICS_MODE"] = "design_guidance_expanded"
    
    # Load heuristics file if it exists
    if os.path.exists(heur_path):
        try:
            with open(heur_path, "r", encoding="utf-8") as f:
                heuristics = json.load(f)
            logger.info(f"Loaded heuristics: {heuristics.get('mode', 'default')}")
        except Exception as e:
            logger.warning(f"Could not load heuristics from {heur_path}: {e}")
    else:
        logger.debug(f"Heuristics file not found: {heur_path}")
    
    # DOCUMENT-LEVEL CLASSIFICATION: Use DocumentClassifier to determine sector/subsector ONCE for the entire document
    # This ensures all records from the same document have the same sector/subsector
    document_title = source_filepath.name if source_filepath else ""
    document_sector_id = None
    document_subsector_id = None
    
    # Get classifier instance (singleton, initialized once per process)
    classifier = None
    if document_title:
        try:
            # Use singleton classifier (initialized once per process, not per document)
            from services.processor.normalization.classifier_context import get_classifier
            
            classifier = get_classifier(enable_semantic=True)
            
            # Extract first pages text and metadata if PDF is available
            first_pages_text = ""
            pdf_metadata = None
            full_text = None
            
            if source_filepath and source_filepath.exists():
                try:
                    # Try to extract first 2-3 pages from PDF
                    import fitz  # PyMuPDF
                    doc = fitz.open(str(source_filepath))
                    first_pages = []
                    for i, page in enumerate(doc[:3]):  # First 3 pages
                        first_pages.append(page.get_text())
                    first_pages_text = "\n".join(first_pages)
                    
                    # Extract PDF metadata
                    pdf_metadata = doc.metadata if hasattr(doc, 'metadata') else None
                    
                    # Extract full text (truncated for performance)
                    full_text_parts = []
                    for page in doc[:10]:  # First 10 pages for context
                        full_text_parts.append(page.get_text())
                    full_text = "\n".join(full_text_parts)
                    
                    doc.close()
                except Exception as e:
                    logger.debug(f"Could not extract PDF content for classification: {e}")
                    # Continue with just title
            
            logger.info(f"Classifying document: {document_title}")
            
            # Classify document
            result = classifier.classify(
                title=document_title,
                metadata=pdf_metadata,
                first_pages_text=first_pages_text,
                full_text=full_text,
                known_sector_id=None,
                return_debug=False
            )
            
            # Extract IDs from result
            # The vocabulary stores actual database UUIDs, so these should be valid UUIDs already
            # But we validate them once at document level (not per record)
            document_sector_id = result.get("sector_id")  # Should be UUID from database
            document_subsector_id = result.get("subsector_id")  # Should be UUID from database
            
            # Validate IDs exist in database (ONCE at document level, not per record)
            # This prevents 406 errors from invalid IDs
            if document_subsector_id:
                try:
                    from services.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    # Validate subsector UUID exists
                    subsector_check = client.table("subsectors").select("id").eq("id", str(document_subsector_id)).maybe_single().execute()
                    if not subsector_check.data:
                        logger.warning(f"Subsector ID '{document_subsector_id}' from classifier not found in database - clearing")
                        document_subsector_id = None
                except Exception as e:
                    logger.warning(f"Could not validate subsector ID '{document_subsector_id}': {e}")
                    document_subsector_id = None
            
            if document_sector_id:
                try:
                    from services.supabase_client import get_supabase_client
                    client = get_supabase_client()
                    # Validate sector UUID exists
                    sector_check = client.table("sectors").select("id").eq("id", str(document_sector_id)).maybe_single().execute()
                    if not sector_check.data:
                        logger.warning(f"Sector ID '{document_sector_id}' from classifier not found in database - clearing")
                        document_sector_id = None
                except Exception as e:
                    logger.warning(f"Could not validate sector ID '{document_sector_id}': {e}")
                    document_sector_id = None
            
            if document_sector_id or document_subsector_id:
                logger.info(f"Document classified ONCE - sector_id: {document_sector_id}, subsector_id: {document_subsector_id} (applying to all {len(model_results)} records)")
            else:
                logger.info(f"No sector/subsector classified for document: {document_title} - all records will have empty sector/subsector")
            
            # Initialize citation extractor V2 if we have page data available
            try:
                from services.processor.normalization.citation_extractor_v2 import CitationExtractorV2
                from services.processor.normalization.pdf_structure import build_document_structure
                
                # Build page_map and page_text from PDF if available
                page_map = {}  # chunk_index -> page_number
                page_text = {}  # page_number -> page_text
                
                if source_filepath and source_filepath.exists() and source_filepath.suffix.lower() == '.pdf':
                    try:
                        import fitz  # PyMuPDF
                        doc = fitz.open(str(source_filepath))
                        
                        # Extract all page text
                        for page_num in range(len(doc)):
                            page = doc[page_num]
                            page_text[page_num + 1] = page.get_text()  # 1-indexed
                        
                        # Build chunk_index -> page_number map from model_results
                        # Try to infer from chunk_id or page_ref
                        for idx, record in enumerate(model_results):
                            chunk_id = record.get("chunk_id", "")
                            page_ref = record.get("page_ref") or record.get("page_range", "")
                            
                            # Try to extract page number from page_ref (e.g., "23" or "23-25")
                            page_num = None
                            if page_ref:
                                # Try to parse page number from page_ref
                                import re
                                page_match = re.search(r'(\d+)', str(page_ref))
                                if page_match:
                                    page_num = int(page_match.group(1))
                            
                            # If we have a page number, map chunk index to it
                            if page_num:
                                page_map[idx] = page_num
                        
                        doc.close()
                        
                        # Build document structure and initialize citation extractor V2
                        if page_map and page_text:
                            # Build hierarchical section structure
                            structure = build_document_structure(page_text, max_level=4)
                            
                            classifier.citation_extractor = CitationExtractorV2(
                                page_map=page_map,
                                page_text=page_text,
                                structure=structure,
                                file_name=document_title
                            )
                            logger.info(f"Citation extractor V2 initialized with {len(page_map)} chunk mappings, {len(page_text)} pages, and {len(structure.get('sections', []))} root sections")
                        else:
                            logger.debug("Insufficient page data for citation extraction")
                            
                    except Exception as e:
                        logger.debug(f"Could not initialize citation extractor V2: {e}")
                        # Continue without citation extraction
                        
            except ImportError:
                logger.debug("CitationExtractorV2 not available")
            except Exception as e:
                logger.debug(f"Citation extractor V2 initialization failed: {e}")
                
        except Exception as e:
            logger.warning(f"Document classification failed: {e}", exc_info=True)
            # Continue without classification - records will have empty sector/subsector
    
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
            
            # Some parsers return nested dicts or lists; convert to string if needed
            if isinstance(vuln, dict):
                vuln = str(vuln)
            elif not isinstance(vuln, str):
                vuln = str(vuln) if vuln else None
            
            # Extract OFCs - handle multiple formats (check before vulnerability check)
            ofcs_raw = r.get("options_for_consideration") or r.get("ofcs") or r.get("options") or r.get("ofc")
            if isinstance(ofcs_raw, str):
                # If OFC is a string, split by newlines or commas
                ofcs_raw = [o.strip() for o in re.split(r'[,\n]', ofcs_raw) if o.strip()]
            elif isinstance(ofcs_raw, dict):
                # Convert dict to string
                ofcs_raw = [str(ofcs_raw)]
            elif not isinstance(ofcs_raw, list):
                ofcs_raw = []
            
            # Handle list items that might be dicts - filter out empty/placeholder content
            ofcs = []
            # NOTE: Do NOT include "implied design weakness", "missing standard", or "gap in planning"
            # These are legitimate system-generated text, not fake data
            placeholder_patterns = [
                "placeholder", "dummy", "test", "example", "sample", "fake"
            ]
            
            for o in ofcs_raw:
                if isinstance(o, dict):
                    o = str(o)
                elif not isinstance(o, str):
                    o = str(o) if o else ""
                
                # Validate OFC content: must be non-empty, meaningful text
                if o and o.strip():
                    ofc_text = o.strip()
                    # Reject placeholder/dummy text in OFCs
                    ofc_lower = ofc_text.lower()
                    if any(pattern in ofc_lower for pattern in placeholder_patterns):
                        logger.warning(f"Record {idx}: Skipping OFC with placeholder text: {ofc_text[:50]}...")
                        continue
                    # Reject very short OFCs (reduced from 5 to 3 chars to capture more valid short OFCs)
                    if len(ofc_text) < 3:
                        logger.warning(f"Record {idx}: Skipping OFC too short (<3 chars): {ofc_text}")
                        continue
                    ofcs.append(ofc_text)
            
            # Accept OFC-only records when vulnerability is implied
            # BUT only if OFCs contain real, meaningful content
            if not vuln or not vuln.strip():
                if ofcs and len(ofcs) > 0:
                    # Validate that OFCs are not just placeholder text (reduced minimum from 5 to 3 chars)
                    has_real_content = any(
                        len(ofc) >= 3 and 
                        not any(pattern in ofc.lower() for pattern in placeholder_patterns)
                        for ofc in ofcs
                    )
                    
                    if has_real_content:
                        # Use AI to generate contextually appropriate implied vulnerability
                        import os
                        use_ai = Config.ENABLE_AI_ENHANCEMENT
                        
                        if use_ai:
                            try:
                                from services.ai_enhancer import ai_generate_implied_vulnerability
                                
                                ofc_text = " ".join([str(o) for o in ofcs[:2]])  # Use first 2 OFCs
                                source_context = r.get("source_context", "")[:500]
                                
                                ai_result = ai_generate_implied_vulnerability(ofc_text, source_context)
                                implied_text = ai_result.get("vulnerability", "")
                                ai_confidence = ai_result.get("confidence", 0.5)
                                
                                if implied_text:
                                    vuln = implied_text
                                    # Store AI confidence for this implied vulnerability
                                    r["implied_vulnerability_confidence"] = ai_confidence
                                    r["implied_vulnerability_reasoning"] = ai_result.get("reasoning", "")
                                    logger.debug(f"Record {idx}: AI generated implied vulnerability '{implied_text[:80]}...' (confidence: {ai_confidence:.2f})")
                                else:
                                    # Fallback to keyword-based
                                    implied_text = _generate_keyword_implied_vulnerability(ofcs, heuristics)
                                    vuln = implied_text
                            except Exception as e:
                                logger.warning(f"AI implied vulnerability generation failed, using keywords: {e}")
                                implied_text = _generate_keyword_implied_vulnerability(ofcs, heuristics)
                                vuln = implied_text
                        else:
                            # Use keyword-based generation
                            implied_text = _generate_keyword_implied_vulnerability(ofcs, heuristics)
                            vuln = implied_text
                        
                        logger.debug(f"Record {idx}: Using implied vulnerability '{implied_text[:80]}...' for OFC-only record with {len(ofcs)} real OFC(s)")
                    else:
                        logger.warning(f"Record {idx}: Skipping - OFCs contain only placeholder text")
                        skipped += 1
                        continue
                else:
                    logger.warning(f"Record {idx}: Skipping - no vulnerability text and no valid OFCs")
                    skipped += 1
                    continue

            # Final validation: must have at least vulnerability OR OFCs (relaxed to allow single-sided records)
            # We'll promote OFC-only records to design considerations, and allow vulnerability-only if needed
            if not vuln or not vuln.strip():
                if not ofcs or len(ofcs) == 0:
                    logger.warning(f"Record {idx}: Skipping - no vulnerability and no OFCs")
                    skipped += 1
                    continue
                # OFC-only records are handled above (implied vulnerability generation)
                # If we get here, implied vulnerability generation failed
                logger.warning(f"Record {idx}: Skipping - no vulnerability and implied generation failed")
                skipped += 1
                continue
            
            # Allow vulnerability-only records (OFCs can be empty, we'll add defaults later if needed)
            if not ofcs or len(ofcs) == 0:
                logger.debug(f"Record {idx}: Vulnerability-only record (no OFCs), allowing through")
                # Add a default OFC based on vulnerability if needed
                ofcs = [f"Address {vuln[:100]}"]

            # Validate vulnerability text is not placeholder
            vuln_lower = vuln.strip().lower()
            if any(pattern in vuln_lower for pattern in placeholder_patterns):
                logger.warning(f"Record {idx}: Skipping vulnerability with placeholder text: {vuln[:50]}...")
                skipped += 1
                continue

            # Validate vulnerability has meaningful length (reduced from 7 to 5 chars to capture more)
            if len(vuln.strip()) < 5:
                logger.warning(f"Record {idx}: Skipping vulnerability too short (<5 chars): {vuln}")
                skipped += 1
                continue

            # Apply document-level sector/subsector IDs to this record (mandatory - no individual inference)
            # All vulnerabilities inherit the document-level classification
            if document_sector_id:
                r["sector_id"] = document_sector_id
                logger.debug(f"Record {idx}: Applied document-level sector_id: {document_sector_id}")
            if document_subsector_id:
                r["subsector_id"] = document_subsector_id
                logger.debug(f"Record {idx}: Applied document-level subsector_id: {document_subsector_id}")
            
            # Resolve discipline using new resolver (includes subtype inference)
            discipline_name = r.get("discipline") or r.get("discipline_name")
            vulnerability_text = r.get("vulnerability", "")
            ofc_text = r.get("options_for_consideration", [])
            if isinstance(ofc_text, list) and ofc_text:
                ofc_text = ofc_text[0] if isinstance(ofc_text[0], str) else ""
            elif not isinstance(ofc_text, str):
                ofc_text = ""
            
            # Use new discipline resolver
            normalized_discipline, disc_id, subtype_name = resolve_discipline_and_subtype(
                discipline_name or "",
                vulnerability_text,
                ofc_text
            )
            
            # Fallback to old resolver if new one returns None
            if not normalized_discipline:
                disc_id, category = resolve_discipline(discipline_name)
                normalized_discipline = discipline_name
            else:
                # Get category from discipline record
                disc_record = get_discipline_record(normalized_discipline, fuzzy=True)
                category = disc_record.get('category') if disc_record else None
            
            # Get subtype_id if subtype was inferred
            subtype_id = None
            if subtype_name and disc_id:
                subtype_id = get_subtype_id(subtype_name, disc_id)
            
            # Use document-level sector/subsector IDs (already set above)
            # No individual inference - all records inherit from document classification
            sector_id = document_sector_id
            subsector_id = document_subsector_id
            
            # Extract citations for OFCs if citation extractor is available
            ofcs_with_citations = []
            if classifier and hasattr(classifier, 'citation_extractor') and classifier.citation_extractor:
                chunk_idx = idx - 1  # Convert to 0-indexed for citation extractor
                chunk_text = r.get("source_context") or r.get("content") or vuln
                
                for ofc in ofcs:
                    if isinstance(ofc, str):
                        try:
                            citation = classifier.citation_extractor.extract(
                                chunk_index=chunk_idx,
                                chunk_text=chunk_text,
                                ofc_text=ofc
                            )
                            # Attach citation to OFC (convert to dict if string)
                            ofc_dict = {"text": ofc, "citation": citation}
                            ofcs_with_citations.append(ofc_dict)
                        except Exception as e:
                            logger.debug(f"Citation extraction failed for OFC: {e}")
                            # Fallback to plain OFC without citation
                            ofcs_with_citations.append(ofc)
                    else:
                        # OFC is already a dict, just add it
                        ofcs_with_citations.append(ofc)
            else:
                # No citation extractor available, use plain OFCs
                ofcs_with_citations = ofcs
            
            # Build cleaned record - preserve ALL fields from input
            cleaned_record = {
                "vulnerability": vuln.strip(),
                "options_for_consideration": ofcs_with_citations,
                "discipline": normalized_discipline or r.get("discipline"),  # Use normalized discipline name
                "discipline_id": disc_id,
                "discipline_subtype": subtype_name,  # Add subtype name
                "discipline_subtype_id": subtype_id,  # Add subtype_id
                "category": category or r.get("category"),
                "sector_id": sector_id,
                "subsector_id": subsector_id,
                "source": r.get("source") or r.get("source_file") or r.get("chunk_id"),
                "page_ref": r.get("page_ref") or r.get("page_range"),
                "chunk_id": r.get("chunk_id"),
                "source_file": r.get("source_file"),
            }
            
            # Preserve all additional fields from input record
            additional_fields = [
                "sector", "subsector",  # Resolved names (discipline already handled above)
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
            
            # Get confidence score for filtering - use AI quality assessment if enabled
            import os
            use_ai = Config.ENABLE_AI_ENHANCEMENT
            
            record_confidence = cleaned_record.get("confidence_score") or cleaned_record.get("confidence", 0.5)
            if isinstance(record_confidence, str):
                try:
                    record_confidence = float(record_confidence)
                except:
                    record_confidence = 0.5
            
            # Use AI quality assessment if enabled
            if use_ai and not vuln.startswith("(Implied"):
                try:
                    from services.ai_enhancer import ai_assess_quality
                    quality_result = ai_assess_quality(cleaned_record)
                    ai_confidence = quality_result.get("confidence", record_confidence)
                    quality_score = quality_result.get("quality_score", 0.5)
                    
                    # Update confidence with AI assessment
                    record_confidence = ai_confidence
                    cleaned_record["ai_quality_score"] = quality_score
                    cleaned_record["ai_confidence"] = ai_confidence
                    cleaned_record["ai_issues"] = quality_result.get("issues", [])
                    cleaned_record["ai_recommendations"] = quality_result.get("recommendations", [])
                    
                    # Use quality score as additional filter
                    if quality_score < min_confidence:
                        logger.debug(f"Record {idx}: Skipping - AI quality score {quality_score:.2f} below threshold {min_confidence}")
                        skipped += 1
                        continue
                except Exception as e:
                    logger.debug(f"AI quality assessment failed, using original confidence: {e}")
            
            # Filter by confidence threshold (unless it's an implied vulnerability, which gets lower threshold)
            if not vuln.startswith("(Implied") and record_confidence < min_confidence:
                logger.debug(f"Record {idx}: Skipping - confidence {record_confidence:.2f} below threshold {min_confidence}")
                skipped += 1
                continue
            
            cleaned.append(cleaned_record)
            
        except Exception as e:
            logger.error(f"Error processing record {idx}: {str(e)}")
            skipped += 1
            continue
    
    # Deduplicate results
    unique_records = dedupe_results(cleaned)
    
    # Merge duplicates if vulnerability text is ≥80% similar and category matches
    unique_records = merge_similar_duplicates(unique_records)
    
    # Apply expanded heuristics post-processing (after deduplication)
    # Only promote records with REAL OFC content (not placeholders)
    if heuristics.get("postprocess", {}).get("promote_ofc_only", False):
        implied_text = heuristics["postprocess"].get(
            "generate_implied_vulnerability",
            "(Implied design weakness or gap in planning guidance)"
        )
        implied_count = 0
        # NOTE: Do NOT include "implied design weakness" - it's legitimate system-generated text
        placeholder_patterns = ["placeholder", "dummy", "test", "example", "sample", "fake"]
        
        for r in unique_records:
            vuln = r.get("vulnerability", "").strip()
            ofcs = r.get("options_for_consideration", [])
            
            # Only promote if vulnerability is missing/empty AND OFCs exist with real content
            if not vuln:
                if ofcs and isinstance(ofcs, list) and len(ofcs) > 0:
                    # Validate OFCs contain real content (not placeholders, minimum length reduced from 10 to 5)
                    has_real_ofc = any(
                        isinstance(ofc, str) and 
                        len(ofc.strip()) >= 5 and 
                        not any(pattern in ofc.lower() for pattern in placeholder_patterns)
                        for ofc in ofcs
                    )
                    
                    if has_real_ofc:
                        r["vulnerability"] = implied_text
                        # Set confidence from heuristics if available
                        if "defaults" in heuristics:
                            r["confidence_score"] = heuristics["defaults"].get("confidence_ofc", 0.6)
                        implied_count += 1
                    else:
                        logger.debug(f"Skipping promotion - OFCs contain only placeholder/empty content")
        
        if implied_count > 0:
            logger.info(f"Promoted {implied_count} OFC-only records with implied vulnerability (all validated for real content)")
    
    # Promote OFCs when they appear without a paired vulnerability (turn them into "design considerations")
    unique_records = promote_orphaned_ofcs(unique_records)
    
    # Add default domains by keyword
    unique_records = add_domain_defaults(unique_records)
    
    logger.info(f"Post-processing complete: {len(unique_records)} unique records (skipped: {skipped})")
    return unique_records


def _generate_keyword_implied_vulnerability(ofcs, heuristics):
    """Helper function for keyword-based implied vulnerability generation (fallback)."""
    ofc_keywords = []
    for ofc in ofcs[:2]:  # Use first 2 OFCs for context
        ofc_lower = str(ofc).lower()
        # Extract key security/design terms
        if any(term in ofc_lower for term in ["visitor", "access", "entry"]):
            ofc_keywords.append("access control")
        elif any(term in ofc_lower for term in ["perimeter", "fence", "barrier", "bollard"]):
            ofc_keywords.append("perimeter security")
        elif any(term in ofc_lower for term in ["camera", "surveillance", "monitoring"]):
            ofc_keywords.append("surveillance")
        elif any(term in ofc_lower for term in ["policy", "procedure", "plan"]):
            ofc_keywords.append("governance")
        elif any(term in ofc_lower for term in ["lighting", "visibility"]):
            ofc_keywords.append("lighting")
    
    # Create context-specific implied vulnerability
    if ofc_keywords:
        primary_domain = ofc_keywords[0] if ofc_keywords else "design element"
        return f"(Implied: Missing or inadequate {primary_domain})"
    else:
        # Fallback to generic text
        if heuristics.get("postprocess", {}).get("promote_ofc_only", False):
            return heuristics["postprocess"].get(
                "generate_implied_vulnerability",
                "(Implied design weakness or gap in planning guidance)"
            )
        else:
            return "(Implied design weakness or missing standard)"


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

