"""
VOFC Physical-Security Seed Extractor v2.0

------------------------------------------

Now reads directly from *_parsed.json files created in Phase 1.

Looks for textual cues that indicate vulnerabilities or OFCs

and emits annotated_seed.jsonl for retraining.
"""

import re
import json
from pathlib import Path
from datetime import datetime


# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
# Training data paths - check new location first, fallback to legacy
TRAIN_DIR = Path(r"C:\Tools\VOFC-Flask\training_data") if Path(r"C:\Tools\VOFC-Flask\training_data").exists() else Path(r"C:\Users\frost\OneDrive\Desktop\Projects\PSA_Tool\training_data")
PARSED_DIR = TRAIN_DIR / "parsed"
OUTPUT_FILE = TRAIN_DIR / "annotated_seed.jsonl"


# Lexical cues
VULN_CUES = [
    r"\blacks?\b", r"does not have", r"\bno\b", r"\bwithout\b",
    r"\binsufficient\b", r"\binadequate\b", r"\bunsecured\b",
    r"\bunauthorized\b", r"\bmissing\b", r"not implemented",
    r"not installed", r"not functional", r"failed to", r"open gate",
    r"no access control", r"no camera", r"no lighting"
]

OFC_CUES = [
    r"\binstall\b", r"\bimplement\b", r"\bdevelop\b", r"\bestablish\b",
    r"\bconduct\b", r"\btrain\b", r"\bupgrade\b", r"\breplace\b",
    r"\benhance\b", r"\bimprove\b", r"\bcoordinate\b", r"\bdeploy\b",
    r"add lighting", r"install camera", r"improve fencing",
    r"implement access control", r"create security plan"
]


# -------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------
def is_vulnerability(text: str) -> bool:
    return any(re.search(pat, text, re.I) for pat in VULN_CUES)


def is_ofc(text: str) -> bool:
    return any(re.search(pat, text, re.I) for pat in OFC_CUES)


def extract_from_parsed(json_path: Path):
    """Pull candidate sentences from *_parsed.json or *_phase1_parser.json structure."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Get source_file from top level or first record
    source_file = data.get("source_file", json_path.name)
    if not source_file or source_file == json_path.name:
        # Try to get from first record if available
        if "records" in data and len(data.get("records", [])) > 0:
            source_file = data["records"][0].get("source_file", json_path.name)
    
    candidates = []

    # Handle new format: *_parsed.json with "chunks" array
    if "chunks" in data:
        chunks = data.get("chunks", [])
        for c in chunks:
            text = c.get("text", "")
            if not text or len(text) < 25:
                continue

            if is_vulnerability(text):
                candidates.append({
                    "input": text.strip(),
                    "output": {"type": "vulnerability"},
                    "source": source_file
                })
            elif is_ofc(text):
                candidates.append({
                    "input": text.strip(),
                    "output": {"type": "ofc"},
                    "source": source_file
                })
    
    # Handle old format: *_phase1_parser.json with "records" array
    elif "records" in data:
        records = data.get("records", [])
        for record in records:
            # Extract vulnerability text
            vuln_text = record.get("vulnerability", "")
            if vuln_text and len(vuln_text) >= 25:
                candidates.append({
                    "input": vuln_text.strip(),
                    "output": {"type": "vulnerability"},
                    "source": source_file
                })
            
            # Extract OFC text
            ofc_text = record.get("ofc", "")
            if ofc_text and len(ofc_text) >= 25:
                candidates.append({
                    "input": ofc_text.strip(),
                    "output": {"type": "ofc"},
                    "source": source_file
                })
            
            # Also check source_context if available
            context_text = record.get("source_context", "")
            if context_text and len(context_text) >= 25:
                if is_vulnerability(context_text):
                    candidates.append({
                        "input": context_text.strip(),
                        "output": {"type": "vulnerability"},
                        "source": source_file
                    })
                elif is_ofc(context_text):
                    candidates.append({
                        "input": context_text.strip(),
                        "output": {"type": "ofc"},
                        "source": source_file
                    })

    return candidates


# ----------------------------------------------------------------
# MAIN  (updated to include *_phase1_parser.json support)
# ----------------------------------------------------------------
def main():
    print(f"[INFO] Scanning {PARSED_DIR} for parsed Phase 1 outputs...")

    results = []

    # 1. Match files ending in *_parsed.json
    for file in PARSED_DIR.glob("*_parsed.json"):
        results.extend(extract_from_parsed(file))

    # 2. Match files ending in *_phase1_parser.json
    for file in PARSED_DIR.glob("*_phase1_parser.json"):
        results.extend(extract_from_parsed(file))

    if not results:
        print("[WARN] No matches found — check regex patterns or parsed folder.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"[SUCCESS] Wrote {len(results)} seed examples to {OUTPUT_FILE}")
    print("Use this file as annotated_seed.jsonl for retraining.")


if __name__ == "__main__":
    main()
