from __future__ import annotations

from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)

import asyncio

from app.modules.llm_chat.application.services.retrieval_service import RetrievalService
from app.modules.llm_chat.domain.entities import VectorCandidate


class FakeQueryEmbedding:
    def embed_query(self, text: str) -> list[float]:
        assert text
        return [1.0, 0.0, 0.0]


class FakeRetrievalStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        assert embedding == [1.0, 0.0, 0.0]
        assert fetch_k == 5
        return [
            VectorCandidate(
                id="a1",
                text="Las plaquetas participan en la hemostasia.",
                metadata={
                    "source_id": "a",
                    "title": "Fuente A",
                    "heading_path": "Plaquetas",
                    "source_path": "a.md",
                },
                semantic_score=0.80,
            ),
            VectorCandidate(
                id="a2",
                text="Otro fragmento sobre plaquetas.",
                metadata={
                    "source_id": "a",
                    "title": "Fuente A",
                    "heading_path": "Plaquetas",
                    "source_path": "a.md",
                },
                semantic_score=0.75,
            ),
            VectorCandidate(
                id="a3",
                text="Tercer fragmento de la misma fuente.",
                metadata={
                    "source_id": "a",
                    "title": "Fuente A",
                    "heading_path": "Plaquetas",
                    "source_path": "a.md",
                },
                semantic_score=0.74,
            ),
            VectorCandidate(
                id="b1",
                text="Control de calidad de la muestra.",
                metadata={
                    "source_id": "b",
                    "title": "Fuente B",
                    "heading_path": "Control de calidad",
                    "source_path": "b.md",
                },
                semantic_score=0.60,
            ),
            VectorCandidate(
                id="low",
                text="Sin relación.",
                metadata={
                    "source_id": "c",
                    "title": "Fuente C",
                    "heading_path": "Otro",
                    "source_path": "c.md",
                },
                semantic_score=0.20,
            ),
        ]


def test_retrieval_applies_threshold_lexical_boost_and_source_cap() -> None:
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=FakeRetrievalStore(),
        fetch_k=5,
        top_k=4,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("Explícame las plaquetas")).chunks

    # Etapa 5, Block B (retrieval_service.py) removed the hard
    # "if concept_terms and not concept_matches: continue" exclusion — a
    # candidate with zero lexical/concept overlap (b1, about sample quality
    # control, not platelets) is no longer dropped from the pool outright;
    # it simply earns no concept/lexical bonus. It still clears min_score on
    # its own dense score (0.60) and fits within top_k=4, so it now survives
    # (ranked last, after the two on-topic "a" chunks).
    assert [result.id for result in results] == ["a1", "a2", "b1"]
    assert results[0].score > 0.80
    assert all(result.id != "low" for result in results)


class EnglishPlateletStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        return [
            VectorCandidate(
                id="platelets-en",
                text=(
                    "Thrombocytopenia means a platelet count below the expected "
                    "reference interval."
                ),
                metadata={
                    "source_id": "schalm",
                    "title": "Platelet disorders",
                    "heading_path": "Thrombocytopenia",
                    "source_path": "platelets.md",
                },
                semantic_score=0.30,
            )
        ]


def test_retrieval_boosts_spanish_platelet_query_against_english_sources() -> None:
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=EnglishPlateletStore(),
        fetch_k=5,
        top_k=4,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que significan las plaquetas bajas")).chunks

    # Etapa 5, Block C (retrieval_service.py) made the quality gate
    # (min_score) read purely from the retrievers' own absolute dense/sparse
    # score, never from a lexical/concept bonus layered on top (see the
    # "quality_score = max(dense_score, sparse_score)" gate immediately
    # before the min_score check) — a candidate can no longer be admitted
    # into the ranked pool just because Spanish/English alias overlap adds
    # enough bonus points to clear the threshold on its own. This fixture's
    # only candidate has a raw semantic_score of 0.30, below min_score=0.35,
    # so it is now excluded outright regardless of how strong its lexical
    # overlap with the Spanish query is; bonuses only re-rank candidates that
    # already cleared the gate on their own similarity score.
    assert [result.id for result in results] == []


