"""Construccion de snapshots clinicos para el chat contextual."""

from __future__ import annotations

from datetime import datetime
from typing import Any

_ABNORMAL_STATUSES = {"low", "high", "critical"}

_CBC_METRICS = {"WBC", "RBC", "HGB", "HCT", "PLT", "LYM", "NEU", "MONO", "EOS", "BASO"}


def _pet_profile(pet: dict[str, Any] | None) -> dict[str, Any] | None:
    if not pet:
        return None
    birth_year = pet.get("birth_year")
    age_label = None
    try:
        if birth_year:
            age = max(0, datetime.now().year - int(birth_year))
            age_label = (
                "Menos de 1 año" if age == 0 else f"{age} año{'s' if age != 1 else ''}"
            )
    except (TypeError, ValueError):
        age_label = None
    return {
        "id": pet.get("id"),
        "name": pet.get("name"),
        "breed": pet.get("breed"),
        "birth_year": birth_year,
        "age_label": age_label,
        "sex": pet.get("sex"),
        "weight_kg": pet.get("weight_kg"),
        "notes": pet.get("notes"),
        "residence_zone_code": pet.get("residence_zone_code"),
        "residence_label": pet.get("residence_label"),
    }


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    metadata = metadata or {}
    allowed = [
        "species",
        "breed",
        "gender",
        "age_str",
        "age_years",
        "date_result",
        "clinic",
        "location",
    ]
    return {key: metadata.get(key) for key in allowed if metadata.get(key) is not None}


def _build_abnormal_values(lab_values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": lv.get("name"),
            "value": lv.get("value"),
            "unit": lv.get("unit"),
            "status": lv.get("status"),
            "ref_min": lv.get("ref_min"),
            "ref_max": lv.get("ref_max"),
        }
        for lv in lab_values
        if str(lv.get("status", "")).lower() in _ABNORMAL_STATUSES
    ]


def _feature_row_to_dict(feature_row: Any) -> dict[str, float]:
    try:
        if getattr(feature_row, "empty", False):
            return {}
        row = feature_row.iloc[0].to_dict()
        return {
            str(key): round(float(value), 4)
            for key, value in row.items()
            if value is not None
        }
    except Exception:
        return {}


def _cbc_from_lab_values(lab_values: list[dict[str, Any]]) -> dict[str, float]:
    cbc: dict[str, float] = {}
    for item in lab_values:
        name = str(item.get("name") or "").upper()
        if name not in _CBC_METRICS:
            continue
        try:
            cbc[name] = round(float(item.get("value")), 4)
        except (TypeError, ValueError):
            continue
    return cbc


