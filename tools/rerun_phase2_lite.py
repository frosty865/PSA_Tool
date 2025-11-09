"""
Re-run Phase 2 Lite on an existing Phase 1 parser output file.

Usage:
    python tools/rerun_phase2_lite.py "C:\Tools\Ollama\Data\review\temp\K-12 School Security Practices Guide_phase1_parser.json"
"""

import json
import sys
from pathlib import Path

# Add project directory to Python path
PROJECT_DIR = Path(__file__).parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from services.phase2_lite_classifier import classify_phase1_records

def rerun_phase2_lite(phase1_file: str):
    """Re-run Phase 2 Lite classification on a Phase 1 parser output file."""
    phase1_path = Path(phase1_file)
    
    if not phase1_path.exists():
        print(f"❌ File not found: {phase1_file}")
        return
    
    print(f"📂 Loading Phase 1 output: {phase1_path.name}")
    
    # Load Phase 1 data
    with open(phase1_path, "r", encoding="utf-8") as f:
        phase1_data = json.load(f)
    
    records = phase1_data.get("records", [])
    if not records:
        print(f"❌ No records found in Phase 1 file")
        return
    
    print(f"✅ Loaded {len(records)} records from Phase 1")
    
    # Run Phase 2 Lite classification
    print(f"🔍 Running Phase 2 Lite classification...")
    scored_records = classify_phase1_records(records)
    
    print(f"✅ Classified {len(scored_records)} records")
    
    # Show confidence score distribution
    confidences = [r.get("confidence_score", r.get("confidence", 0)) for r in scored_records]
    if confidences:
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        print(f"📊 Confidence scores: min={min_conf:.3f}, avg={avg_conf:.3f}, max={max_conf:.3f}")
        
        # Count boosted scores (0.3 floor)
        boosted = sum(1 for c in confidences if c == 0.3)
        if boosted > 0:
            print(f"   {boosted} records boosted to minimum 0.3 floor")
    
    # Build Phase 2 output structure
    phase2_output = {
        "records": scored_records,
        "phase": "engine_lite",
        "count": len(scored_records),
        "source_file": phase1_data.get("source_file", phase1_path.stem),
        "model_version": "phase2-lite-classifier:v1"
    }
    
    # Save Phase 2 output
    output_file = phase1_path.parent / f"{phase1_path.stem.replace('_phase1_parser', '')}_phase2_engine.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(phase2_output, f, indent=2, default=str)
    
    print(f"💾 Saved Phase 2 output to: {output_file.name}")
    print(f"   File size: {output_file.stat().st_size:,} bytes")
    
    # Show sample record
    if scored_records:
        sample = scored_records[0]
        print(f"\n📋 Sample record:")
        print(f"   Discipline: {sample.get('discipline', 'N/A')}")
        print(f"   Sector: {sample.get('sector', 'N/A')}")
        print(f"   Subsector: {sample.get('subsector', 'N/A')}")
        print(f"   Confidence: {sample.get('confidence_score', sample.get('confidence', 'N/A'))}")
    
    return str(output_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/rerun_phase2_lite.py <phase1_parser.json>")
        sys.exit(1)
    
    phase1_file = sys.argv[1]
    output_file = rerun_phase2_lite(phase1_file)
    
    if output_file:
        print(f"\n✅ Phase 2 Lite re-run complete!")
        print(f"   Output: {output_file}")

