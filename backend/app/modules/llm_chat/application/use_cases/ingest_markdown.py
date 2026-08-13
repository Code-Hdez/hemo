from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)
from app.modules.llm_chat.domain.ports.retrieval import RefreshableRetrievalIndex
from app.modules.llm_chat.domain.rag_index import (
    EmbeddingFingerprintSpec,
    RAGIndexFingerprint,
    build_rag_index_fingerprint,
    corpus_content_version,
)

from app.modules.llm_chat.domain.ports.ingestion import (
    DocumentEmbeddingClient,
    IngestionVectorStore,
)
from app.modules.llm_chat.infrastructure.documents.markdown_chunker import (
    MarkdownChunker,
)
from app.modules.llm_chat.infrastructure.documents.markdown_loader import MarkdownLoader


@dataclass(frozen=True, slots=True)
class IngestionResult:
    indexed_sources: int
    indexed_chunks: int
    skipped_sources: int
    deleted_chunks: int
    pruned_sources: int
    collection_chunks: int
    quarantined_sources: int = 0
    corpus_revision: str = "unversioned"
    schema_version: str = MarkdownChunker.SCHEMA_VERSION
    content_version: str = "unversioned"
    index_fingerprint: str = "unversioned"


class IngestMarkdownUseCase:
    def __init__(
        self,
        *,
        loader: MarkdownLoader,
        chunker: MarkdownChunker,
        embeddings: DocumentEmbeddingClient,
        vector_store: IngestionVectorStore,
        batch_size: int,
        index_fingerprint: RAGIndexFingerprint | None = None,
        index_refresher: RefreshableRetrievalIndex | None = None,
        blocking_executor: BoundedBlockingExecutor | None = None,
    ) -> None:
        self.loader = loader
        self.chunker = chunker
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.batch_size = batch_size
        self.index_fingerprint = index_fingerprint
        self.index_refresher = index_refresher
        self.blocking_executor = blocking_executor or BoundedBlockingExecutor(
            max_concurrency=1
        )

    async def execute_async(self, *, prune: bool = False) -> IngestionResult:
        """Run the synchronous ingestion safely from an async worker.

        An in-process sparse index is atomically refreshed only after the dense
        mutation and integrity checks complete. Cross-process promotion still
        requires a version/alias coordinator rather than an unsafe live write.
        """

        result = await self.blocking_executor.run(self.execute, prune=prune)
        index_changed = bool(
            result.indexed_chunks or result.deleted_chunks or result.pruned_sources
        )
        if self.index_refresher is not None and index_changed:
            await self.index_refresher.refresh(
                expected_index_fingerprint=result.index_fingerprint
            )
        return result

    def execute(self, *, prune: bool = False) -> IngestionResult:
        indexed_sources = 0
        indexed_chunks = 0
        skipped_sources = 0
        deleted_chunks = 0
        pruned_sources = 0
        documents = self.loader.load()
        quarantined_sources = len(self.loader.last_issues)
        if not documents:
            raise RuntimeError(
                "El corpus aprobado está vacío; se cancela la ingesta y el prune."
            )
        content_version = corpus_content_version(documents)
        fingerprint = self._resolved_fingerprint(content_version=content_version)
        chunked_documents = [
            (
                document,
                self.chunker.chunk(
                    document,
                    index_fingerprint=fingerprint.digest,
                    # Etapa 5, Block G: chunk identity must be stable across
                    # unrelated corpus edits. structural_digest excludes the
                    # corpus-wide content_version, so editing one document
                    # never reshuffles every other document's chunk ids and
                    # forces a full re-embed (see ids_for_document skip-check
                    # below).
                    chunk_identity_fingerprint=fingerprint.structural_digest,
                ),
            )
            for document in documents
        ]
        if not any(chunks for _, chunks in chunked_documents):
            raise RuntimeError(
                "El corpus aprobado no produjo ningún chunk; se cancela la ingesta."
            )
        for document, chunks in chunked_documents:
            new_ids = {chunk.id for chunk in chunks}
            existing_ids = self.vector_store.ids_for_document(document.source_path)
            if existing_ids == new_ids:
                skipped_sources += 1
                continue
            for start in range(0, len(chunks), self.batch_size):
                batch = chunks[start : start + self.batch_size]
                vectors = self.embeddings.embed_documents(
                    [
                        "\n".join(
                            [
                                str(chunk.metadata.get("title") or ""),
                                str(chunk.metadata.get("heading_path") or ""),
                                chunk.text,
                            ]
                        ).strip()
                        for chunk in batch
                    ]
                )
                self.vector_store.upsert(batch, vectors)
                indexed_chunks += len(batch)
            stale_ids = existing_ids - new_ids
            if stale_ids:
                self.vector_store.delete(stale_ids)
                deleted_chunks += len(stale_ids)
            indexed_sources += 1
        if prune:
            active_document_paths = {document.source_path for document in documents}
            for source_path in (
                self.vector_store.document_paths() - active_document_paths
            ):
                deleted_chunks += self.vector_store.delete_document(source_path)
                pruned_sources += 1
        collection_chunks = self.vector_store.count()
        expected_chunks = sum(len(chunks) for _, chunks in chunked_documents)
        if prune and collection_chunks != expected_chunks:
            raise RuntimeError(
                "El conteo final de Chroma no coincide con los chunks del corpus: "
                f"esperados={expected_chunks}, encontrados={collection_chunks}."
            )
        return IngestionResult(
            indexed_sources=indexed_sources,
            indexed_chunks=indexed_chunks,
            skipped_sources=skipped_sources,
            deleted_chunks=deleted_chunks,
            pruned_sources=pruned_sources,
            collection_chunks=collection_chunks,
            quarantined_sources=quarantined_sources,
            corpus_revision=self.loader.corpus_revision,
            content_version=content_version,
            index_fingerprint=fingerprint.digest,
        )

    def _resolved_fingerprint(self, *, content_version: str) -> RAGIndexFingerprint:
        calculated = build_rag_index_fingerprint(
            embedding=_embedding_spec(self.embeddings),
            chunking_version=self.chunker.SCHEMA_VERSION,
            chunk_size=self.chunker.chunk_size_words,
            chunk_overlap=self.chunker.overlap_words,
            metadata_schema_version=self.chunker.CORPUS_SCHEMA_VERSION,
            content_version=content_version,
        )
        if (
            self.index_fingerprint is not None
            and self.index_fingerprint.digest != calculated.digest
        ):
            raise RuntimeError("Configured RAG index fingerprint is incompatible")
        return self.index_fingerprint or calculated


def _embedding_spec(embeddings: Any) -> EmbeddingFingerprintSpec:
    factory = getattr(embeddings, "index_fingerprint_spec", None)
    if callable(factory):
        spec = factory()
        if isinstance(spec, EmbeddingFingerprintSpec):
            return spec
        raise TypeError("index_fingerprint_spec must return EmbeddingFingerprintSpec")

    model_name = str(getattr(embeddings, "model_name", "unknown-model"))
    module_name = type(embeddings).__module__.split(".", 1)[0] or "unknown-library"
    return EmbeddingFingerprintSpec(
        provider=str(getattr(embeddings, "embedding_provider", module_name)),
        model=model_name,
        model_revision=str(getattr(embeddings, "model_revision", model_name)),
        library_name=str(getattr(embeddings, "library_name", module_name)),
        library_version=str(getattr(embeddings, "library_version", "unversioned")),
        pooling_strategy=str(
            getattr(embeddings, "pooling_strategy", "provider-default")
        ),
        vector_dimension=int(getattr(embeddings, "dimension")),
        normalization=bool(getattr(embeddings, "normalization", False)),
        document_prefix=str(getattr(embeddings, "document_prefix", "")),
        query_prefix=str(getattr(embeddings, "query_prefix", "")),
    )