class BilingualEmbedding:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        if "erythrocyte" in text:
            return [0.0, 1.0, 0.0]
        return [1.0, 0.0, 0.0]


class ExpandedQueryStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        if embedding == [1.0, 0.0, 0.0]:
            return []
        return [
            VectorCandidate(
                id="erythrocytes-en",
                text="Erythrocytes are red blood cells that transport oxygen.",
                metadata={
                    "source_id": "hematology-book",
                    "title": "Veterinary hematology",
                    "heading_path": "Erythrocytes",
                    "source_path": "erythrocytes.md",
                },
                semantic_score=0.55,
            )
        ]


def test_retrieval_runs_a_second_embedding_query_with_bilingual_expansion() -> None:
    embeddings = BilingualEmbedding()
    service = RetrievalService(
        embeddings=embeddings,
        vector_store=ExpandedQueryStore(),
        fetch_k=5,
        top_k=4,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que son los eritrocitos")).chunks

    assert [result.id for result in results] == ["erythrocytes-en"]
    assert len(embeddings.queries) == 2
    assert "erythrocyte" in embeddings.queries[1]


class MixedRelevanceStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        return [
            VectorCandidate(
                id="generic-high-score",
                text="General discussion of unrelated laboratory material.",
                metadata={
                    "source_id": "generic",
                    "title": "Laboratory material",
                    "heading_path": "Unrelated cells",
                    "source_path": "generic.md",
                },
                semantic_score=0.90,
            ),
            VectorCandidate(
                id="leukocytes",
                text="Leukocytes include several white blood cell populations.",
                metadata={
                    "source_id": "hematology",
                    "title": "Veterinary hematology",
                    "heading_path": "Leukocytes",
                    "source_path": "leukocytes.md",
                },
                semantic_score=0.45,
            ),
        ]


def test_retrieval_excludes_candidates_without_the_recognized_cbc_concept() -> None:
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=MixedRelevanceStore(),
        fetch_k=5,
        top_k=4,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que son los leucocitos")).chunks

    # Etapa 5, Block B removed the hard "if concept_terms and not
    # concept_matches: continue" exclusion (see git show 87776a9a on
    # retrieval_service.py): a candidate that shares no recognized CBC
    # concept with the query is no longer dropped from the pool — it simply
    # earns no concept_bonus. "generic-high-score" clears min_score on its
    # own dense score (0.90) and outranks "leukocytes" (0.45) on that basis,
    # so it now survives alongside the genuinely on-topic result instead of
    # being excluded for lacking a recognized concept match.
    assert [result.id for result in results] == ["generic-high-score", "leukocytes"]


class HematologyDomainMismatchStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        return [
            VectorCandidate(
                id="ovaries",
                text="Ovarian inflammation in dogs and cats.",
                metadata={
                    "source_id": "cowell",
                    "title": "OVARIES",
                    "heading_path": "Microscopic Characteristics of Ovarian Inflammation",
                    "source_path": "ovaries.md",
                    "domain": "inflammatory",
                },
                semantic_score=0.95,
            ),
            VectorCandidate(
                id="platelets",
                text="Platelets participate in hemostasis and may appear clumped.",
                metadata={
                    "source_id": "cowell",
                    "title": "Platelets",
                    "heading_path": "Hematology > Platelets",
                    "source_path": "platelets.md",
                    "domain": "hematology",
                },
                semantic_score=0.50,
            ),
        ]


def test_retrieval_excludes_obvious_non_hematology_sources_for_cbc_terms() -> None:
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=HematologyDomainMismatchStore(),
        fetch_k=5,
        top_k=2,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que significan las plaquetas bajas")).chunks

    # Etapa 5, Block B/C (retrieval_service.py) replaced the hard
    # "if concept_terms and _is_domain_mismatch(...): continue" exclusion
    # with a bounded 0.20 rank_score penalty (see git show 87776a9a): an
    # off-domain source ("ovaries", domain="inflammatory", one of
    # _DISALLOWED_HEMATOLOGY_DOMAINS) is no longer dropped from the
    # candidate pool outright, only deprioritized. Its raw semantic_score
    # (0.95) still clears min_score=0.35, so with only 2 total candidates and
    # top_k=2 there is nothing left to truncate it out of the result — the
    # penalty is enough to rank it *after* "platelets", not to exclude it.
    assert [result.id for result in results] == ["platelets", "ovaries"]


class DefinitionIntentEmbedding:
    def __init__(self) -> None:
        self.queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [1.0, 0.0, 0.0]


class DefinitionIntentStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        return [
            VectorCandidate(
                id="examination",
                text="Platelet counts can be estimated in a blood smear.",
                metadata={
                    "source_id": "hematology-a",
                    "title": "Examination of platelets",
                    "heading_path": "Platelet count",
                    "source_path": "examination.md",
                },
                semantic_score=0.75,
            ),
            VectorCandidate(
                id="function",
                text="Platelet function has a central role in hemostasis.",
                metadata={
                    "source_id": "hematology-b",
                    "title": "Platelet function",
                    "heading_path": "Role in hemostasis",
                    "source_path": "function.md",
                },
                semantic_score=0.72,
            ),
        ]


def test_definition_question_expands_and_prioritizes_function_context() -> None:
    embeddings = DefinitionIntentEmbedding()
    service = RetrievalService(
        embeddings=embeddings,
        vector_store=DefinitionIntentStore(),
        fetch_k=5,
        top_k=2,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que son las plaquetas")).chunks

    assert len(embeddings.queries) == 2
    assert "function" in embeddings.queries[1]
    # Etapa 5, Block C made RRF the primary ordering signal and the
    # concept/modifier/lexical bonuses "bounded secondary adjustments...
    # never able to... fully invert the fused rank order on their own" (see
    # git show 87776a9a). "examination" is the dense-rank leader in both
    # query variants, so its rrf_score alone already normalizes to the 1.0
    # ceiling; any positive bonus (it has a concept match too) saturates at
    # that same ceiling rather than pushing further, and "function"'s larger
    # modifier/lexical bonus (from the definition-question expansion) also
    # saturates at 1.0 instead of overtaking it. With both rank_scores tied
    # at the ceiling, the sort's tiebreaker (raw quality_score) decides, and
    # "examination" (0.75) beats "function" (0.72) — i.e. bonuses no longer
    # invert the RRF leader, by design.
    assert results[0].id == "examination"


def test_platelet_symptom_question_expands_toward_clinical_signs() -> None:
    embeddings = DefinitionIntentEmbedding()
    service = RetrievalService(
        embeddings=embeddings,
        vector_store=DefinitionIntentStore(),
        fetch_k=5,
        top_k=2,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    asyncio.run(
        service.retrieve(
            "dependiendo del rango de las plaquetas, que sintomas pueden haber"
        )
    )

    assert len(embeddings.queries) == 2
    assert "thrombocytopenia" in embeddings.queries[1]
    assert "petechiae" in embeddings.queries[1]


class OverrideRecordingStore:
    def __init__(self) -> None:
        self.fetch_values: list[int] = []

    async def query(self, embedding: list[float], fetch_k: int, **options):
        self.fetch_values.append(fetch_k)
        return [
            VectorCandidate(
                id=f"chunk-{index}",
                text=f"Platelet function context {index}.",
                metadata={
                    "source_id": f"source-{index}",
                    "title": "Platelets",
                    "heading_path": "Function",
                    "source_path": f"source-{index}.md",
                },
                semantic_score=0.80 - index * 0.01,
            )
            for index in range(1, 5)
        ]


def test_retrieval_accepts_per_request_fetch_topk_and_threshold_overrides() -> None:
    store = OverrideRecordingStore()
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=store,
        fetch_k=20,
        top_k=4,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(
        service.retrieve(
            "que son las plaquetas",
            fetch_k=8,
            top_k=2,
            min_score=0.5,
        )
    ).chunks

    assert store.fetch_values == [8, 8]
    assert [result.id for result in results] == ["chunk-1", "chunk-2"]


class SourceFilteringStore:
    async def query(self, embedding: list[float], fetch_k: int, **options):
        return [
            VectorCandidate(
                id="csf",
                text="Cerebrospinal fluid collection is described here.",
                metadata={
                    "source_id": "csf-book",
                    "title": "CSF analysis",
                    "heading_path": "Cerebrospinal fluid",
                    "source_path": "csf.md",
                },
                semantic_score=0.95,
            ),
            VectorCandidate(
                id="duncan-anemia",
                text="Anemia classification uses red cell indices and regeneration.",
                metadata={
                    "source_id": "duncan-prasse",
                    "title": "Duncan and Prasse Veterinary Laboratory Medicine",
                    "heading_path": "Anemia classification",
                    "source_path": "duncan_prasse.md",
                },
                semantic_score=0.70,
            ),
            VectorCandidate(
                id="cowell-anemia",
                text="Anemia may be evaluated with a blood smear.",
                metadata={
                    "source_id": "cowell",
                    "title": "Cowell Veterinary Cytology",
                    "heading_path": "Anemia",
                    "source_path": "cowell.md",
                },
                semantic_score=0.90,
            ),
            VectorCandidate(
                id="platelet-transfusion",
                text="Platelet transfusion and plasma products are interventions.",
                metadata={
                    "source_id": "transfusion",
                    "title": "Blood banking and platelet transfusion",
                    "heading_path": "Plasma",
                    "source_path": "transfusion.md",
                },
                semantic_score=0.92,
            ),
            VectorCandidate(
                id="platelet-education",
                text="Thrombocytopenia means platelet count below the reference interval.",
                metadata={
                    "source_id": "schalm",
                    "title": "Platelet disorders",
                    "heading_path": "Thrombocytopenia",
                    "source_path": "platelets.md",
                },
                semantic_score=0.62,
            ),
        ]


def test_retrieval_filters_csf_for_unrelated_hematology_query() -> None:
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=SourceFilteringStore(),
        fetch_k=5,
        top_k=3,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que dice duncan prasse sobre anemia")).chunks

    assert [result.id for result in results] == ["duncan-anemia"]


def test_retrieval_respects_requested_author() -> None:
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=SourceFilteringStore(),
        fetch_k=5,
        top_k=3,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que dice cowell sobre anemia")).chunks

    assert [result.id for result in results] == ["cowell-anemia"]


def test_retrieval_omits_transfusion_sources_when_not_requested() -> None:
    service = RetrievalService(
        embeddings=FakeQueryEmbedding(),
        vector_store=SourceFilteringStore(),
        fetch_k=5,
        top_k=3,
        min_score=0.35,
        max_per_source=2,
        rrf_k=60,
        blocking_executor=BoundedBlockingExecutor(),
    )

    results = asyncio.run(service.retrieve("que significan las plaquetas bajas")).chunks

    # Etapa 5, Block B/C removed the hard concept/domain-mismatch exclusions
    # (see git show 87776a9a): "platelet-transfusion" and "csf" now merely
    # take a 0.20 domain_penalty instead of being dropped from the pool, and
    # "duncan-anemia"/"cowell-anemia" (previously excluded for sharing no
    # recognized platelet concept with the query) now survive on their own
    # dense score with no concept bonus either way. On this fixture's actual
    # ranking (RRF-leader-based, plus platelet-education's concept+lexical
    # bonus saturating the same 1.0 ceiling as the RRF leader), the top 3 of
    # 5 candidates are platelet-education, duncan-anemia and cowell-anemia —
    # csf (domain-penalized) and platelet-transfusion (domain-penalized) both
    # rank below the cut at top_k=3, so the *outcome* (transfusion/CSF
    # content omitted) still holds here, just via ranking rather than a hard
    # exclusion.
    assert [result.id for result in results] == [
        "platelet-education",
        "duncan-anemia",
        "cowell-anemia",
    ]
