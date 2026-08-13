from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Protocol

from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)
from app.modules.llm_chat.application.services.rerankers import NoopReranker
from app.modules.llm_chat.domain.entities import RetrievedChunk, VectorCandidate
from app.modules.llm_chat.domain.ports.retrieval import RerankCandidate, Reranker

logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    """Chunks plus whether the retrieval infrastructure itself was healthy.

    Etapa 5, Block A/C: ``available`` distinguishes "the store worked but
    found nothing" (``chunks`` empty, ``available`` True → RetrievalStatus.
    NO_MATCH upstream) from "one or more retrieval components could not be
    reached" (``available`` False → RetrievalStatus.UNAVAILABLE). Neither
    ever implies a blanket prohibition on answering; the caller only reads
    this to choose the right technical status metadata.
    """

    chunks: tuple[RetrievedChunk, ...]
    available: bool

_SHORT_HEMATOLOGY_TERMS = {
    "chcm",
    "hcm",
    "hct",
    "mch",
    "mchc",
    "mcv",
    "mpv",
    "pcv",
    "plt",
    "rbc",
    "rdw",
    "vcm",
    "vpm",
    "wbc",
}
_UNKNOWN_SOURCE_ID = "Fuente no identificada"
_UNKNOWN_SOURCE_TITLE = "Tema no identificado"


class QueryEmbeddingClient(Protocol):
    def embed_query(self, text: str) -> list[float]: ...


class RetrievalVectorStore(Protocol):
    async def query(
        self,
        embedding: list[float],
        fetch_k: int,
        *,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorCandidate]: ...


class LexicalRetrievalStore(Protocol):
    async def query(
        self,
        query: str,
        fetch_k: int,
        *,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorCandidate]: ...


def _terms(value: str) -> set[str]:
    # Etapa 5, Block B: NFKD + dropping combining marks still normalizes
    # accents usefully (Spanish/French/Portuguese diacritics, Arabic
    # harakat), but the previous `[a-z0-9]+` regex then discarded every
    # non-Latin character outright — Cyrillic, Greek, CJK, Arabic script
    # all disappeared. `[^\W_]+` is Unicode-aware by default for `str`
    # patterns in Python's `re`, so it keeps any script's letters/digits.
    folded = unicodedata.normalize("NFKD", value.lower())
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char))
    return {
        term
        for term in re.findall(r"[^\W_]+", ascii_text)
        if len(term) >= 4 or term in _SHORT_HEMATOLOGY_TERMS
    }


def _normalized_text(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in folded if not unicodedata.combining(char))


def _clean_metadata_text(value: object, *, fallback: str) -> str:
    cleaned = " ".join(str(value or "").replace("\x00", "").split())
    if not cleaned or cleaned.casefold() in {"unknown", "none", "null", "nan"}:
        return fallback
    return cleaned


def _is_definition_question(value: str) -> bool:
    normalized = _normalized_text(value)
    return bool(
        re.search(
            r"\b(?:que\s+(?:es|son)|what\s+(?:is|are)|definicion|"
            r"funcion|para\s+que\s+sirve(?:n)?)\b",
            normalized,
        )
    )


