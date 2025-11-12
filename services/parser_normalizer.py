"""
VOFC Document Parser Normalizer

Normalizes Phase 2 records, classifies modality and domain, generates OFCs,
derives or pairs Vulnerabilities, deduplicates, and outputs clean file for sync.
"""

import re
import uuid
from collections import defaultdict
from typing import Dict, Any, List, Optional


MODALITY_RULES = [
    ("industry_standard", r"\b(shall|must|required|min(?:\.|imum))\b"),
    ("recommendation",    r"\b(should|strongly\s+recommended|recommends?)\b"),
    ("best_practice",     r"\b(may|can|consider|example|practice\s*note)\b"),
]

DOMAIN_MAP = {
    "Physical":   r"\b(perimeter|standoff|bollard|barrier|glazing|door|window|fencing|vehicular|ECP|blast|ram|HVAC|intake|air\s*intake|screen|bollards?)\b",
    "Operational":r"\b(inspection|screening|posture|exercise|drill|evacuation|lockdown|SOP|procedure|training)\b",
    "Governance": r"\b(policy|plan|governance|MOU|agreement|accountability|transparency|rights|oversight)\b",
    "Cyber":      r"\b(cyber|network|IT|access\s*control\s*system|credential\s*system|IDS/IPS)\b",
    "Public Health": r"\b(CBRN|toxic|hazardous\s*materials|decon|PPE|health|air\s*quality)\b",
}

SEC_RE = re.compile(r"(§\s*[\w\-\.\:]+|\b(?:para(?:graph)?|section)\s*[\w\.\-]+)", re.I)


def classify_modality(text: str, doc_hint: str = "") -> str:
    """Classify the modality (industry_standard, recommendation, best_practice) from text."""
    t = text.lower()
    for label, rx in MODALITY_RULES:
        if re.search(rx, t):
            return label
    # fallback by doc type
    if "ufc 4-010-01" in doc_hint.lower() or "unified facilities criteria" in doc_hint.lower():
        return "industry_standard"
    return "recommendation"  # safe default for guidance docs


def map_domain(text: str) -> str:
    """Map text to domain (Physical, Operational, Governance, Cyber, Public Health)."""
    t = text.lower()
    for domain, rx in DOMAIN_MAP.items():
        if re.search(rx, t):
            return domain
    # sensible fallbacks
    if "visitor" in t or "access control" in t:
        return "Governance" if "policy" in t else "Operational"
    return "Physical"


def extract_section(text: str) -> str:
    """Extract section reference (e.g., § 4.2.1 or paragraph 3.4) from text."""
    m = SEC_RE.search(text or "")
    return m.group(0).strip() if m else ""


def normalize_text(x) -> str:
    """Normalize text input to string, stripping whitespace."""
    return (x or "").strip()


def derive_vuln_from_clause(clause_text: str, modality: str) -> dict:
    """
    If the clause is normative or recommendational and the upstream Phase1 already
    says 'Lack of ...' we keep that. Otherwise we create a template title for when unmet.
    """
    t = normalize_text(clause_text)
    if not t:
        return {}

    title = None
    if re.search(r"\black\s+of\b|\bno\s+\w+", t, re.I):
        # Already a vulnerability statement.
        title = t[0:200]
    else:
        # Derive a future-unmet condition
        core = re.sub(r"\b(shall|must|should|may|can|consider|required|min(?:\.|imum))\b", "", t, flags=re.I)
        core = core.strip(" .;:")
        title = f"Noncompliance: {core}" if modality == "industry_standard" else f"Gap: {core}"

    return {
        "title": title[:300],
        "description": t[:1000],
        "impact": "High" if modality == "industry_standard" else "Medium",
        "likelihood": "Medium",
    }


def build_ofc_from_clause(clause_text: str, domain: str, reference: str) -> dict:
    """Build OFC object from clause text."""
    t = normalize_text(clause_text)
    # Action: imperative rewrite heuristic
    action = re.sub(r"\b(shall|must|should|may|can|consider|required|min(?:\.|imum))\b", "", t, flags=re.I).strip(" .;:")
    # Tidy verbs
    action = re.sub(r"\b(be|is|are)\s+", "", action)
    title = action[:100] if len(action) > 0 else "Implement requirement"
    return {
        "title": title,
        "domain": domain,
        "action": action or "Implement requirement as written in reference.",
        "rationale": "Reduces attack surface and aligns with referenced requirement.",
        "effort": "Med",
        "reference": reference
    }


