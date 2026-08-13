from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import pytest

from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)
from app.modules.llm_chat.application.services.retrieval_evaluation import (
    RetrievalEvaluationCase,
    evaluate_retrieval,
    reranker_is_promotable,
)
from app.modules.llm_chat.application.services.retrieval_service import RetrievalService
from app.modules.llm_chat.application.use_cases.ingest_markdown import (
    IngestMarkdownUseCase,
)
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.rag_index import (
    EmbeddingFingerprintSpec,
    RAGIndexFingerprint,
    build_rag_index_fingerprint,
)
from app.modules.llm_chat.infrastructure.documents.markdown_chunker import (
    MarkdownChunker,
)
from app.modules.llm_chat.infrastructure.documents.markdown_loader import MarkdownLoader
from app.modules.llm_chat.infrastructure.retrieval import bm25_store
from app.modules.llm_chat.infrastructure.retrieval.bm25_store import ChromaBM25Store


MARKDOWN = """---
source_id: hardening-test
title: Documento de endurecimiento RAG
language: es
species: canine
version: "1"
status: test
domain: hematology
---

# Leucocitos

Los leucocitos forman parte de la respuesta inmunitaria.
"""


def _embedding_spec(**overrides: object) -> EmbeddingFingerprintSpec:
    values: dict[str, object] = {
        "provider": "fastembed",
        "model": "multilingual-minilm",
        "model_revision": "revision-a",
        "library_name": "fastembed",
        "library_version": "0.8.0",
        "pooling_strategy": "mean",
        "vector_dimension": 384,
        "normalization": True,
        "document_prefix": "passage: ",
        "query_prefix": "query: ",
    }
    values.update(overrides)
    return EmbeddingFingerprintSpec(**values)  # type: ignore[arg-type]


def _fingerprint(**overrides: object) -> RAGIndexFingerprint:
    values: dict[str, object] = {
        "embedding": _embedding_spec(),
        "chunking_version": "markdown-v5",
        "chunk_size": 384,
        "chunk_overlap": 64,
        "metadata_schema_version": "hemovet-rag-v2",
        "content_version": "content-a",
    }
    values.update(overrides)
    return build_rag_index_fingerprint(**values)  # type: ignore[arg-type]


def test_index_fingerprint_is_stable_roundtrippable_and_configuration_complete() -> None:
    fingerprint = _fingerprint()

    restored = RAGIndexFingerprint.from_collection_metadata(
        fingerprint.collection_metadata()
    )

    assert restored == fingerprint
    assert restored.digest == fingerprint.digest
    assert len(restored.digest) == 64
    assert restored.pooling_strategy == "mean"
    assert restored.document_prefix == "passage: "


@pytest.mark.parametrize(
    "changed",
    [
        _fingerprint(content_version="content-b"),
        _fingerprint(chunk_size=512),
        _fingerprint(embedding=_embedding_spec(model_revision="revision-b")),
        _fingerprint(embedding=_embedding_spec(library_version="0.9.0")),
        _fingerprint(embedding=_embedding_spec(pooling_strategy="cls")),
    ],
)
def test_index_fingerprint_changes_for_every_incompatible_component(
    changed: RAGIndexFingerprint,
) -> None:
    assert changed.digest != _fingerprint().digest


def test_index_fingerprint_rejects_tampered_collection_metadata() -> None:
    metadata = _fingerprint().collection_metadata()
    metadata["pooling_strategy"] = "cls"

    with pytest.raises(ValueError, match="digest_mismatch"):
        RAGIndexFingerprint.from_collection_metadata(metadata)


