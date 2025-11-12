#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production Pattern Extractor
Extracts patterns from approved production vulnerabilities and OFCs
to improve future extraction quality, especially proper wording.

This tool:
1. Queries production tables (vulnerabilities, options_for_consideration)
2. Analyzes patterns in vulnerability statements and OFC wording
3. Generates:
   - Pattern library (JSON) for prompt enhancement
   - Training examples (JSONL) for model fine-tuning
   - Quality reference dataset (CSV/JSON) for validation

Usage:
    python tools/extract_production_patterns.py
    OR
    python3 tools/extract_production_patterns.py
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.supabase_client import get_supabase_client

# Output directories
OUTPUT_DIR = Path(__file__).parent.parent / "training_data" / "production_patterns"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PATTERNS_FILE = OUTPUT_DIR / "vulnerability_ofc_patterns.json"
TRAINING_EXAMPLES_FILE = OUTPUT_DIR / "production_training_examples.jsonl"
QUALITY_REFERENCE_FILE = OUTPUT_DIR / "quality_reference_dataset.json"
STATISTICS_FILE = OUTPUT_DIR / "pattern_statistics.json"


def extract_vulnerability_patterns(vulnerabilities: List[Dict]) -> Dict[str, Any]:
    """
    Extract patterns from production vulnerability statements.
    
    Returns:
        Dictionary with:
        - opening_phrases: Common ways vulnerabilities start
        - structure_patterns: Common sentence structures
        - domain_keywords: Keywords by discipline
        - length_stats: Average length, min, max
        - quality_indicators: What makes a good vulnerability statement
    """
    patterns = {
        "opening_phrases": Counter(),
        "structure_patterns": Counter(),
        "domain_keywords": defaultdict(Counter),
        "lengths": [],
        "quality_examples": []
    }
    
    for vuln in vulnerabilities:
        # Try multiple field names (production table might use different field names)
        name = (
            vuln.get("vulnerability_name") or 
            vuln.get("name") or 
            vuln.get("title") or 
            vuln.get("vulnerability") or
            ""
        ).strip()
        description = vuln.get("description", "").strip()
        discipline = vuln.get("discipline", "").strip()
        
        if not name:
            continue
        
        # Extract opening phrase (first 3-5 words)
        words = name.split()
        if len(words) >= 3:
            opening = " ".join(words[:min(5, len(words))]).lower()
            patterns["opening_phrases"][opening] += 1
        
        # Analyze sentence structure
        # Check for common patterns: "Lack of...", "Inadequate...", "Missing...", etc.
        structure_markers = [
            (r"^lack\s+of", "Lack of [X]"),
            (r"^inadequate", "Inadequate [X]"),
            (r"^missing", "Missing [X]"),
            (r"^insufficient", "Insufficient [X]"),
            (r"^no\s+", "No [X]"),
            (r"^failure\s+to", "Failure to [X]"),
            (r"^absence\s+of", "Absence of [X]"),
            (r"^unable\s+to", "Unable to [X]"),
            (r"^does\s+not\s+", "Does not [X]"),
            (r"^without\s+", "Without [X]"),
        ]
        
        name_lower = name.lower()
        for pattern, label in structure_markers:
            if re.search(pattern, name_lower):
                patterns["structure_patterns"][label] += 1
                break
        
        # Extract keywords by discipline
        if discipline:
            # Simple keyword extraction (words > 3 chars, not common stop words)
            stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use"}
            words = re.findall(r'\b[a-z]{4,}\b', name_lower)
            keywords = [w for w in words if w not in stop_words]
            for keyword in keywords[:5]:  # Top 5 keywords per vulnerability
                patterns["domain_keywords"][discipline][keyword] += 1
        
        # Track length
        patterns["lengths"].append(len(name))
        
        # Quality indicators: well-formed statements
        if len(name) >= 20 and len(name) <= 200:  # Good length
            if name[0].isupper() and name.endswith('.'):  # Proper sentence
                patterns["quality_examples"].append({
                    "text": name,
                    "discipline": discipline,
                    "length": len(name),
                    "has_description": bool(description)
                })
    
    return patterns


