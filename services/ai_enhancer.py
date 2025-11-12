"""
AI-Driven Enhancement and Validation Layer
Replaces rule-based logic with intelligent, context-aware AI decisions.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Use Ollama client for AI operations
try:
    from services.ollama_client import run_model
except ImportError:
    logger.warning("Could not import ollama_client - AI enhancement will be disabled")
    run_model = None


def ai_classify_domain(vulnerability_text: str, ofc_text: str, source_context: str = "") -> Dict[str, Any]:
    """
    Use AI to intelligently classify domain/category based on semantic understanding.
    Replaces keyword-based domain mapping.
    
    Args:
        vulnerability_text: The vulnerability description
        ofc_text: The option for consideration text
        source_context: Optional source context for better understanding
        
    Returns:
        Dict with 'category', 'discipline', 'confidence', and 'reasoning'
    """
    if not run_model:
        return {"category": None, "discipline": None, "confidence": 0.5, "reasoning": "AI not available"}
    
    combined_text = f"{vulnerability_text} {ofc_text}"
    if source_context:
        combined_text = f"{source_context[:500]} {combined_text}"
    
    prompt = f"""Analyze this security-related text and classify it into the most appropriate domain.

Text: {combined_text[:1000]}

Available domains:
- Perimeter Security (physical barriers, standoff, bollards, fencing, blast protection)
- Access Control (visitor management, screening, credentials, entry points)
- Surveillance (cameras, monitoring, lighting, visibility)
- Operations (procedures, training, drills, SOPs, maintenance)
- Governance (policies, plans, oversight, accountability)
- Design Process (planning, integration, stakeholder engagement)
- Community Integration (public engagement, outreach, transparency)
- Sustainability (environmental, energy efficiency, green building)

Respond with JSON:
{{
  "category": "<most appropriate domain>",
  "discipline": "<specific discipline if applicable>",
  "confidence": 0.0-1.0,
  "reasoning": "<brief explanation of why this domain>"
}}"""
    
    try:
        response = run_model(
            model=os.getenv("VOFC_MODEL", "vofc-engine:v3"),
            prompt=prompt,
            temperature=0.2  # Low temperature for consistent classification
        )
        
        if response and isinstance(response, str):
            # Try to extract JSON from response
            if "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
        
        logger.warning("AI classification returned invalid response")
        return {"category": None, "discipline": None, "confidence": 0.5, "reasoning": "AI response invalid"}
    except Exception as e:
        logger.error(f"AI classification failed: {e}")
        return {"category": None, "discipline": None, "confidence": 0.5, "reasoning": f"Error: {str(e)}"}


def ai_generate_implied_vulnerability(ofc_text: str, source_context: str = "") -> Dict[str, Any]:
    """
    Use AI to generate contextually appropriate implied vulnerability from OFC text.
    Replaces keyword-based implied vulnerability generation.
    
    Args:
        ofc_text: The option for consideration text
        source_context: Optional source context for better understanding
        
    Returns:
        Dict with 'vulnerability', 'confidence', and 'reasoning'
    """
    if not run_model:
        return {
            "vulnerability": "(Implied: Missing or inadequate security measure)",
            "confidence": 0.5,
            "reasoning": "AI not available"
        }
    
    context = source_context[:500] if source_context else ""
    
    prompt = f"""Given this recommendation/option for consideration, infer what security vulnerability or gap it addresses.

Recommendation: {ofc_text}

Context: {context}

Generate a specific, meaningful vulnerability statement that explains what security issue this recommendation addresses.
Be specific and contextual - don't use generic phrases like "missing standard" or "design weakness".

