# services/processing/parse_matrix_survey.py

# v1.1.0  — robust, invisible DHS-style matrix survey parser

from __future__ import annotations

import re
import json
from typing import Dict, List, Any, Optional

SEVERITY_ORDER = ["Very Low", "Low", "Medium", "High", "Very High"]


class MatrixSurveyParser:
    """
    Robust parser for DHS-style matrix surveys (e.g., K-12 School Security Survey 508).
    Detects Question → Severity Levels → OFCs blocks, with optional background/references.
    """
    
    # --- Tunables for confidence / validation ---
    MIN_GROUPS_REQUIRED = 3           # require >= N questions to accept parser output
    MIN_LEVELS_PER_GROUP = 3          # require >= N severity levels per question
    ACCEPT_IF_ANY_SEVERITY_MISSING = False  # if False, prefer 5/5 severities
    
    # Bullet starters commonly used for OFCs; extend as needed
    OFC_STARTERS = (
        "Designate", "Provide", "Implement", "Expand", "Continue", "Assess",
        "Develop", "Establish", "Train", "Test", "Exercise", "Install", "Enhance",
        "Ensure", "Encourage", "Coordinate", "Stock", "Create", "Consult", "Join",
        "Invite", "Collaborate"
    )
    
    # Regexes
    _re_section_hdr = re.compile(r'^[A-Z][A-Za-z/\s\-\&]+$')
    _re_question = re.compile(r'^\s*\d+\.\s*(Does|Is|Are|Has|Have|Do|Maintain|Maintain(s)?)\b', re.IGNORECASE)
    _re_severity = re.compile(r'^(Very Low|Low|Medium|High|Very High)\s*$', re.IGNORECASE)
    _re_ofc_bullet = re.compile(r'^\s*(?:[\u2022\u25E6\u2043\-•]|[0-9]+\.)\s*(.+)$')  # •, -, 1.
    _re_reference_heading = re.compile(r'^(References?|Background|Background/References?)\s*:?$', re.IGNORECASE)
    
    @staticmethod
    def detect(text: str) -> bool:
        """
        Lightweight heuristic detection:
        - mentions "Option(s) for Consideration"
        - includes at least 3 of the 5 severity tokens
        - contains question numbering like "1. " with a Does/Is/Are/Has...
        """
        t = text
        has_ofc = ("Option for Consideration" in t) or ("Options for Consideration" in t)
        severities = sum(1 for s in SEVERITY_ORDER if s in t)
        has_question = bool(MatrixSurveyParser._re_question.search(t))
        return has_ofc and severities >= 3 and has_question
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        # Merge hyphenation at EOL and collapse excessive spaces
        text = re.sub(r'-\n', '', text)
        text = text.replace('\r', '')
        # Keep line structure; do not join lines globally, parser is line-oriented
        return text
    
    @classmethod
    def parse(cls, text: str, source_file: str) -> Dict[str, Any]:
        """
        Main entry point. Returns a dict ready for JSONB submission.
        Raises no exceptions; returns a safe, validated structure or a minimal placeholder.
        """
        try:
            norm = cls._normalize_text(text)
            sections = cls._extract_sections(norm)
            result = {
                "source_file": source_file,
                "document_type": "Matrix Survey",
                "handler": "matrix_survey_parser",
                "parser_version": "1.1.0",
                "sections": sections
            }
            valid = cls._validate(result)
            if not valid:
                # Return minimal payload to signal fallback should occur
                return {"_matrix_parser_failed": True, "reason": "validation_failed"}
            return result
        except Exception as exc:
            return {"_matrix_parser_failed": True, "reason": f"exception: {exc.__class__.__name__}"}
    
    # ---------- internals ----------
    
    @classmethod
    def _extract_sections(cls, text: str) -> List[Dict[str, Any]]:
        lines = text.splitlines()
        sections: List[Dict[str, Any]] = []
        cur_section: Optional[Dict[str, Any]] = None
        cur_q: Optional[Dict[str, Any]] = None
        cur_levels: List[Dict[str, Any]] = []
        cur_severity: Optional[str] = None
        in_refs_block = False
        refs_accum: List[str] = []
        bkg_accum: List[str] = []
        
        def flush_question():
            nonlocal cur_q, cur_levels, cur_section
            if cur_q:
                # attach levels
                cur_q["levels"] = cur_levels
                # attach background/references if any
                if bkg_accum:
                    cur_q["background"] = cls._clean_join(bkg_accum)
                if refs_accum:
                    cur_q["references"] = cls._clean_refs(refs_accum)
                cur_section["vulnerability_groups"].append(cur_q)
            cur_q = None
        
        def flush_section():
            nonlocal cur_section, sections
            if cur_section:
                # If there was an unterminated question, flush it
                if cur_q:
                    flush_question()
                sections.append(cur_section)
        
        for raw in lines:
            line = raw.strip()
            
            # Skip empty lines unless we're accumulating background/references
            if not line:
                if in_refs_block:
                    continue
                # If we're inside a severity block, allow blank lines to just pass
                continue
            
            # Detect section header
            if cls._re_section_hdr.match(line) and "Question" not in line:
                # Close out previous section
                if cur_section:
                    flush_section()
                cur_section = {"section_title": line, "vulnerability_groups": []}
                # reset per-section state
                cur_q, cur_levels, cur_severity = None, [], None
                in_refs_block, refs_accum[:] = False, []
                bkg_accum[:] = []
                continue
            
            # Detect new question
            if cls._re_question.match(line):
                # Close previous question if any
                if cur_q:
                    flush_question()
                
                # Start new question
                cur_q = {"question": cls._strip_number_prefix(line), "levels": []}
                cur_levels, cur_severity = [], None
                in_refs_block = False
                refs_accum[:] = []
                bkg_accum[:] = []
                
                # Ensure section exists in case the doc omits headers
                if cur_section is None:
                    cur_section = {"section_title": "General", "vulnerability_groups": []}
                continue
            
            # Inside a question: check severity headings
            if cur_q and cls._re_severity.match(line):
                cur_severity = cls._normalize_severity(line)
                cur_levels.append({
                    "severity": cur_severity,
                    "vulnerability_text": "",
                    "ofcs": []
                })
                in_refs_block = False
                continue
            
            # References/Background header toggles
            if cur_q and cls._re_reference_heading.match(line):
                in_refs_block = True
                continue
            
            # Accumulate references/background if in that block
            if cur_q and in_refs_block:
                # Try to identify reference-ish lines (very permissive)
                refs_accum.append(line)
                continue
            
            # Capture OFCs: explicit bullets or line starting with verbs in OFC_STARTERS
            if cur_q and cur_levels:
                m_bullet = cls._re_ofc_bullet.match(line)
                if m_bullet:
                    cur_levels[-1]["ofcs"].append(m_bullet.group(1).strip())
                    continue
                
                if cls._starts_with_ofc_verb(line):
                    cur_levels[-1]["ofcs"].append(line)
                    continue
                
                # Otherwise treat as vulnerability narrative for the current severity
                if cur_levels[-1]["vulnerability_text"]:
                    cur_levels[-1]["vulnerability_text"] += " " + line
                else:
                    cur_levels[-1]["vulnerability_text"] = line
                continue
            
            # If we reach here: stray lines before first question; ignore.
        
        # End of file: flush
        if cur_section:
            if cur_q:
                flush_question()
            sections.append(cur_section)
        
        # Post-process: normalize severities order, trim text
        for s in sections:
            for vg in s.get("vulnerability_groups", []):
                for lvl in vg.get("levels", []):
                    lvl["vulnerability_text"] = cls._clean_text(lvl.get("vulnerability_text", ""))
        
        return sections
    
    @staticmethod
    def _starts_with_ofc_verb(line: str) -> bool:
        for v in MatrixSurveyParser.OFC_STARTERS:
            if line.startswith(v):
                return True
        return False
    
    @staticmethod
    def _clean_text(t: str) -> str:
        return re.sub(r'\s+', ' ', t).strip()
    
    @staticmethod
    def _clean_join(parts: List[str]) -> str:
        return MatrixSurveyParser._clean_text(" ".join(parts))
    
    @staticmethod
    def _clean_refs(parts: List[str]) -> List[str]:
        # Split on semicolons if they exist; otherwise return individual lines
        merged = " ".join(parts)
        # Soft split; keep as list for linking later
        items = [p.strip() for p in re.split(r';(?=\s*[A-Z0-9(])', merged) if p.strip()]
        return items if items else [MatrixSurveyParser._clean_text(merged)]
    
    @staticmethod
    def _strip_number_prefix(q: str) -> str:
        return re.sub(r'^\s*\d+\.\s*', '', q).strip()
    
    @staticmethod
    def _normalize_severity(s: str) -> str:
        s = s.strip().title()
        # enforce exact labels
        for label in SEVERITY_ORDER:
            if s.lower() == label.lower():
                return label
        return s
    
    # ---------- validation ----------
    
    @classmethod
    def _validate(cls, payload: Dict[str, Any]) -> bool:
        """
        Structural validation for confidence. We want:
         - sections ≥ 1
         - total groups ≥ MIN_GROUPS_REQUIRED
         - each group has levels ≥ MIN_LEVELS_PER_GROUP
         - if strict: prefer groups that include all 5 severities or at least ordered subset
        """
        if not isinstance(payload, dict):
            return False
        
        if "sections" not in payload or not isinstance(payload["sections"], list):
            return False
        
        total_groups = 0
        for s in payload["sections"]:
            vgs = s.get("vulnerability_groups", [])
            total_groups += len(vgs)
            
            for g in vgs:
                lvls = g.get("levels", [])
                if len(lvls) < cls.MIN_LEVELS_PER_GROUP:
                    return False
                
                # check severity labels are recognizable
                sev_labels = [l.get("severity") for l in lvls if "severity" in l]
                
                if not cls.ACCEPT_IF_ANY_SEVERITY_MISSING:
                    # require all five unique severities if present in document
                    uniq = set(sev_labels)
                    if len(uniq) < min(5, cls.MIN_LEVELS_PER_GROUP):
                        return False
                
                # narratives or OFCs must exist
                has_content = any((l.get("vulnerability_text") or l.get("ofcs")) for l in lvls)
                if not has_content:
                    return False
        
        return total_groups >= cls.MIN_GROUPS_REQUIRED

