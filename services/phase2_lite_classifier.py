"""
Phase 2 (Lite) — Scoring + Sector/Subsector/Discipline Classification

- Input: Phase 1 records (text + page_ref; optionally vulnerability/ofc/source_context)
- Output: Adds {discipline, sector, subsector, confidence, tags, reasons}
- No LLM usage. Deterministic keyword scoring with penalties + tie-breakers.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple

# -------------------------------
# Keyword maps (edit to tune)
# -------------------------------

# Discipline keywords (mutually exclusive priority order)
DISCIPLINE_MAP: Dict[str, List[str]] = {
    "Access Control": [
        r"\baccess control\b", r"\bcredential\b", r"\bbadge\b", r"\bturnstile\b",
        r"\bvisitor (management|check[- ]?in)\b", r"\bdoor control\b", r"\bcard reader\b"
    ],
    "Lighting": [
        r"\blighting\b", r"\billumination\b", r"\blux\b", r"\blumin(aires|ous)\b"
    ],
    "Perimeter / Barriers": [
        r"\b(perimeter|fenc(e|ing)|gate|barrier|bollard|anti[- ]ram)\b"
    ],
    "Video Surveillance (VSS)": [
        r"\b(cctv|camera|video surveillance|vss|nvr|dvr|video analytics)\b"
    ],
    "Intrusion Detection": [
        r"\bintrusion (alarm|detection)\b", r"\bmotion sensor\b", r"\bdoor contact\b"
    ],
    "Locks / Hardware": [
        r"\block(s|ing)? hardware\b", r"\bdeadbolt\b", r"\bstrike\b", r"\bdoor closer\b"
    ],
    "Emergency Planning / MNS": [
        r"\bemergency (plan|planning|procedures)\b", r"\bdrill(s)?\b",
        r"\bmass notification\b", r"\bpublic address\b", r"\bMNS\b"
    ],
    "Security Operations": [
        r"\bguard(s)?\b", r"\bpost orders\b", r"\bsecurity operations\b", r"\bpatrol\b"
    ],
    "Key / Asset Control": [
        r"\bkey control\b", r"\bkey box\b", r"\bmaster key\b", r"\basset control\b"
    ],
    "Doors / Windows / Glazing": [
        r"\b(glaz(ed|ing)|laminated|blast film|door frame|window)\b"
    ],
    "CPTED": [
        r"\bcpted\b", r"\bnatural surveillance\b", r"\bterritorial (reinforce|ity)\b",
        r"\bnatural access control\b", r"\bmaintenance\b"
    ],
}

# Sector → Subsector keyword hints (non-exclusive; we pick best scoring sector, then subsector)
SECTOR_MAP: Dict[str, Dict[str, List[str]]] = {
    "K-12 Education": {
        "K-12 Schools": [r"\bschool\b", r"\bcampus\b", r"\bclassroom\b", r"\bstudent\b", r"\bk-12\b"]
    },
    "Higher Education": {
        "Universities / Colleges": [r"\buniversity\b", r"\bcollege\b", r"\bhigher education\b", r"\bdorm\b"]
    },
    "Healthcare": {
        "Hospitals": [r"\bhospital\b", r"\bclinic\b", r"\ber\b", r"\bpatient\b"]
    },
    "Commercial Facilities": {
        "Public Assembly / Venues": [r"\barena\b", r"\bstadium\b", r"\bmall\b", r"\btheater\b", r"\bmass gathering\b"]
    },
    "Government Facilities": {
        "Local Government": [r"\bcity hall\b", r"\bcourthouse\b", r"\bmunicipal\b"]
    },
    "Transportation Systems": {
        "Aviation": [r"\bairport\b", r"\btsa\b", r"\bterminal\b"],
        "Mass Transit": [r"\btransit\b", r"\bmetro\b", r"\brail\b", r"\bstation\b"]
    },
}

# Negative keywords to suppress cyber bleed
NEGATIVE_CYBER = [
    r"\bcve\b", r"\bexploit\b", r"\bpatch\b", r"\bapache\b", r"\blog4j\b",
    r"\bsql\b", r"\bxss\b", r"\bmalware\b", r"\bransomware\b", r"\bendpoint\b"
]

# Generic physical positives to boost confidence a bit
PHYSICAL_POSITIVES = [
    r"\bperimeter\b", r"\bfence\b", r"\bguard\b", r"\bgate\b", r"\bcamera\b",
    r"\blighting\b", r"\bdoor\b", r"\bwindow\b", r"\bglazing\b", r"\bkey control\b",
    r"\bpatrol\b", r"\bintrusion\b", r"\bbarrier\b", r"\bbollard\b", r"\bvisitor\b",
]

# Core terms that boost confidence when matched
CORE_TERMS = {"visitor", "policy", "management", "security", "access"}

# Weights
W_DISCIPLINE = 1.0
W_SECTOR = 0.7
W_SUBSECTOR = 0.5
W_PHYSICAL_POS = 0.15
PENALTY_CYBER = 0.8   # subtract this *count* from score

# -------------------------------
# Helpers
# -------------------------------

def _count_matches(text: str, patterns: List[str]) -> Tuple[int, List[str]]:
    hits = []
    cnt = 0
    for pat in patterns:
        if re.search(pat, text, flags=re.I):
            cnt += 1
            hits.append(pat)
    return cnt, hits

def _best_key_by_hits(text: str, mapping: Dict[str, List[str]]) -> Tuple[str, int, List[str]]:
    best_key, best_cnt, best_hits = "", 0, []
    for key, pats in mapping.items():
        cnt, hits = _count_matches(text, pats)
        if cnt > best_cnt:
            best_key, best_cnt, best_hits = key, cnt, hits
    return best_key, best_cnt, best_hits

@dataclass
class ClassifiedRecord:
    text: str
    page_ref: str | int | None
    discipline: str
    sector: str
    subsector: str
    confidence: float
    tags: List[str]
    reasons: List[str]

# -------------------------------
# Core classification
# -------------------------------

def classify_text(text: str) -> ClassifiedRecord:
    t = text.lower()

    # Negative penalties (cyber bleed)
    neg_cnt, neg_hits = _count_matches(t, NEGATIVE_CYBER)
    penalty = neg_cnt * PENALTY_CYBER
    reasons = []
    tags = []

    # Discipline
    best_disc = "Unknown"
    best_disc_cnt = 0
    best_disc_pats = []
    for disc, pats in DISCIPLINE_MAP.items():
        cnt, hits = _count_matches(t, pats)
        if cnt > best_disc_cnt:
            best_disc, best_disc_cnt, best_disc_pats = disc, cnt, hits

    if best_disc_cnt > 0:
        reasons.append(f"discipline:{best_disc} hits={best_disc_cnt}")
        tags.extend([f"disc:{p}" for p in best_disc_pats])

    # Sector/Subsector
    best_sector = "General"
    best_sector_cnt = 0
    best_sector_hits = []
    best_subsector = "General"
    best_sub_cnt = 0
    best_sub_hits = []

    for sector, submap in SECTOR_MAP.items():
        # sector-level aggregate hits = union of all subsector patterns
        sector_pats = [p for pats in submap.values() for p in pats]
        scnt, shits = _count_matches(t, sector_pats)
        if scnt > best_sector_cnt:
            best_sector, best_sector_cnt, best_sector_hits = sector, scnt, shits
            # pick best subsector within that sector
            sub_name, sub_cnt, sub_hits = _best_key_by_hits(t, submap)
            best_subsector, best_sub_cnt, best_sub_hits = sub_name or "General", sub_cnt, sub_hits

    if best_sector_cnt > 0:
        reasons.append(f"sector:{best_sector} hits={best_sector_cnt}")
        tags.extend([f"sec:{p}" for p in best_sector_hits])
    if best_sub_cnt > 0:
        reasons.append(f"subsector:{best_subsector} hits={best_sub_cnt}")
        tags.extend([f"sub:{p}" for p in best_sub_hits])

    # Physical positive boost
    pos_cnt, pos_hits = _count_matches(t, PHYSICAL_POSITIVES)
    if pos_cnt:
        tags.extend([f"pos:{p}" for p in pos_hits])

    # Check text directly for core terms (not from patterns, but from actual text)
    text_lower_words = set(re.findall(r'\b\w+\b', t))
    core_hits = sum(1 for term in CORE_TERMS if term in text_lower_words)
    
    # Calculate base_score from total matches
    total_matches = best_disc_cnt + best_sector_cnt + best_sub_cnt + pos_cnt
    # Use total unique pattern matches as denominator (approximate keyword count)
    total_patterns = len(best_disc_pats) + len(best_sector_hits) + len(best_sub_hits) + len(pos_hits)
    base_score = total_matches / max(1, total_patterns) if total_patterns > 0 else total_matches / 5.0
    
    # Calculate confidence with core term boost
    confidence = min(1.0, base_score + (0.15 * core_hits))
    
    # Apply minimum floor for weak matches (keep them viable for training)
    if confidence < 0.3:
        confidence = 0.3
    
    # Ensure bounded 0..1
    confidence = max(0.0, min(1.0, confidence))

    # Final discipline fallback if obvious physical terms present
    if best_disc == "Unknown" and (pos_cnt >= 2 or best_sector_cnt >= 1):
        best_disc = "Physical Security (General)"
    
    # Add core term info to reasons if applicable
    if core_hits > 0:
        reasons.append(f"core_terms={core_hits}")

    return ClassifiedRecord(
        text=text,
        page_ref=None,
        discipline=best_disc,
        sector=best_sector,
        subsector=best_subsector,
        confidence=round(confidence, 3),
        tags=tags,
        reasons=reasons + ([f"penalty_cyber={penalty}"] if penalty else [])
    )

# -------------------------------
# Batch API
# -------------------------------

def classify_phase1_records(records: List[dict]) -> List[dict]:
    """
    Phase 2 Lite: ONLY assign taxonomy (discipline, sector, subsector, confidence).
    
    Does NOT extract or restructure vulnerability/OFC pairs.
    Takes Phase 1 output as-is and adds taxonomy fields only.
    
    Returns list of dicts with original Phase 1 structure + taxonomy fields added.
    """
    out = []
    
    for r in records:
        # Keep original record structure - just add taxonomy
        enriched = dict(r)  # Copy all original fields
        
        # Determine text to classify for taxonomy assignment
        # Priority: vulnerability text > ofc text > source_context > text field
        text_to_classify = ""
        
        # If record has vulnerabilities array, classify based on first vulnerability
        if "vulnerabilities" in r and isinstance(r["vulnerabilities"], list) and len(r["vulnerabilities"]) > 0:
            first_vuln = r["vulnerabilities"][0]
            vuln_text = first_vuln.get("vulnerability", "").strip()
            ofc_text = first_vuln.get("ofc", "").strip()
            text_to_classify = f"{vuln_text} {ofc_text}".strip()
        
        # If record has single vulnerability field
        elif "vulnerability" in r:
            vuln_text = r.get("vulnerability", "").strip()
            # Check for options_for_consideration (standardized) or ofc (legacy)
            ofc_data = r.get("options_for_consideration") or r.get("ofc")
            if isinstance(ofc_data, list):
                ofc_text = " ".join([str(o) for o in ofc_data if o]).strip()
            else:
                ofc_text = str(ofc_data).strip() if ofc_data else ""
            text_to_classify = f"{vuln_text} {ofc_text}".strip()
        
        # Fallback to other text fields
        if not text_to_classify:
            text_to_classify = (
                r.get("source_context", "") or
                r.get("text", "") or
                r.get("ofc", "") or
                ""
            ).strip()
        
        # Classify text to get taxonomy
        if text_to_classify and len(text_to_classify) >= 10:
            c = classify_text(text_to_classify)
            
            # Add taxonomy fields to the record
            enriched["discipline"] = c.discipline
            enriched["sector"] = c.sector
            enriched["subsector"] = c.subsector
            enriched["confidence"] = c.confidence
            enriched["confidence_score"] = c.confidence
        else:
            # No text to classify - use defaults
            enriched["discipline"] = "Unknown"
            enriched["sector"] = "General"
            enriched["subsector"] = "General"
            enriched["confidence"] = 0.5
            enriched["confidence_score"] = 0.5
        
        # If record has vulnerabilities array, also add taxonomy to each vulnerability item
        if "vulnerabilities" in enriched and isinstance(enriched["vulnerabilities"], list):
            for vuln_item in enriched["vulnerabilities"]:
                # Classify each vulnerability individually
                vuln_text = vuln_item.get("vulnerability", "").strip()
                ofc_text = vuln_item.get("ofc", "").strip()
                item_text = f"{vuln_text} {ofc_text}".strip()
                
                if item_text and len(item_text) >= 10:
                    c_item = classify_text(item_text)
                    vuln_item["discipline"] = c_item.discipline
                    vuln_item["sector"] = c_item.sector
                    vuln_item["subsector"] = c_item.subsector
                    vuln_item["confidence"] = c_item.confidence
                    vuln_item["confidence_score"] = c_item.confidence
                else:
                    # Use parent record taxonomy
                    vuln_item["discipline"] = enriched.get("discipline", "Unknown")
                    vuln_item["sector"] = enriched.get("sector", "General")
                    vuln_item["subsector"] = enriched.get("subsector", "General")
                    vuln_item["confidence"] = enriched.get("confidence", 0.5)
                    vuln_item["confidence_score"] = enriched.get("confidence_score", 0.5)
        
        out.append(enriched)
    
    return out