def extract_ofc_patterns(ofcs: List[Dict]) -> Dict[str, Any]:
    """
    Extract patterns from production OFC statements.
    
    Returns:
        Dictionary with:
        - action_verbs: Common action verbs used
        - structure_patterns: Common OFC structures
        - domain_keywords: Keywords by discipline
        - length_stats: Average length, min, max
        - quality_indicators: What makes a good OFC statement
    """
    patterns = {
        "action_verbs": Counter(),
        "structure_patterns": Counter(),
        "domain_keywords": defaultdict(Counter),
        "lengths": [],
        "quality_examples": []
    }
    
    # Common action verbs for OFCs
    action_verb_patterns = [
        (r"\binstall\b", "install"),
        (r"\bimplement\b", "implement"),
        (r"\bestablish\b", "establish"),
        (r"\bdevelop\b", "develop"),
        (r"\bconduct\b", "conduct"),
        (r"\btrain\b", "train"),
        (r"\bupgrade\b", "upgrade"),
        (r"\breplace\b", "replace"),
        (r"\benhance\b", "enhance"),
        (r"\bimprove\b", "improve"),
        (r"\bcoordinate\b", "coordinate"),
        (r"\bdeploy\b", "deploy"),
        (r"\bcreate\b", "create"),
        (r"\badopt\b", "adopt"),
        (r"\bbuild\b", "build"),
        (r"\breinforce\b", "reinforce"),
        (r"\bmaintain\b", "maintain"),
        (r"\bensure\b", "ensure"),
        (r"\bprovide\b", "provide"),
        (r"\bdesign\b", "design"),
    ]
    
    for ofc in ofcs:
        text = ofc.get("option_text", "").strip()
        discipline = ofc.get("discipline", "").strip()
        
        if not text:
            continue
        
        # Extract action verbs
        text_lower = text.lower()
        for pattern, verb in action_verb_patterns:
            if re.search(pattern, text_lower):
                patterns["action_verbs"][verb] += 1
        
        # Analyze structure
        # Check for imperative vs. declarative
        if text[0].isupper() and not text[0].islower():
            # Imperative (starts with verb)
            if any(re.search(rf"^{verb}", text_lower) for verb in ["install", "implement", "establish", "develop"]):
                patterns["structure_patterns"]["Imperative: [Action] [Object]"] += 1
            else:
                patterns["structure_patterns"]["Declarative: [Subject] should [action]"] += 1
        
        # Extract keywords by discipline
        if discipline:
            stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", "her", "was", "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "way", "who", "boy", "did", "its", "let", "put", "say", "she", "too", "use", "should", "must", "shall"}
            words = re.findall(r'\b[a-z]{4,}\b', text_lower)
            keywords = [w for w in words if w not in stop_words]
            for keyword in keywords[:5]:
                patterns["domain_keywords"][discipline][keyword] += 1
        
        # Track length
        patterns["lengths"].append(len(text))
        
        # Quality indicators
        if len(text) >= 15 and len(text) <= 300:  # Good length
            if text[0].isupper():
                patterns["quality_examples"].append({
                    "text": text,
                    "discipline": discipline,
                    "length": len(text)
                })
    
    return patterns


def generate_training_examples(vulnerabilities: List[Dict], ofcs: List[Dict], links: List[Dict]) -> List[Dict]:
    """
    Generate training examples in JSONL format from production data.
    
    Format matches what the model expects for fine-tuning.
    """
    examples = []
    
    # Create vulnerability -> OFCs mapping
    vuln_ofc_map = defaultdict(list)
    for link in links:
        vuln_id = link.get("vulnerability_id")
        ofc_id = link.get("ofc_id")
        if vuln_id and ofc_id:
            vuln_ofc_map[vuln_id].append(ofc_id)
    
    # Create OFC lookup
    ofc_lookup = {ofc["id"]: ofc for ofc in ofcs}
    
    # Generate examples
    for vuln in vulnerabilities:
        vuln_id = vuln.get("id")
        # Try multiple field names (production table might use different field names)
        vuln_name = (
            vuln.get("vulnerability_name") or 
            vuln.get("name") or 
            vuln.get("title") or 
            vuln.get("vulnerability") or
            ""
        ).strip()
        description = vuln.get("description", "").strip()
        discipline = vuln.get("discipline", "").strip()
        
        if not vuln_name:
            continue
        
        # Get linked OFCs
        linked_ofc_ids = vuln_ofc_map.get(vuln_id, [])
        linked_ofcs = [ofc_lookup[ofc_id] for ofc_id in linked_ofc_ids if ofc_id in ofc_lookup]
        
        # Build training example
        example = {
            "vulnerability": vuln_name,
            "description": description or vuln_name,  # Use name as description if missing
            "discipline": discipline,
            "options_for_consideration": [
                ofc.get("option_text", "").strip() 
                for ofc in linked_ofcs 
                if ofc.get("option_text", "").strip()
            ],
            "source": "production_approved",
            "quality_score": 1.0  # All production data is high quality
        }
        
        # Only include if we have at least one OFC
        if example["options_for_consideration"]:
            examples.append(example)
    
    return examples