Respond with JSON:
{{
  "vulnerability": "<specific vulnerability statement>",
  "confidence": 0.0-1.0,
  "reasoning": "<brief explanation>"
}}"""
    
    try:
        response = run_model(
            model=os.getenv("VOFC_MODEL", "vofc-engine:v3"),
            prompt=prompt,
            temperature=0.3  # Slightly higher for creativity, but still controlled
        )
        
        if response and isinstance(response, str):
            if "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
        
        logger.warning("AI implied vulnerability generation returned invalid response")
        return {
            "vulnerability": "(Implied: Missing or inadequate security measure)",
            "confidence": 0.5,
            "reasoning": "AI response invalid"
        }
    except Exception as e:
        logger.error(f"AI implied vulnerability generation failed: {e}")
        return {
            "vulnerability": "(Implied: Missing or inadequate security measure)",
            "confidence": 0.5,
            "reasoning": f"Error: {str(e)}"
        }


def ai_validate_extraction(vulnerability_text: str, source_context: str) -> Dict[str, Any]:
    """
    Use AI to validate that extracted vulnerability actually appears in source context.
    Uses semantic understanding rather than simple word overlap.
    
    Args:
        vulnerability_text: The extracted vulnerability
        source_context: The source text from the document
        
    Returns:
        Dict with 'is_valid', 'confidence', 'reasoning', and 'evidence'
    """
    if not run_model:
        # Fallback to simple word overlap
        vuln_words = set(vulnerability_text.lower().split())
        context_words = set(source_context.lower().split())
        overlap = len(vuln_words & context_words) / max(len(vuln_words), 1)
        return {
            "is_valid": overlap >= 0.2,
            "confidence": overlap,
            "reasoning": f"Word overlap: {overlap:.2f}",
            "evidence": None
        }
    
    prompt = f"""Validate whether this extracted vulnerability is actually stated or clearly implied in the source text.

Extracted Vulnerability: {vulnerability_text}

Source Text: {source_context[:1500]}

Determine:
1. Is the vulnerability explicitly stated in the source?
2. Is it clearly implied (not hallucinated)?
3. What evidence supports this?

Respond with JSON:
{{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "<explanation>",
  "evidence": "<quote from source that supports the vulnerability, or 'none' if invalid>"
}}"""
    
    try:
        response = run_model(
            model=os.getenv("VOFC_MODEL", "vofc-engine:v3"),
            prompt=prompt,
            temperature=0.1  # Very low temperature for validation
        )
        
        if response and isinstance(response, str):
            if "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
        
        logger.warning("AI validation returned invalid response")
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reasoning": "AI response invalid",
            "evidence": None
        }
    except Exception as e:
        logger.error(f"AI validation failed: {e}")
        return {
            "is_valid": False,
            "confidence": 0.0,
            "reasoning": f"Error: {str(e)}",
            "evidence": None
        }


def ai_assess_quality(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use AI to assess the quality and confidence of an extracted record.
    Provides intelligent confidence scoring based on semantic understanding.
    
    Args:
        record: The extracted record with vulnerability, OFC, etc.
        
    Returns:
        Dict with 'quality_score', 'confidence', 'issues', and 'recommendations'
    """
    if not run_model:
        return {
            "quality_score": 0.5,
            "confidence": record.get("confidence_score", 0.5),
            "issues": [],
            "recommendations": []
        }
    
    vuln = record.get("vulnerability", "")
    ofcs = record.get("options_for_consideration", [])
    ofc_text = " ".join([str(o) for o in ofcs]) if isinstance(ofcs, list) else str(ofcs)
    context = record.get("source_context", "")[:500]
    
    prompt = f"""Assess the quality of this extracted security record.

Vulnerability: {vuln}
Options for Consideration: {ofc_text}
Context: {context}

Evaluate:
1. Is the vulnerability clearly stated and specific?
2. Are the OFCs relevant and actionable?
3. Is there sufficient context?
4. What is the overall confidence?

Respond with JSON:
{{
  "quality_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "issues": ["<list of quality issues, if any>"],
  "recommendations": ["<suggestions for improvement, if any>"]
}}"""
    
    try:
        response = run_model(
            model=os.getenv("VOFC_MODEL", "vofc-engine:v3"),
            prompt=prompt,
            temperature=0.2
        )
        
        if response and isinstance(response, str):
            if "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
        
        logger.warning("AI quality assessment returned invalid response")
        return {
            "quality_score": 0.5,
            "confidence": record.get("confidence_score", 0.5),
            "issues": [],
            "recommendations": []
        }
    except Exception as e:
        logger.error(f"AI quality assessment failed: {e}")
        return {
            "quality_score": 0.5,
            "confidence": record.get("confidence_score", 0.5),
            "issues": [],
            "recommendations": []
        }


