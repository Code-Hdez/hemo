"""Common validation for extraction attempts."""

from __future__ import annotations

from app.modules.gemini_extraction.constants import BASIC_NUMERIC_RANGES
from app.modules.gemini_extraction.normalizer import normalize_extracted_payload
from app.modules.gemini_extraction.schemas import NormalizedExtraction
from app.modules.hematology.extraction_types import ExtractionResult


def validate_extraction_result(
    extraction: ExtractionResult,
    *,
    min_valid_fields: int,
) -> NormalizedExtraction:
    """Normalize and validate an ExtractionResult without throwing away metadata."""
    normalized = normalize_extracted_payload(extraction.cbc)

    for field, value in normalized.normalized_data.items():
        allowed = BASIC_NUMERIC_RANGES.get(field)
        if allowed is None:
            continue
        min_value, max_value = allowed
        if value < min_value or value > max_value:
            normalized.warnings.append(
                f"{field}: valor fuera de rango operativo amplio ({value:g})."
            )

    if normalized.valid_fields_count < min_valid_fields:
        normalized.errors.append(
            "La extraccion contiene pocos campos CBC validos "
            f"({normalized.valid_fields_count}/{min_valid_fields})."
        )
    return normalized


def is_valid_extraction(
    extraction: ExtractionResult,
    *,
    min_valid_fields: int,
) -> bool:
    return (
        validate_extraction_result(
            extraction,
            min_valid_fields=min_valid_fields,
        ).valid_fields_count
        >= min_valid_fields
    )
