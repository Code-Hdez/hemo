from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Protocol


FINGERPRINT_VERSION = "rag-index-fingerprint-v1"


class FingerprintDocument(Protocol):
    source_path: str
    source_hash: str


@dataclass(frozen=True, slots=True)
class EmbeddingFingerprintSpec:
    provider: str
    model: str
    model_revision: str
    library_name: str
    library_version: str
    pooling_strategy: str
    vector_dimension: int
    normalization: bool
    document_prefix: str = ""
    query_prefix: str = ""

    def __post_init__(self) -> None:
        for field in (
            "provider",
            "model",
            "model_revision",
            "library_name",
            "library_version",
            "pooling_strategy",
        ):
            if not str(getattr(self, field)).strip():
                raise ValueError(f"{field} is required for the embedding fingerprint")
        if self.vector_dimension < 1:
            raise ValueError("vector_dimension must be positive")


@dataclass(frozen=True, slots=True)
class RAGIndexFingerprint:
    embedding_provider: str
    embedding_model: str
    model_revision: str
    library_name: str
    library_version: str
    pooling_strategy: str
    vector_dimension: int
    normalization: bool
    distance_metric: str
    document_prefix: str
    query_prefix: str
    chunking_version: str
    chunk_size: int
    chunk_overlap: int
    metadata_schema_version: str
    content_version: str
    fingerprint_version: str = FINGERPRINT_VERSION

    def __post_init__(self) -> None:
        for field in (
            "embedding_provider",
            "embedding_model",
            "model_revision",
            "library_name",
            "library_version",
            "pooling_strategy",
            "distance_metric",
            "chunking_version",
            "metadata_schema_version",
            "content_version",
            "fingerprint_version",
        ):
            if not str(getattr(self, field)).strip():
                raise ValueError(f"{field} is required for the RAG index fingerprint")
        if self.vector_dimension < 1:
            raise ValueError("vector_dimension must be positive")
        if self.chunk_size < 1:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be lower than chunk_size")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def structural_digest(self) -> str:
        """Identity of the vector space and chunking algorithm, not corpus content.

        ``content_version`` is a hash of every document's ``(path, hash)`` pair
        in the whole corpus (see ``corpus_content_version``): it changes when
        *any* document changes, even one unrelated to a given chunk. Chunk IDs
        must not depend on it, or editing one document reindexes the entire
        corpus (etapa 5, Block G — every chunk id embeds ``index_fingerprint``,
        so hashing that in directly propagates unrelated content changes to
        every id). This digest excludes ``content_version`` and
        ``fingerprint_version``-adjacent bookkeeping that does not affect
        embedding-space or chunking compatibility, keeping only the fields
        that legitimately require a full reindex when they change.
        """
        payload = asdict(self)
        payload.pop("content_version", None)
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def canonical_json(self) -> str:
        return json.dumps(
            asdict(self),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    def collection_metadata(self) -> dict[str, str | int | bool]:
        values: dict[str, str | int | bool] = dict(asdict(self))
        values["index_fingerprint"] = self.digest
        return values

    @classmethod
    def from_collection_metadata(
        cls,
        metadata: dict[str, Any],
    ) -> RAGIndexFingerprint:
        try:
            fingerprint = cls(
                embedding_provider=str(metadata["embedding_provider"]),
                embedding_model=str(metadata["embedding_model"]),
                model_revision=str(metadata["model_revision"]),
                library_name=str(metadata["library_name"]),
                library_version=str(metadata["library_version"]),
                pooling_strategy=str(metadata["pooling_strategy"]),
                vector_dimension=int(metadata["vector_dimension"]),
                normalization=_strict_bool(metadata["normalization"]),
                distance_metric=str(metadata["distance_metric"]),
                document_prefix=str(metadata.get("document_prefix") or ""),
                query_prefix=str(metadata.get("query_prefix") or ""),
                chunking_version=str(metadata["chunking_version"]),
                chunk_size=int(metadata["chunk_size"]),
                chunk_overlap=int(metadata["chunk_overlap"]),
                metadata_schema_version=str(metadata["metadata_schema_version"]),
                content_version=str(metadata["content_version"]),
                fingerprint_version=str(metadata["fingerprint_version"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("incomplete_index_fingerprint_metadata") from exc
        if str(metadata.get("index_fingerprint") or "") != fingerprint.digest:
            raise ValueError("index_fingerprint_digest_mismatch")
        return fingerprint


def _strict_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.casefold() in {"true", "false"}:
        return value.casefold() == "true"
    raise ValueError("normalization must be a boolean")


def corpus_content_version(documents: Iterable[FingerprintDocument]) -> str:
    rows = sorted(
        (str(document.source_path), str(document.source_hash))
        for document in documents
    )
    if not rows:
        raise ValueError("Cannot fingerprint an empty corpus")
    payload = json.dumps(rows, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_rag_index_fingerprint(
    *,
    embedding: EmbeddingFingerprintSpec,
    chunking_version: str,
    chunk_size: int,
    chunk_overlap: int,
    metadata_schema_version: str,
    content_version: str,
    distance_metric: str = "cosine",
) -> RAGIndexFingerprint:
    return RAGIndexFingerprint(
        embedding_provider=embedding.provider,
        embedding_model=embedding.model,
        model_revision=embedding.model_revision,
        library_name=embedding.library_name,
        library_version=embedding.library_version,
        pooling_strategy=embedding.pooling_strategy,
        vector_dimension=embedding.vector_dimension,
        normalization=embedding.normalization,
        distance_metric=distance_metric,
        document_prefix=embedding.document_prefix,
        query_prefix=embedding.query_prefix,
        chunking_version=chunking_version,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        metadata_schema_version=metadata_schema_version,
        content_version=content_version,
    )