def test_chunk_ids_change_with_the_index_fingerprint(tmp_path: Path) -> None:
    (tmp_path / "source.md").write_text(MARKDOWN, encoding="utf-8")
    document = MarkdownLoader(tmp_path, allow_test_documents=True).load()[0]
    chunker = MarkdownChunker(chunk_size_words=20, overlap_words=4)

    first = chunker.chunk(document, index_fingerprint="a" * 64)
    second = chunker.chunk(document, index_fingerprint="b" * 64)

    assert {chunk.id for chunk in first}.isdisjoint(chunk.id for chunk in second)
    assert {chunk.metadata["index_fingerprint"] for chunk in first} == {"a" * 64}


class ThreadRecordingEmbedding:
    def __init__(self) -> None:
        self.thread_ids: list[int] = []

    def embed_query(self, _text: str) -> list[float]:
        self.thread_ids.append(threading.get_ident())
        return [1.0]


class EmptyVectorStore:
    async def query(self, _embedding: list[float], _fetch_k: int, **_options: object):
        return []


def test_fastembed_query_work_runs_outside_the_event_loop_thread() -> None:
    async def run() -> None:
        event_loop_thread = threading.get_ident()
        embeddings = ThreadRecordingEmbedding()
        service = RetrievalService(
            embeddings=embeddings,
            vector_store=EmptyVectorStore(),
            fetch_k=5,
            top_k=3,
            min_score=0.3,
            max_per_source=2,
            rrf_k=60,
            blocking_executor=BoundedBlockingExecutor(),
        )

        await service.retrieve("consulta sin expansión")

        assert embeddings.thread_ids
        assert all(thread_id != event_loop_thread for thread_id in embeddings.thread_ids)

    asyncio.run(run())


def test_blocking_executor_enforces_its_concurrency_limit() -> None:
    async def run() -> None:
        executor = BoundedBlockingExecutor(max_concurrency=1)
        lock = threading.Lock()
        active = 0
        maximum = 0

        def blocking_call() -> None:
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.02)
            with lock:
                active -= 1

        await asyncio.gather(*(executor.run(blocking_call) for _ in range(4)))
        assert maximum == 1

    asyncio.run(run())