def ai_should_merge(record1: Dict[str, Any], record2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use AI to determine if two records should be merged (semantic deduplication).
    Replaces simple text similarity matching.
    
    Args:
        record1: First record
        record2: Second record
        
    Returns:
        Dict with 'should_merge', 'confidence', 'reasoning', and 'merged_suggestion'
    """
    if not run_model:
        # Fallback to text similarity
        from difflib import SequenceMatcher
        vuln1 = str(record1.get("vulnerability", ""))
        vuln2 = str(record2.get("vulnerability", ""))
        similarity = SequenceMatcher(None, vuln1.lower(), vuln2.lower()).ratio()
        return {
            "should_merge": similarity >= 0.8,
            "confidence": similarity,
            "reasoning": f"Text similarity: {similarity:.2f}",
            "merged_suggestion": None
        }
    
    vuln1 = record1.get("vulnerability", "")
    vuln2 = record2.get("vulnerability", "")
    ofc1 = record1.get("options_for_consideration", [])
    ofc2 = record2.get("options_for_consideration", [])
    
    prompt = f"""Determine if these two security records describe the same vulnerability and should be merged.

Record 1:
Vulnerability: {vuln1}
OFCs: {ofc1}

Record 2:
Vulnerability: {vuln2}
OFCs: {ofc2}

Consider:
- Do they describe the same security issue?
- Are they semantically equivalent (even if worded differently)?
- Would merging them improve clarity?

Respond with JSON:
{{
  "should_merge": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "<explanation>",
  "merged_suggestion": "<suggested merged vulnerability text, or null>"
}}"""
    
    try:
        response = run_model(
            model=os.getenv("VOFC_MODEL", "vofc-engine:v3"),
            prompt=prompt,
            temperature=0.2
        )
        
        if response and isinstance(response, str):
            if "{" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
        
        logger.warning("AI merge decision returned invalid response")
        return {
            "should_merge": False,
            "confidence": 0.0,
            "reasoning": "AI response invalid",
            "merged_suggestion": None
        }
    except Exception as e:
        logger.error(f"AI merge decision failed: {e}")
        return {
            "should_merge": False,
            "confidence": 0.0,
            "reasoning": f"Error: {str(e)}",
            "merged_suggestion": None
        }


def enhance_record_with_ai(record: Dict[str, Any], source_context: str = "") -> Dict[str, Any]:
    """
    Comprehensive AI enhancement of a record.
    Applies all AI-driven improvements in one pass.
    
    Args:
        record: The extracted record
        source_context: Source text for context
        
    Returns:
        Enhanced record with AI-generated fields
    """
    enhanced = record.copy()
    
    # 1. AI domain classification (if not already set or low confidence)
    if not enhanced.get("category") or enhanced.get("category_confidence", 1.0) < 0.7:
        domain_result = ai_classify_domain(
            enhanced.get("vulnerability", ""),
            " ".join([str(o) for o in enhanced.get("options_for_consideration", [])]),
            source_context
        )
        if domain_result.get("category"):
            enhanced["category"] = domain_result["category"]
            enhanced["category_confidence"] = domain_result.get("confidence", 0.5)
            enhanced["category_reasoning"] = domain_result.get("reasoning", "")
    
    # 2. AI validation (if vulnerability is not implied)
    vuln = enhanced.get("vulnerability", "")
    if source_context and not vuln.startswith("(Implied"):
        validation_result = ai_validate_extraction(vuln, source_context)
        if not validation_result.get("is_valid", True):
            enhanced["validation_failed"] = True
            enhanced["validation_reasoning"] = validation_result.get("reasoning", "")
        else:
            enhanced["validation_confidence"] = validation_result.get("confidence", 1.0)
            enhanced["validation_evidence"] = validation_result.get("evidence")
    
    # 3. AI quality assessment
    quality_result = ai_assess_quality(enhanced)
    enhanced["ai_quality_score"] = quality_result.get("quality_score", 0.5)
    enhanced["ai_confidence"] = quality_result.get("confidence", enhanced.get("confidence_score", 0.5))
    enhanced["ai_issues"] = quality_result.get("issues", [])
    enhanced["ai_recommendations"] = quality_result.get("recommendations", [])
    
    # Update confidence score with AI assessment
    if quality_result.get("confidence"):
        enhanced["confidence_score"] = quality_result["confidence"]
    
    return enhanced

