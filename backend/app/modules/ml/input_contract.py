"""
Validación y normalización del contrato de entrada CBC para inferencia.

Normaliza aliases de nombres de campo (variantes de capitalización y
abreviaturas comunes), descarta valores fuera de rangos operativos amplios
(errores de parseo o unidades), e imputa NaN para los campos opcionales
ausentes. Rechaza la solicitud si los campos nucleares mínimos no están
presentes o son inválidos.

API pública
-----------
validate_cbc_contract(cbc: dict) -> dict[str, float]
    Retorna el CBC normalizado.
    Lanza InputContractError con error_code y lista de fields problemáticos.
"""

from __future__ import annotations

import math
from typing import Any

# Campos nucleares para considerar valida una entrada CBC.
REQUIRED_CBC_FIELDS: set[str] = {"WBC", "RBC", "HGB", "HCT", "Platelets"}
MIN_REQUIRED_CORE_FIELDS = 3

ERROR_CODE_MISSING_FIELD = "MISSING_FIELD"
ERROR_CODE_TYPE_ERROR = "TYPE_ERROR"
ERROR_CODE_RANGE_VIOLATION = "RANGE_VIOLATION"

# Rangos operativos amplios (no clinicos) para filtrar valores imposibles.
# Objetivo: detectar errores de parseo/unidades, no diagnosticar.
CBC_NUMERIC_RANGES: dict[str, tuple[float, float]] = {
    "WBC": (0.0, 400.0),
    "RBC": (0.0, 20.0),
    "HGB": (0.0, 40.0),
    "HCT": (0.0, 90.0),
    "MCV": (20.0, 150.0),
    "MCH": (5.0, 60.0),
    # El predictor maneja MCHC > 50 como artefacto preanalitico; el contrato debe
    # permitir que esa regla se ejecute en vez de rechazar el hemograma antes.
    "MCHC": (10.0, 100.0),
    "RDW": (1.0, 50.0),
    "Platelets": (0.0, 3000.0),
    "MPV": (2.0, 30.0),
    "PDW": (1.0, 80.0),
    "Neutrophils": (0.0, 250.0),
    "Lymphocytes": (0.0, 250.0),
    "Monocytes": (0.0, 250.0),
    "Eosinophils": (0.0, 250.0),
    "Basophils": (0.0, 250.0),
    "Neutrophils_pct": (0.0, 100.0),
    "Lymphocytes_pct": (0.0, 100.0),
    "Monocytes_pct": (0.0, 100.0),
    "Eosinophils_pct": (0.0, 100.0),
    "Basophils_pct": (0.0, 100.0),
    "Reticulocytes": (0.0, 2000.0),
    "Reticulocytes_pct": (0.0, 100.0),
    "PCT": (0.0, 5.0),
    "age_years": (0.0, 30.0),
}

# Algunos analizadores exportan conteos absolutos por microlitro aunque la
# interfaz del modelo use K/uL o M/uL. Solo se convierten magnitudes que no
# pueden ser válidas en la unidad esperada.
ABSOLUTE_COUNT_DIVISORS: dict[str, tuple[float, float]] = {
    "WBC": (1000.0, 1000.0),
    "RBC": (100_000.0, 1_000_000.0),
    "Platelets": (10_000.0, 1000.0),
    "Neutrophils": (1000.0, 1000.0),
    "Lymphocytes": (1000.0, 1000.0),
    "Monocytes": (1000.0, 1000.0),
    "Eosinophils": (1000.0, 1000.0),
    "Basophils": (1000.0, 1000.0),
}

CBC_FIELD_ALIASES: dict[str, str] = {
    "PLT": "Platelets",
    "platelets": "Platelets",
    "NEU": "Neutrophils",
    "neutrophils": "Neutrophils",
}


