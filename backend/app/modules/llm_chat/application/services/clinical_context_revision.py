"""Stable revision fingerprints for authorized clinical chat contexts.

The digest contains no prose from the conversation and is never used as a
substitute for authorization.  It only invalidates memory when the database
snapshot behind an otherwise identical context key changes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    HemogramStudy,
    PatientContext,
)


def clinical_context_fingerprint(context: ClinicalContext) -> str:
    payload: dict[str, Any] = {
        "mode": context.mode,
        "pet_id": context.pet_id,
        "selected_analysis_id": context.analysis_id,
        "patient": _patient_payload(context.patient),
        "studies": [
            _study_payload(study)
            for study in _authorized_studies(context)
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _authorized_studies(context: ClinicalContext) -> tuple[HemogramStudy, ...]:
    if context.mode == "selected_hemogram":
        return (context.selected,) if context.selected is not None else ()
    if context.mode == "hemogram_history":
        return context.history
    return ()


def _patient_payload(patient: PatientContext | None) -> dict[str, Any] | None:
    # Authorized profile fields (etapa 2's general+pet_id mode, and the
    # profile shown alongside any selected/history study) must rotate the
    # clinical revision when they change — a general-mode conversation about
    # one pet's weight/notes/residence must not keep answering from a stale
    # profile snapshot bound at conversation start.
    if patient is None:
        return None
    return {
        "pet_id": patient.pet_id,
        "name": patient.name,
        "species": patient.species,
        "breed": patient.breed,
        "sex": patient.sex,
        "age_years": patient.age_years,
        "birth_year": patient.birth_year,
        "weight_kg": patient.weight_kg,
        "notes": patient.notes,
        "residence_zone_code": patient.residence_zone_code,
        "residence_label": patient.residence_label,
    }


def _study_payload(study: HemogramStudy) -> dict[str, Any]:
    return {
        "analysis_id": study.analysis_id,
        "date": study.date,
        "data_origin": study.data_origin,
        "laboratory": study.laboratory,
        "analyzer": study.analyzer,
        "source_revision": study.source_revision,
        "extraction_confidence": study.extraction_confidence,
        # Structured quality/ML signals only — narrative text (``observations``)
        # is deliberately excluded: a rephrasing must not be treated as a
        # factual clinical-data change, and it is never authorized evidence.
        "quality_flags": list(study.quality_flags),
        "classifier_outcome": study.classifier_outcome,
        "parameters": [
            {
                "code": parameter.canonical_name,
                "value": parameter.value_text,
                "unit": parameter.unit,
                "reference_min": (
                    str(parameter.reference_min)
                    if parameter.reference_min is not None
                    else None
                ),
                "reference_max": (
                    str(parameter.reference_max)
                    if parameter.reference_max is not None
                    else None
                ),
                "status": parameter.flag,
                "reference_origin": parameter.reference_origin,
                "recorded_flag": parameter.recorded_flag,
                "extraction_confidence": parameter.extraction_confidence,
            }
            for parameter in study.parameters
        ],
    }
