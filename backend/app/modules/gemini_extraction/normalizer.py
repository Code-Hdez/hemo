"""Alias normalization for model-bound CBC extraction fields."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.modules.gemini_extraction.constants import MODEL_CBC_FIELD_SET
from app.modules.gemini_extraction.schemas import NormalizedExtraction
from app.modules.hematology.extraction_types import ExtractedParameter, coerce_lab_number


def normalize_label(text: str) -> str:
    """Normalize a lab label conservatively for alias lookup."""
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    ascii_text = ascii_text.lower()
    ascii_text = ascii_text.replace("%", " pct ")
    ascii_text = ascii_text.replace("#", " abs ")
    ascii_text = ascii_text.replace("+", " ")
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _alias_variants(*aliases: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for alias in aliases:
        mapping[normalize_label(alias)] = alias
    return mapping


_CANONICAL_ALIAS_GROUPS: dict[str, tuple[str, ...]] = {
    "WBC": (
        "WBC",
        "Leucocitos",
        "Leucocytes",
        "White Blood Cells",
        "White Blood Cell Count",
        "Recuento de leucocitos",
        "Leucocitos(WBC)",
        "VEC",
    ),
    "RBC": (
        "RBC",
        "Hematies",
        "Hematíes",
        "Eritrocitos",
        "Erythrocytes",
        "Red Blood Cells",
        "Red Blood Cell Count",
        "Hematíes(RBC)",
        "REC",
        "REBC",
    ),
    "HGB": (
        "HGB",
        "Hb",
        "Hemoglobin",
        "Hemoglobina",
        "Hemoglobina(HGB)",
        "HCB",
        "NGB",
    ),
    "HCT": (
        "HCT",
        "HT",
        "PCV",
        "Hematocrit",
        "Hematocrito",
        "Hematocrito (HCT)",
    ),
    "MCV": (
        "MCV",
        "VCM",
        "Mean Corpuscular Volume",
        "Volumen corpuscular medio",
        "MCV(MCV)",
        "HEV",
        "NEV",
    ),
    "MCH": (
        "MCH",
        "HCM",
        "Mean Corpuscular Hemoglobin",
        "Hemoglobina corpuscular media",
        "MCH(MCH)",
        "HCH",
        "NCH",
    ),
    "MCHC": (
        "MCHC",
        "CHCM",
        "Mean Corpuscular Hemoglobin Concentration",
        "Concentracion de hemoglobina corpuscular media",
        "Concentración de hemoglobina corpuscular media",
        "MCHC(MCHC)",
        "HCHC",
        "NCHC",
    ),
    "RDW": (
        "RDW",
        "RDW-CV",
        "RDW-SD",
        "Red Cell Distribution Width",
        "Distribucion eritrocitaria",
        "Distribución eritrocitaria",
        "Distribucion eritrocitaria (RDW-SD)",
        "Distribución eritrocitaria (RDW-SD)",
        "Distribucion eritrocitaria (RDW-CV)",
        "Distribución eritrocitaria (RDW-CV)",
        "RD¥-CV",
        "ROV-CV",
        "KOV-CV",
    ),
    "Reticulocytes_pct": (
        "% Reticulocytes",
        "Reticulocytes %",
        "Reticulocitos %",
        "RET%",
        "RET %",
        "Reticulocitos %(RET%)",
    ),
    "Reticulocytes": (
        "Reticulocytes",
        "Reticulocitos",
        "RET#",
        "RET abs",
        "Reticulocitos(RET#)",
    ),
    "Neutrophils_pct": (
        "% Neutrophils",
        "Neutrophils %",
        "Neutrofilos %",
        "Neutrófilos %",
        "NEU%",
        "Gran%",
        "GRA%",
        "Neutrofilos %(NEU%)",
        "Neutrófilos %(NEU%)",
    ),
    "Neutrophils": (
        "Neutrophils",
        "Neutrofilos",
        "Neutrófilos",
        "NEU#",
        "NEU",
        "Gran#",
        "GRA",
        "GRA#",
        "Neutrofilos(NEU#)",
        "Neutrófilos(NEU#)",
    ),
    "Lymphocytes_pct": (
        "% Lymphocytes",
        "Lymphocytes %",
        "Linfocitos %",
        "LYM%",
        "Lymph%",
        "Linfocitos %(LYM%)",
    ),
    "Lymphocytes": (
        "Lymphocytes",
        "Linfocitos",
        "LYM#",
        "LYM",
        "Lymph#",
        "Linfocitos(LYM#)",
    ),
    "Monocytes_pct": (
        "% Monocytes",
        "Monocytes %",
        "Monocitos %",
        "MON%",
        "Mid%",
        "Monocitos % (MON%)",
    ),
    "Monocytes": (
        "Monocytes",
        "Monocitos",
        "MON#",
        "MON",
        "Mid#",
        "Monocitos (MON#)",
    ),
    "Eosinophils": (
        "Eosinophils",
        "Eosinofilos",
        "Eosinófilos",
        "EOS#",
        "EOS",
        "Eosinofilos (EOS#)",
        "Eosinófilos (EOS#)",
    ),
    "Eosinophils_pct": (
        "% Eosinophils",
        "Eosinophils %",
        "Eosinofilos %",
        "Eosinófilos %",
        "EOS%",
        "Eosinofilos % (EOS%)",
        "Eosinófilos % (EOS%)",
    ),
    "Basophils": (
        "Basophils",
        "Basofilos",
        "Basófilos",
        "BAS#",
        "BAS",
        "BASO",
        "Basofilos(BAS#)",
        "Basófilos(BAS#)",
    ),
    "Basophils_pct": (
        "% Basophils",
        "Basophils %",
        "Basofilos %",
        "Basófilos %",
        "BAS%",
        "Basofilos %(BAS%)",
        "Basófilos %(BAS%)",
    ),
    "Platelets": (
        "Platelets",
        "Platelet Count",
        "Plaquetas",
        "PLT",
        "PLT#",
        "EPLT",
        "Recuento total de plaquetas",
        "Recuento absoluto de plaquetas",
    ),
    "PDW": (
        "PDW",
        "PDW-SD",
        "PDW-CV",
        "Platelet Distribution Width",
        "Distribucion plaquetaria",
        "Distribución plaquetaria",
        "Distribucion plaquetaria (PDW-SD)",
        "Distribución plaquetaria (PDW-SD)",
        "Distribucion plaquetaria (PDW-CV)",
        "Distribución plaquetaria (PDW-CV)",
        "POV",
    ),
    "MPV": (
        "MPV",
        "Mean Platelet Volume",
        "Volumen plaquetario medio",
        "MPV(MPV)",
        "WPV",
        "UPV",
    ),
    "PCT": (
        "PCT",
        "Plateletcrit",
        "Platelet Crit",
        "Plaquetocrito",
        "Plaquetocrito (PCT)",
    ),
}

_ALIAS_TO_KEY: dict[str, str] = {}
for _key, _aliases in _CANONICAL_ALIAS_GROUPS.items():
    for _alias in _aliases:
        _ALIAS_TO_KEY[normalize_label(_alias)] = _key
_ALIASES_BY_SPECIFICITY = sorted(
    _ALIAS_TO_KEY.items(),
    key=lambda item: len(item[0]),
    reverse=True,
)


def canonical_model_key(raw_label: str) -> str | None:
    """Return the model canonical key for a label, or None if unsupported."""
    normalized = normalize_label(raw_label)
    if not normalized:
        return None
    if normalized in _ALIAS_TO_KEY:
        return _ALIAS_TO_KEY[normalized]

    # Analyzer exports often join Spanish labels with abbreviations in parentheses.
    for alias, key in _ALIASES_BY_SPECIFICITY:
        if alias and re.search(rf"(^| ){re.escape(alias)}( |$)", normalized):
            return key
    return None


def _priority_for_label(key: str, raw_label: str) -> int:
    normalized = normalize_label(raw_label)
    if key in {"RDW", "PDW"}:
        if " cv" in f" {normalized} ":
            return 30
        if " sd" in f" {normalized} ":
            return 10
    if key == "Platelets":
        if "eplt" in normalized or "recuento total de plaquetas" in normalized:
            return 30
        if "plt abs" in normalized or "recuento absoluto de plaquetas" in normalized:
            return 20
    return 20


def _extract_value(raw_value: Any) -> Any:
    if isinstance(raw_value, dict):
        return raw_value.get("value")
    return raw_value


def _optional_number(value: Any) -> float | None:
    return coerce_lab_number(value)


def _optional_confidence(value: Any) -> float | None:
    number = coerce_lab_number(value)
    if number is None:
        return None
    if number > 1 and number <= 100:
        number /= 100
    return min(1.0, max(0.0, number))


def _parameter_detail(
    *, key: str, raw_key: str, raw_value: Any, value: float
) -> ExtractedParameter:
    payload = raw_value if isinstance(raw_value, dict) else {}
    original_value = payload.get("value") if payload else raw_value
    return ExtractedParameter(
        canonical_name=key,
        value=value,
        original_value=(None if original_value is None else str(original_value)),
        original_name=str(payload.get("raw_label") or raw_key).strip() or raw_key,
        unit=(str(payload.get("unit")).strip() if payload.get("unit") else None),
        reference_min=_optional_number(
            payload.get("reference_min", payload.get("ref_min"))
        ),
        reference_max=_optional_number(
            payload.get("reference_max", payload.get("ref_max"))
        ),
        recorded_flag=(
            str(payload.get("flag") or payload.get("status")).strip().lower()
            if payload.get("flag") or payload.get("status")
            else None
        ),
        confidence=_optional_confidence(payload.get("confidence")),
        notes=(str(payload.get("notes")).strip() if payload.get("notes") else None),
        data_origin="extractor",
    )


def normalize_extracted_payload(payload: dict[str, Any] | None) -> NormalizedExtraction:
    """Normalize extractor output to the raw CBC fields consumed by the ML model."""
    if not isinstance(payload, dict):
        return NormalizedExtraction(
            raw_data={},
            normalized_data={},
            valid_fields_count=0,
            errors=["Extractor output is not a dictionary."],
        )

    normalized: dict[str, float] = {}
    details: dict[str, ExtractedParameter] = {}
    selected_priority: dict[str, int] = {}
    warnings: list[str] = []

    for raw_key, raw_value in payload.items():
        key = canonical_model_key(str(raw_key))
        if key is None:
            continue
        if key not in MODEL_CBC_FIELD_SET:
            continue

        value = coerce_lab_number(_extract_value(raw_value))
        if value is None:
            continue

        priority = _priority_for_label(key, str(raw_key))
        if key in normalized and priority < selected_priority.get(key, 0):
            continue
        normalized[key] = value
        details[key] = _parameter_detail(
            key=key,
            raw_key=str(raw_key),
            raw_value=raw_value,
            value=value,
        )
        selected_priority[key] = priority

    return NormalizedExtraction(
        raw_data=payload,
        normalized_data=normalized,
        valid_fields_count=len(normalized),
        parameter_details=details,
        warnings=warnings,
    )