class MutableAsyncCollection:
    def __init__(self, *, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        self.rows = [self._row("old", "leucopenia")]

    def _row(self, chunk_id: str, text: str) -> dict[str, object]:
        return {
            "id": chunk_id,
            "text": text,
            "metadata": {
                "status": "approved",
                "species": "canine",
                "domain": "hematology",
                "rag_eligible": True,
                "corpus_revision": "corpus-a",
                "index_fingerprint": self.fingerprint,
            },
        }

    async def get(self, *, include: list[str]) -> dict[str, list[object]]:
        assert include == ["documents", "metadatas"]
        return {
            "ids": [row["id"] for row in self.rows],
            "documents": [row["text"] for row in self.rows],
            "metadatas": [row["metadata"] for row in self.rows],
        }


def test_bm25_build_query_and_refresh_are_off_loop_and_atomically_updated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        event_loop_thread = threading.get_ident()
        work_threads: list[int] = []
        real_index = bm25_store.BM25Index

        class ThreadRecordingIndex(real_index):
            def __init__(self, *args: object, **kwargs: object) -> None:
                work_threads.append(threading.get_ident())
                super().__init__(*args, **kwargs)  # type: ignore[arg-type]

            def query(self, *args: object, **kwargs: object):
                work_threads.append(threading.get_ident())
                return super().query(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(bm25_store, "BM25Index", ThreadRecordingIndex)
        collection = MutableAsyncCollection(fingerprint="f" * 64)
        store = ChromaBM25Store(
            collection,
            expected_corpus_revision="corpus-a",
            expected_index_fingerprint="f" * 64,
            strict_revision=True,
            blocking_executor=BoundedBlockingExecutor(),
        )

        first_status = await store.refresh()
        assert [item.id for item in await store.query("leucopenia", 3)] == ["old"]

        collection.rows = [collection._row("new", "leucocitosis")]
        second_status = await store.refresh()
        assert await store.query("leucopenia", 3) == []
        assert [item.id for item in await store.query("leucocitosis", 3)] == ["new"]
        assert first_status.document_count == second_status.document_count == 1
        assert work_threads
        assert all(thread_id != event_loop_thread for thread_id in work_threads)

    asyncio.run(run())


def test_bm25_rejects_mixed_embedding_fingerprints() -> None:
    async def run() -> None:
        collection = MutableAsyncCollection(fingerprint="a" * 64)
        collection.rows.append(collection._row("second", "plaquetas"))
        collection.rows[1]["metadata"] = {
            **collection.rows[1]["metadata"],  # type: ignore[dict-item]
            "index_fingerprint": "b" * 64,
        }
        store = ChromaBM25Store(
            collection,
            expected_corpus_revision="corpus-a",
            expected_index_fingerprint="a" * 64,
            strict_revision=True,
            blocking_executor=BoundedBlockingExecutor(),
        )

        with pytest.raises(ChatRuntimeUnavailable, match="mixed"):
            await store.refresh()

    asyncio.run(run())


class FakeEmbeddingClient:
    model_name = "fake-model"
    dimension = 2

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0] for text in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.rows: dict[str, object] = {}

    def ids_for_document(self, source_path: str) -> set[str]:
        return {
            chunk_id
            for chunk_id, row in self.rows.items()
            if row.metadata["source_path"] == source_path  # type: ignore[attr-defined]
        }

    def upsert(self, chunks: list[object], _embeddings: list[list[float]]) -> None:
        for chunk in chunks:
            self.rows[chunk.id] = chunk  # type: ignore[attr-defined]

    def delete(self, ids: set[str]) -> None:
        for chunk_id in ids:
            self.rows.pop(chunk_id, None)

    def document_paths(self) -> set[str]:
        return {
            row.metadata["source_path"]  # type: ignore[attr-defined]
            for row in self.rows.values()
        }

    def delete_document(self, source_path: str) -> int:
        ids = self.ids_for_document(source_path)
        self.delete(ids)
        return len(ids)

    def count(self) -> int:
        return len(self.rows)


class RecordingRefresher:
    def __init__(self) -> None:
        self.fingerprints: list[str | None] = []

    async def refresh(
        self,
        *,
        expected_index_fingerprint: str | None = None,
    ) -> object:
        self.fingerprints.append(expected_index_fingerprint)
        return object()


def test_async_ingestion_refreshes_bm25_only_after_dense_index_changes(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        (tmp_path / "source.md").write_text(MARKDOWN, encoding="utf-8")
        refresher = RecordingRefresher()
        use_case = IngestMarkdownUseCase(
            loader=MarkdownLoader(tmp_path, allow_test_documents=True),
            chunker=MarkdownChunker(chunk_size_words=20, overlap_words=4),
            embeddings=FakeEmbeddingClient(),
            vector_store=FakeVectorStore(),
            batch_size=4,
            index_refresher=refresher,
        )

        first = await use_case.execute_async()
        second = await use_case.execute_async()

        assert refresher.fingerprints == [first.index_fingerprint]
        assert second.skipped_sources == 1

    asyncio.run(run())


def test_retrieval_metrics_support_a_measured_reranker_promotion_gate() -> None:
    baseline = evaluate_retrieval(
        [
            RetrievalEvaluationCase(
                case_id="wbc",
                relevant_chunk_ids=frozenset({"relevant"}),
                ranked_chunk_ids=("noise", "relevant"),
            )
        ]
    )
    candidate = evaluate_retrieval(
        [
            RetrievalEvaluationCase(
                case_id="wbc",
                relevant_chunk_ids=frozenset({"relevant"}),
                ranked_chunk_ids=("relevant", "noise"),
            )
        ]
    )

    assert reranker_is_promotable(
        baseline=baseline,
        candidate=candidate,
        minimum_rank_gain=0.03,
    )
    assert candidate.recall_at_5 >= baseline.recall_at_5
    assert candidate.mrr > baseline.mrr
