from __future__ import annotations

import re

from app.modules.llm_chat.application.services.conversation_memory import normalize_text
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    HemogramParameter,
    HemogramStudy,
    ResolvedQuestion,
    clinical_fact_id,
)


_COMPARISON = re.compile(
    r"\b(anterior|previo|antes|compara|comparacion|evolucion|cambi\w*|"
    r"aument\w*|disminu\w*|subi\w*|bajaron|bajado|bajando)\b"
)


def project_public_case_facts(value: object) -> list[dict[str, object]]:
    """Accept only the intentionally small public evidence contract.

    Full clinical payloads remain available to the controlled prompt builder,
    but are never copied wholesale into public response metadata. This also
    prevents legacy cached rows from exposing their historical ``case_facts``.
    """

    if not isinstance(value, list):
        return []
    projected: list[dict[str, object]] = []
    allowed_keys = {
        "parameter",
        "fact_id",
        "value",
        "code",
        "analysis_id",
        "study_key",
        "study_date",
        "unit",
        "status",
        "reference_min",
        "reference_max",
    }
    for item in value:
        if not isinstance(item, dict) or not set(item).issubset(allowed_keys):
            continue
        parameter = item.get("parameter")
        fact_value = item.get("value")
        if not isinstance(parameter, str) or not parameter.strip():
            continue
        if not isinstance(fact_value, (str, int, float)):
            continue
        public = {
            "parameter": parameter.strip(),
            "value": str(fact_value).strip(),
        }
        for key in allowed_keys - {"parameter", "value"}:
            field = item.get(key)
            if isinstance(field, (str, int, float)) and str(field).strip():
                public[key] = str(field).strip()
        projected.append(public)
    return projected


def project_relevant_case_facts(
    clinical: ClinicalContext,
    question: ResolvedQuestion,
) -> list[dict[str, object]]:
    """Project exact facts referenced by the generated response.

    This function chooses data, not prose. The values are deterministic so the
    frontend can show traceability while all normal user-visible wording still
    comes from the LLM.
    """

    code = question.referenced_parameter
    if not code:
        return []
    compare = bool(_COMPARISON.search(normalize_text(question.standalone)))
    targets = _targets(clinical, code, compare=compare)
    if not targets:
        return []
    if compare:
        latest_unit = _normalized_unit(targets[-1][1].unit)
        targets = [
            target
            for target in targets
            if _normalized_unit(target[1].unit) == latest_unit
        ]
    return [_public_fact(study, parameter) for study, parameter in targets]


def project_selected_case_facts(
    clinical: ClinicalContext,
    parameter_codes: frozenset[str] | None,
    *,
    limit: int = 4,
) -> list[dict[str, object]]:
    """Expose a bounded trace of selected evidence without dumping the CBC."""
    if parameter_codes is None or not parameter_codes:
        return []
    studies = (
        (clinical.selected,)
        if clinical.mode == "selected_hemogram" and clinical.selected
        else clinical.history
    )
    if not studies:
        return []
    latest = studies[-1]
    values = {
        item.canonical_name: item
        for item in latest.parameters
        if item.canonical_name in parameter_codes
    }
    return [
        _public_fact(latest, values[code])
        for code in sorted(parameter_codes)
        if code in values
    ][: max(0, int(limit))]


def _targets(
    clinical: ClinicalContext,
    code: str,
    *,
    compare: bool,
) -> list[tuple[HemogramStudy, HemogramParameter]]:
    if clinical.mode == "selected_hemogram" and clinical.selected:
        current = _parameter(clinical.selected, code)
        if current is None:
            return []
        return [(clinical.selected, current)]
    if clinical.mode == "hemogram_history":
        series = _series(clinical.history, code)
        return series if compare else series[-1:]
    return []


def _series(
    studies: tuple[HemogramStudy, ...],
    code: str,
) -> list[tuple[HemogramStudy, HemogramParameter]]:
    return [
        (study, parameter)
        for study in studies
        for parameter in [_parameter(study, code)]
        if parameter is not None
    ]


def _parameter(study: HemogramStudy, code: str) -> HemogramParameter | None:
    return next(
        (item for item in study.parameters if item.canonical_name == code),
        None,
    )


def _normalized_unit(unit: str | None) -> str:
    translation = str.maketrans(
        {"×": "x", "·": "x", "µ": "u", "μ": "u", "³": "3", "⁶": "6", "⁹": "9"}
    )
    return re.sub(
        r"[\s^*()]",
        "",
        str(unit or "").casefold().translate(translation),
    )


def _public_fact(
    study: HemogramStudy,
    parameter: HemogramParameter,
) -> dict[str, object]:
    return {
        "parameter": parameter.canonical_name,
        "fact_id": clinical_fact_id(study.analysis_id, parameter.canonical_name),
        "code": parameter.canonical_name,
        "value": parameter.value_text,
        "analysis_id": study.analysis_id,
        "study_key": study.study_key,
        "study_date": study.date,
        "unit": parameter.unit or "",
        "status": parameter.flag,
        "reference_min": (
            str(parameter.reference_min) if parameter.reference_min is not None else ""
        ),
        "reference_max": (
            str(parameter.reference_max) if parameter.reference_max is not None else ""
        ),
    }
