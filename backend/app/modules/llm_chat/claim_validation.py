"""Validacion tipada de claims para respuestas grounded."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .utils import normalize_for_match, tokenize_retrieval

_STOPWORDS = {
    "acerca",
    "ademas",
    "ahora",
    "algo",
    "algun",
    "alguna",
    "algunas",
    "algunos",
    "aqui",
    "asi",
    "cada",
    "como",
    "con",
    "contra",
    "cual",
    "cuales",
    "cuando",
    "de",
    "del",
    "desde",
    "donde",
    "dos",
    "el",
    "ella",
    "ellas",
    "ellos",
    "en",
    "entre",
    "era",
    "es",
    "esa",
    "ese",
    "eso",
    "esta",
    "este",
    "esto",
    "estos",
    "forma",
    "fue",
    "ha",
    "hay",
    "incluye",
    "indica",
    "indican",
    "la",
    "las",
    "libro",
    "lo",
    "los",
    "mas",
    "menos",
    "mismo",
    "muestran",
    "muy",
    "no",
    "otra",
    "otro",
    "para",
    "pero",
    "por",
    "porque",
    "puede",
    "que",
    "quien",
    "se",
    "segun",
    "si",
    "sin",
    "sobre",
    "solo",
    "tambien",
    "tema",
    "tiene",
    "todo",
    "una",
    "uno",
    "unos",
    "y",
    "extract",
    "extracts",
}

_GENERIC_REPLY_PATTERNS = (
    "la explicacion es orientativa",
    "no sustituye la evaluacion",
    "consulta con tu veterinario",
    "consultar a un veterinario",
    "no puedo confirmar diagnosticos",
    "no puedo responder preguntas de medicacion",
    "no puedo indicar tratamientos",
    "no puedo indicar dosis",
    "puedo ayudarte a entender",
    "si quieres",
)

_TERM_EQUIVALENTS = {
    "agregacion": "aggregation",
    "agregado": "aggregate",
    "agregados": "aggregate",
    "blanca": "white",
    "caballo": "horse",
    "caballos": "horse",
    "calidad": "quality",
    "causa": "cause",
    "causan": "cause",
    "causar": "cause",
    "canina": "canine",
    "canino": "canine",
    "caninos": "canine",
    "control": "control",
    "corticoide": "corticosteroid",
    "corticoides": "corticosteroid",
    "corticosteroide": "corticosteroid",
    "corticosteroides": "corticosteroid",
    "eosinofilia": "eosinophilia",
    "equino": "equine",
    "equinos": "equine",
    "estres": "stress",
    "stresses": "stress",
    "felina": "feline",
    "felino": "feline",
    "felinos": "feline",
    "frotis": "smear",
    "gato": "cat",
    "gatos": "cat",
    "glucocorticoide": "corticosteroid",
    "glucocorticoides": "corticosteroid",
    "leucocitaria": "leukocyte",
    "leucocitario": "leukocyte",
    "leucocitos": "leukocyte",
    "leucopenia": "leukopenia",
    "leucograma": "leukogram",
    "linfopenia": "lymphopenia",
    "linfocito": "lymphocyte",
    "linfocitos": "lymphocyte",
    "madura": "mature",
    "maduro": "mature",
    "monocitosis": "monocytosis",
    "neutrofilo": "neutrophil",
    "neutrofilos": "neutrophil",
    "neutrofilia": "neutrophilia",
    "patron": "pattern",
    "perro": "dog",
    "perros": "dog",
    "plaqueta": "platelet",
    "plaquetas": "platelet",
    "plaquetaria": "platelet",
    "plaquetario": "platelet",
    "plaquetarios": "platelet",
    "plaquetopenia": "thrombocytopenia",
    "plt": "platelet",
    "lym": "lymphocyte",
    "neu": "neutrophil",
    "wbc": "leukocyte",
    "respuesta": "response",
    "rumiante": "ruminant",
    "rumiantes": "ruminant",
    "serie": "series",
    "thrombocytopenia": "thrombocytopenia",
    "trombocitopenia": "thrombocytopenia",
    "thrombocytosis": "thrombocytosis",
    "trombocitosis": "thrombocytosis",
    "transitoria": "transient",
    "transitorio": "transient",
}


_ENGLISH_FUNCTION_WORDS = frozenset(
    {
        "the",
        "and",
        "of",
        "in",
        "to",
        "is",
        "are",
        "with",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "can",
        "has",
        "have",
        "was",
        "were",
        "be",
        "by",
        "for",
        "from",
        "on",
        "at",
        "but",
        "or",
        "not",
        "you",
        "your",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "an",
        "as",
        "if",
        "then",
        "than",
        "when",
        "while",
        "such",
        "any",
        "all",
        "also",
        "more",
        "most",
        "less",
        "their",
        "they",
        "them",
        "we",
        "our",
        "us",
        "his",
        "her",
        "which",
        "who",
        "what",
        "where",
        "how",
        "below",
        "above",
        "between",
        "during",
        "after",
        "before",
        "often",
        "always",
        "never",
        "either",
        "both",
        "much",
        "many",
        "few",
        "including",
        "include",
        "due",
        "however",
        "although",
        "even",
        "refers",
        "called",
        "known",
        "found",
        "used",
        "includes",
        "contains",
        "occurs",
        "results",
        "shows",
        "indicates",
        "reported",
        "described",
        "associated",
        "characterized",
        "defined",
        "involved",
        "considered",
        "increased",
        "decreased",
        "enhanced",
        "suggested",
        # English content words that almost never appear in Spanish veterinary writing
        # but show up frequently in OCR fragments from English textbooks.
        "platelet",
        "platelets",
        "blood",
        "count",
        "counts",
        "dogs",
        "cats",
        "feline",
        "canine",
        "thrombocytopenia",
        "lymphopenia",
        "neutrophil",
        "weight",
        "drug",
        "drugs",
    }
)


def contains_english_passage(text: str) -> bool:
    """Detecta texto narrativo en ingles que el LLM olvido traducir.

    Heuristica:
    - 3 o mas palabras inglesas funcionales consecutivas;
    - O ratio de palabras inglesas >30% en textos de >=8 tokens.
    Pensado para parsed.answer, no para claims tecnicas que pueden incluir
    siglas como MCHC, PCV o WBC sin ser ingles narrativo.
    """
    if not text or not text.strip():
        return False
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return False
    consecutive = 0
    for token in tokens:
        if token in _ENGLISH_FUNCTION_WORDS:
            consecutive += 1
            if consecutive >= 3:
                return True
        else:
            consecutive = 0
    if len(tokens) >= 8:
        eng_count = sum(1 for token in tokens if token in _ENGLISH_FUNCTION_WORDS)
        if eng_count / len(tokens) >= 0.25:
            return True
    return False


# Common Spanish function words, ascii-folded/lowercased to match
# tokenize_retrieval's normalization (accents stripped: "esta" covers both
# "esta" and "está", "mas" covers both "mas" and "más").
_SPANISH_FUNCTION_WORDS = frozenset(
    {
        "que", "de", "la", "el", "los", "las", "es", "son", "un", "una",
        "unos", "unas", "con", "para", "por", "no", "se", "su", "sus", "en",
        "del", "al", "y", "o", "pero", "como", "cuando", "donde", "porque",
        "tambien", "muy", "mas", "este", "esta", "estos", "estas", "ese",
        "esa", "esos", "esas", "puede", "pueden", "debe", "deben", "tiene",
        "tienen", "estan", "fue", "ser", "hay", "sin", "entre", "sobre",
        "hasta", "desde", "si", "lo", "le", "les", "nos", "vos", "ni", "ya",
        "asi", "cual", "quien", "cada", "otro", "otra", "todo", "toda",
        "todos", "todas", "sea", "sido", "siendo",
    }
)


def contains_non_spanish_passage(text: str) -> bool:
    """Detect visible prose that is not predominantly Spanish.

    A positive Spanish-density check rather than a per-foreign-language
    blacklist: it does not need to enumerate every language a model might
    drift into (English, French, German, Portuguese, or anything else) to
    reject it, only recognize enough of the Spanish it is contractually
    required to produce. Complements ``contains_english_passage`` above,
    which stays English-specific for its other callers (local_model.py's
    generation-time heuristics) and is not touched here. Thresholds mirror
    that function's: skip texts too short to be meaningful (<8 significant
    tokens), and accept a wide margin below genuine Spanish's natural
    article/preposition density so short or jargon-heavy authorized answers
    are never penalized.
    """
    if not text or not text.strip():
        return False
    tokens = [
        token for token in tokenize_retrieval(text) if len(token) >= 2 and token.isalpha()
    ]
    if len(tokens) < 8:
        return False
    spanish_count = sum(1 for token in tokens if token in _SPANISH_FUNCTION_WORDS)
    return (spanish_count / len(tokens)) < 0.10


@dataclass(frozen=True)
class UnsupportedClaimDetail:
    claim: str
    kind: str
    reason: str


def _claim_units(text: str) -> list[str]:
    units: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", raw_line).strip()
        if not line:
            continue
        pieces = [
            piece.strip() for piece in re.split(r"(?<=[.!?])\s+", line) if piece.strip()
        ]
        units.extend(pieces or [line])
    return units


def _significant_terms(text: str) -> set[str]:
    return {
        _TERM_EQUIVALENTS.get(token, token)
        for token in tokenize_retrieval(text)
        if len(token) >= 4 and token not in _STOPWORDS
    }


def _is_generic_claim(claim: str) -> bool:
    lowered = claim.strip().lower()
    if not lowered:
        return True
    return any(pattern in lowered for pattern in _GENERIC_REPLY_PATTERNS)


def _case_fact_texts(case_facts: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for fact in case_facts:
        pieces = [
            str(fact.get("label") or ""),
            str(fact.get("detail") or ""),
            str(fact.get("value") or ""),
            str(fact.get("unit") or ""),
            str(fact.get("status") or ""),
        ]
        text = " ".join(piece for piece in pieces if piece).strip()
        if text:
            texts.append(text)
    return texts


def _source_texts(sources: list[dict[str, Any]]) -> list[str]:
    texts: list[str] = []
    for source in sources:
        text = str(source.get("clean_text") or source.get("text") or "").strip()
        if text:
            texts.append(text)
    return texts


def _evidence_term_sets(evidence_texts: list[str]) -> list[set[str]]:
    sets: list[set[str]] = []
    for evidence in evidence_texts:
        evidence_terms = _significant_terms(evidence)
        if evidence_terms:
            sets.append(evidence_terms)
    if len(sets) > 1:
        sets.append(set().union(*sets))
    return sets


def _text_supports_claim(
    claim: str, evidence_texts: list[str], *, strict_numbers: bool
) -> bool:
    claim_terms = _significant_terms(claim)
    if len(claim_terms) < 2:
        return True

    claim_tokens = set(tokenize_retrieval(claim))
    claim_numbers = {
        token for token in claim_tokens if token.replace(".", "", 1).isdigit()
    }
    needed_overlap = (
        2 if len(claim_terms) <= 4 else min(4, max(2, len(claim_terms) // 2))
    )

    evidence_term_sets = _evidence_term_sets(evidence_texts)
    evidence_number_sets = [
        {
            token
            for token in tokenize_retrieval(evidence)
            if token.replace(".", "", 1).isdigit()
        }
        for evidence in evidence_texts
    ]
    if len(evidence_number_sets) > 1:
        evidence_number_sets.append(set().union(*evidence_number_sets))

    for index, evidence_terms in enumerate(evidence_term_sets):
        overlap = claim_terms.intersection(evidence_terms)
        if len(overlap) < needed_overlap:
            continue
        evidence_numbers = (
            evidence_number_sets[min(index, len(evidence_number_sets) - 1)]
            if evidence_number_sets
            else set()
        )
        if (
            strict_numbers
            and claim_numbers
            and not claim_numbers.intersection(evidence_numbers)
        ):
            continue
        return True
    return False


def _claim_kind(claim: str) -> str:
    normalized = normalize_for_match(claim)
    if re.search(r"\b\d+(?:\.\d+)?\b", normalized):
        return "numeric"
    if any(
        term in normalized for term in ("frotis", "agregad", "interferencia", "calidad")
    ):
        return "qc"
    if any(
        term in normalized
        for term in ("urgente", "prioritaria", "revision veterinaria", "critico")
    ):
        return "urgency"
    if any(
        term in normalized
        for term in (
            "patron",
            "leucograma",
            "anemia",
            "hemolisis",
            "policitemia",
            "inflamatorio",
        )
    ):
        return "pattern"
    return "literature"


def unsupported_claims(
    *,
    text: str,
    context: dict[str, Any],
    case_facts: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    support_snippets: list[str] | None = None,
) -> list[str]:
    return [
        detail.claim
        for detail in unsupported_claim_details(
            text=text,
            context=context,
            case_facts=case_facts,
            sources=sources,
            support_snippets=support_snippets,
        )
    ]


def unsupported_claim_details(
    *,
    text: str,
    context: dict[str, Any],
    case_facts: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    support_snippets: list[str] | None = None,
) -> list[UnsupportedClaimDetail]:
    """Devuelve claims no soportados por evidencia del caso o del corpus."""
    case_fact_texts = _case_fact_texts(case_facts)
    source_texts = _source_texts(sources)
    snippet_texts = [
        str(snippet).strip()
        for snippet in (support_snippets or [])
        if str(snippet).strip()
    ]
    warnings_texts = [str(item) for item in context.get("warnings", []) if item]
    qc_texts = [str(label) for label in context.get("qc_labels", [])]
    label_texts = [str(label) for label in context.get("active_labels", [])]

    unsupported: list[UnsupportedClaimDetail] = []
    for claim in _claim_units(text):
        if _is_generic_claim(claim):
            continue

        kind = _claim_kind(claim)
        if kind == "numeric":
            if not _text_supports_claim(claim, case_fact_texts, strict_numbers=True):
                unsupported.append(
                    UnsupportedClaimDetail(
                        claim=claim, kind=kind, reason="numeric_not_supported"
                    )
                )
            continue

        if kind == "pattern":
            if not _text_supports_claim(
                claim,
                case_fact_texts + label_texts + source_texts + snippet_texts,
                strict_numbers=False,
            ):
                unsupported.append(
                    UnsupportedClaimDetail(
                        claim=claim, kind=kind, reason="pattern_not_supported"
                    )
                )
            continue

        if kind == "qc":
            if not _text_supports_claim(
                claim,
                case_fact_texts + qc_texts + warnings_texts + snippet_texts,
                strict_numbers=False,
            ):
                unsupported.append(
                    UnsupportedClaimDetail(
                        claim=claim, kind=kind, reason="qc_not_supported"
                    )
                )
            continue

        if kind == "urgency":
            if not _text_supports_claim(
                claim,
                case_fact_texts + warnings_texts + snippet_texts,
                strict_numbers=False,
            ):
                unsupported.append(
                    UnsupportedClaimDetail(
                        claim=claim, kind=kind, reason="urgency_not_supported"
                    )
                )
            continue

        if not _text_supports_claim(
            claim,
            source_texts + snippet_texts + case_fact_texts,
            strict_numbers=False,
        ):
            unsupported.append(
                UnsupportedClaimDetail(
                    claim=claim, kind=kind, reason="literature_not_supported"
                )
            )

    return unsupported
