from __future__ import annotations

import asyncio
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)
from app.modules.llm_chat.domain.entities import VectorCandidate
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable


def tokenize(value: str) -> list[str]:
    # Etapa 5, Block B: keep Unicode letters/digits from any script instead
    # of discarding everything outside [a-z0-9] (see retrieval_service._terms
    # for the identical reasoning).
    folded = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char))
    return [term for term in re.findall(r"[^\W_]+", ascii_text) if len(term) > 1]


@dataclass(frozen=True, slots=True)
class BM25Document:
    id: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class BM25IndexStatus:
    document_count: int
    corpus_revision: str | None
    index_fingerprint: str | None


class BM25Index:
    """Small dependency-free BM25 index suitable for the curated corpus."""

    def __init__(
        self,
        documents: Iterable[BM25Document],
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self._term_frequencies: list[Counter[str]] = []
        self._lengths: list[int] = []
        document_frequency: Counter[str] = Counter()
        for document in self.documents:
            metadata_text = " ".join(
                str(document.metadata.get(field) or "")
                for field in (
                    "bibliographic_title",
                    "title",
                    "chapter",
                    "section",
                    "heading_path",
                )
            )
            # Bibliographic/heading terms are repeated once to give exact lexical
            # matches a modest, deterministic field boost.
            terms = tokenize(f"{metadata_text} {metadata_text} {document.text}")
            frequencies = Counter(terms)
            self._term_frequencies.append(frequencies)
            self._lengths.append(len(terms))
            document_frequency.update(frequencies.keys())
        self._average_length = (
            sum(self._lengths) / len(self._lengths) if self._lengths else 0.0
        )
        total = len(self.documents)
        self._idf = {
            term: math.log(1.0 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def query(
        self,
        query: str,
        *,
        limit: int,
        metadata_filter: dict[str, object] | None = None,
        allowed_statuses: tuple[str, ...] = ("approved", "test"),
        allowed_species: tuple[str, ...] = ("canine", "canine_feline"),
        allowed_domains: tuple[str, ...] = (
            "hematology",
            "clinical_pathology",
            "coagulation",
            "sample_collection",
            "laboratory_methods",
            "cytology",
        ),
    ) -> list[VectorCandidate]:
        query_terms = Counter(tokenize(query))
        if not query_terms or not self.documents:
            return []
        scored: list[tuple[float, BM25Document]] = []
        average = self._average_length or 1.0
        for index, document in enumerate(self.documents):
            metadata = document.metadata
            if str(metadata.get("status") or "") not in allowed_statuses:
                continue
            if str(metadata.get("species") or "") not in allowed_species:
                continue
            if str(metadata.get("domain") or "") not in allowed_domains:
                continue
            if metadata.get("rag_eligible") is False:
                continue
            if metadata_filter and not _matches_filter(metadata, metadata_filter):
                continue
            frequencies = self._term_frequencies[index]
            length = self._lengths[index]
            score = 0.0
            for term, query_frequency in query_terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1.0 - self.b + self.b * length / average
                )
                score += (
                    self._idf.get(term, 0.0)
                    * (frequency * (self.k1 + 1.0) / denominator)
                    * min(query_frequency, 2)
                )
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        selected = scored[:limit]
        # Etapa 5, Block C: dividing every score by the top score forced the
        # #1 result to always normalize to exactly 1.0 regardless of how
        # strong or weak the actual match was, so a min_score threshold on
        # the fused result lost all meaning (a lone mediocre hit in an
        # otherwise empty result set still reported "1.0"). A saturating
        # transform (score / (score + k)) keeps 0..1 bounds and monotonic
        # ordering but preserves *relative magnitude*: k is the batch's own
        # average score, so "average quality for this query" maps to ~0.5
        # instead of being silently thrown away.
        batch_average = (
            sum(score for score, _ in selected) / len(selected) if selected else 0.0
        )
        saturation_k = max(batch_average, 1e-6)
        return [
            VectorCandidate(
                id=document.id,
                text=document.text,
                metadata=dict(document.metadata),
                semantic_score=max(
                    0.0, min(1.0, score / (score + saturation_k))
                ),
            )
            for score, document in selected
        ]


class ChromaBM25Store:
    """Lazily builds one reusable sparse index from the Chroma collection."""

    def __init__(
        self,
        collection: Any,
        *,
        allowed_statuses: tuple[str, ...] = ("approved", "test"),
        expected_corpus_revision: str | None = None,
        expected_index_fingerprint: str | None = None,
        strict_revision: bool = False,
        # Etapa 5, Block C/F: these defaults exist only as a safety net for
        # callers that do not pass a value; composition.py always supplies
        # the single configured allowlist (RAG_ALLOWED_SPECIES/_DOMAINS) so
        # this store and ChromaRetrievalStore never drift apart.
        allowed_species: tuple[str, ...] = ("canine", "canine_feline"),
        allowed_domains: tuple[str, ...] = (
            "hematology",
            "clinical_pathology",
            "coagulation",
            "sample_collection",
            "laboratory_methods",
            "cytology",
        ),
        blocking_executor: BoundedBlockingExecutor,
    ) -> None:
        self.collection = collection
        self.allowed_statuses = allowed_statuses
        self.expected_corpus_revision = expected_corpus_revision
        self.expected_index_fingerprint = expected_index_fingerprint
        self.strict_revision = strict_revision
        self.allowed_species = allowed_species
        self.allowed_domains = allowed_domains
        self._index: BM25Index | None = None
        self._status: BM25IndexStatus | None = None
        self._lock = asyncio.Lock()
        self.blocking_executor = blocking_executor

    async def query(
        self,
        query: str,
        fetch_k: int,
        *,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorCandidate]:
        try:
            index = await self._get_index()
            return await self.blocking_executor.run(
                index.query,
                query,
                limit=fetch_k,
                metadata_filter=metadata_filter,
                allowed_statuses=self.allowed_statuses,
                allowed_species=self.allowed_species,
                allowed_domains=self.allowed_domains,
            )
        except ChatRuntimeUnavailable:
            raise
        except Exception as exc:
            raise ChatRuntimeUnavailable("BM25 retrieval failed") from exc

    async def refresh(
        self,
        *,
        expected_index_fingerprint: str | None = None,
    ) -> BM25IndexStatus:
        async with self._lock:
            target_fingerprint = (
                expected_index_fingerprint or self.expected_index_fingerprint
            )
            index, status = await self._load_index(
                expected_index_fingerprint=target_fingerprint
            )
            # The fully-built immutable index is swapped only after validation.
            self._index = index
            self._status = status
            self.expected_index_fingerprint = target_fingerprint
            return status

    async def _get_index(self) -> BM25Index:
        if self._index is not None:
            return self._index
        async with self._lock:
            if self._index is None:
                self._index, self._status = await self._load_index(
                    expected_index_fingerprint=self.expected_index_fingerprint
                )
        return self._index

    async def _load_index(
        self,
        *,
        expected_index_fingerprint: str | None,
    ) -> tuple[BM25Index, BM25IndexStatus]:
        result = await self.collection.get(include=["documents", "metadatas"])
        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        rows: list[BM25Document] = []
        mismatched_revisions: set[str] = set()
        missing_revision = False
        fingerprints: set[str] = set()
        missing_fingerprint = False
        for chunk_id, text, metadata in zip(ids, documents, metadatas, strict=True):
            values = dict(metadata or {})
            revision = str(values.get("corpus_revision") or "")
            if self.expected_corpus_revision:
                if not revision:
                    missing_revision = True
                elif revision != self.expected_corpus_revision:
                    mismatched_revisions.add(revision)
            fingerprint = str(values.get("index_fingerprint") or "")
            if fingerprint:
                fingerprints.add(fingerprint)
            else:
                missing_fingerprint = True
            rows.append(
                BM25Document(id=str(chunk_id), text=str(text or ""), metadata=values)
            )
        if self.strict_revision and (
            mismatched_revisions or (missing_revision and rows)
        ):
            raise ChatRuntimeUnavailable("rag_bm25_corpus_revision_mismatch")
        if len(fingerprints) > 1:
            raise ChatRuntimeUnavailable("rag_bm25_mixed_index_fingerprints")
        if expected_index_fingerprint and (
            fingerprints != {expected_index_fingerprint}
            or (missing_fingerprint and rows)
        ):
            raise ChatRuntimeUnavailable("rag_bm25_index_fingerprint_mismatch")
        index = await self.blocking_executor.run(BM25Index, rows)
        status = BM25IndexStatus(
            document_count=len(rows),
            corpus_revision=(
                self.expected_corpus_revision
                or next(
                    iter(
                        {
                            str(row.metadata.get("corpus_revision"))
                            for row in rows
                            if row.metadata.get("corpus_revision")
                        }
                    ),
                    None,
                )
            ),
            index_fingerprint=next(iter(fingerprints), None),
        )
        return index, status


def _matches_filter(metadata: dict[str, Any], expression: dict[str, object]) -> bool:
    if "$and" in expression:
        values = expression["$and"]
        return isinstance(values, list) and all(
            isinstance(item, dict) and _matches_filter(metadata, item)
            for item in values
        )
    if "$or" in expression:
        values = expression["$or"]
        return isinstance(values, list) and any(
            isinstance(item, dict) and _matches_filter(metadata, item)
            for item in values
        )
    for field, expected in expression.items():
        actual = metadata.get(field)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$eq" in expected and actual != expected["$eq"]:
                return False
            if "$ne" in expected and actual == expected["$ne"]:
                return False
        elif actual != expected:
            return False
    return True
