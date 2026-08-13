#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.modules.llm_chat.application.use_cases.ingest_markdown import (  # noqa: E402
    IngestMarkdownUseCase,
)
from app.modules.llm_chat.infrastructure.documents.markdown_chunker import (  # noqa: E402
    MarkdownChunker,
)
from app.modules.llm_chat.infrastructure.documents.markdown_loader import MarkdownLoader  # noqa: E402
from app.modules.llm_chat.infrastructure.embeddings.fastembed_client import (  # noqa: E402
    FastEmbedEmbeddingClient,
)
from app.modules.llm_chat.domain.rag_index import (  # noqa: E402
    EmbeddingFingerprintSpec,
    RAGIndexFingerprint,
    build_rag_index_fingerprint,
    corpus_content_version,
)
from app.modules.llm_chat.infrastructure.vectorstores.chroma_store import (  # noqa: E402
    ChromaIngestionStore,
    validate_chroma_index_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Indexa Markdown curado de HemoVet en ChromaDB."
    )
    parser.add_argument("command", choices=["index"])
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--collection", default=settings.RAG_COLLECTION_NAME)
    parser.add_argument("--chunk-size", type=int, default=settings.RAG_CHUNK_SIZE_WORDS)
    parser.add_argument("--overlap", type=int, default=settings.RAG_CHUNK_OVERLAP_WORDS)
    parser.add_argument(
        "--batch-size", type=int, default=settings.RAG_INGEST_BATCH_SIZE
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--stage",
        action="store_true",
        help="Indexa en una colección versionada sin tocar la colección activa.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Valida una colección ya indexada sin generar embeddings.",
    )
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--prune", action="store_true")
    parser.add_argument("--allow-test-documents", action="store_true")
    parser.add_argument("--allow-ai-provisional", action="store_true")
    return parser.parse_args()


def source_directory(argument: Path | None) -> Path:
    selected = argument or settings.RAG_SOURCE_DIR
    if selected.is_absolute():
        return selected
    return (settings.HEMOVET_PROJECT_ROOT / selected).resolve()


def build_dry_run_summary(
    loader: MarkdownLoader,
    chunker: MarkdownChunker,
    root: Path,
    *,
    embedding_spec: EmbeddingFingerprintSpec | None = None,
) -> dict[str, object]:
    documents = loader.load()
    if not documents:
        raise RuntimeError("El corpus aprobado está vacío.")
    fingerprint = build_rag_index_fingerprint(
        embedding=embedding_spec or configured_embedding_spec(),
        chunking_version=chunker.SCHEMA_VERSION,
        chunk_size=chunker.chunk_size_words,
        chunk_overlap=chunker.overlap_words,
        metadata_schema_version=chunker.CORPUS_SCHEMA_VERSION,
        content_version=corpus_content_version(documents),
    )
    chunk_count = sum(
        len(chunker.chunk(document, index_fingerprint=fingerprint.digest))
        for document in documents
    )
    if chunk_count == 0:
        raise RuntimeError("El corpus aprobado no produjo ningún chunk.")
    return {
        "source_dir": str(root),
        "sources": len(documents),
        "chunks": chunk_count,
        "quarantined_sources": len(loader.last_issues),
        "corpus_revision": loader.corpus_revision,
        "content_version": fingerprint.content_version,
        "index_fingerprint": fingerprint.digest,
        "schema_version": MarkdownChunker.SCHEMA_VERSION,
        "corpus_schema_version": MarkdownChunker.CORPUS_SCHEMA_VERSION,
        "dry_run": True,
    }


def configured_embedding_spec() -> EmbeddingFingerprintSpec:
    return FastEmbedEmbeddingClient.fingerprint_spec(
        model_name=settings.RAG_EMBEDDING_MODEL,
        dimension=settings.RAG_EMBEDDING_DIMENSION,
        model_revision=settings.RAG_EMBEDDING_MODEL_REVISION,
        pooling_strategy=settings.RAG_EMBEDDING_POOLING_STRATEGY,
        normalization=settings.RAG_EMBEDDING_NORMALIZATION,
        document_prefix=settings.RAG_EMBEDDING_DOCUMENT_PREFIX,
        query_prefix=settings.RAG_EMBEDDING_QUERY_PREFIX,
    )


def index_fingerprint(
    *,
    loader: MarkdownLoader,
    chunker: MarkdownChunker,
    embedding_spec: EmbeddingFingerprintSpec,
) -> RAGIndexFingerprint:
    documents = loader.load()
    if not documents:
        raise RuntimeError("El corpus aprobado está vacío.")
    return build_rag_index_fingerprint(
        embedding=embedding_spec,
        chunking_version=chunker.SCHEMA_VERSION,
        chunk_size=chunker.chunk_size_words,
        chunk_overlap=chunker.overlap_words,
        metadata_schema_version=chunker.CORPUS_SCHEMA_VERSION,
        content_version=corpus_content_version(documents),
    )


