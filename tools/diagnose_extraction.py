#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extraction Diagnostic Tool
Analyzes what the model is extracting and why valid items might be getting filtered out.
"""

import json
import sys
from pathlib import Path
from collections import Counter

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def analyze_json_file(json_path: Path):
    """Analyze a JSON output file to see what was extracted."""
    print("=" * 60)
    print(f"Analyzing: {json_path.name}")
    print("=" * 60)
    print()
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Error reading file: {e}")
        return
    
    # Check different possible structures
    records = []
    if "records" in data:
        raw_records = data["records"]
        # Handle nested structure (records with "vulnerabilities" array inside)
        for rec in raw_records:
            if "vulnerabilities" in rec and isinstance(rec["vulnerabilities"], list):
                # Extract each vulnerability from the nested array
                for vuln in rec["vulnerabilities"]:
                    records.append({
                        "vulnerability": vuln.get("vulnerability") or vuln.get("vulnerability_name") or vuln.get("title", ""),
                        "options_for_consideration": [vuln.get("ofc")] if vuln.get("ofc") else vuln.get("options_for_consideration", []),
                        "confidence_score": vuln.get("confidence_score") or 0.5
                    })
            else:
                # Flat structure
                records.append(rec)
    elif "all_phase2_records" in data:
        records = data["all_phase2_records"]
    elif "vulnerabilities" in data:
        # Convert vulnerabilities array to records format
        for v in data.get("vulnerabilities", []):
            records.append({
                "vulnerability": v.get("vulnerability") or v.get("vulnerability_name") or v.get("title"),
                "options_for_consideration": v.get("options_for_consideration", []),
                "confidence_score": v.get("confidence_score", 0.5)
            })
    
    print(f"Found {len(records)} records in JSON")
    print()
    
    if not records:
        print("WARNING: No records found! Model may not be extracting anything.")
        print()
        print("Possible issues:")
        print("  1. Model not running correctly")
        print("  2. Prompts too restrictive")
        print("  3. JSON parsing failed")
        print("  4. Empty response from model")
        return
    
    # Analyze each record
    valid_count = 0
    invalid_reasons = Counter()
    
    for idx, rec in enumerate(records, 1):
        vuln = rec.get("vulnerability", "").strip()
        ofcs = rec.get("options_for_consideration", [])
        if isinstance(ofcs, str):
            ofcs = [ofcs]
        elif not isinstance(ofcs, list):
            ofcs = []
        
        confidence = rec.get("confidence_score", 0.5)
        if isinstance(confidence, str):
            confidence = 0.5
        
        issues = []
        
        # Check vulnerability
        if not vuln:
            issues.append("No vulnerability text")
        elif len(vuln) < 7:
            issues.append(f"Vulnerability too short ({len(vuln)} chars, need 7+)")
        else:
            placeholder_patterns = ["placeholder", "dummy", "test", "example", "sample", "fake"]
            if any(p in vuln.lower() for p in placeholder_patterns):
                issues.append("Vulnerability contains placeholder text")
        
        # Check OFCs
        if not ofcs or len(ofcs) == 0:
            issues.append("No OFCs")
        else:
            valid_ofcs = []
            for ofc in ofcs:
                ofc_text = str(ofc).strip() if ofc else ""
                if not ofc_text:
                    continue
                if len(ofc_text) < 5:
                    issues.append(f"OFC too short ({len(ofc_text)} chars, need 5+)")
                    continue
                placeholder_patterns = ["placeholder", "dummy", "test", "example", "sample", "fake"]
                if any(p in ofc_text.lower() for p in placeholder_patterns):
                    issues.append(f"OFC contains placeholder text: {ofc_text[:50]}")
                    continue
                valid_ofcs.append(ofc_text)
            
            if not valid_ofcs:
                issues.append("No valid OFCs after filtering")
        
        # Check confidence
        if confidence < 0.4:
            issues.append(f"Confidence too low ({confidence:.2f}, need 0.4+)")
        
        if not issues:
            valid_count += 1
            print(f"[VALID] Record {idx}: VALID")
            print(f"   Vulnerability: {vuln[:80]}...")
            print(f"   OFCs: {len(ofcs)}")
            print(f"   Confidence: {confidence:.2f}")
        else:
            print(f"[INVALID] Record {idx}: INVALID")
            print(f"   Vulnerability: {vuln[:80] if vuln else '(empty)'}...")
            print(f"   OFCs: {len(ofcs)}")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Issues: {', '.join(issues)}")
            for issue in issues:
                invalid_reasons[issue] += 1
        
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total records: {len(records)}")
    print(f"Valid records: {valid_count}")
    print(f"Invalid records: {len(records) - valid_count}")
    print()
    
    if invalid_reasons:
        print("Top rejection reasons:")
        for reason, count in invalid_reasons.most_common():
            print(f"  - {reason}: {count}")
    
    print()
    if valid_count == 0:
        print("WARNING: NO VALID RECORDS FOUND!")
        print()
        print("Recommendations:")
        print("  1. Check model prompts - may be too restrictive")
        print("  2. Lower confidence threshold (currently 0.3)")
        print("  3. Allow OFC-only records (currently requires both vuln + OFC)")
        print("  4. Check model is actually running and returning JSON")
        print("  5. Review raw model output in logs")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python tools/diagnose_extraction.py <json_file>")
        print()
        print("Example:")
        print("  python tools/diagnose_extraction.py C:\\Tools\\Ollama\\Data\\review\\temp\\document_phase2_engine.json")
        sys.exit(1)
    
    json_path = Path(sys.argv[1])
    
    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        sys.exit(1)
    
    analyze_json_file(json_path)


if __name__ == "__main__":
    main()

