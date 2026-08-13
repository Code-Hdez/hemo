"""Local extraction fallback wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.gemini_extraction.extractors.base import run_with_timeout
from app.modules.gemini_extraction.schemas import ExtractionAttemptError
from app.modules.hematology.extraction_types import ExtractionError, ExtractionResult


@dataclass(slots=True)
class LocalFallbackExtractor:
    name: str = "local"
    model: str | None = None
    timeout_seconds: float = 20.0

    def extract(
        self,
        *,
        contents: bytes,
        content_type: str,
        filename: str | None,
    ) -> ExtractionResult:
        def _run() -> ExtractionResult:
            from app.modules.hematology import extractor

            return extractor.extract_from_file(
                contents,
                content_type,
                filename=filename,
            )

        try:
            return run_with_timeout(
                _run,
                timeout_seconds=self.timeout_seconds,
                error_code="LOCAL_EXTRACTION_TIMEOUT",
                message="La extraccion local excedio el timeout configurado.",
            )
        except ExtractionError as exc:
            raise ExtractionAttemptError("LOCAL_EXTRACTION_ERROR", str(exc)) from exc
