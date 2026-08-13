from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RerankCandidate:
    id: str
    text: str
    retrieval_score: float
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RerankResult:
    candidate_id: str
    score: float


class Reranker(Protocol):
    model_name: str

    async def rerank(
        self,
        query: str,
        candidates: tuple[RerankCandidate, ...],
    ) -> list[RerankResult]: ...


class RefreshableRetrievalIndex(Protocol):
    async def refresh(
        self,
        *,
        expected_index_fingerprint: str | None = None,
    ) -> object: ...