_TERM_ALIASES = {
    "plaqueta": {"platelet"},
    "plaquetas": {"platelet", "platelets"},
    "plaquetaz": {"platelet", "platelets"},
    "plaquetario": {"platelet"},
    "plaquetarios": {"platelet"},
    "plaquetaria": {"platelet"},
    "plaquetarias": {"platelet"},
    "trombocito": {"platelet"},
    "trombocitos": {"platelet", "platelets"},
    "trombocitopenia": {"thrombocytopenia", "platelet"},
    "trombositopenia": {"thrombocytopenia", "platelet"},
    "trombocitopnia": {"thrombocytopenia", "platelet"},
    "plaquetopenia": {"thrombocytopenia", "platelet"},
    "trombocitosis": {"thrombocytosis", "platelet"},
    "hematocrito": {"hematocrit", "packed cell volume", "pcv"},
    "hemoglobina": {"hemoglobin"},
    "emoglobina": {"hemoglobin"},
    "emoglovina": {"hemoglobin"},
    "hemoglovina": {"hemoglobin"},
    "homoglobina": {"hemoglobin"},
    "hemoglobna": {"hemoglobin"},
    "eritrocito": {"erythrocyte", "red blood cell", "rbc"},
    "eritrocitos": {"erythrocyte", "erythrocytes", "red blood cells", "rbc"},
    "leucocito": {"leukocyte", "white blood cell", "wbc"},
    "leucocitos": {"leukocyte", "leukocytes", "white blood cells", "wbc"},
    "leuco": {"leukocyte", "leukocytes", "white blood cells", "wbc"},
    "leucos": {"leukocyte", "leukocytes", "white blood cells", "wbc"},
    "neutrofilo": {"neutrophil"},
    "neutrofilos": {"neutrophil", "neutrophils"},
    "neutropenia": {"neutropenia"},
    "neutrofilia": {"neutrophilia"},
    "linfocito": {"lymphocyte"},
    "linfocitos": {"lymphocyte", "lymphocytes"},
    "linfopenia": {"lymphopenia"},
    "linfocitosis": {"lymphocytosis"},
    "monocito": {"monocyte"},
    "monocitos": {"monocyte", "monocytes"},
    "eosinofilo": {"eosinophil"},
    "eosinofilos": {"eosinophil", "eosinophils"},
    "basofilo": {"basophil"},
    "basofilos": {"basophil", "basophils"},
    "reticulocito": {"reticulocyte"},
    "reticulocitos": {"reticulocyte", "reticulocytes"},
    "anemia": {"anemia", "anaemia"},
    "pancitopenia": {"pancytopenia"},
    "policitemia": {"polycythemia", "erythrocytosis"},
    "vcm": {"mcv", "mean corpuscular volume"},
    "hcm": {"mch", "mean corpuscular hemoglobin"},
    "chcm": {"mchc", "mean corpuscular hemoglobin concentration"},
    "vpm": {"mpv", "mean platelet volume"},
    "baja": {"low", "decreased"},
    "bajas": {"low", "decreased"},
    "bajo": {"low", "decreased"},
    "bajos": {"low", "decreased"},
    "alta": {"high", "increased"},
    "altas": {"high", "increased"},
    "alto": {"high", "increased"},
    "altos": {"high", "increased"},
    "sintoma": {"symptom", "sign"},
    "sintomas": {"symptoms", "signs"},
    "sangrado": {"bleeding", "hemorrhage"},
    "coagulacion": {"coagulation", "hemostasis"},
    "rango": {"range", "reference interval"},
    "rangos": {"ranges", "reference intervals"},
}

_MODIFIER_GROUPS = (
    (
        {"baja", "bajas", "bajo", "bajos"},
        {"baja", "bajas", "bajo", "bajos", "low", "decreased"},
    ),
    (
        {"alta", "altas", "alto", "altos"},
        {"alta", "altas", "alto", "altos", "high", "increased"},
    ),
    (
        {"sintoma", "sintomas"},
        {"sintoma", "sintomas", "symptom", "symptoms", "sign", "signs"},
    ),
    (
        {"rango", "rangos"},
        {"rango", "rangos", "range", "ranges", "reference", "interval", "intervals"},
    ),
)
_MODIFIER_KEYS = {term for triggers, _ in _MODIFIER_GROUPS for term in triggers}
_CONCEPT_KEYS = set(_TERM_ALIASES) - _MODIFIER_KEYS
_DISALLOWED_HEMATOLOGY_DOMAINS = {
    "endocrine",
    "inflammatory",
    "neurology",
    "neurologic",
    "renal",
    "hepatic",
    "reproductive",
}
_BAD_HEMATOLOGY_SOURCE_TERMS = {
    "adrenal",
    "blood banking",
    "cerebrospinal",
    "cryoprecipitate",
    "cryoprecipitado",
    "csf",
    "glucose",
    "hypothyroidism",
    "hyperthyroidism",
    "natriuretic",
    "ovarian",
    "ovary",
    "ovaries",
    "thoracocentesis",
    "thymus",
}
_TRANSFUSION_TERMS = {
    "transfusion",
    "transfusions",
    "transfusiones",
    "plasma",
    "concentrate",
    "cryoprecipitate",
    "cryoprecipitado",
}
_AUTHOR_ALIASES = {
    "schalm": {"schalm"},
    "duncan": {"duncan", "prasse"},
    "prasse": {"duncan", "prasse"},
    "cowell": {"cowell"},
}


