"""
Pattern Enhancer Service
Loads production patterns and enhances prompts with quality examples.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

PATTERNS_FILE = Path(__file__).parent.parent / "training_data" / "production_patterns" / "vulnerability_ofc_patterns.json"

_patterns_cache: Optional[Dict[str, Any]] = None


def load_production_patterns() -> Dict[str, Any]:
    """Load production patterns from JSON file."""
    global _patterns_cache
    
    if _patterns_cache is not None:
        return _patterns_cache
    
    if not PATTERNS_FILE.exists():
        return {}
    
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            _patterns_cache = json.load(f)
        return _patterns_cache
    except Exception as e:
        print(f"Warning: Could not load production patterns: {e}")
        return {}


def get_vulnerability_examples(discipline: Optional[str] = None, limit: int = 5) -> List[str]:
    """
    Get example vulnerability statements from production patterns.
    
    Args:
        discipline: Optional discipline to filter examples
        limit: Maximum number of examples to return
        
    Returns:
        List of example vulnerability statements
    """
    patterns = load_production_patterns()
    vuln_patterns = patterns.get("vulnerability_patterns", {})
    examples = vuln_patterns.get("quality_examples", [])
    
    # Filter by discipline if provided
    if discipline:
        examples = [e for e in examples if e.get("discipline", "").lower() == discipline.lower()]
    
    # Return text only, limit count
    return [e["text"] for e in examples[:limit]]


def get_ofc_examples(discipline: Optional[str] = None, limit: int = 5) -> List[str]:
    """
    Get example OFC statements from production patterns.
    
    Args:
        discipline: Optional discipline to filter examples
        limit: Maximum number of examples to return
        
    Returns:
        List of example OFC statements
    """
    patterns = load_production_patterns()
    ofc_patterns = patterns.get("ofc_patterns", {})
    examples = ofc_patterns.get("quality_examples", [])
    
    # Filter by discipline if provided
    if discipline:
        examples = [e for e in examples if e.get("discipline", "").lower() == discipline.lower()]
    
    # Return text only, limit count
    return [e["text"] for e in examples[:limit]]


def get_vulnerability_opening_phrases(limit: int = 10) -> List[str]:
    """Get common vulnerability opening phrases."""
    patterns = load_production_patterns()
    vuln_patterns = patterns.get("vulnerability_patterns", {})
    phrases = vuln_patterns.get("opening_phrases", {})
    
    # Return top phrases
    return list(phrases.keys())[:limit]


def get_ofc_action_verbs(limit: int = 15) -> List[str]:
    """Get common OFC action verbs."""
    patterns = load_production_patterns()
    ofc_patterns = patterns.get("ofc_patterns", {})
    verbs = ofc_patterns.get("action_verbs", {})
    
    # Return top verbs
    return list(verbs.keys())[:limit]


def build_pattern_enhanced_prompt(base_prompt: str, discipline: Optional[str] = None) -> str:
    """
    Enhance a base prompt with production pattern examples.
    
    Args:
        base_prompt: Base prompt text
        discipline: Optional discipline for targeted examples
        
    Returns:
        Enhanced prompt with examples
    """
    patterns = load_production_patterns()
    
    if not patterns:
        return base_prompt  # No patterns available, return base prompt
    
    # Get examples
    vuln_examples = get_vulnerability_examples(discipline, limit=3)
    ofc_examples = get_ofc_examples(discipline, limit=3)
    opening_phrases = get_vulnerability_opening_phrases(limit=8)
    action_verbs = get_ofc_action_verbs(limit=12)
    
    # Build enhancement section
    enhancement = "\n\n**QUALITY GUIDELINES (from approved production data):**\n"
    
    if opening_phrases:
        enhancement += f"\n**Common vulnerability opening phrases:**\n"
        enhancement += f"{', '.join(opening_phrases[:5])}\n"
        enhancement += f"\n**Example vulnerability statements:**\n"
        for i, example in enumerate(vuln_examples[:3], 1):
            enhancement += f"{i}. {example}\n"
    
    if action_verbs:
        enhancement += f"\n**Common OFC action verbs:**\n"
        enhancement += f"{', '.join(action_verbs[:10])}\n"
        enhancement += f"\n**Example OFC statements:**\n"
        for i, example in enumerate(ofc_examples[:3], 1):
            enhancement += f"{i}. {example}\n"
    
    enhancement += "\n**Use these patterns as guidance for proper wording and structure.**\n"
    
    # Insert enhancement before the final "Text:" section
    if "Text:" in base_prompt or "{chunk_text}" in base_prompt:
        # Insert before the text section
        parts = base_prompt.split("Text:")
        if len(parts) == 2:
            return parts[0] + enhancement + "\n\nText:" + parts[1]
        else:
            parts = base_prompt.split("{chunk_text}")
            if len(parts) == 2:
                return parts[0] + enhancement + "\n\nText:\n{chunk_text}" + parts[1]
    
    # Fallback: append to end
    return base_prompt + enhancement