def confidence_for_pair(text: str, modality: str, domain: str) -> float:
    """Calculate confidence score based on modality and domain."""
    base = 0.8 if modality == "industry_standard" else (0.6 if modality == "recommendation" else 0.5)
    if domain in ("Physical", "Operational"):
        base += 0.05
    # clip
    return max(0.0, min(1.0, base))


def _pair_key(v_text, ofc_title):
    """Create normalized pair key for deduplication."""
    return (normalize_text(v_text).lower(), normalize_text(ofc_title).lower())


def normalize_phase2_records(phase2_json: dict, doc_meta: dict) -> dict:
    """
    Input: Phase2 output (any shape: records / all_phase2_records)
    Output: {records:[{vulnerability, ofc, ...}] , vulnerabilities:[...], options_for_consideration:[...]}
    Only complete unique pairs are emitted. Orphans are discarded.
    """
    raw = phase2_json.get("records") or phase2_json.get("all_phase2_records") or []
    source_file = phase2_json.get("source_file") or doc_meta.get("doc", "")
    clean_pairs = []
    seen_pairs = set()

    # Phase 2 may have two shapes; normalize to iterable of clauses
    def iter_items():
        for r in raw:
            # (A) fully formed entry
            if "vulnerability" in r or "ofc" in r or "options_for_consideration" in r:
                yield r
            # (B) nested list of 'vulnerabilities' each containing vulnerability/ofc
            for vv in r.get("vulnerabilities", []):
                yield {**r, **vv}

    for item in iter_items():
        clause = normalize_text(item.get("clause_text") or item.get("source_context") or item.get("vulnerability") or item.get("ofc") or "")
        if not clause:
            continue

        # classification & domain
        modality = classify_modality(clause, doc_hint=doc_meta.get("doc_hint", ""))
        domain   = item.get("domain") or map_domain(clause)
        section  = extract_section(item.get("section") or clause)
        reference = f"{doc_meta.get('doc','') or source_file} {section}".strip()

        # build OFC from clause OR pick explicit text
        ofc_text = item.get("ofc") or (item.get("options_for_consideration", [None])[0] if item.get("options_for_consideration") else None)
        ofc_obj  = build_ofc_from_clause(ofc_text or clause, domain, reference)

        # vulnerability: prefer explicit Phase1/2 vulnerability text; else derive unmet condition
        v_text = item.get("vulnerability")
        if not v_text:
            v = derive_vuln_from_clause(clause, modality)
            v_text = v.get("title")
            vuln_obj = v
        else:
            vuln_obj = {
                "title": normalize_text(v_text)[:300],
                "description": normalize_text(item.get("source_context") or clause)[:1000],
                "impact": "Medium",
                "likelihood": "Medium",
            }

        # Skip orphans (strict)
        if not v_text or not ofc_obj.get("title"):
            continue

        # dedupe by pair
        k = _pair_key(v_text, ofc_obj["title"])
        if k in seen_pairs:
            continue
        seen_pairs.add(k)

        conf = confidence_for_pair(clause, modality, domain)

        clean_pairs.append({
            "source": {
                "doc": doc_meta.get("doc") or source_file,
                "edition": doc_meta.get("edition", ""),
                "section": section
            },
            "classification": modality,
            "clause_text": clause,
            "discipline": item.get("discipline") or ("Access Control" if "visitor" in clause.lower() else None),
            "domain": domain,
            "confidence_score": conf,
            "vulnerability": {
                **vuln_obj,
                "derived_from": section or "text",
            },
            "ofc": [ofc_obj],
            "source_file": source_file,
            "source_page": item.get("source_page"),
            "chunk_id": item.get("chunk_id"),
        })

    # Output shape the sync already expects
    return {
        "records": clean_pairs,
        "phase": "engine_normalized",
        "count": len(clean_pairs)
    }

