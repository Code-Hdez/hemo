"""Tipos livianos compartidos por extractores sin dependencias OCR/PDF."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Optional


class ExtractionError(Exception):
    """Se lanza cuando no se pueden extraer datos CBC del archivo subido."""


@dataclass
class ExtractedParameter:
    canonical_name: str
    value: float
    original_value: str | None = None
    original_name: str | None = None
    unit: str | None = None
    reference_min: float | None = None
    reference_max: float | None = None
    recorded_flag: str | None = None
    confidence: float | None = None
    notes: str | None = None
    data_origin: str = "unknown"


@dataclass
class ExtractionResult:
    """Resultado estructurado de la extraccion de un hemograma."""

    cbc: dict[str, float]
    metadata: dict[str, Optional[str]]
    comments: Optional[str] = None
    parameter_details: dict[str, ExtractedParameter] = field(default_factory=dict)


REQUIRED_FIELDS = {"WBC", "RBC", "HGB", "HCT", "Platelets"}

_NUMERIC_TOKEN_RE = re.compile(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?")


def coerce_lab_number(value: Any) -> Optional[float]:
    """Convierte un valor de laboratorio a float tolerando flags del analizador."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    text = text.replace("*", "").replace("<", "").replace(">", "")
    text = text.replace("\u2264", "").replace("\u2265", "").strip()

    match = _NUMERIC_TOKEN_RE.search(text)
    if not match:
        return None

    token = match.group(0)
    if "," in token and "." not in token:
        token = token.replace(",", ".")
    elif "," in token and "." in token:
        token = token.replace(",", "")

    try:
        number = float(token)
    except ValueError:
        return None

    return number if math.isfinite(number) else None
