"""Canonical visible CBC field definitions for extraction review."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any
import unicodedata

from app.modules.hematology.extraction_types import coerce_lab_number


@dataclass(frozen=True)
class CbcFieldDefinition:
    key: str
    label: str
    unit: str
    aliases: tuple[str, ...]
    required: bool
    group: str
    order: int


@dataclass(frozen=True)
class CbcExtractedField:
    key: str
    label: str
    unit: str
    value: str
    detected: bool
    required: bool
    group: str
    order: int


_CBC_FIELDS_PATH = Path(__file__).resolve().parents[4] / "shared" / "cbc_fields.json"


def _load_field_definitions() -> tuple[CbcFieldDefinition, ...]:
    raw_fields = json.loads(_CBC_FIELDS_PATH.read_text(encoding="utf-8"))
    return tuple(
        CbcFieldDefinition(
            key=str(item["key"]),
            label=str(item["label"]),
            unit=str(item["unit"]),
            aliases=tuple(str(alias) for alias in item.get("aliases", [])),
            required=bool(item["required"]),
            group=str(item["group"]),
            order=int(item["order"]),
        )
        for item in raw_fields
    )


CBC_FIELD_DEFINITIONS: tuple[CbcFieldDefinition, ...] = _load_field_definitions()


# Stable clinical codes used outside the extraction UI.  Absolute differential
# counts keep their historical short codes for backwards compatibility, while
# percentages receive an explicit suffix so both measurements can coexist in a
# single study without overwriting or authorizing one another accidentally.
_CBC_CLINICAL_CODE_BY_KEY: dict[str, str] = {
    "WBC": "WBC",
    "RBC": "RBC",
    "HGB": "HGB",
    "HCT": "HCT",
    "MCV": "MCV",
    "MCH": "MCH",
    "MCHC": "MCHC",
    "RDW": "RDW",
    "Reticulocytes_pct": "RETIC_PCT",
    "Reticulocytes": "RETIC",
    "Platelets": "PLT",
    "MPV": "MPV",
    "PDW": "PDW",
    "PCT": "PCT",
    "Neutrophils": "NEU",
    "Neutrophils_pct": "NEU_PCT",
    "Lymphocytes": "LYM",
    "Lymphocytes_pct": "LYM_PCT",
    "Monocytes": "MONO",
    "Monocytes_pct": "MONO_PCT",
    "Eosinophils": "EOS",
    "Eosinophils_pct": "EOS_PCT",
    "Basophils": "BASO",
    "Basophils_pct": "BASO_PCT",
}

_CBC_KEY_BY_CLINICAL_CODE = {
    code: key for key, code in _CBC_CLINICAL_CODE_BY_KEY.items()
}

_EXTRA_CLINICAL_ALIASES: dict[str, tuple[str, ...]] = {
    "WBC": (
        "leucosito",
        "leucositos",
        "leuco",
        "leucos",
        "globulos blancos",
        "leucocitosis",
        "leucopenia",
    ),
    "RBC": ("globulos rojos",),
    "HGB": ("emoglobina", "emoglovina", "hemoglovina", "homoglobina"),
    "PLT": (
        "platelet",
        "thrombocyte",
        "trombocito",
        "trombocitos",
        "trombocitosis",
        "trombocitopenia",
    ),
    "NEU": (
        "neutrophil",
        "neutrofilo",
        "neut",
        "neu#",
        "neutrofilos absolutos",
        "neutrofilia",
        "neutropenia",
    ),
    "NEU_PCT": ("neutrophils pct", "porcentaje de neutrofilos"),
    "LYM": (
        "lymphocyte",
        "linfocito",
        "lymph",
        "lym#",
        "linfocitos absolutos",
        "linfocitosis",
        "linfopenia",
    ),
    "LYM_PCT": ("lymphocytes pct", "porcentaje de linfocitos"),
    "MONO": (
        "monocyte",
        "monocito",
        "mon",
        "mono#",
        "monocitos absolutos",
        "monocitosis",
        "monocitopenia",
    ),
    "MONO_PCT": ("monocytes pct", "porcentaje de monocitos"),
    "EOS": (
        "eosinophil",
        "eosinofilo",
        "eosin",
        "eos#",
        "eosinofilos absolutos",
        "eosinofilia",
        "eosinopenia",
    ),
    "EOS_PCT": ("eosinophils pct", "porcentaje de eosinofilos"),
    "BASO": (
        "basophil",
        "basofilo",
        "bas",
        "baso#",
        "basofilos absolutos",
        "basofilia",
        "basopenia",
    ),
    "BASO_PCT": ("basophils pct", "porcentaje de basofilos"),
    "RETIC": ("reticulocyte", "reticulocito", "retic#", "reticulocitos absolutos"),
    "RETIC_PCT": ("reticulocytes pct", "porcentaje de reticulocitos"),
}

_EXPLICIT_CLINICAL_LABELS: dict[str, str] = {
    "NEU": "NEU absoluto / Neutrófilos",
    "NEU_PCT": "NEU % / Neutrófilos %",
    "LYM": "LYM absoluto / Linfocitos",
    "LYM_PCT": "LYM % / Linfocitos %",
    "MONO": "MONO absoluto / Monocitos",
    "MONO_PCT": "MONO % / Monocitos %",
    "EOS": "EOS absoluto / Eosinófilos",
    "EOS_PCT": "EOS % / Eosinófilos %",
    "BASO": "BASO absoluto / Basófilos",
    "BASO_PCT": "BASO % / Basófilos %",
    "RETIC": "RETIC absoluto / Reticulocitos",
    "RETIC_PCT": "RETIC % / Reticulocitos %",
}

_ALIAS_TO_KEY: dict[str, str] = {}
for definition in CBC_FIELD_DEFINITIONS:
    _ALIAS_TO_KEY[definition.key.lower()] = definition.key
    for alias in definition.aliases:
        _ALIAS_TO_KEY[alias.lower()] = definition.key


def normalize_cbc_alias(value: str) -> str:
    """Normalize a CBC label without erasing percentage/absolute markers."""

    folded = unicodedata.normalize("NFKD", str(value or "").casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    plain = plain.replace("_", " ")
    plain = re.sub(r"[^a-z0-9%#]+", " ", plain)
    return re.sub(r"\s+", " ", plain).strip()


_NORMALIZED_ALIAS_TO_KEY: dict[str, str] = {}
_CLINICAL_ALIASES_BY_CODE: dict[str, list[str]] = {}
for definition in CBC_FIELD_DEFINITIONS:
    code = _CBC_CLINICAL_CODE_BY_KEY[definition.key]
    values = (
        definition.key,
        definition.label,
        code,
        *definition.aliases,
        *_EXTRA_CLINICAL_ALIASES.get(code, ()),
    )
    for value in values:
        normalized = normalize_cbc_alias(value)
        if not normalized:
            continue
        _NORMALIZED_ALIAS_TO_KEY[normalized] = definition.key
        if normalized not in _CLINICAL_ALIASES_BY_CODE.setdefault(code, []):
            _CLINICAL_ALIASES_BY_CODE[code].append(normalized)


def canonical_cbc_key(key: str) -> str:
    """Return the canonical visible CBC key for common extractor aliases."""
    direct = _ALIAS_TO_KEY.get(key.strip().lower())
    if direct is not None:
        return direct
    return _NORMALIZED_ALIAS_TO_KEY.get(normalize_cbc_alias(key), key)


def canonical_cbc_clinical_code(value: str) -> str:
    """Return the stable clinical code for an extraction key or lab alias."""

    normalized = normalize_cbc_alias(value)
    if not normalized:
        return ""
    key = _NORMALIZED_ALIAS_TO_KEY.get(normalized)
    if key is not None:
        return _CBC_CLINICAL_CODE_BY_KEY[key]
    upper = str(value).strip().upper()
    if upper in _CBC_KEY_BY_CLINICAL_CODE:
        return upper
    return upper


def cbc_clinical_aliases() -> dict[str, tuple[str, ...]]:
    """Expose immutable normalized aliases grouped by stable clinical code."""

    return {
        code: tuple(aliases)
        for code, aliases in _CLINICAL_ALIASES_BY_CODE.items()
    }


def cbc_clinical_display_label(code: str) -> str | None:
    """Return an unambiguous prompt/display label for a stable clinical code."""

    normalized_code = str(code or "").strip().upper()
    explicit = _EXPLICIT_CLINICAL_LABELS.get(normalized_code)
    if explicit is not None:
        return explicit
    key = _CBC_KEY_BY_CLINICAL_CODE.get(normalized_code)
    if key is None:
        return None
    definition = next(
        item for item in CBC_FIELD_DEFINITIONS if item.key == key
    )
    return definition.label


def normalize_visible_cbc_values(cbc: dict[str, Any]) -> dict[str, float]:
    """Normalize aliases and keep only numeric values for visible CBC fields."""
    visible_keys = {field.key for field in CBC_FIELD_DEFINITIONS}
    normalized: dict[str, float] = {}
    for raw_key, raw_value in (cbc or {}).items():
        key = canonical_cbc_key(str(raw_key))
        if key not in visible_keys:
            continue
        value = coerce_lab_number(raw_value)
        if value is not None:
            normalized[key] = value
    return normalized


def _format_value(value: float) -> str:
    return f"{value:g}"


def complete_cbc_fields(cbc: dict[str, Any]) -> list[CbcExtractedField]:
    """Return all 24 visible CBC fields, marking absent values as empty."""
    normalized = normalize_visible_cbc_values(cbc)
    return [
        CbcExtractedField(
            key=definition.key,
            label=definition.label,
            unit=definition.unit,
            value=_format_value(normalized[definition.key])
            if definition.key in normalized
            else "",
            detected=definition.key in normalized,
            required=definition.required,
            group=definition.group,
            order=definition.order,
        )
        for definition in CBC_FIELD_DEFINITIONS
    ]