def main():
    """Main extraction function."""
    print("=" * 60)
    print("Production Pattern Extractor")
    print("=" * 60)
    print()
    
    try:
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Error: Could not connect to Supabase")
            return
        
        print("📊 Fetching production data from Supabase...")
        
        # Fetch production vulnerabilities
        vuln_response = supabase.table("vulnerabilities").select("*").execute()
        vulnerabilities = vuln_response.data if vuln_response.data else []
        print(f"   Found {len(vulnerabilities)} production vulnerabilities")
        
        # Fetch production OFCs
        ofc_response = supabase.table("options_for_consideration").select("*").execute()
        ofcs = ofc_response.data if ofc_response.data else []
        print(f"   Found {len(ofcs)} production OFCs")
        
        # Fetch vulnerability-OFC links
        links_response = supabase.table("vulnerability_ofc_links").select("*").execute()
        links = links_response.data if links_response.data else []
        print(f"   Found {len(links)} vulnerability-OFC links")
        print()
        
        if not vulnerabilities and not ofcs:
            print("⚠️  No production data found. Run this after approving some submissions.")
            return
        
        # Extract patterns
        print("🔍 Extracting patterns...")
        vuln_patterns = extract_vulnerability_patterns(vulnerabilities)
        ofc_patterns = extract_ofc_patterns(ofcs)
        
        # Generate training examples
        print("📚 Generating training examples...")
        training_examples = generate_training_examples(vulnerabilities, ofcs, links)
        
        # Compile statistics
        print("📈 Compiling statistics...")
        stats = {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "vulnerabilities": {
                "total": len(vulnerabilities),
                "with_descriptions": sum(1 for v in vulnerabilities if v.get("description")),
                "disciplines": Counter(v.get("discipline", "Unknown") for v in vulnerabilities),
                "avg_length": sum(vuln_patterns["lengths"]) / len(vuln_patterns["lengths"]) if vuln_patterns["lengths"] else 0,
                "top_opening_phrases": dict(vuln_patterns["opening_phrases"].most_common(20)),
                "top_structure_patterns": dict(vuln_patterns["structure_patterns"].most_common(10)),
            },
            "ofcs": {
                "total": len(ofcs),
                "disciplines": Counter(o.get("discipline", "Unknown") for o in ofcs),
                "avg_length": sum(ofc_patterns["lengths"]) / len(ofc_patterns["lengths"]) if ofc_patterns["lengths"] else 0,
                "top_action_verbs": dict(ofc_patterns["action_verbs"].most_common(20)),
                "top_structure_patterns": dict(ofc_patterns["structure_patterns"].most_common(10)),
            },
            "training_examples": len(training_examples),
        }
        
        # Save patterns
        patterns_output = {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "vulnerability_patterns": {
                "opening_phrases": dict(vuln_patterns["opening_phrases"].most_common(50)),
                "structure_patterns": dict(vuln_patterns["structure_patterns"].most_common(20)),
                "domain_keywords": {
                    discipline: dict(keywords.most_common(20))
                    for discipline, keywords in vuln_patterns["domain_keywords"].items()
                },
                "length_stats": {
                    "avg": sum(vuln_patterns["lengths"]) / len(vuln_patterns["lengths"]) if vuln_patterns["lengths"] else 0,
                    "min": min(vuln_patterns["lengths"]) if vuln_patterns["lengths"] else 0,
                    "max": max(vuln_patterns["lengths"]) if vuln_patterns["lengths"] else 0,
                },
                "quality_examples": vuln_patterns["quality_examples"][:100],  # Top 100
            },
            "ofc_patterns": {
                "action_verbs": dict(ofc_patterns["action_verbs"].most_common(30)),
                "structure_patterns": dict(ofc_patterns["structure_patterns"].most_common(10)),
                "domain_keywords": {
                    discipline: dict(keywords.most_common(20))
                    for discipline, keywords in ofc_patterns["domain_keywords"].items()
                },
                "length_stats": {
                    "avg": sum(ofc_patterns["lengths"]) / len(ofc_patterns["lengths"]) if ofc_patterns["lengths"] else 0,
                    "min": min(ofc_patterns["lengths"]) if ofc_patterns["lengths"] else 0,
                    "max": max(ofc_patterns["lengths"]) if ofc_patterns["lengths"] else 0,
                },
                "quality_examples": ofc_patterns["quality_examples"][:100],  # Top 100
            }
        }
        
        # Save files
        print("💾 Saving output files...")
        
        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(patterns_output, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Patterns saved: {PATTERNS_FILE}")
        
        with open(TRAINING_EXAMPLES_FILE, "w", encoding="utf-8") as f:
            for example in training_examples:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        print(f"   ✅ Training examples saved: {TRAINING_EXAMPLES_FILE} ({len(training_examples)} examples)")
        
        with open(QUALITY_REFERENCE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "vulnerabilities": vulnerabilities[:500],  # Top 500 for reference
                "ofcs": ofcs[:500],
                "extracted_at": datetime.utcnow().isoformat()
            }, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Quality reference dataset saved: {QUALITY_REFERENCE_FILE}")
        
        with open(STATISTICS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Statistics saved: {STATISTICS_FILE}")
        
        print()
        print("=" * 60)
        print("✅ Extraction Complete!")
        print("=" * 60)
        print()
        print("📋 Summary:")
        print(f"   - Vulnerability patterns: {len(patterns_output['vulnerability_patterns']['opening_phrases'])} opening phrases")
        print(f"   - OFC patterns: {len(patterns_output['ofc_patterns']['action_verbs'])} action verbs")
        print(f"   - Training examples: {len(training_examples)}")
        print()
        print("💡 Next Steps:")
        print("   1. Review patterns in: training_data/production_patterns/vulnerability_ofc_patterns.json")
        print("   2. Use patterns to enhance prompts in ollama_auto_processor.py")
        print("   3. Use training examples for model fine-tuning")
        print("   4. Use quality reference for validation")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

