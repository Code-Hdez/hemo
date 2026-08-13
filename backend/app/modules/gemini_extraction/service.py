"""Hemogram extraction fallback pipeline."""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence

from app.modules.gemini_extraction.config import get_extraction_settings
from app.modules.gemini_extraction.extractors.gemini_extractor import (
    GeminiFallbackExtractor,
)
from app.modules.gemini_extraction.extractors.local_extractor import (
    LocalFallbackExtractor,
)
from app.modules.gemini_extraction.extractors.openrouter_extractor import (
    OpenRouterExtractor,
)
from app.modules.gemini_extraction.extractors.base import run_with_timeout
from app.modules.gemini_extraction.schemas import (
    ExtractionAttempt,
    ExtractionAttemptError,
    PipelineExtractionResult,
)
from app.modules.gemini_extraction.validators import validate_extraction_result
from app.modules.hematology.extraction_types import ExtractionResult

logger = logging.getLogger("hemovet.extraction.pipeline")


def build_default_attempts() -> list[ExtractionAttempt]:
    settings = get_extraction_settings()
    attempts: list[ExtractionAttempt] = [
        GeminiFallbackExtractor(
            timeout_seconds=settings.gemini_extraction_timeout_seconds,
        ),
    ]
    if settings.openrouter_extraction_enabled:
        attempts.extend(
            [
                OpenRouterExtractor(
                    name="openrouter_gemma",
                    model=settings.openrouter_gemma_model,
                    api_key=settings.openrouter_api_key,
                    base_url=settings.openrouter_base_url,
                    timeout_seconds=settings.openrouter_gemma_timeout_seconds,
                    http_referer=settings.openrouter_http_referer,
                    x_title=settings.openrouter_x_title,
                ),
                OpenRouterExtractor(
                    name="openrouter_nemotron",
                    model=settings.openrouter_nemotron_model,
                    api_key=settings.openrouter_api_key,
                    base_url=settings.openrouter_base_url,
                    timeout_seconds=settings.openrouter_nemotron_timeout_seconds,
                    http_referer=settings.openrouter_http_referer,
                    x_title=settings.openrouter_x_title,
                ),
            ]
        )
    attempts.append(
        LocalFallbackExtractor(
            timeout_seconds=settings.local_extraction_timeout_seconds,
        )
    )
    return attempts


def _attempt_timeout_seconds(
    attempt: ExtractionAttempt, remaining_seconds: float | None
) -> float | None:
    limits: list[float] = []
    configured = getattr(attempt, "timeout_seconds", None)
    if configured is not None:
        try:
            configured_float = float(configured)
        except (TypeError, ValueError):
            configured_float = 0.0
        if configured_float > 0:
            limits.append(configured_float)
    if remaining_seconds is not None and remaining_seconds > 0:
        limits.append(remaining_seconds)
    return min(limits) if limits else None


def run_extraction_pipeline(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
    attempts: Sequence[ExtractionAttempt],
    min_valid_fields: int,
    total_timeout_seconds: float | None = None,
) -> PipelineExtractionResult:
    started = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []
    best_result: (
        tuple[
            ExtractionResult,
            str,
            str | None,
            int,
            list[str],
        ]
        | None
    ) = None

    for index, attempt in enumerate(attempts):
        remaining_seconds: float | None = None
        if total_timeout_seconds is not None:
            elapsed = time.perf_counter() - started
            remaining_seconds = total_timeout_seconds - elapsed
            if remaining_seconds <= 0:
                errors.append("HEMOGRAM_EXTRACTION_TOTAL_TIMEOUT")
                break

        attempt_started = time.perf_counter()
        attempt_timeout = _attempt_timeout_seconds(attempt, remaining_seconds)
        logger.info(
            "extraction.attempt.start extractor=%s model=%s",
            attempt.name,
            attempt.model,
        )
        try:
            def _extract_attempt() -> ExtractionResult:
                return attempt.extract(
                    contents=contents,
                    content_type=content_type,
                    filename=filename,
                )

            extraction = (
                run_with_timeout(
                    _extract_attempt,
                    timeout_seconds=attempt_timeout,
                    error_code="HEMOGRAM_EXTRACTION_ATTEMPT_TIMEOUT",
                    message=(
                        f"{attempt.name} excedio el timeout de "
                        f"{attempt_timeout:.1f} segundos."
                    ),
                )
                if attempt_timeout is not None
                else _extract_attempt()
            )
            normalized = validate_extraction_result(
                extraction,
                min_valid_fields=min_valid_fields,
            )
            extraction.cbc = normalized.normalized_data
            duration_ms = round((time.perf_counter() - attempt_started) * 1000)
            logger.info(
                "extraction.attempt.finish extractor=%s model=%s duration_ms=%s fields=%s",
                attempt.name,
                attempt.model,
                duration_ms,
                normalized.valid_fields_count,
            )
            if best_result is None or normalized.valid_fields_count > best_result[3]:
                best_result = (
                    extraction,
                    attempt.name,
                    attempt.model,
                    normalized.valid_fields_count,
                    list(normalized.warnings),
                )
            if normalized.valid_fields_count >= min_valid_fields:
                return PipelineExtractionResult(
                    extraction=extraction,
                    extractor_used=attempt.name,
                    model_used=attempt.model,
                    fallback_used=index > 0,
                    warnings=[*warnings, *normalized.warnings],
                    errors=errors,
                    valid_fields_count=normalized.valid_fields_count,
                    duration_ms=round((time.perf_counter() - started) * 1000),
                )

            warning = (
                f"{attempt.name} produjo pocos campos validos "
                f"({normalized.valid_fields_count}/{min_valid_fields})."
            )
            warnings.append(warning)
            errors.extend(normalized.errors)
            logger.warning(
                "extraction.attempt.insufficient extractor=%s model=%s fields=%s min=%s",
                attempt.name,
                attempt.model,
                normalized.valid_fields_count,
                min_valid_fields,
            )
        except ExtractionAttemptError as exc:
            duration_ms = round((time.perf_counter() - attempt_started) * 1000)
            errors.append(exc.error_code)
            logger.warning(
                "extraction.attempt.fail extractor=%s model=%s code=%s duration_ms=%s",
                attempt.name,
                attempt.model,
                exc.error_code,
                duration_ms,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - attempt_started) * 1000)
            errors.append(type(exc).__name__)
            logger.exception(
                "extraction.attempt.unexpected extractor=%s model=%s duration_ms=%s",
                attempt.name,
                attempt.model,
                duration_ms,
            )

    if best_result is not None:
        extraction, extractor_used, model_used, fields, attempt_warnings = best_result
        return PipelineExtractionResult(
            extraction=extraction,
            extractor_used=extractor_used,
            model_used=model_used,
            fallback_used=True,
            warnings=[
                *warnings,
                *attempt_warnings,
                "La extraccion final es parcial y requiere revision.",
            ],
            errors=errors,
            valid_fields_count=fields,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )

    raise ExtractionAttemptError(
        "HEMOGRAM_EXTRACTION_FAILED",
        "Ningun extractor pudo obtener valores CBC del hemograma.",
    )


def extract_hemogram_with_fallbacks(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
) -> PipelineExtractionResult:
    settings = get_extraction_settings()
    return run_extraction_pipeline(
        contents=contents,
        content_type=content_type,
        filename=filename,
        attempts=build_default_attempts(),
        min_valid_fields=settings.min_valid_fields,
        total_timeout_seconds=settings.total_timeout_seconds,
    )