def main() -> int:
    args = parse_args()
    root = source_directory(args.source_dir)
    loader = MarkdownLoader(
        root,
        allow_test_documents=(
            args.allow_test_documents or settings.RAG_ALLOW_TEST_DOCUMENTS
        ),
        allow_ai_provisional_documents=(
            args.allow_ai_provisional or settings.RAG_ALLOW_AI_PROVISIONAL
        ),
    )
    chunker = MarkdownChunker(
        chunk_size_words=args.chunk_size,
        overlap_words=args.overlap,
    )
    embedding_spec = configured_embedding_spec()
    if args.dry_run:
        print(
            json.dumps(
                build_dry_run_summary(
                    loader,
                    chunker,
                    root,
                    embedding_spec=embedding_spec,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    import chromadb

    fingerprint = index_fingerprint(
        loader=loader,
        chunker=chunker,
        embedding_spec=embedding_spec,
    )
    base_collection = args.collection
    target_collection = (
        f"{base_collection}__{fingerprint.digest[:12]}"
        if args.stage
        else base_collection
    )
    if args.reset and not args.stage:
        raise RuntimeError("rag_active_collection_reset_forbidden")

    client = chromadb.HttpClient(
        host=settings.CHROMA_HOST,
        port=settings.CHROMA_PORT,
        ssl=settings.CHROMA_SSL,
        tenant=settings.CHROMA_TENANT,
        database=settings.CHROMA_DATABASE,
    )
    if args.validate_only:
        collection = client.get_collection(name=target_collection)
        snapshot = _validated_collection_snapshot(
            collection=collection,
            fingerprint=fingerprint,
            corpus_revision=loader.corpus_revision,
        )
        print(
            json.dumps(
                {
                    "validated": True,
                    "collection": target_collection,
                    "snapshot": asdict(snapshot),
                    "promotion": _promotion_contract(
                        base_collection=base_collection,
                        target_collection=target_collection,
                        staged=args.stage,
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.reset:
        try:
            client.delete_collection(target_collection)
        except Exception:
            pass
    collection = client.get_or_create_collection(
        name=target_collection,
        metadata={
            "schema_version": MarkdownChunker.SCHEMA_VERSION,
            "corpus_schema_version": MarkdownChunker.CORPUS_SCHEMA_VERSION,
            "corpus_revision": loader.corpus_revision,
            **fingerprint.collection_metadata(),
        },
        configuration={"hnsw": {"space": "cosine"}},
    )
    try:
        configured_fingerprint = RAGIndexFingerprint.from_collection_metadata(
            dict(collection.metadata or {})
        )
    except ValueError as exc:
        raise RuntimeError(
            "La colección no tiene un fingerprint íntegro; utiliza una colección "
            "nueva o --reset."
        ) from exc
    if configured_fingerprint.digest != fingerprint.digest:
        raise RuntimeError(
            "La colección usa otro fingerprint de índice; utiliza una colección "
            "nueva o --reset."
        )
    configured_schema = (collection.metadata or {}).get("schema_version")
    if configured_schema and configured_schema != MarkdownChunker.SCHEMA_VERSION:
        raise RuntimeError(
            "La colección usa otro schema de chunks; utiliza otra colección o --reset."
        )
    configured_revision = (collection.metadata or {}).get("corpus_revision")
    if configured_revision and configured_revision != loader.corpus_revision:
        raise RuntimeError(
            "La colección pertenece a otra revisión del corpus; utiliza --reset."
        )
    embedding_client = FastEmbedEmbeddingClient(
        model_name=settings.RAG_EMBEDDING_MODEL,
        dimension=settings.RAG_EMBEDDING_DIMENSION,
        cache_dir=str(settings.RAG_EMBEDDING_CACHE_DIR),
        model_revision=settings.RAG_EMBEDDING_MODEL_REVISION,
        pooling_strategy=settings.RAG_EMBEDDING_POOLING_STRATEGY,
        normalization=settings.RAG_EMBEDDING_NORMALIZATION,
        document_prefix=settings.RAG_EMBEDDING_DOCUMENT_PREFIX,
        query_prefix=settings.RAG_EMBEDDING_QUERY_PREFIX,
    )
    use_case = IngestMarkdownUseCase(
        loader=loader,
        chunker=chunker,
        embeddings=embedding_client,
        vector_store=ChromaIngestionStore(
            collection,
            expected_schema_version=MarkdownChunker.SCHEMA_VERSION,
            expected_corpus_revision=loader.corpus_revision,
            expected_index_fingerprint=fingerprint.digest,
        ),
        batch_size=args.batch_size,
        index_fingerprint=fingerprint,
    )
    result = use_case.execute(prune=args.prune)
    snapshot = _validated_collection_snapshot(
        collection=collection,
        fingerprint=fingerprint,
        corpus_revision=loader.corpus_revision,
        expected_chunk_count=result.collection_chunks,
    )
    print(
        json.dumps(
            {
                **asdict(result),
                "collection": target_collection,
                "validated": True,
                "snapshot": asdict(snapshot),
                "promotion": _promotion_contract(
                    base_collection=base_collection,
                    target_collection=target_collection,
                    staged=args.stage,
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _validated_collection_snapshot(
    *,
    collection: object,
    fingerprint: RAGIndexFingerprint,
    corpus_revision: str,
    expected_chunk_count: int | None = None,
):
    metadata = dict(getattr(collection, "metadata", None) or {})
    configured = RAGIndexFingerprint.from_collection_metadata(metadata)
    if configured.digest != fingerprint.digest:
        raise RuntimeError("rag_index_fingerprint_runtime_mismatch")
    return validate_chroma_index_snapshot(
        collection,
        expected_index_fingerprint=fingerprint.digest,
        expected_schema_version=MarkdownChunker.SCHEMA_VERSION,
        expected_corpus_revision=corpus_revision,
        expected_chunk_count=expected_chunk_count,
    )


def _promotion_contract(
    *,
    base_collection: str,
    target_collection: str,
    staged: bool,
) -> dict[str, object]:
    return {
        "ready": True,
        "requires_backend_restart": staged,
        "set_environment": {"RAG_COLLECTION_NAME": target_collection},
        "staging_namespace": base_collection if staged else None,
        "rollback_requires_previous_release": staged,
    }


if __name__ == "__main__":
    raise SystemExit(main())
