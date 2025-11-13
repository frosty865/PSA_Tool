"""VOFC Model Module"""
from .vofc_prompt import BASE_PROMPT
from .vofc_client import extract_from_chunk, OLLAMA_URL, MODEL

__all__ = ['BASE_PROMPT', 'extract_from_chunk', 'OLLAMA_URL', 'MODEL']

