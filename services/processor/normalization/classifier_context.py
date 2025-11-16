"""
Classifier Context Module
Provides a singleton DocumentClassifier instance initialized once per process.

This ensures embeddings are loaded only once, not per document or per record.
"""
import logging
from pathlib import Path
from typing import Optional
from .document_classifier import DocumentClassifier

logger = logging.getLogger(__name__)

# Global classifier instance (singleton)
_classifier_instance: Optional[DocumentClassifier] = None


def get_classifier(
    subsector_vocab_path: Optional[str | Path] = None,
    enable_semantic: bool = True,
    force_reload: bool = False
) -> DocumentClassifier:
    """
    Get or create the global DocumentClassifier instance.
    
    This function ensures the classifier is initialized only once per process,
    preventing expensive embedding reloads on every document.
    
    Args:
        subsector_vocab_path: Path to subsector_vocabulary.json (only used on first init)
        enable_semantic: Whether to enable semantic similarity (only used on first init)
        force_reload: If True, reinitialize the classifier (useful for testing)
        
    Returns:
        The global DocumentClassifier instance
    """
    global _classifier_instance
    
    if _classifier_instance is None or force_reload:
        logger.info("Initializing DocumentClassifier (singleton - only once per process)")
        
        # Default vocab path: same directory as document_classifier module
        if subsector_vocab_path is None:
            module_dir = Path(__file__).parent
            subsector_vocab_path = module_dir / "subsector_vocabulary.json"
        
        _classifier_instance = DocumentClassifier(
            subsector_vocab_path=subsector_vocab_path,
            enable_semantic=enable_semantic
        )
        
        logger.info("DocumentClassifier initialized successfully")
    else:
        logger.debug("Reusing existing DocumentClassifier instance")
    
    return _classifier_instance


def reset_classifier():
    """
    Reset the global classifier instance (useful for testing or memory management).
    """
    global _classifier_instance
    _classifier_instance = None
    logger.info("DocumentClassifier instance reset")

