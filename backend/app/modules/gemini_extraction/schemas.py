"""Internal schemas for the hemogram extraction fallback pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.modules.hematology.extraction_types import ExtractionResult


class ExtractionAttemptError(RuntimeError):
    """Controlled extractor failure that should advance to the next fallback."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class ExtractionAttempt(Protocol):
    name: str
    model: str | None

    def extract(
        self,
        *,
        contents: bytes,
        content_type: str,
        filename: str | None,
    ) -> ExtractionResult:
        """Return an ExtractionResult or raise ExtractionAttemptError."""


@dataclass(slots=True)
class NormalizedExtraction:
    raw_data: dict[str, Any]
    normalized_data: dict[str, float]
    valid_fields_count: int
    parameter_details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PipelineExtractionResult:
    extraction: ExtractionResult
    extractor_used: str
    model_used: str | None
    fallback_used: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    valid_fields_count: int = 0
    duration_ms: int = 0
