from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationCase:
    case_id: str
    relevant_chunk_ids: frozenset[str]
    ranked_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    case_count: int
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    mrr: float
    ndcg_at_10: float


def evaluate_retrieval(
    cases: list[RetrievalEvaluationCase],
) -> RetrievalMetrics:
    if not cases:
        raise ValueError("At least one retrieval evaluation case is required")
    if any(not case.relevant_chunk_ids for case in cases):
        raise ValueError("Every evaluation case requires a relevance judgment")

    def recall(case: RetrievalEvaluationCase, limit: int) -> float:
        found = set(case.ranked_chunk_ids[:limit]) & case.relevant_chunk_ids
        return len(found) / len(case.relevant_chunk_ids)

    def reciprocal_rank(case: RetrievalEvaluationCase) -> float:
        for rank, chunk_id in enumerate(case.ranked_chunk_ids, start=1):
            if chunk_id in case.relevant_chunk_ids:
                return 1.0 / rank
        return 0.0

    def ndcg(case: RetrievalEvaluationCase, limit: int = 10) -> float:
        actual = sum(
            1.0 / math.log2(rank + 1)
            for rank, chunk_id in enumerate(case.ranked_chunk_ids[:limit], start=1)
            if chunk_id in case.relevant_chunk_ids
        )
        ideal_count = min(len(case.relevant_chunk_ids), limit)
        ideal = sum(
            1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1)
        )
        return actual / ideal if ideal else 0.0

    return RetrievalMetrics(
        case_count=len(cases),
        recall_at_1=fmean(recall(case, 1) for case in cases),
        recall_at_5=fmean(recall(case, 5) for case in cases),
        recall_at_10=fmean(recall(case, 10) for case in cases),
        mrr=fmean(reciprocal_rank(case) for case in cases),
        ndcg_at_10=fmean(ndcg(case) for case in cases),
    )


def reranker_is_promotable(
    *,
    baseline: RetrievalMetrics,
    candidate: RetrievalMetrics,
    minimum_rank_gain: float,
) -> bool:
    if baseline.case_count != candidate.case_count:
        raise ValueError("Baseline and candidate must evaluate the same case count")
    return bool(
        candidate.recall_at_5 >= baseline.recall_at_5
        and (
            candidate.mrr - baseline.mrr >= minimum_rank_gain
            or candidate.ndcg_at_10 - baseline.ndcg_at_10 >= minimum_rank_gain
        )
    )