def _expanded_query_terms(value: str) -> set[str]:
    terms = _terms(value)
    expanded = set(terms)
    for term in terms:
        expanded.update(_TERM_ALIASES.get(term, set()))
    if {"plaquetas", "bajas"} <= terms or "trombocitopenia" in terms:
        expanded.add("thrombocytopenia")
    if {"plaquetas", "altas"} <= terms or "trombocitosis" in terms:
        expanded.add("thrombocytosis")
    if {"globulos", "rojos"} <= terms:
        expanded.update({"erythrocyte", "erythrocytes", "red blood cells", "rbc"})
    if {"globulos", "blancos"} <= terms:
        expanded.update({"leukocyte", "leukocytes", "white blood cells", "wbc"})
    if terms & {"plaqueta", "plaquetas", "trombocito", "trombocitos"} and terms & {
        "sintoma",
        "sintomas",
    }:
        expanded.update(
            {
                "thrombocytopenia",
                "clinical",
                "signs",
                "bleeding",
                "petechiae",
                "bruising",
            }
        )
    if _is_definition_question(value):
        expanded.update({"definition", "function", "role"})
    return expanded


def _recognized_concept_terms(value: str) -> set[str]:
    query_terms = _terms(value)
    recognized: set[str] = set()
    for term in query_terms & _CONCEPT_KEYS:
        recognized.add(term)
        recognized.update(_TERM_ALIASES[term])
    if {"globulos", "rojos"} <= query_terms:
        recognized.update(
            {"globulos", "rojos", "erythrocyte", "erythrocytes", "red", "blood", "rbc"}
        )
    if {"globulos", "blancos"} <= query_terms:
        recognized.update(
            {"globulos", "blancos", "leukocyte", "leukocytes", "white", "blood", "wbc"}
        )
    return recognized


def _requested_modifier_groups(value: str) -> list[set[str]]:
    query_terms = _terms(value)
    groups = [
        candidates
        for triggers, candidates in _MODIFIER_GROUPS
        if query_terms & triggers
    ]
    if _is_definition_question(value):
        groups.append({"definition", "function", "role", "purpose"})
    return groups


def _is_domain_mismatch(query_terms: set[str], candidate: VectorCandidate) -> bool:
    domain = _normalized_text(str(candidate.metadata.get("domain") or ""))
    if domain and domain in _DISALLOWED_HEMATOLOGY_DOMAINS:
        return True

    searchable = _normalized_text(
        " ".join(
            [
                str(candidate.metadata.get("title") or ""),
                str(candidate.metadata.get("heading_path") or ""),
                str(candidate.metadata.get("source_path") or ""),
            ]
        )
    )
    source_terms = _terms(searchable)
    if source_terms & _BAD_HEMATOLOGY_SOURCE_TERMS or any(
        term in searchable for term in _BAD_HEMATOLOGY_SOURCE_TERMS
    ):
        return True
    if source_terms & _TRANSFUSION_TERMS and not (query_terms & _TRANSFUSION_TERMS):
        return True
    return False


def _requested_author_terms(value: str) -> set[str]:
    requested: set[str] = set()
    for term in _terms(value):
        requested.update(_AUTHOR_ALIASES.get(term, set()))
    return requested


