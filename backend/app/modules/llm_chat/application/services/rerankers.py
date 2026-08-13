from __future__ import annotations

import re
import unicodedata

from app.modules.llm_chat.domain.ports.retrieval import (
    RerankCandidate,
    RerankResult,
)


class NoopReranker:
    """Explicit baseline used when reranking is disabled or degraded.

    Etapa 5, Block D: this is no longer silently the only production
    implementation — composition.py only selects it when
    ``RAG_RERANKER_ENABLED`` is false, or as the fallback a real reranker
    degrades to on failure. It always preserves fusion order/scores exactly.
    """

    model_name = "none"

    async def rerank(
        self,
        _query: str,
        candidates: tuple[RerankCandidate, ...],
    ) -> list[RerankResult]:
        return [
            RerankResult(candidate_id=item.id, score=item.retrieval_score)
            for item in candidates
        ]


def _reranker_tokens(value: str) -> set[str]:
    """Unicode-aware tokenization shared with retrieval_service._terms.

    Not imported from there to avoid a circular import (retrieval_service
    already imports NoopReranker from this module).
    """
    folded = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char))
    return {term for term in re.findall(r"[^\W_]+", ascii_text) if len(term) >= 3}


class HeuristicMultilingualReranker:
    """Real, dependency-free second-pass rescoring, not a neural cross-encoder.

    Etapa 5, Block D asks for a configurable multilingual reranker but this
    task explicitly forbids downloading new models or calling external
    services. A cross-encoder (e.g. fastembed's ``TextCrossEncoder``) would
    require exactly that on first use, so it is not wired here. This
    reranker instead recomputes a language-agnostic query/candidate overlap
    directly over the full chunk text (the retrieval stage's lexical signals
    only look at title/heading/section metadata), blended with the fused
    retrieval score, and is honestly named for what it is. The ``Reranker``
    protocol this implements is unchanged, so a neural implementation can
    replace it later without touching any caller.
    """

    model_name = "heuristic-lexical-v1"

    def __init__(self, *, top_n: int = 20, blend_weight: float = 0.3) -> None:
        if top_n < 1:
            raise ValueError("top_n must be positive")
        if not 0.0 <= blend_weight <= 1.0:
            raise ValueError("blend_weight must be between zero and one")
        self.top_n = top_n
        self.blend_weight = blend_weight

    async def rerank(
        self,
        query: str,
        candidates: tuple[RerankCandidate, ...],
    ) -> list[RerankResult]:
        query_tokens = _reranker_tokens(query)
        results: list[RerankResult] = []
        for index, candidate in enumerate(candidates):
            if index >= self.top_n or not query_tokens:
                # Beyond the configured budget (or an empty/unusable query):
                # preserve fusion order/score rather than guess.
                results.append(
                    RerankResult(
                        candidate_id=candidate.id, score=candidate.retrieval_score
                    )
                )
                continue
            candidate_tokens = _reranker_tokens(candidate.text)
            if not candidate_tokens:
                results.append(
                    RerankResult(
                        candidate_id=candidate.id, score=candidate.retrieval_score
                    )
                )
                continue
            overlap = query_tokens & candidate_tokens
            # Jaccard-style coverage of the query by the candidate's own
            # vocabulary: language-agnostic (relies only on shared tokens,
            # never a translation dictionary), and distinct from the
            # retrieval stage's title/heading-focused lexical signal.
            content_overlap = len(overlap) / len(query_tokens)
            blended = (
                (1.0 - self.blend_weight) * candidate.retrieval_score
                + self.blend_weight * content_overlap
            )
            results.append(
                RerankResult(
                    candidate_id=candidate.id,
                    score=max(0.0, min(1.0, blended)),
                )
            )
        return results
