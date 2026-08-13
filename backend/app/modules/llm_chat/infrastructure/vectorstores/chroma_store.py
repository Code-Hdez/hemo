from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.llm_chat.domain.entities import (
    KnowledgeChunk,
    VectorCandidate,
)
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable


@dataclass(frozen=True, slots=True)
class ChromaIndexSnapshot:
    collection_chunks: int
    index_fingerprint: str
    schema_version: str
    corpus_revision: str


def validate_chroma_index_snapshot(
    collection: Any,
    *,
    expected_index_fingerprint: str,
    expected_schema_version: str,
    expected_corpus_revision: str,
    expected_chunk_count: int | None = None,
) -> ChromaIndexSnapshot:
    result = collection.get(include=["metadatas"])
    ids = [str(value) for value in result.get("ids") or []]
    metadatas = [dict(value or {}) for value in result.get("metadatas") or []]
    if len(ids) != len(metadatas) or len(set(ids)) != len(ids):
        raise RuntimeError("rag_index_snapshot_shape_invalid")
    if expected_chunk_count is not None and len(ids) != expected_chunk_count:
        raise RuntimeError("rag_index_snapshot_count_mismatch")
    if not ids:
        raise RuntimeError("rag_index_snapshot_empty")
    for metadata in metadatas:
        if metadata.get("index_fingerprint") != expected_index_fingerprint:
            raise RuntimeError("rag_index_snapshot_fingerprint_mismatch")
        if metadata.get("schema_version") != expected_schema_version:
            raise RuntimeError("rag_index_snapshot_schema_mismatch")
        if metadata.get("corpus_revision") != expected_corpus_revision:
            raise RuntimeError("rag_index_snapshot_corpus_revision_mismatch")
    return ChromaIndexSnapshot(
        collection_chunks=len(ids),
        index_fingerprint=expected_index_fingerprint,
        schema_version=expected_schema_version,
        corpus_revision=expected_corpus_revision,
    )


class ChromaIngestionStore:
    def __init__(
        self,
        collection: Any,
        *,
        expected_schema_version: str | None = None,
        expected_corpus_revision: str | None = None,
        expected_index_fingerprint: str | None = None,
    ) -> None:
        self.collection = collection
        self.expected_schema_version = expected_schema_version
        self.expected_corpus_revision = expected_corpus_revision
        self.expected_index_fingerprint = expected_index_fingerprint

    def ids_for_document(self, source_path: str) -> set[str]:
        result = self.collection.get(
            where={"source_path": source_path},
            include=[],
        )
        return set(result.get("ids") or [])

    def upsert(
        self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Every chunk requires exactly one embedding")
        for chunk in chunks:
            if (
                self.expected_schema_version
                and chunk.metadata.get("schema_version") != self.expected_schema_version
            ):
                raise ValueError("Chunk schema version mismatch")
            if (
                self.expected_corpus_revision
                and chunk.metadata.get("corpus_revision")
                != self.expected_corpus_revision
            ):
                raise ValueError("Chunk corpus revision mismatch")
            if (
                self.expected_index_fingerprint
                and chunk.metadata.get("index_fingerprint")
                != self.expected_index_fingerprint
            ):
                raise ValueError("Chunk index fingerprint mismatch")
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks],
            embeddings=embeddings,
        )

    def delete(self, ids: set[str]) -> None:
        if ids:
            self.collection.delete(ids=sorted(ids))

    def document_paths(self) -> set[str]:
        result = self.collection.get(include=["metadatas"])
        return {
            str(metadata.get("source_path"))
            for metadata in (result.get("metadatas") or [])
            if metadata and metadata.get("source_path")
        }

    def delete_document(self, source_path: str) -> int:
        ids = self.ids_for_document(source_path)
        self.delete(ids)
        return len(ids)

    def count(self) -> int:
        return int(self.collection.count())


class ChromaRetrievalStore:
    def __init__(
        self,
        collection: Any,
        *,
        allowed_statuses: tuple[str, ...] = ("approved", "test"),
        # Etapa 5, Block C/F: defaults are a safety net only; composition.py
        # always supplies the single configured allowlist
        # (RAG_ALLOWED_SPECIES/_DOMAINS) so this store and ChromaBM25Store
        # never drift apart.
        allowed_species: tuple[str, ...] = ("canine", "canine_feline"),
        allowed_domains: tuple[str, ...] = (
            "hematology",
            "clinical_pathology",
            "coagulation",
            "sample_collection",
            "laboratory_methods",
            "cytology",
        ),
        expected_index_fingerprint: str | None = None,
    ) -> None:
        self.collection = collection
        self.allowed_statuses = allowed_statuses
        self.allowed_species = allowed_species
        self.allowed_domains = allowed_domains
        self.expected_index_fingerprint = expected_index_fingerprint

    async def query(
        self,
        embedding: list[float],
        fetch_k: int,
        *,
        metadata_filter: dict[str, object] | None = None,
    ) -> list[VectorCandidate]:
        where_clauses: list[dict[str, Any]] = [
            {"species": {"$in": list(self.allowed_species)}},
            {"status": {"$in": list(self.allowed_statuses)}},
            {"rag_eligible": {"$eq": True}},
            {"domain": {"$in": list(self.allowed_domains)}},
        ]
        if self.expected_index_fingerprint:
            where_clauses.append(
                {
                    "index_fingerprint": {
                        "$eq": self.expected_index_fingerprint
                    }
                }
            )
        if metadata_filter:
            extra_and = metadata_filter.get("$and")
            if isinstance(extra_and, list):
                where_clauses.extend(
                    item for item in extra_and if isinstance(item, dict)
                )
            else:
                where_clauses.append(metadata_filter)
        try:
            result = await self.collection.query(
                query_embeddings=[embedding],
                n_results=fetch_k,
                where={"$and": where_clauses},
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise ChatRuntimeUnavailable("Chroma retrieval failed") from exc
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [
            VectorCandidate(
                id=str(chunk_id),
                text=str(document or ""),
                metadata=dict(metadata or {}),
                semantic_score=max(0.0, min(1.0, 1.0 - float(distance))),
            )
            for chunk_id, document, metadata, distance in zip(
                ids, documents, metadatas, distances, strict=True
            )
        ]


class ChromaNeighborStore:
    """Fetch specific chunks by id for bounded neighbor expansion (Block F).

    ``markdown_chunker.py`` already stores ``previous_chunk_id``/
    ``next_chunk_id`` in every chunk's metadata; nothing previously read
    them back. This is a plain id lookup, not a ranked query, so it carries
    no relevance score of its own.
    """

    def __init__(self, collection: Any) -> None:
        self.collection = collection

    async def get_by_ids(self, ids: list[str]) -> list[VectorCandidate]:
        if not ids:
            return []
        try:
            result = await self.collection.get(
                ids=ids, include=["documents", "metadatas"]
            )
        except Exception as exc:
            raise ChatRuntimeUnavailable("Chroma neighbor lookup failed") from exc
        found_ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        return [
            VectorCandidate(
                id=str(chunk_id),
                text=str(document or ""),
                metadata=dict(metadata or {}),
                # Neighbor expansion is not a relevance judgment: the anchor
                # chunk's own score already justified fetching it.
                semantic_score=0.0,
            )
            for chunk_id, document, metadata in zip(
                found_ids, documents, metadatas, strict=True
            )
        ]