def _legacy_labels_from_findings(
    findings: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    active_labels: list[str] = []
    qc_labels: list[str] = []
    for finding in findings:
        label = str(finding.get("label") or "").strip()
        detail = str(finding.get("detail") or "").strip()
        lowered = f"{label} {detail}".lower()
        if not label:
            continue
        if any(
            term in lowered
            for term in (
                "frotis",
                "agregado",
                "interferencia",
                "control de calidad",
                "qc_",
            )
        ):
            qc_labels.append(
                label
                if label.upper().startswith("QC_")
                else f"QC_{label.replace(' ', '_').upper()}"
            )
            continue
        active_labels.append(label)
    return active_labels[:6], qc_labels[:6]


def build_case_snapshot(
    *,
    result_dict: dict[str, Any],
    extraction: Any,
    prediction: Any,
    pet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construye un snapshot interno enriquecido para un analisis nuevo."""
    probabilities = {
        str(label): round(float(prob), 4)
        for label, prob in (prediction.probabilities or {}).items()
    }
    active_labels = sorted(
        [
            label
            for label, is_active in (prediction.predictions or {}).items()
            if is_active
        ]
    )
    qc_labels = [label for label in active_labels if label.startswith("QC_")]
    feature_values = _feature_row_to_dict(prediction.feature_row)
    abnormal_values = _build_abnormal_values(result_dict.get("lab_values", []))

    return {
        "snapshot_type": "analysis",
        "schema_version": "1.0.0",
        "limited_context": False,
        "analysis_id": result_dict.get("id"),
        "created_at": result_dict.get("created_at"),
        "pet_id": pet.get("id") if pet else None,
        "pet_name": pet.get("name") if pet else None,
        "pet_profile": _pet_profile(pet),
        "species": result_dict.get("species")
        or extraction.metadata.get("species")
        or "Canino",
        "quality_score": result_dict.get("quality_score"),
        "confidence": result_dict.get("confidence"),
        "summary": result_dict.get("summary"),
        "diagnoses": result_dict.get("diagnoses", []),
        "findings": result_dict.get("findings", []),
        "lab_values": result_dict.get("lab_values", []),
        "abnormal_values": abnormal_values,
        "metadata": _safe_metadata(getattr(extraction, "metadata", None)),
        "cbc": {
            str(key): round(float(value), 4)
            for key, value in (getattr(extraction, "cbc", {}) or {}).items()
            if value is not None
        },
        "instrument_comments": getattr(extraction, "comments", None),
        "active_labels": active_labels,
        "qc_labels": qc_labels,
        "probabilities": probabilities,
        "feature_values": feature_values,
        "classifier_outcome": {
            "classification_status": (
                "NO_PREDICTION"
                if str(getattr(prediction, "status", "success")) == "no_prediction"
                else "CLASSIFIED"
                if [label for label in active_labels if not label.startswith("QC_")]
                else "NO_TARGET_PATTERN_DETECTED"
            ),
            "active_labels": [
                label for label in active_labels if not label.startswith("QC_")
            ],
            "probabilities": probabilities,
            "model_version": result_dict.get("model_version"),
            "policy_version": result_dict.get("policy_version"),
            "schema_version": result_dict.get("schema_version"),
            "uploaded_at": result_dict.get("created_at"),
            "sample_date": _safe_metadata(
                getattr(extraction, "metadata", None)
            ).get("date_result"),
        },
    }


def rebuild_case_snapshot_from_analysis(
    analysis: dict[str, Any],
    pet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconstruye un snapshot reducido para analisis legados sin contexto interno."""
    lab_values = analysis.get("lab_values", [])
    abnormal_values = _build_abnormal_values(lab_values)
    active_labels, qc_labels = _legacy_labels_from_findings(
        analysis.get("findings", [])
    )
    return {
        "snapshot_type": "analysis",
        "schema_version": "1.0.0",
        "limited_context": True,
        "analysis_id": analysis.get("id"),
        "created_at": analysis.get("created_at"),
        "pet_id": pet.get("id") if pet else analysis.get("_pet_id"),
        "pet_name": pet.get("name") if pet else None,
        "pet_profile": _pet_profile(pet),
        "species": analysis.get("species") or "Canino",
        "quality_score": analysis.get("quality_score"),
        "confidence": analysis.get("confidence"),
        "summary": analysis.get("summary"),
        "diagnoses": analysis.get("diagnoses", []),
        "findings": analysis.get("findings", []),
        "lab_values": lab_values,
        "abnormal_values": abnormal_values,
        "metadata": {},
        "cbc": _cbc_from_lab_values(lab_values),
        "instrument_comments": None,
        "active_labels": active_labels,
        "qc_labels": qc_labels,
        "probabilities": {},
        "feature_values": {},
        "classifier_outcome": {
            "classification_status": "LEGACY_INCOMPLETE",
            "uploaded_at": analysis.get("created_at"),
            "active_labels": active_labels,
        },
    }


def _lab_value_number(analysis: dict[str, Any], target_name: str) -> float | None:
    for item in analysis.get("lab_values", []):
        if str(item.get("name")).upper() == target_name.upper():
            try:
                return float(item.get("value"))
            except (TypeError, ValueError):
                return None
    return None


def build_history_snapshot(
    *,
    pet: dict[str, Any],
    analyses: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resume un historial corto (2-5 analisis) para comparacion conversacional."""
    ordered = sorted(
        analyses, key=lambda item: item.get("created_at") or "", reverse=True
    )[:5]
    latest = ordered[0] if ordered else {}
    previous = ordered[1] if len(ordered) > 1 else None

    tracked = ["WBC", "RBC", "HGB", "HCT", "PLT"]
    trends: list[dict[str, Any]] = []
    if previous:
        for key in tracked:
            latest_val = _lab_value_number(latest, key)
            prev_val = _lab_value_number(previous, key)
            if latest_val is None or prev_val is None:
                continue
            delta = round(latest_val - prev_val, 3)
            if delta == 0:
                direction = "sin cambio"
            elif delta > 0:
                direction = "subio"
            else:
                direction = "bajo"
            trends.append(
                {
                    "metric": key,
                    "latest": latest_val,
                    "previous": prev_val,
                    "delta": delta,
                    "direction": direction,
                }
            )

    return {
        "snapshot_type": "history",
        "schema_version": "1.0.0",
        "pet_id": pet.get("id"),
        "pet_name": pet.get("name"),
        "pet_profile": _pet_profile(pet),
        "used_history_window": len(ordered),
        "analysis_ids": [item.get("id") for item in ordered if item.get("id")],
        "latest_analysis_id": latest.get("id"),
        "latest_analysis_date": latest.get("created_at"),
        "latest_summary": latest.get("summary"),
        "latest_findings": latest.get("findings", []),
        "latest_diagnoses": latest.get("diagnoses", []),
        "trend_deltas": trends,
        "recent_analyses": [
            {
                "analysis_id": item.get("id"),
                "created_at": item.get("created_at"),
                "summary": item.get("summary"),
                "findings": item.get("findings", [])[:3],
            }
            for item in ordered
        ],
        "limited_context": any("_case_snapshot" not in item for item in ordered),
    }
