"""
VOFC Parser Engine
Autonomous parser for extracting vulnerabilities and OFCs from standards-based documents.
"""

import re
import json
from pathlib import Path
from .utils import find_section_heading, generate_vuln_inverse, clean_text

try:
    from nltk import sent_tokenize
except ImportError:
    # Fallback if NLTK not available
    def sent_tokenize(text):
        """Simple sentence tokenizer fallback."""
        # Split on sentence-ending punctuation
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]


class VOFCParserEngine:
    """Autonomous parser for extracting vulnerabilities and OFCs from standards-based documents."""

    def __init__(self, ruleset):
        self.rules = ruleset
        self.positive = [re.compile(p, re.I) for p in ruleset["patterns"]["positive_directives"]]
        self.negative = [re.compile(p, re.I) for p in ruleset["patterns"]["negative_triggers"]]
        self.sections = [re.compile(p, re.I) for p in ruleset["patterns"]["section_headers"]]
        self.window = ruleset["patterns"]["inference"].get("window_sentences", 2)
        self.invert_positive = ruleset["patterns"]["inference"].get("invert_positive_directives", True)

    def extract(self, text, source_title="Unknown Document"):
        """
        Extract vulnerabilities and OFCs from text.
        
        Args:
            text: Raw text content from document
            source_title: Title/source identifier for the document
            
        Returns:
            List of extracted records with vulnerability and OFC information
        """
        # Clean and tokenize text
        cleaned = clean_text(text)
        sentences = sent_tokenize(cleaned)
        results = []

        for i, s in enumerate(sentences):
            # Check for positive directives (OFCs)
            for pat in self.positive:
                if pat.search(s):
                    section = find_section_heading(sentences, i, self.sections)
                    context = " ".join(sentences[max(0, i-self.window): i+self.window+1])
                    
                    # Generate vulnerability from positive directive if inversion enabled
                    vuln_text = generate_vuln_inverse(s) if self.invert_positive else None
                    
                    results.append({
                        "section": section,
                        "vulnerability": vuln_text,
                        "option_text": s,
                        "pattern_matched": pat.pattern,
                        "context": context,
                        "source_title": source_title,
                        "confidence_score": 0.9,
                    })
                    break  # Only match first pattern per sentence
            
            # Check for negative triggers (vulnerabilities)
            for pat in self.negative:
                if pat.search(s):
                    section = find_section_heading(sentences, i, self.sections)
                    context = " ".join(sentences[max(0, i-self.window): i+self.window+1])
                    
                    results.append({
                        "section": section,
                        "vulnerability": s,
                        "option_text": None,  # Negative triggers don't generate OFCs
                        "pattern_matched": pat.pattern,
                        "context": context,
                        "source_title": source_title,
                        "confidence_score": 0.8,
                    })
                    break  # Only match first pattern per sentence

        return results

    def load_ruleset(self, ruleset_path):
        """Load ruleset from YAML file."""
        import yaml
        with open(ruleset_path, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
        # Reinitialize with new rules
        self.__init__(rules)
        return rules

