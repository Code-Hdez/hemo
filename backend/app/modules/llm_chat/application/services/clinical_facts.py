from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from app.modules.llm_chat.domain.clinical import (
    ClinicalFactKey,
    TruthState,
    clinical_fact_id,
    normalize_clinical_unit,
)


_RED_CELL_CODES = {"RBC", "HGB", "HCT"}


@dataclass(frozen=True, slots=True)
class LabFact:
    code: str
    value: float | None
    unit: str
    reference_low: float | None
    reference_high: float | None
    status: str
    analysis_id: str = "__single__"
    study_key: str = ""
    study_date: str = ""
    canonical_name: str = ""
    display_name: str = ""
    aliases: tuple[str, ...] = ()
    fact_id: str = ""
    pet_id: str | None = None
    date_origin: str = "unknown"
    laboratory: str | None = None
    analyzer: str | None = None
    data_origin: str = "analysis_database"
    source_revision: str = "unknown"

    @property
    def key(self) -> ClinicalFactKey:
        return ClinicalFactKey(self.analysis_id, self.code)

    @property
    def provenance(self) -> Mapping[str, str]:
        return MappingProxyType(
            {
                key: value
                for key, value in {
                    "pet_id": self.pet_id or "",
                    "analysis_id": self.analysis_id,
                    "field": self.code,
                    "study_date": self.study_date,
                    "date_origin": self.date_origin,
                    "laboratory": self.laboratory or "",
                    "analyzer": self.analyzer or "",
                    "data_origin": self.data_origin,
                    "source_revision": self.source_revision,
                }.items()
                if value
            }
        )


@dataclass(frozen=True, slots=True)
class ClinicalFactIndex:
    """Lossless indexes over the clinical facts claimable in one validation.

    ``by_code`` deliberately stores a chronological tuple.  Callers must opt in
    to ``latest`` instead of silently overwriting earlier measurements.
    """

    by_key: Mapping[ClinicalFactKey, LabFact]
    by_code: Mapping[str, tuple[LabFact, ...]]
    by_study: Mapping[str, tuple[LabFact, ...]]

    @property
    def available_codes(self) -> frozenset[str]:
        return frozenset(self.by_code)

    def series(self, code: str) -> tuple[LabFact, ...]:
        return self.by_code.get(code.strip().upper(), ())

    def latest(self, code: str) -> LabFact | None:
        values = self.series(code)
        return values[-1] if values else None

    def previous(self, code: str) -> LabFact | None:
        values = self.series(code)
        return values[-2] if len(values) >= 2 else None

    def compatible_series(self, code: str) -> tuple[LabFact, ...]:
        """Return the newest unit-compatible run for a parameter.

        No implicit unit conversion is safe for patient facts.  A unit change
        starts another run rather than mixing incomparable values.
        """

        values = self.series(code)
        if not values:
            return ()
        unit = normalize_clinical_unit(values[-1].unit)
        compatible: list[LabFact] = []
        for value in reversed(values):
            if normalize_clinical_unit(value.unit) != unit:
                break
            compatible.append(value)
        return tuple(reversed(compatible))


