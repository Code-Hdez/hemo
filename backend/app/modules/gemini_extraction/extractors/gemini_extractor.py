"""Wrapper that keeps the existing Gemini extractor as a bounded fallback."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.gemini_extraction.client import (
    GeminiExtractionConfig,
    GeminiExtractionError,
    extract_with_gemini,
    get_gemini_config_from_env,
)
from app.modules.gemini_extraction.extractors.base import run_with_timeout
from app.modules.gemini_extraction.schemas import ExtractionAttemptError
from app.modules.hematology.extraction_types import ExtractionResult


@dataclass(slots=True)
class GeminiFallbackExtractor:
    name: str = "gemini"
    model: str | None = None
    timeout_seconds: float = 30.0

    def extract(
        self,
        *,
        contents: bytes,
        content_type: str,
        filename: str | None,
    ) -> ExtractionResult:
        config = get_gemini_config_from_env()
        config = GeminiExtractionConfig(
            api_key=config.api_key,
            model=config.model,
            timeout_seconds=self.timeout_seconds,
            file_poll_seconds=config.file_poll_seconds,
            file_poll_max_attempts=max(
                1, int(self.timeout_seconds // max(config.file_poll_seconds, 0.1))
            ),
        )
        self.model = config.model

        def _run() -> ExtractionResult:
            return extract_with_gemini(
                contents=contents,
                content_type=content_type,
                filename=filename,
                config=config,
            ).extraction

        try:
            return run_with_timeout(
                _run,
                timeout_seconds=self.timeout_seconds,
                error_code="GEMINI_TIMEOUT",
                message="Gemini excedio el timeout de extraccion.",
            )
        except GeminiExtractionError as exc:
            raise ExtractionAttemptError(exc.error_code, exc.message) from exc
