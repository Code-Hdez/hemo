from __future__ import annotations

from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)

import asyncio

from app.modules.llm_chat.application.services.retrieval_service import RetrievalService
from app.modules.llm_chat.domain.entities import VectorCandidate
from app.modules.llm_chat.infrastructure.retrieval.bm25_store import (
    BM25Document,
    BM25Index,
)


def test_bm25_finds_a_lexical_candidate_and_respects_metadata() -> None:
    index = BM25Index(
        [
            BM25Document(
                id="platelets",
                text="Thrombocytopenia is a decreased platelet count.",
                metadata={
                    "status": "approved",
                    "species": "canine",
                    "domain": "hematology",
                    "title": "Platelet disorders",
                },
            ),
            BM25Document(
                id="feline",
                text="Thrombocytopenia in a feline case.",
                metadata={
                    "status": "approved",
                    "species": "feline",
                    "domain": "hematology",
                    "title": "Feline case",
                },
            ),
        ]
    )

    results = index.query(
        "thrombocytopenia platelet",
        limit=4,
        metadata_filter={"domain": "hematology"},
    )

    assert [result.id for result in results] == ["platelets"]
    # Etapa 5, Block C (bm25_store.py): scores are no longer normalized by
    # dividing by the top score (which forced the #1 result to always read
    # 1.0); they now use a saturating transform score / (score + k) where k
    # is the batch's own average score. With a single result in the batch,
    # k equals that result's own score, so semantic_score is always exactly
    # 0.5 regardless of the raw BM25 score's magnitude.
    assert results[0].semantic_score == 0.5


class FakeEmbedding:
    def embed_query(self, text: str) -> list[float]:
        return [1.0]


class EmptyDenseStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        return []


class SparseOnlyStore:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def query(self, query: str, fetch_k: int, **options):
        self.queries.append(query)
        return [
            VectorCandidate(
                id="wbc-sparse",
                text="Leukocytosis means an increased leukocyte count.",
                metadata={
                    "source_id": "schalm",
                    "canonical_source_id": "schalm",
                    "display_title": "Schalm's Veterinary Hematology, 6th edition",
                    "bibliographic_title": "Schalm's Veterinary Hematology",
                    "authors_json": '["Douglas J. Weiss", "K. Jane Wardrop"]',
                    "edition": "6th",
                    "heading_path": "Leukocyte disorders > Leukocytosis",
                    "section": "Leukocytosis",
                    "source_path": "private/internal.md",
                    "status": "approved",
                    "species": "canine",
                    "rag_eligible": True,
                    "citation_allowed": True,
                },
                semantic_score=1.0,
            )
        ]


def test_hybrid_retrieval_recovers_sparse_only_candidate_and_accepts_variants() -> None:
    sparse = SparseOnlyStore()
    service = RetrievalService(
        embeddings=FakeEmbedding(),
        vector_store=EmptyDenseStore(),
        lexical_store=sparse,
        fetch_k=12,
        top_k=4,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(
        service.retrieve(
            "¿Están altos?",
            query_variants=["leucocitos altos en un hemograma canino"],
        )
    ).chunks

    assert [result.id for result in results] == ["wbc-sparse"]
    assert any("leucocitos" in query for query in sparse.queries)
    assert results[0].title == "Schalm's Veterinary Hematology, 6th edition"
    assert results[0].source_path == ""
    assert results[0].authors == ("Douglas J. Weiss", "K. Jane Wardrop")