def _normalize_absolute_count(field: str, value: float) -> float:
    rule = ABSOLUTE_COUNT_DIVISORS.get(field)
    if rule is None:
        return value
    activation_threshold, divisor = rule
    maximum = CBC_NUMERIC_RANGES[field][1]
    converted = value / divisor
    return converted if value >= activation_threshold and converted <= maximum else value


class InputContractError(ValueError):
    """Error semantico del contrato de entrada para inferencia CBC."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        fields: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.fields = fields or []
        self.context = context or {}

    def to_api_detail(self) -> dict[str, Any]:
        """Serializa el error en formato estable para respuestas HTTP."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "fields": self.fields,
            "context": self.context,
        }


def _coerce_float(field: str, value: Any) -> float:
    if isinstance(value, bool):
        raise InputContractError(
            ERROR_CODE_TYPE_ERROR,
            "El valor CBC contiene tipos no numericos.",
            fields=[field],
            context={"field": field, "value": str(value)},
        )

    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise InputContractError(
            ERROR_CODE_TYPE_ERROR,
            "El valor CBC contiene tipos no numericos.",
            fields=[field],
            context={"field": field, "value": str(value)},
        ) from exc

    if not math.isfinite(num):
        raise InputContractError(
            ERROR_CODE_TYPE_ERROR,
            "El valor CBC contiene numeros no finitos.",
            fields=[field],
            context={"field": field, "value": str(value)},
        )

    return num


def validate_cbc_contract(cbc: dict[str, Any]) -> dict[str, float]:
    """
    Valida y normaliza entrada CBC para inferencia.

    Reglas:
    - Debe existir un dict con al menos 3 campos nucleares entre WBC/RBC/HGB/HCT/Platelets.
    - Todos los valores presentes deben ser numericos finitos.
    - Los campos conocidos deben caer en rangos operativos amplios.
    """
    if not isinstance(cbc, dict):
        raise InputContractError(
            ERROR_CODE_TYPE_ERROR,
            "El payload CBC debe ser un objeto tipo diccionario.",
            context={"received_type": type(cbc).__name__},
        )

    normalized: dict[str, float] = {}
    type_error_fields: list[str] = []

    for field, raw_value in cbc.items():
        if raw_value is None:
            continue
        canonical_field = CBC_FIELD_ALIASES.get(field, field)
        try:
            normalized[canonical_field] = _normalize_absolute_count(
                canonical_field, _coerce_float(canonical_field, raw_value)
            )
        except InputContractError:
            type_error_fields.append(canonical_field)

    if type_error_fields:
        raise InputContractError(
            ERROR_CODE_TYPE_ERROR,
            "El valor CBC contiene tipos no numericos o no finitos.",
            fields=sorted(set(type_error_fields)),
        )

    found_required = sorted(REQUIRED_CBC_FIELDS.intersection(normalized.keys()))
    if len(found_required) < MIN_REQUIRED_CORE_FIELDS:
        missing_required = sorted(REQUIRED_CBC_FIELDS.difference(found_required))
        raise InputContractError(
            ERROR_CODE_MISSING_FIELD,
            "No hay suficientes campos CBC nucleares para inferencia.",
            fields=missing_required,
            context={
                "min_required": MIN_REQUIRED_CORE_FIELDS,
                "found_required": found_required,
                "found_all_fields": sorted(normalized.keys()),
            },
        )

    range_violations: list[dict[str, Any]] = []
    for field, (min_val, max_val) in CBC_NUMERIC_RANGES.items():
        if field not in normalized:
            continue
        value = normalized[field]
        if value < min_val or value > max_val:
            range_violations.append(
                {
                    "field": field,
                    "value": value,
                    "min": min_val,
                    "max": max_val,
                }
            )

    if range_violations:
        raise InputContractError(
            ERROR_CODE_RANGE_VIOLATION,
            "Se detectaron valores CBC fuera de rango operativo.",
            fields=sorted({v["field"] for v in range_violations}),
            context={"violations": range_violations},
        )

    return normalized