def _matches_requested_author(requested: set[str], candidate: VectorCandidate) -> bool:
    if not requested:
        return True
    searchable = _normalized_text(
        " ".join(
            [
                str(candidate.metadata.get("source_id") or ""),
                str(candidate.metadata.get("title") or ""),
                str(candidate.metadata.get("source_path") or ""),
                str(candidate.metadata.get("heading_path") or ""),
            ]
        )
    )
    return all(term in searchable for term in requested)


def _expanded_query(value: str) -> str | None:
    original_terms = _terms(value)
    aliases = _expanded_query_terms(value) - original_terms
    if not aliases:
        return None
    return f"{value.strip()} {' '.join(sorted(aliases))}".strip()


def _metadata_authors(metadata: dict[str, object]) -> tuple[str, ...]:
    value = metadata.get("authors_json") or metadata.get("authors")
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = value.split(";")
    else:
        decoded = value
    if not isinstance(decoded, (list, tuple)):
        return ()
    return tuple(
        cleaned for item in decoded if (cleaned := " ".join(str(item or "").split()))
    )


def _metadata_page(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None


def _optional_metadata_text(value: object) -> str | None:
    cleaned = " ".join(str(value or "").replace("\x00", "").split())
    return cleaned or None


def _citation_allowed(metadata: dict[str, object]) -> bool:
    value = metadata.get("citation_allowed", True)
    if isinstance(value, str):
        return value.casefold() not in {"false", "0", "no"}
    return value is not False


def _generation_use_allowed(metadata: dict[str, object]) -> bool:
    """Eligibility for use as generation context (etapa 5, Block E).

    Distinct from ``_citation_allowed``: this is the only remaining hard
    exclusion in the ranking loop. In practice ``rag_eligible=False`` chunks
    are already excluded before reaching here (the store queries filter on
    it), so this mostly guards against metadata drift rather than doing the
    primary filtering — the primary filtering intentionally happens once,
    upstream, at the store query level (see chroma_store.py/bm25_store.py).
    """
    value = metadata.get("rag_eligible", True)
    if isinstance(value, str):
        return value.casefold() not in {"false", "0", "no"}
    return value is not False


_TECHNICAL_TITLE_RE = re.compile(
    r"(?:_pdf(?:_|$)|_pages?_\d|docling|\.(?:pdf|md|json|epub)$|[/\\])",
    re.IGNORECASE,
)


def _readable_title(metadata: dict[str, object]) -> str:
    for field in ("display_title", "bibliographic_title", "title"):
        title = _optional_metadata_text(metadata.get(field))
        if title and not _TECHNICAL_TITLE_RE.search(title):
            return title
    return _UNKNOWN_SOURCE_TITLE


class NeighborLookupStore(Protocol):
    async def get_by_ids(self, ids: list[str]) -> list[VectorCandidate]: ...


class RetrievalService:
    def __init__(
        self,
        *,
        embeddings: QueryEmbeddingClient,
        vector_store: RetrievalVectorStore,
        fetch_k: int,
        top_k: int,
        min_score: float,
        max_per_source: int,
        rrf_k: int,
        blocking_executor: BoundedBlockingExecutor,
        lexical_store: LexicalRetrievalStore | None = None,
        reranker: Reranker | None = None,
        query_max_variants: int = 4,
        neighbor_store: NeighborLookupStore | None = None,
        neighbor_expansion_max_chunks: int = 0,
    ) -> None:
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        if query_max_variants < 1:
            raise ValueError("query_max_variants must be positive")
        if neighbor_expansion_max_chunks < 0:
            raise ValueError("neighbor_expansion_max_chunks cannot be negative")
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.fetch_k = fetch_k
        self.top_k = top_k
        self.min_score = min_score
        self.max_per_source = max_per_source
        self.lexical_store = lexical_store
        self.rrf_k = rrf_k
        self.blocking_executor = blocking_executor
        self.reranker = reranker or NoopReranker()
        self.query_max_variants = query_max_variants
        self.neighbor_store = neighbor_store
        self.neighbor_expansion_max_chunks = neighbor_expansion_max_chunks

    async def retrieve(
        self,
        query: str,
        *,
        fetch_k: int | None = None,
        top_k: int | None = None,
        min_score: float | None = None,
        metadata_filter: dict[str, object] | None = None,
        query_variants: tuple[str, ...] | list[str] | None = None,
    ) -> RetrievalOutcome:
        started = time.perf_counter()
        effective_fetch_k = self.fetch_k if fetch_k is None else fetch_k
        effective_top_k = self.top_k if top_k is None else top_k
        effective_min_score = self.min_score if min_score is None else min_score
        variants: list[str] = []
        for value in [query, *(query_variants or ())]:
            cleaned = " ".join(value.split())
            if cleaned and cleaned not in variants:
                variants.append(cleaned)
        for value in list(variants):
            expanded_query = _expanded_query(value)
            if expanded_query and expanded_query not in variants:
                variants.append(expanded_query)
            if len(variants) >= self.query_max_variants:
                break
        variants = variants[: self.query_max_variants]

        embedding_started = time.perf_counter()
        embeddings = await self.blocking_executor.run(
            lambda: [
                self.embeddings.embed_query(query_variant)
                for query_variant in variants
            ]
        )
        embedding_ms = (time.perf_counter() - embedding_started) * 1000

        # Etapa 5, Block C: dense and lexical retrieval are independent
        # components. return_exceptions=True at both the per-variant and the
        # dense-vs-lexical level means one component's outage never cancels
        # the other — a degraded, partial result set is still usable
        # evidence, never a hard failure of the whole turn.
        async def dense_queries() -> tuple[list[list[VectorCandidate]], float, bool]:
            query_started = time.perf_counter()
            raw = await asyncio.gather(
                *(
                    self.vector_store.query(
                        embedding,
                        effective_fetch_k,
                        metadata_filter=metadata_filter,
                    )
                    for embedding in embeddings
                ),
                return_exceptions=True,
            )
            results: list[list[VectorCandidate]] = []
            succeeded = 0
            for item in raw:
                if isinstance(item, BaseException):
                    logger.warning(
                        "llm_chat.retrieval_dense_variant_failed code=%s",
                        type(item).__name__,
                    )
                    results.append([])
                    continue
                succeeded += 1
                results.append(item)
            return results, (time.perf_counter() - query_started) * 1000, bool(
                succeeded
            )

        async def lexical_queries() -> tuple[list[list[VectorCandidate]], float, bool]:
            if self.lexical_store is None:
                # Not configured is not a failure, but it contributes no
                # capacity either: it must not make an actually-failed dense
                # component look "available" in the OR below.
                return [], 0.0, False
            query_started = time.perf_counter()
            raw = await asyncio.gather(
                *(
                    self.lexical_store.query(
                        variant,
                        effective_fetch_k,
                        metadata_filter=metadata_filter,
                    )
                    for variant in variants
                ),
                return_exceptions=True,
            )
            results: list[list[VectorCandidate]] = []
            succeeded = 0
            for item in raw:
                if isinstance(item, BaseException):
                    logger.warning(
                        "llm_chat.retrieval_lexical_variant_failed code=%s",
                        type(item).__name__,
                    )
                    results.append([])
                    continue
                succeeded += 1
                results.append(item)
            return results, (time.perf_counter() - query_started) * 1000, bool(
                succeeded
            )

        (
            (dense_results, vector_query_ms, dense_available),
            (lexical_results, lexical_query_ms, lexical_available),
        ) = await asyncio.gather(
            dense_queries(), lexical_queries(), return_exceptions=False
        )
        # At least one component must have produced *something* runnable for
        # this to count as an available retrieval attempt. An empty result
        # from a healthy component is NO_MATCH (handled by the caller from
        # an empty ``chunks`` tuple with ``available=True``), not UNAVAILABLE.
        retrieval_available = dense_available or lexical_available

        candidates_by_id: dict[str, VectorCandidate] = {}
        dense_scores: dict[str, float] = {}
        lexical_scores: dict[str, float] = {}
        reciprocal_scores: dict[str, float] = {}

        def merge_ranked(
            rankings: list[list[VectorCandidate]],
            *,
            scores: dict[str, float],
        ) -> None:
            for ranking in rankings:
                for rank, candidate in enumerate(ranking, start=1):
                    existing = candidates_by_id.get(candidate.id)
                    if existing is None or (
                        len(candidate.metadata) > len(existing.metadata)
                        and candidate.text
                    ):
                        candidates_by_id[candidate.id] = candidate
                    scores[candidate.id] = max(
                        scores.get(candidate.id, 0.0), candidate.semantic_score
                    )
                    reciprocal_scores[candidate.id] = reciprocal_scores.get(
                        candidate.id, 0.0
                    ) + 1.0 / (self.rrf_k + rank)

        merge_ranked(dense_results, scores=dense_scores)
        merge_ranked(lexical_results, scores=lexical_scores)
        candidates = list(candidates_by_id.values())
        max_reciprocal = max(reciprocal_scores.values(), default=1.0)
        selection_started = time.perf_counter()
        query_terms = _expanded_query_terms(query)
        concept_terms = _recognized_concept_terms(query)
        modifier_groups = _requested_modifier_groups(query)
        requested_authors = _requested_author_terms(query)
        # Etapa 5, Block B: candidate eligibility (this loop's only
        # `continue`s now) must never depend on lexical/concept overlap —
        # only on things independent of phrasing/language: an explicit
        # author request, or a chunk this turn is not allowed to use for
        # generation at all. A dense-only semantic match in a language with
        # no entry in the Spanish/English alias dictionary below must
        # survive; the dictionary only ever adds a *bonus*.
        ranked: list[tuple[float, float, float, VectorCandidate]] = []
        for candidate in candidates:
            if not _generation_use_allowed(candidate.metadata):
                continue
            if not _matches_requested_author(requested_authors, candidate):
                continue
            searchable = " ".join(
                [
                    candidate.text,
                    str(candidate.metadata.get("heading_path") or ""),
                    str(candidate.metadata.get("section") or ""),
                    str(candidate.metadata.get("bibliographic_title") or ""),
                    str(candidate.metadata.get("title") or ""),
                ]
            )
            searchable_terms = _terms(searchable)
            concept_matches = concept_terms & searchable_terms
            lexical = 0.0
            if query_terms:
                lexical = min(
                    1.0,
                    len(query_terms & searchable_terms) / min(len(query_terms), 4),
                )
            modifier_coverage = 0.0
            if modifier_groups:
                modifier_coverage = sum(
                    bool(group & searchable_terms) for group in modifier_groups
                ) / len(modifier_groups)
            concept_bonus = 0.12 if concept_matches else 0.0
            domain_penalty = (
                0.20
                if concept_terms and _is_domain_mismatch(query_terms, candidate)
                else 0.0
            )
            # Etapa 5, Block C: the *quality gate* (min_score) is decided
            # purely from the retrievers' own absolute similarity scores —
            # never from lexical/concept overlap — so a strong cross-lingual
            # dense match can never be rejected for lacking literal overlap
            # with the (Spanish/English-only) alias dictionary.
            dense_score = dense_scores.get(candidate.id, 0.0)
            sparse_score = lexical_scores.get(candidate.id, 0.0)
            quality_score = max(dense_score, sparse_score)
            if quality_score < effective_min_score:
                continue
            # RRF is the primary *ordering* signal among qualified
            # candidates (previously a 5% decorative term dominated by an
            # ad hoc dense/sparse blend). Lexical/concept/domain signals are
            # bounded secondary adjustments layered on top, never able to
            # promote a candidate that did not clear the quality gate above,
            # nor to fully invert the fused rank order on their own.
            rrf_score = reciprocal_scores.get(candidate.id, 0.0) / max_reciprocal
            rank_score = max(
                0.0,
                min(
                    1.0,
                    rrf_score
                    + concept_bonus
                    + 0.10 * modifier_coverage
                    + 0.08 * lexical
                    - domain_penalty,
                ),
            )
            ranked.append((rank_score, quality_score, rrf_score, candidate))
        ranked.sort(key=lambda item: (-item[0], -item[1], item[3].id))

        reranking_started = time.perf_counter()
        reranked = await self.reranker.rerank(
            query,
            tuple(
                RerankCandidate(
                    id=candidate.id,
                    text=candidate.text,
                    retrieval_score=rank_score,
                    metadata=dict(candidate.metadata),
                )
                for rank_score, _quality, _rrf_score, candidate in ranked
            ),
        )
        reranking_ms = (time.perf_counter() - reranking_started) * 1000
        expected_ids = {candidate.id for *_scores, candidate in ranked}
        reranked_ids = [result.candidate_id for result in reranked]
        if set(reranked_ids) != expected_ids or len(reranked_ids) != len(expected_ids):
            raise ValueError("Reranker must return every candidate exactly once")
        if any(not math.isfinite(result.score) for result in reranked):
            raise ValueError("Reranker returned a non-finite score")
        ranked_by_id = {
            candidate.id: (quality_score, candidate)
            for _rank, quality_score, _rrf, candidate in ranked
        }
        ranked = [
            (
                max(0.0, min(1.0, result.score)),
                ranked_by_id[result.candidate_id][0],
                0.0,
                ranked_by_id[result.candidate_id][1],
            )
            for result in reranked
        ]
        ranked.sort(key=lambda item: (-item[0], -item[1], item[3].id))

        selected: list[RetrievedChunk] = []
        selected_ids: set[str] = set()
        source_counts: dict[str, int] = {}
        neighbor_ids_by_anchor: dict[str, list[str]] = {}
        for score, quality_score, _rrf, candidate in ranked:
            source_id = _clean_metadata_text(
                candidate.metadata.get("canonical_source_id")
                or candidate.metadata.get("source_id"),
                fallback=_UNKNOWN_SOURCE_ID,
            )
            if source_counts.get(source_id, 0) >= self.max_per_source:
                continue
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            selected.append(
                self._build_retrieved_chunk(
                    candidate, score=max(score, quality_score), source_id=source_id
                )
            )
            selected_ids.add(candidate.id)
            if self.neighbor_store is not None and self.neighbor_expansion_max_chunks:
                neighbor_ids_by_anchor[candidate.id] = [
                    str(value)
                    for field in ("previous_chunk_id", "next_chunk_id")
                    if (value := candidate.metadata.get(field))
                ][: self.neighbor_expansion_max_chunks]
            if len(selected) >= effective_top_k:
                break

        selected = await self._expand_neighbors(
            selected,
            selected_ids=selected_ids,
            neighbor_ids_by_anchor=neighbor_ids_by_anchor,
            source_counts=source_counts,
        )

        logger.info(
            "llm_chat.retrieval %s",
            json.dumps(
                {
                    "attempts": len(variants),
                    "candidate_count": len(candidates),
                    "dense_candidate_count": len(dense_scores),
                    "dense_available": dense_available,
                    "embedding_ms": round(embedding_ms, 2),
                    "fetch_k": effective_fetch_k,
                    "min_score": effective_min_score,
                    "lexical_candidate_count": len(lexical_scores),
                    "lexical_available": lexical_available,
                    "lexical_query_ms": round(lexical_query_ms, 2),
                    "retrieval_strategy": (
                        "dense_bm25_rrf" if self.lexical_store else "dense_rrf"
                    ),
                    "reranker_model": self.reranker.model_name,
                    "reranking_ms": round(reranking_ms, 2),
                    "selected_count": len(selected),
                    "selection_ms": round(
                        (time.perf_counter() - selection_started) * 1000, 2
                    ),
                    "top_k": effective_top_k,
                    "top_score": selected[0].score if selected else None,
                    "total_ms": round((time.perf_counter() - started) * 1000, 2),
                    "vector_query_ms": round(vector_query_ms, 2),
                },
                sort_keys=True,
            ),
        )
        return RetrievalOutcome(chunks=tuple(selected), available=retrieval_available)

    @staticmethod
    def _build_retrieved_chunk(
        candidate: VectorCandidate,
        *,
        score: float,
        source_id: str,
    ) -> RetrievedChunk:
        title = _readable_title(candidate.metadata)
        page_start = _metadata_page(candidate.metadata.get("page_start"))
        page_end = _metadata_page(candidate.metadata.get("page_end"))
        if page_start and page_end and page_start > page_end:
            page_start = page_end = None
        section = _optional_metadata_text(
            candidate.metadata.get("section") or candidate.metadata.get("heading_path")
        )
        return RetrievedChunk(
            id=candidate.id,
            text=candidate.text,
            source_id=source_id,
            title=title,
            heading_path=_clean_metadata_text(section, fallback=title),
            # Paths remain retrieval-internal and are never propagated to
            # the public/persisted source representation.
            source_path="",
            score=round(max(0.0, min(1.0, score)), 4),
            authors=_metadata_authors(candidate.metadata),
            edition=_optional_metadata_text(candidate.metadata.get("edition")),
            chapter=_optional_metadata_text(candidate.metadata.get("chapter")),
            section=section,
            page_start=page_start,
            page_end=page_end,
            source_type=_optional_metadata_text(candidate.metadata.get("source_type"))
            or "book",
            # Etapa 5, Block E: generation eligibility and public citation
            # permission are independent. A chunk without citation_allowed
            # can still ground the answer; it is only excluded from
            # project_citation_sources() later, never from this context set.
            generation_use_allowed=True,
            citation_allowed=_citation_allowed(candidate.metadata),
            source_language=_optional_metadata_text(candidate.metadata.get("language")),
        )

    async def _expand_neighbors(
        self,
        selected: list[RetrievedChunk],
        *,
        selected_ids: set[str],
        neighbor_ids_by_anchor: dict[str, list[str]],
        source_counts: dict[str, int],
    ) -> list[RetrievedChunk]:
        """Bounded, same-document neighbor expansion (etapa 5, Block F).

        Optional and off by default (``RAG_NEIGHBOR_EXPANSION_ENABLED``).
        Neighbor ids come only from the anchor chunk's own stored
        ``previous_chunk_id``/``next_chunk_id`` (markdown_chunker.py), so
        this can never cross into a different document or section by
        construction. Appended after the ranked selection, never reordering
        it; deduplicated against chunks already selected and against the
        per-source cap that already governs the primary selection.
        """
        if self.neighbor_store is None or not neighbor_ids_by_anchor:
            return selected
        requested_ids = [
            chunk_id
            for ids in neighbor_ids_by_anchor.values()
            for chunk_id in ids
            if chunk_id not in selected_ids
        ]
        if not requested_ids:
            return selected
        try:
            neighbors = await self.neighbor_store.get_by_ids(
                list(dict.fromkeys(requested_ids))
            )
        except Exception as exc:
            # Neighbor expansion is a continuity aid, not a requirement: a
            # lookup failure degrades to the unexpanded selection rather
            # than failing the whole turn.
            logger.warning(
                "llm_chat.retrieval_neighbor_expansion_failed code=%s",
                type(exc).__name__,
            )
            return selected
        expanded = list(selected)
        seen_ids = set(selected_ids)
        for neighbor in neighbors:
            if neighbor.id in seen_ids or not _generation_use_allowed(
                neighbor.metadata
            ):
                continue
            source_id = _clean_metadata_text(
                neighbor.metadata.get("canonical_source_id")
                or neighbor.metadata.get("source_id"),
                fallback=_UNKNOWN_SOURCE_ID,
            )
            if source_counts.get(source_id, 0) >= self.max_per_source:
                continue
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            seen_ids.add(neighbor.id)
            expanded.append(
                self._build_retrieved_chunk(neighbor, score=0.0, source_id=source_id)
            )
        return expanded
