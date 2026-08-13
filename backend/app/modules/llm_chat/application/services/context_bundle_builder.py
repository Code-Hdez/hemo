from __future__ import annotations

from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    ClinicalContextSnapshot,
    ConversationMemory,
    HemogramStudy,
)
from app.modules.llm_chat.domain.context_bundle import (
    ContextBundle,
    DerivedClinicalFinding,
)
from app.modules.llm_chat.domain.entities import RetrievedChunk


def build_context_bundle(
    clinical: ClinicalContext,
    *,
    memory: ConversationMemory,
    context_revision: int,
    snapshot: ClinicalContextSnapshot | None = None,
    rag_evidence: tuple[RetrievedChunk, ...] = (),
) -> ContextBundle:
    """Project the authorized ``ClinicalContext`` into a traceable ContextBundle.

    Reuses the existing PostgreSQL-authorized ``ClinicalContext`` (and, when
    available, its ``ClinicalContextSnapshot`` materialization record) rather
    than re-querying PostgreSQL: this stage adds stable, traceable identity to
    the ML classification and extraction-quality signals that
    ``HemogramStudy`` already carries but that previously had no claimable
    fact_id outside narrative text.

    Works unmodified for all three modes: general (``selected``/``history``
    are always empty; only ``patient_profile`` may be populated when the user
    consented to sharing a pet in general scope), selected_hemogram (a single
    authorized study) and hemogram_history (every authorized study for the
    pet).
    """

    studies: dict[str, HemogramStudy] = {}
    if clinical.selected is not None:
        studies[clinical.selected.analysis_id] = clinical.selected
    for study in clinical.history:
        studies.setdefault(study.analysis_id, study)

    ml_findings: list[DerivedClinicalFinding] = []
    quality_findings: list[DerivedClinicalFinding] = []
    for study in studies.values():
        ml_findings.extend(_ml_findings(study))
        quality_findings.extend(_quality_findings(study))

    omitted_fact_ids: tuple[str, ...] = ()
    if snapshot is not None:
        omitted_keys = set(snapshot.prioritized_fact_keys) - set(
            snapshot.materialized_fact_keys
        )
        omitted_fact_ids = tuple(sorted(key.fact_id for key in omitted_keys))

    return ContextBundle(
        mode=clinical.mode,
        patient_profile=clinical.patient,
        selected_study=clinical.selected,
        history=clinical.history,
        ml_findings=tuple(ml_findings),
        quality_findings=tuple(quality_findings),
        conversation=memory,
        rag_evidence=rag_evidence,
        omitted_fact_ids=omitted_fact_ids,
        context_revision=context_revision,
    )


def _ml_findings(study: HemogramStudy) -> list[DerivedClinicalFinding]:
    outcome = study.classifier_outcome
    if not isinstance(outcome, dict):
        return []
    findings: list[DerivedClinicalFinding] = []
    status = outcome.get("classification_status")
    if isinstance(status, str) and status.strip():
        findings.append(
            DerivedClinicalFinding(
                fact_id=f"analysis:{study.analysis_id}:ml:classification_status",
                fact_type="ml_classification_status",
                value=status.strip(),
                unit=None,
                study_id=study.analysis_id,
                study_date=study.date,
                provenance=study.data_origin,
            )
        )
    probabilities = outcome.get("probabilities")
    probabilities = probabilities if isinstance(probabilities, dict) else {}
    active_labels = outcome.get("active_labels")
    for label in active_labels if isinstance(active_labels, list) else []:
        label_text = str(label or "").strip()
        if not label_text:
            continue
        confidence = probabilities.get(label_text)
        findings.append(
            DerivedClinicalFinding(
                fact_id=f"analysis:{study.analysis_id}:ml:label:{label_text}",
                fact_type="ml_classification_label",
                value=label_text,
                unit=None,
                study_id=study.analysis_id,
                study_date=study.date,
                provenance=study.data_origin,
                confidence=(
                    confidence if isinstance(confidence, (int, float)) else None
                ),
            )
        )
    return findings


def _quality_findings(study: HemogramStudy) -> list[DerivedClinicalFinding]:
    findings: list[DerivedClinicalFinding] = []
    if study.extraction_confidence is not None:
        findings.append(
            DerivedClinicalFinding(
                fact_id=f"analysis:{study.analysis_id}:quality:extraction_confidence",
                fact_type="extraction_confidence",
                value=study.extraction_confidence,
                unit=None,
                study_id=study.analysis_id,
                study_date=study.date,
                provenance=study.data_origin,
                confidence=study.extraction_confidence,
            )
        )
    for index, flag in enumerate(study.quality_flags, start=1):
        flag_text = str(flag or "").strip()
        if not flag_text:
            continue
        findings.append(
            DerivedClinicalFinding(
                fact_id=f"analysis:{study.analysis_id}:quality:flag:{index}",
                fact_type="quality_flag",
                value=flag_text,
                unit=None,
                study_id=study.analysis_id,
                study_date=study.date,
                provenance=study.data_origin,
            )
        )
    return findings


__all__ = ["build_context_bundle"]
