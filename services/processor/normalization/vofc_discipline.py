"""
vofc_discipline.py (DEPRECATED - Use DisciplineResolverV2)

⚠️ DEPRECATED: This module is deprecated. Use DisciplineResolverV2 instead.

Intelligent VOFC discipline resolver:
- Hybrid keyword/phrase/semantic scoring
- Designed for vulnerability / OFC text
"""
import warnings

# Deprecation warning
warnings.warn(
    "vofc_discipline.DisciplineResolver is deprecated. Use DisciplineResolverV2 from discipline_resolver_v2 instead.",
    DeprecationWarning,
    stacklevel=2
)

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer, util
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

# -----------------------
# Basic text utilities
# -----------------------

def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    # strip weird characters but keep spaces and alphanumerics
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def tokenize(text: str) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []
    return text.split()


def ngrams(tokens: List[str], n: int) -> List[str]:
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


# -----------------------
# Data structures
# -----------------------

@dataclass
class DisciplineConfig:
    name: str
    category: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    phrases: List[str] = field(default_factory=list)


@dataclass
class DisciplineScore:
    name: str
    category: Optional[str]
    total_score: float
    keyword_hits: int
    phrase_hits: int
    semantic_score: float
    details: Dict[str, Any] = field(default_factory=dict)


# -----------------------
# Resolver
# -----------------------

class DisciplineResolver:
    """
    ⚠️ DEPRECATED: Use DisciplineResolverV2 instead.
    
    Intelligent discipline resolver.
    
    Usage:
        resolver = DisciplineResolver("disciplines_vocabulary.json")
        result = resolver.resolve(text, top_k=3, return_debug=True)
    """

    def __init__(
        self,
        vocab_path: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
        enable_semantic: bool = True
    ):
        # Default vocab path: same directory as this module
        if vocab_path is None:
            module_dir = Path(__file__).parent
            vocab_path = str(module_dir / "disciplines_vocabulary.json")
        
        if not os.path.exists(vocab_path):
            raise FileNotFoundError(f"Discipline vocabulary not found: {vocab_path}")

        with open(vocab_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        self.disciplines: Dict[str, DisciplineConfig] = {}
        for name, cfg in raw.items():
            self.disciplines[name] = DisciplineConfig(
                name=name,
                category=cfg.get("category"),
                keywords=[normalize_text(k) for k in cfg.get("keywords", [])],
                phrases=[normalize_text(p) for p in cfg.get("phrases", [])],
            )

        self.enable_semantic = enable_semantic and _HAS_ST

        # Load semantic model & precompute discipline embeddings
        self.model = None
        self.disc_embeddings = {}  # name -> embedding tensor

        if self.enable_semantic:
            self._init_semantic_model(model_name)

    def _init_semantic_model(self, model_name: str):
        try:
            self.model = SentenceTransformer(model_name)
            # We embed the canonical discipline names plus their phrases
            for name, cfg in self.disciplines.items():
                texts = [name] + cfg.phrases[:5]  # keep it small
                emb = self.model.encode(texts, convert_to_tensor=True)
                self.disc_embeddings[name] = emb
        except Exception as e:
            # If semantic model fails to load, disable it
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load semantic model '{model_name}': {e}. Semantic scoring disabled.")
            self.enable_semantic = False
            self.model = None

    # -----------------------
    # Core scoring functions
    # -----------------------

    def _score_keywords_and_phrases(
        self,
        text_norm: str,
        tokens: List[str],
        discipline: DisciplineConfig
    ) -> tuple:
        """
        Returns: (score, keyword_hits, phrase_hits)
        """
        score = 0.0
        keyword_hits = 0
        phrase_hits = 0

        # 1-4 gram search
        grams = set(tokens)
        for n in range(2, 5):
            grams.update(ngrams(tokens, n))

        # keyword scoring
        for kw in discipline.keywords:
            if not kw:
                continue
            if kw in text_norm or kw in grams:
                score += 2.0
                keyword_hits += 1

        # phrase scoring
        for phrase in discipline.phrases:
            if not phrase:
                continue
            if phrase in text_norm:
                score += 4.0
                phrase_hits += 1

        return score, keyword_hits, phrase_hits

    def _score_semantic(self, text: str, discipline_name: str) -> float:
        if not self.enable_semantic or not self.model:
            return 0.0
        if discipline_name not in self.disc_embeddings:
            return 0.0

        text = text.strip()
        if not text:
            return 0.0

        try:
            text_emb = self.model.encode(text, convert_to_tensor=True)
            disc_emb = self.disc_embeddings[discipline_name]
            sim = util.cos_sim(text_emb, disc_emb)[0]  # shape: (N,)

            # max sim across name + sample phrases
            max_sim = float(sim.max().item())
            return max_sim
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Semantic scoring failed for '{discipline_name}': {e}")
            return 0.0

    # -----------------------
    # Public API
    # -----------------------

    def resolve(
        self,
        text: str,
        top_k: int = 3,
        return_debug: bool = False,
        semantic_weight: float = 5.0,
        min_score: float = 2.0
    ) -> Dict[str, Any]:
        """
        Resolve the most likely discipline(s) for a given text.

        Returns:
            {
                "best": { ... } or None,
                "candidates": [ ... ],
                "raw_text": text
            }

        Each candidate is a DisciplineScore converted to dict.
        """
        text = text or ""
        text_norm = normalize_text(text)
        tokens = tokenize(text)

        scores: List[DisciplineScore] = []

        for name, cfg in self.disciplines.items():
            kw_score, kw_hits, ph_hits = self._score_keywords_and_phrases(
                text_norm, tokens, cfg
            )
            sem_score = self._score_semantic(text, name) if self.enable_semantic else 0.0

            # weight semantic into total
            total = kw_score + semantic_weight * sem_score

            scores.append(
                DisciplineScore(
                    name=name,
                    category=cfg.category,
                    total_score=total,
                    keyword_hits=kw_hits,
                    phrase_hits=ph_hits,
                    semantic_score=sem_score,
                    details={
                        "keyword_score": kw_score,
                        "semantic_weight": semantic_weight
                    }
                )
            )

        # Sort by score desc
        scores.sort(key=lambda s: s.total_score, reverse=True)

        # Filter out noise
        filtered = [s for s in scores if s.total_score >= min_score]

        best = filtered[0] if filtered else None
        top_candidates = filtered[:top_k] if filtered else []

        result = {
            "raw_text": text,
            "best": None,
            "candidates": []
        }

        if best:
            result["best"] = {
                "discipline_name": best.name,
                "category": best.category,
                "score": best.total_score,
                "keyword_hits": best.keyword_hits,
                "phrase_hits": best.phrase_hits,
                "semantic_score": best.semantic_score
            }

        if return_debug:
            result["candidates"] = [
                {
                    "discipline_name": s.name,
                    "category": s.category,
                    "score": s.total_score,
                    "keyword_hits": s.keyword_hits,
                    "phrase_hits": s.phrase_hits,
                    "semantic_score": s.semantic_score,
                    "details": s.details
                }
                for s in top_candidates
            ]

        return result

