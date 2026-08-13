"""Utilidades compartidas para normalizacion y matching textual."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_WHITESPACE_RE = re.compile(r"\s+")


def _ascii_fold(text: str) -> str:
    """Convierte texto unicode a ASCII seguro para matching flexible."""
    normalized = unicodedata.normalize("NFKD", text or "")
    return normalized.encode("ascii", "ignore").decode("ascii")


def collapse_whitespace(text: str) -> str:
    """Colapsa espacios en blanco conservando texto legible."""
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def normalize_for_match(text: str) -> str:
    """Normaliza texto para matching exacto/fuzzy entre cadenas cortas."""
    ascii_text = _ascii_fold(text)
    lowered = ascii_text.lower()
    return collapse_whitespace(lowered)


def normalize_for_retrieval(text: str) -> str:
    """Normaliza texto para retrieval lexical sin destruir la evidencia original."""
    normalized = normalize_for_match(text)
    normalized = re.sub(r"[^a-z0-9_\-./:% ]+", " ", normalized)
    return collapse_whitespace(normalized)


def normalize_text(text: str) -> str:
    """Compatibilidad historica: alias de normalize_for_match."""
    return normalize_for_match(text)


def tokenize(text: str) -> list[str]:
    """Tokeniza texto normalizado para matching flexible."""
    return _TOKEN_RE.findall(normalize_for_match(text))


def tokenize_retrieval(text: str) -> list[str]:
    """Tokeniza texto pensando en retrieval, no en reconstruccion de evidencia."""
    return _TOKEN_RE.findall(normalize_for_retrieval(text))


def fuzzy_ratio(a: str, b: str) -> float:
    """Retorna un score de similitud [0, 1]."""
    a_norm = normalize_for_match(a)
    b_norm = normalize_for_match(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(a=a_norm, b=b_norm).ratio()


def contains_whole_phrase(haystack: str, phrase: str) -> bool:
    """Indica si la frase aparece como secuencia delimitada en el texto."""
    haystack_norm = normalize_for_match(haystack)
    phrase_norm = normalize_for_match(phrase)
    if not haystack_norm or not phrase_norm:
        return False
    pattern = rf"(?<![a-z0-9_]){re.escape(phrase_norm)}(?![a-z0-9_])"
    return re.search(pattern, haystack_norm) is not None
