from __future__ import annotations

import asyncio

from app.modules.llm_chat.domain.entities import KnowledgeChunk
from app.modules.llm_chat.infrastructure.embeddings.fastembed_client import (
    FastEmbedEmbeddingClient,
)
from app.modules.llm_chat.infrastructure.vectorstores.chroma_store import (
    ChromaIngestionStore,
    ChromaRetrievalStore,
    validate_chroma_index_snapshot,
)


class FakeEmbeddingModel:
    def query_embed(self, texts):
        assert texts == ["consulta"]
        return iter([[1.0, 2.0]])

    def passage_embed(self, texts):
        assert texts == ["uno", "dos"]
        return iter([[1.0, 0.0], [0.0, 1.0]])


def test_fastembed_adapter_uses_query_and_passage_modes() -> None:
    adapter = FastEmbedEmbeddingClient(
        model_name="fake", model=FakeEmbeddingModel(), dimension=2
    )

    assert adapter.embed_query("consulta") == [1.0, 2.0]
    assert adapter.embed_documents(["uno", "dos"]) == [[1.0, 0.0], [0.0, 1.0]]


class FakeSyncCollection:
    def __init__(self) -> None:
        self.upsert_payload = None
        self.deleted = None

    def get(self, where, include):
        assert where == {"source_path": "book/section.md"}
        return {"ids": ["old-1"]}

    def upsert(self, **payload):
        self.upsert_payload = payload

    def delete(self, ids):
        self.deleted = ids


def test_chroma_ingestion_store_maps_documents_metadata_and_embeddings() -> None:
    collection = FakeSyncCollection()
    store = ChromaIngestionStore(collection)
    chunk = KnowledgeChunk(
        id="new-1",
        text="texto",
        metadata={
            "source_id": "source-a",
            "source_path": "book/section.md",
            "title": "A",
        },
    )

    assert store.ids_for_document("book/section.md") == {"old-1"}
    store.upsert([chunk], [[0.1, 0.2]])
    store.delete({"old-1"})

    assert collection.upsert_payload == {
        "ids": ["new-1"],
        "documents": ["texto"],
        "metadatas": [
            {
                "source_id": "source-a",
                "source_path": "book/section.md",
                "title": "A",
            }
        ],
        "embeddings": [[0.1, 0.2]],
    }
    assert collection.deleted == ["old-1"]


class FakeAsyncCollection:
    def __init__(self) -> None:
        self.query_payload = None

    async def query(self, **payload):
        self.query_payload = payload
        assert payload["query_embeddings"] == [[1.0, 0.0]]
        assert payload["n_results"] == 3
        return {
            "ids": [["c1"]],
            "documents": [["contenido"]],
            "metadatas": [[{"source_id": "s1", "title": "Fuente"}]],
            "distances": [[0.2]],
        }


def test_chroma_retrieval_converts_cosine_distance_to_similarity() -> None:
    collection = FakeAsyncCollection()
    store = ChromaRetrievalStore(collection)

    candidates = asyncio.run(store.query([1.0, 0.0], 3))

    assert candidates[0].id == "c1"
    assert candidates[0].semantic_score == 0.8
    assert collection.query_payload["where"]["$and"][1] == {
        "status": {"$in": ["approved", "test"]}
    }


def test_chroma_retrieval_can_allow_ai_provisional_status() -> None:
    collection = FakeAsyncCollection()
    store = ChromaRetrievalStore(
        collection,
        allowed_statuses=("approved", "ai_approved_provisional"),
    )

    asyncio.run(store.query([1.0, 0.0], 3))

    assert collection.query_payload["where"]["$and"][1] == {
        "status": {"$in": ["approved", "ai_approved_provisional"]}
    }


class FakeSnapshotCollection:
    def get(self, *, include):
        assert include == ["metadatas"]
        return {
            "ids": ["chunk-a"],
            "metadatas": [
                {
                    "index_fingerprint": "f" * 64,
                    "schema_version": "markdown-v5",
                    "corpus_revision": "corpus-a",
                }
            ],
        }


def test_chroma_snapshot_validation_checks_the_promotable_index_contract() -> None:
    snapshot = validate_chroma_index_snapshot(
        FakeSnapshotCollection(),
        expected_index_fingerprint="f" * 64,
        expected_schema_version="markdown-v5",
        expected_corpus_revision="corpus-a",
        expected_chunk_count=1,
    )

    assert snapshot.collection_chunks == 1
    assert snapshot.index_fingerprint == "f" * 64
