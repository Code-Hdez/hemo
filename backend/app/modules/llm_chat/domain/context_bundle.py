from __future__ import annotations

from dataclasses import dataclass

from app.modules.llm_chat.domain.clinical import (
    ConversationMemory,
    HemogramStudy,
    PatientContext,
)
from app.modules.llm_chat.domain.entities import RetrievedChunk


@dataclass(frozen=True, slots=True)
class DerivedClinicalFinding:
    """One ML or extraction-quality signal surfaced as a traceable fact.

    Distinct from ``ClinicalParameter``/``VerifiedFact`` (domain/clinical.py),
    which represent structured lab *values*. This carries the ML
    classification and extraction-quality signals a study's
    ``classifier_outcome``/``quality_flags``/``extraction_confidence`` already
    contain but that had no stable, claimable identifier before this stage.
    ``fact_id`` is for internal traceability and validation only; it must
    never be rendered verbatim to the user.
    """

    fact_id: str
    fact_type: str
    value: object
    unit: str | None
    study_id: str | None
    study_date: str | None
    provenance: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Authorized, traceable context for one chat turn, across all three modes.

    Built once per turn from ``ClinicalContext`` (the existing PostgreSQL
    authorization boundary) before any prompt-budget compaction runs. This is
    the single typed source later stages read from; it does not itself decide
    what fits in the final prompt — that remains the ``PromptBudgetPlanner``
    responsibility of a later stage. ``omitted_fact_ids`` records facts that
    were authorized but not materialized into the prompt for this turn (for
    example due to the existing token-budget selector), so a later stage can
    make that omission explicit instead of silently dropping data.
    """

    mode: str
    patient_profile: PatientContext | None
    selected_study: HemogramStudy | None
    history: tuple[HemogramStudy, ...]
    ml_findings: tuple[DerivedClinicalFinding, ...]
    quality_findings: tuple[DerivedClinicalFinding, ...]
    # Full conversational continuity for this turn (etapa 3): last exchange,
    # recent window, structured summary, active topic/parameter/analysis,
    # style preference and insistence state. ``conversation.conversation_revision``
    # is the distinct, stable conversation identity; ``context_revision``
    # below is specifically the clinical-data revision (see
    # ``ConversationMemory`` for why the two must not be conflated).
    conversation: ConversationMemory
    rag_evidence: tuple[RetrievedChunk, ...] = ()
    omitted_fact_ids: tuple[str, ...] = ()
    context_revision: int = 1


__all__ = ["ContextBundle", "DerivedClinicalFinding"]
