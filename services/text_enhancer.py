"""
Text Enhancement Module
Rewrites and rephrases extracted vulnerabilities and OFCs to be more natural,
varied, and contextually rich.
"""
import logging
import json
from typing import Dict, List, Optional, Any
from config import Config
from services.ollama_client import run_model

logger = logging.getLogger(__name__)


def enhance_vulnerability_text(
    vulnerability: str,
    context: Optional[str] = None,
    discipline: Optional[str] = None,
    sector: Optional[str] = None,
    source_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhance a vulnerability statement with context and natural variation.
    
    Args:
        vulnerability: Original vulnerability text
        context: Additional context about the vulnerability
        discipline: Security discipline (e.g., "Physical Security")
        sector: Sector (e.g., "Government Facilities")
        source_context: Original source text context
        
    Returns:
        Dictionary with:
            - enhanced_text: Rewritten vulnerability
            - variations: List of alternative phrasings
            - context_added: Whether context was added
    """
    if not vulnerability or len(vulnerability.strip()) < 5:
        return {
            "enhanced_text": vulnerability,
            "variations": [],
            "context_added": False
        }
    
    # Build enhancement prompt
    prompt_parts = [
        "Rewrite the following security vulnerability statement to be:",
        "1. More natural and professional",
        "2. Clear and specific",
        "3. Contextually appropriate for physical security",
        "",
        f"Original: {vulnerability}"
    ]
    
    if context:
        prompt_parts.append(f"\nAdditional context: {context}")
    
    if discipline:
        prompt_parts.append(f"Discipline: {discipline}")
    
    if sector:
        prompt_parts.append(f"Sector: {sector}")
    
    if source_context:
        # Use first 200 chars of source context
        prompt_parts.append(f"\nSource context: {source_context[:200]}...")
    
    prompt_parts.extend([
        "",
        "Provide a single, well-written vulnerability statement.",
        "Do not add information not present in the original.",
        "Keep it concise (1-2 sentences maximum)."
    ])
    
    prompt = "\n".join(prompt_parts)
    
    try:
        model = Config.DEFAULT_MODEL
        response = run_model(
            model=model,
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent rewrites
            max_tokens=200
        )
        
        enhanced = response.get("response", "").strip()
        
        # Fallback if response is empty or too different
        if not enhanced or len(enhanced) < len(vulnerability) * 0.5:
            logger.warning(f"Enhancement produced poor result, using original")
            enhanced = vulnerability
        
        # Generate variations
        variations = generate_variations(vulnerability, enhanced, discipline, sector)
        
        return {
            "enhanced_text": enhanced,
            "variations": variations,
            "context_added": bool(context or source_context),
            "original": vulnerability
        }
        
    except Exception as e:
        logger.error(f"Error enhancing vulnerability text: {e}")
        return {
            "enhanced_text": vulnerability,
            "variations": [],
            "context_added": False,
            "error": str(e)
        }


def enhance_ofc_text(
    ofc: str,
    vulnerability: Optional[str] = None,
    context: Optional[str] = None,
    discipline: Optional[str] = None,
    source_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhance an OFC (Option for Consideration) statement with context and natural variation.
    
    Args:
        ofc: Original OFC text
        vulnerability: Associated vulnerability (for context)
        context: Additional context
        discipline: Security discipline
        source_context: Original source text context
        
    Returns:
        Dictionary with enhanced text and variations
    """
    if not ofc or len(ofc.strip()) < 5:
        return {
            "enhanced_text": ofc,
            "variations": [],
            "context_added": False
        }
    
    # Build enhancement prompt
    prompt_parts = [
        "Rewrite the following security recommendation (Option for Consideration) to be:",
        "1. Action-oriented and clear",
        "2. Professional and specific",
        "3. Appropriate for physical security guidance",
        "",
        f"Original: {ofc}"
    ]
    
    if vulnerability:
        prompt_parts.append(f"\nAddresses vulnerability: {vulnerability}")
    
    if context:
        prompt_parts.append(f"\nAdditional context: {context}")
    
    if discipline:
        prompt_parts.append(f"Discipline: {discipline}")
    
    if source_context:
        prompt_parts.append(f"\nSource context: {source_context[:200]}...")
    
    prompt_parts.extend([
        "",
        "Provide a single, well-written recommendation statement.",
        "Use active voice and be specific about the action.",
        "Keep it concise (1 sentence preferred, 2 maximum)."
    ])
    
    prompt = "\n".join(prompt_parts)
    
    try:
        model = Config.DEFAULT_MODEL
        response = run_model(
            model=model,
            prompt=prompt,
            temperature=0.3,
            max_tokens=200
        )
        
        enhanced = response.get("response", "").strip()
        
        # Fallback if response is empty or too different
        if not enhanced or len(enhanced) < len(ofc) * 0.5:
            logger.warning(f"OFC enhancement produced poor result, using original")
            enhanced = ofc
        
        # Generate variations
        variations = generate_variations(ofc, enhanced, discipline, None)
        
        return {
            "enhanced_text": enhanced,
            "variations": variations,
            "context_added": bool(context or vulnerability or source_context),
            "original": ofc
        }
        
    except Exception as e:
        logger.error(f"Error enhancing OFC text: {e}")
        return {
            "enhanced_text": ofc,
            "variations": [],
            "context_added": False,
            "error": str(e)
        }


def generate_variations(
    original: str,
    enhanced: str,
    discipline: Optional[str] = None,
    sector: Optional[str] = None
) -> List[str]:
    """
    Generate alternative phrasings for a text.
    
    Args:
        original: Original text
        enhanced: Enhanced/rewritten text
        discipline: Security discipline
        sector: Sector
        
    Returns:
        List of alternative phrasings (up to 3)
    """
    variations = []
    
    # If enhanced is different from original, include it as a variation
    if enhanced and enhanced != original:
        variations.append(enhanced)
    
    # Generate 1-2 additional variations if we have context
    if discipline and len(variations) < 3:
        try:
            prompt = f"""Generate 2 alternative phrasings for this security statement:
"{original}"

Requirements:
- Same meaning and specificity
- Professional tone
- Appropriate for {discipline}
- Each variation should use different sentence structure

Output as JSON array: ["variation1", "variation2"]"""
            
            model = Config.DEFAULT_MODEL
            response = run_model(
                model=model,
                prompt=prompt,
                temperature=0.5,  # Higher temperature for more variation
                max_tokens=300
            )
            
            response_text = response.get("response", "").strip()
            
            # Try to parse JSON array
            try:
                # Extract JSON from response if wrapped in markdown
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                parsed = json.loads(response_text)
                if isinstance(parsed, list):
                    variations.extend(parsed[:2])  # Add up to 2 more
            except (json.JSONDecodeError, ValueError):
                # If JSON parsing fails, try to extract sentences
                lines = [l.strip() for l in response_text.split('\n') if l.strip()]
                variations.extend(lines[:2])
                
        except Exception as e:
            logger.debug(f"Could not generate variations: {e}")
    
    # Deduplicate and limit
    seen = set()
    unique_variations = []
    for v in variations:
        v_lower = v.lower().strip()
        if v_lower not in seen and v_lower != original.lower():
            seen.add(v_lower)
            unique_variations.append(v)
            if len(unique_variations) >= 3:
                break
    
    return unique_variations


def enhance_record(
    record: Dict[str, Any],
    enable_variations: bool = True
) -> Dict[str, Any]:
    """
    Enhance a complete record (vulnerability + OFCs) with rewritten text.
    
    Args:
        record: Record dictionary with vulnerability and options_for_consideration
        enable_variations: Whether to generate alternative phrasings
        
    Returns:
        Enhanced record with rewritten text
    """
    enhanced = record.copy()
    
    # Enhance vulnerability
    vulnerability = record.get("vulnerability", "")
    if vulnerability:
        vuln_enhancement = enhance_vulnerability_text(
            vulnerability=vulnerability,
            context=record.get("description"),
            discipline=record.get("discipline"),
            sector=record.get("sector"),
            source_context=record.get("source_context")
        )
        
        enhanced["vulnerability"] = vuln_enhancement["enhanced_text"]
        enhanced["vulnerability_original"] = vuln_enhancement.get("original", vulnerability)
        
        if enable_variations and vuln_enhancement.get("variations"):
            enhanced["vulnerability_variations"] = vuln_enhancement["variations"]
    
    # Enhance OFCs
    ofcs = record.get("options_for_consideration", [])
    if isinstance(ofcs, str):
        ofcs = [ofcs]
    
    enhanced_ofcs = []
    enhanced_ofc_variations = []
    
    for ofc in ofcs:
        if not ofc or not isinstance(ofc, str):
            continue
        
        ofc_enhancement = enhance_ofc_text(
            ofc=ofc,
            vulnerability=enhanced.get("vulnerability", vulnerability),
            discipline=record.get("discipline"),
            source_context=record.get("source_context")
        )
        
        enhanced_ofcs.append(ofc_enhancement["enhanced_text"])
        
        if enable_variations and ofc_enhancement.get("variations"):
            enhanced_ofc_variations.append({
                "original": ofc,
                "enhanced": ofc_enhancement["enhanced_text"],
                "variations": ofc_enhancement["variations"]
            })
    
    enhanced["options_for_consideration"] = enhanced_ofcs
    
    if enable_variations and enhanced_ofc_variations:
        enhanced["ofc_variations"] = enhanced_ofc_variations
    
    return enhanced


def enhance_records_batch(
    records: List[Dict[str, Any]],
    enable_variations: bool = True,
    max_records: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Enhance multiple records in batch.
    
    Args:
        records: List of record dictionaries
        enable_variations: Whether to generate variations
        max_records: Optional limit on number of records to enhance (for testing)
        
    Returns:
        List of enhanced records
    """
    if max_records:
        records = records[:max_records]
    
    enhanced_records = []
    
    for i, record in enumerate(records, 1):
        try:
            logger.info(f"Enhancing record {i}/{len(records)}")
            enhanced = enhance_record(record, enable_variations=enable_variations)
            enhanced_records.append(enhanced)
        except Exception as e:
            logger.error(f"Error enhancing record {i}: {e}")
            # Include original record if enhancement fails
            enhanced_records.append(record)
    
    return enhanced_records

