from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RetrievalPolicy(str, Enum):
    """Whether retrieval is requested, independently from its outcome."""

    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class RetrievalStatus(str, Enum):
    """Usable retrieval outcome for one concrete generation attempt."""

    NOT_REQUESTED = "not_requested"
    USED = "used"
    NO_MATCH = "no_match"
    UNAVAILABLE = "unavailable"


class KnowledgeMode(str, Enum):
    """Knowledge actually available to generation, not a retrieval decision."""

    PARAMETRIC = "parametric"
    DATABASE = "database"
    RAG_AUGMENTED = "rag_augmented"
    DATABASE_AND_RAG = "database_and_rag"
    SAFETY_BOUNDARY = "safety_boundary"


@dataclass(frozen=True, slots=True)
class ResponsePlan:
    """Provider-neutral constraints for a future response planner.

    Stage 1 defines this contract without replacing the current router. In
    particular, retrieval policy, retrieval status, and knowledge mode remain
    separate concepts and this plan never contains user-visible prose.
    """

    domain: str
    intent: str
    risk_level: str
    retrieval_policy: RetrievalPolicy
    allow_parametric_knowledge: bool
    context_scope: str
    allowed_claim_types: tuple[str, ...]
    required_fact_ids: tuple[str, ...]
    required_safety_elements: tuple[str, ...]
    prohibited_content: tuple[str, ...]
    output_language: str = "es"
    max_generation_attempts: int = 2

    def __post_init__(self) -> None:
        required_text = {
            "domain": self.domain,
            "intent": self.intent,
            "risk_level": self.risk_level,
            "context_scope": self.context_scope,
            "output_language": self.output_language,
        }
        for name, value in required_text.items():
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        if self.max_generation_attempts < 1:
            raise ValueError("max_generation_attempts must be positive")


__all__ = [
    "KnowledgeMode",
    "ResponsePlan",
    "RetrievalPolicy",
    "RetrievalStatus",
]