def enrich_case_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add derived checks per study without collapsing longitudinal values."""

    enriched: list[dict[str, Any]] = []
    facts_by_study: dict[str, dict[str, LabFact]] = {}
    for fact in facts:
        copy = dict(fact)
        lab_fact = lab_fact_from_mapping(copy)
        if lab_fact is not None:
            copy.setdefault("status", lab_fact.status)
            copy["derived_status"] = lab_fact.status
            copy.setdefault("reference_low", lab_fact.reference_low)
            copy.setdefault("reference_high", lab_fact.reference_high)
            copy.setdefault("ref_min", lab_fact.reference_low)
            copy.setdefault("ref_max", lab_fact.reference_high)
            study_facts = facts_by_study.setdefault(lab_fact.analysis_id, {})
            if lab_fact.code in study_facts:
                raise ValueError("clinical_facts_duplicate_analysis_parameter")
            study_facts[lab_fact.code] = lab_fact
        enriched.append(copy)

    for study_id, lab_facts in facts_by_study.items():
        if not lab_facts:
            continue
        present_codes = _RED_CELL_CODES.intersection(lab_facts)
        missing_codes = _RED_CELL_CODES.difference(present_codes)
        red_facts = [lab_facts[code] for code in sorted(present_codes)]
        red_cell_mass_decreased = _decreased_truth_state(
            red_facts,
            complete=not missing_codes,
        )
        all_red_cell_values_normal = _all_normal_truth_state(
            [fact.status for fact in red_facts],
            complete=not missing_codes,
        )
        example = next(iter(lab_facts.values()))
        enriched.extend(
            [
                _derived_fact(
                    "red_cell_mass_decreased",
                    red_cell_mass_decreased,
                    analysis_id=study_id,
                    study_key=example.study_key,
                    study_date=example.study_date,
                    present_codes=present_codes,
                    missing_codes=missing_codes,
                ),
                _derived_fact(
                    "anemia_pattern_possible",
                    red_cell_mass_decreased,
                    analysis_id=study_id,
                    study_key=example.study_key,
                    study_date=example.study_date,
                    present_codes=present_codes,
                    missing_codes=missing_codes,
                ),
                _derived_fact(
                    "all_red_cell_values_normal",
                    all_red_cell_values_normal,
                    analysis_id=study_id,
                    study_key=example.study_key,
                    study_date=example.study_date,
                    present_codes=present_codes,
                    missing_codes=missing_codes,
                ),
            ]
        )
    return enriched


def lab_fact_from_mapping(fact: Mapping[str, Any]) -> LabFact | None:
    raw_provenance = fact.get("provenance")
    provenance = (
        raw_provenance if isinstance(raw_provenance, Mapping) else {}
    )
    fact_type = str(fact.get("fact_type") or "").strip()
    if fact_type and fact_type != "lab_value":
        return None
    code = str(fact.get("code") or fact.get("parameter") or "").strip().upper()
    if not code:
        return None
    value = _number(fact.get("value"))
    if value is None:
        return None
    low = _number(
        fact.get("reference_low")
        if fact.get("reference_low") is not None
        else fact.get("ref_min")
    )
    high = _number(
        fact.get("reference_high")
        if fact.get("reference_high") is not None
        else fact.get("ref_max")
    )
    recorded_status = str(
        fact.get("status") or fact.get("flag") or ""
    ).strip().lower()
    if recorded_status == "critical":
        status = "critical"
    elif low is not None and value < low:
        status = "low"
    elif high is not None and value > high:
        status = "high"
    elif low is not None and high is not None:
        status = "normal"
    elif low is not None or high is not None:
        status = "unknown"
    elif recorded_status in {"low", "high", "normal", "critical", "unknown"}:
        status = recorded_status
    else:
        status = "unknown"
    analysis_id = str(
        fact.get("analysis_id")
        or provenance.get("analysis_id")
        or fact.get("study_key")
        or "__single__"
    ).strip() or "__single__"
    study_key = str(fact.get("study_key") or "").strip()
    study_date = str(
        fact.get("analysis_date") or fact.get("study_date") or fact.get("date") or ""
    ).strip()
    canonical_name = str(fact.get("parameter") or code).strip()
    display_name = str(fact.get("label") or canonical_name).strip()
    raw_aliases = fact.get("aliases")
    aliases = (
        tuple(str(alias).strip() for alias in raw_aliases if str(alias).strip())
        if isinstance(raw_aliases, (list, tuple, set, frozenset))
        else ()
    )
    return LabFact(
        code=code,
        value=value,
        unit=str(fact.get("unit") or "").strip(),
        reference_low=low,
        reference_high=high,
        status=status,
        analysis_id=analysis_id,
        study_key=study_key,
        study_date=study_date,
        canonical_name=canonical_name,
        display_name=display_name,
        aliases=aliases,
        fact_id=str(fact.get("fact_id") or clinical_fact_id(analysis_id, code)),
        pet_id=str(fact.get("pet_id") or provenance.get("pet_id") or "").strip()
        or None,
        date_origin=str(
            fact.get("date_origin") or provenance.get("date_origin") or "unknown"
        ).strip(),
        laboratory=str(
            fact.get("laboratory") or provenance.get("laboratory") or ""
        ).strip()
        or None,
        analyzer=str(
            fact.get("analyzer") or provenance.get("analyzer") or ""
        ).strip()
        or None,
        data_origin=str(
            fact.get("data_origin")
            or provenance.get("data_origin")
            or "analysis_database"
        ).strip(),
        source_revision=str(
            fact.get("source_revision")
            or provenance.get("source_revision")
            or "unknown"
        ).strip(),
    )


def temporal_fact_index(facts: list[dict[str, Any]]) -> ClinicalFactIndex:
    """Build compound and longitudinal indexes while preserving source order."""

    by_key: dict[ClinicalFactKey, LabFact] = {}
    by_code: dict[str, list[LabFact]] = {}
    by_study: dict[str, list[LabFact]] = {}
    pet_ids: set[str] = set()
    for fact in facts:
        lab_fact = lab_fact_from_mapping(fact)
        if lab_fact is None or lab_fact.code.startswith("DERIVED:"):
            continue
        if lab_fact.pet_id:
            pet_ids.add(lab_fact.pet_id)
        if lab_fact.key in by_key:
            raise ValueError("clinical_facts_duplicate_analysis_parameter")
        by_key[lab_fact.key] = lab_fact
        by_code.setdefault(lab_fact.code, []).append(lab_fact)
        by_study.setdefault(lab_fact.analysis_id, []).append(lab_fact)
    if len(pet_ids) > 1:
        raise ValueError("clinical_facts_cannot_mix_patients")
    return ClinicalFactIndex(
        by_key=MappingProxyType(dict(by_key)),
        by_code=MappingProxyType(
            {code: tuple(values) for code, values in by_code.items()}
        ),
        by_study=MappingProxyType(
            {study_id: tuple(values) for study_id, values in by_study.items()}
        ),
    )


def fact_index(facts: list[dict[str, Any]]) -> dict[str, LabFact]:
    """Compatibility view for legacy single-study consumers.

    New validation and history code must use :func:`temporal_fact_index`.
    Keeping this facade avoids breaking unrelated callers while making the
    lossy operation explicit and isolated.
    """

    index = temporal_fact_index(facts)
    return {code: values[-1] for code, values in index.by_code.items() if values}


def _derived_fact(
    name: str,
    truth_state: TruthState,
    *,
    analysis_id: str,
    study_key: str,
    study_date: str,
    present_codes: set[str],
    missing_codes: set[str],
) -> dict[str, object]:
    return {
        "type": "derived_fact",
        "code": f"DERIVED:{name}",
        "label": name,
        "value": (
            True
            if truth_state == "true"
            else False
            if truth_state == "false"
            else None
        ),
        "status": truth_state,
        "truth_state": truth_state,
        "analysis_id": analysis_id,
        "study_key": study_key,
        "analysis_date": study_date,
        "required_codes": sorted(_RED_CELL_CODES),
        "present_codes": sorted(present_codes),
        "missing_codes": sorted(missing_codes),
    }


def _decreased_truth_state(
    facts: list[LabFact],
    *,
    complete: bool,
) -> TruthState:
    if any(
        fact.status == "low"
        or (
            fact.value is not None
            and fact.reference_low is not None
            and fact.value < fact.reference_low
        )
        for fact in facts
    ):
        return "true"
    if not complete:
        return "insufficient_data"
    if any(fact.status in {"unknown", "critical"} for fact in facts):
        return "unknown"
    return "false"


def _all_normal_truth_state(
    statuses: list[str],
    *,
    complete: bool,
) -> TruthState:
    if not complete:
        return "insufficient_data"
    if any(status == "unknown" for status in statuses):
        return "unknown"
    return "true" if all(status == "normal" for status in statuses) else "false"


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
