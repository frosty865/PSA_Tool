"""
discipline_resolver_v2.py

Intelligent VOFC discipline resolver (Version 2)
Maps vulnerability text → correct discipline using:
  • Keyword scoring
  • Phrase scoring
  • Semantic similarity (SentenceTransformers)
  • Discipline weighting (active, category)
  • Cyber suppression logic
  • Physical discipline prioritization

Input: discipline table rows (id, name, description, category, code, is_active)
Output: best discipline (ID + name + score) + diagnostic candidates
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Optional: use sentence transformers for semantic anchors
try:
    from sentence_transformers import SentenceTransformer, util
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------

def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def tokenize(text: str) -> List[str]:
    text = normalize(text)
    return text.split() if text else []


def ngrams(tokens: List[str], n: int) -> List[str]:
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


# ------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------

@dataclass
class Discipline:
    id: str
    name: str
    description: str
    category: str
    code: Optional[str]
    is_active: bool

    # Generated / derived fields
    keywords: List[str] = field(default_factory=list)
    phrases: List[str] = field(default_factory=list)
    semantic_seeds: List[str] = field(default_factory=list)


@dataclass
class MatchScore:
    id: str
    name: str
    category: str
    total_score: float
    keyword_hits: int
    phrase_hits: int
    semantic_score: float
    details: Dict[str, Any]


# ------------------------------------------------------------
# Resolver Class
# ------------------------------------------------------------

class DisciplineResolverV2:

    def __init__(
        self,
        disciplines: List[Dict[str, Any]],
        model_name: str = "all-MiniLM-L6-v2",
        enable_semantic: bool = True
    ):
        """
        disciplines: list of records from your database:
            {id, name, description, category, is_active, code}
        """

        # Load discipline objects
        self.disciplines: List[Discipline] = []
        for row in disciplines:
            disc = Discipline(
                id=row["id"],
                name=row["name"],
                description=row.get("description", ""),
                category=row.get("category", ""),
                code=row.get("code"),
                is_active=row.get("is_active", False),
            )
            self._generate_keywords(disc)
            self._generate_phrases(disc)
            self._generate_semantic_seeds(disc)
            self.disciplines.append(disc)

        self.enable_semantic = enable_semantic and _HAS_ST
        self.model = None
        self.disc_embeddings = {}  # id -> emb_tensor

        if self.enable_semantic:
            self._init_semantic_model(model_name)

        # Signals that indicate cyber content
        self.cyber_signals = {
            "malware", "firewall", "network", "phishing",
            "encryption", "servers", "endpoint",
            "patch", "software", "vpn", "tls"
        }

    # --------------------------------------------------------
    # Discipline Vocabulary Builders
    # --------------------------------------------------------

    def _generate_keywords(self, disc: Discipline):
        """
        Auto-generate keyword list based on:
          • name
          • description
          • discipline code
        """
        base = []

        # Add normalized variants of name
        name_words = normalize(disc.name).split()
        base.extend(name_words)

        # Code is strong hint
        if disc.code:
            base.append(normalize(disc.code))

        # Add keywords extracted from description (simple split)
        desc_keywords = normalize(disc.description).split()
        base.extend(desc_keywords)

        # Deduplicate
        base = list({k for k in base if len(k) > 2})

        disc.keywords = base

    def _generate_phrases(self, disc: Discipline):
        """
        Simple two-word phrase generator using name + code + description.
        """
        words = normalize(f"{disc.name} {disc.description}").split()
        phrases = []

        for n in range(2, 5):  # bi-gram to 4-gram
            for i in range(len(words) - n + 1):
                phrases.append(" ".join(words[i:i+n]))

        disc.phrases = list({p for p in phrases if len(p.split()) > 1})

    def _generate_semantic_seeds(self, disc: Discipline):
        """
        Seeds for embeddings:
          • discipline name
          • discipline description 
        """
        disc.semantic_seeds = [
            disc.name,
            disc.description,
            f"{disc.name} {disc.description}"
        ]

    # --------------------------------------------------------
    # Semantic Model Initialization
    # --------------------------------------------------------

    def _init_semantic_model(self, model_name: str):
        try:
            self.model = SentenceTransformer(model_name)

            for disc in self.disciplines:
                emb = self.model.encode(disc.semantic_seeds, convert_to_tensor=True)
                self.disc_embeddings[disc.id] = emb
        except Exception as e:
            logger.warning(f"Failed to load semantic model '{model_name}': {e}. Semantic scoring disabled.")
            self.enable_semantic = False
            self.model = None

    # --------------------------------------------------------
    # Scoring Engines
    # --------------------------------------------------------

    def _score_keywords_and_phrases(self, text_norm: str, tokens: List[str], disc: Discipline):
        score = 0
        kw_hits = 0
        ph_hits = 0

        grams = set(tokens)
        for n in range(2, 5):
            grams.update(ngrams(tokens, n))

        # keyword scoring
        for kw in disc.keywords:
            if kw in text_norm or kw in grams:
                score += 2
                kw_hits += 1

        # phrase scoring
        for ph in disc.phrases:
            if ph in text_norm:
                score += 4
                ph_hits += 1

        return score, kw_hits, ph_hits

    def _score_semantic(self, text: str, disc: Discipline):
        if not self.enable_semantic:
            return 0.0
        if disc.id not in self.disc_embeddings:
            return 0.0

        try:
            text_emb = self.model.encode(text, convert_to_tensor=True)
            emb = self.disc_embeddings[disc.id]

            sim = util.cos_sim(text_emb, emb)[0]  # shape: (N,)
            return float(sim.max().item())
        except Exception as e:
            logger.debug(f"Semantic scoring failed for '{disc.name}': {e}")
            return 0.0

    def _apply_category_adjustments(self, disc: Discipline, score: float, text_norm: str):
        """
        Adjust score:
          • Physical disciplines get +20%
          • Active disciplines get +10%
          • Cyber disciplines suppressed unless text contains cyber signals
        """
        if disc.category.lower() == "physical":
            score *= 1.20

        if disc.is_active:
            score *= 1.10

        if disc.category.lower() == "cyber":
            if not any(sig in text_norm for sig in self.cyber_signals):
                score *= 0.2  # suppress cyber

        return score

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def resolve(self, text: str, top_k: int = 3, return_debug: bool = False, min_score: float = 2.0):
        """
        Resolve the most likely discipline(s) for a given text.

        Args:
            text: Vulnerability or OFC text to analyze
            top_k: Number of top candidates to return in debug mode
            return_debug: If True, return full diagnostic information
            min_score: Minimum score threshold (filter out noise)

        Returns:
            Dict with best discipline or full diagnostic info
        """
        text_norm = normalize(text)
        tokens = tokenize(text)

        candidates: List[MatchScore] = []

        for disc in self.disciplines:
            kw_score, kw_hits, ph_hits = self._score_keywords_and_phrases(
                text_norm, tokens, disc
            )
            sem_score = self._score_semantic(text, disc)
            total = kw_score + sem_score * 6

            # apply category & activity adjustments
            total = self._apply_category_adjustments(disc, total, text_norm)

            candidates.append(
                MatchScore(
                    id=disc.id,
                    name=disc.name,
                    category=disc.category,
                    total_score=total,
                    keyword_hits=kw_hits,
                    phrase_hits=ph_hits,
                    semantic_score=sem_score,
                    details={"keywords": kw_hits, "phrases": ph_hits}
                )
            )

        # sort by total score
        candidates.sort(key=lambda c: c.total_score, reverse=True)
        
        # Filter out low-scoring candidates
        filtered = [c for c in candidates if c.total_score >= min_score]
        best = filtered[0] if filtered else None

        if return_debug:
            return {
                "raw_text": text,
                "best": best.__dict__ if best else None,
                "candidates": [c.__dict__ for c in filtered[:top_k]]
            }
        else:
            return {
                "discipline_id": best.id if best else None,
                "discipline_name": best.name if best else None,
                "score": best.total_score if best else 0
            }


def create_resolver_from_supabase(enable_semantic: bool = True) -> Optional[DisciplineResolverV2]:
    """
    Factory function to create a DisciplineResolverV2 from Supabase disciplines.
    
    Args:
        enable_semantic: Whether to enable semantic similarity scoring
        
    Returns:
        DisciplineResolverV2 instance or None if Supabase not available
    """
    try:
        from services.supabase_client import get_supabase_client
        
        client = get_supabase_client()
        result = client.table("disciplines") \
            .select("id, name, description, category, code, is_active") \
            .eq("is_active", True) \
            .execute()
        
        if not result.data:
            logger.warning("No active disciplines found in Supabase")
            return None
        
        return DisciplineResolverV2(result.data, enable_semantic=enable_semantic)
    except Exception as e:
        logger.error(f"Failed to create resolver from Supabase: {e}", exc_info=True)
        return None

