"""
Orquestación de la extracción CBC para archivos subidos.

Implementa una estrategia fija: OpenRouter Gemma, OpenRouter Nemotron, Gemini y
fallback local (pdfplumber + Tesseract) con timeouts configurables.

API pública
-----------
extract_uploaded_file(contents, content_type, filename, mode) -> ExtractionServiceResult
    Lanza ExtractionError si ningún extractor produce un resultado válido.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from app.core.config import settings

from .extraction_types import ExtractionError, ExtractionResult
from app.modules.gemini_extraction.schemas import ExtractionAttemptError
from app.modules.gemini_extraction.service import (
    extract_hemogram_with_fallbacks,
)
from app.modules.gemini_extraction.normalizer import normalize_extracted_payload

logger = logging.getLogger("hemovet.extraction")

ExtractionMode = Literal["auto", "gemini", "local"]
ExtractionProvider = Literal["gemini", "local", "local_fallback"]

PUBLIC_EXTRACTION_FAILURE_MESSAGE = (
    "No pudimos extraer suficientes datos del hemograma. "
    "Revisa que el archivo sea legible o ingresa los valores manualmente."
)
PUBLIC_EXTRACTION_FALLBACK_WARNING = (
    "La extraccion automatica requirio un metodo alternativo. "
    "Revisa los valores antes de continuar."
)
_INTERNAL_WARNING_MARKERS = (
    "api",
    "extractor",
    "gemini",
    "gemma",
    "http",
    "modelo",
    "nemotron",
    "openrouter",
    "timeout",
)


@dataclass
class ExtractionServiceResult:
    extraction: ExtractionResult
    provider: ExtractionProvider
    mode: ExtractionMode
    fallback_used: bool = False
    warnings: list[str] = field(default_factory=list)


def _validate_mode(mode: str | None) -> ExtractionMode:
    normalized = (mode or "auto").strip().lower()
    if normalized not in {"auto", "gemini", "local"}:
        raise ExtractionError("Modo de extraccion invalido. Usa auto, gemini o local.")
    if normalized != "auto":
        logger.info(
            "extraction.mode_ignored requested=%s effective=auto",
            normalized,
        )
    return "auto"


def _local_extraction_enabled() -> bool:
    return settings.HEMOVET_ENABLE_LOCAL_EXTRACTION


def _prefers_local_extraction(content_type: str | None, filename: str | None) -> bool:
    ct = (content_type or "").lower()
    ext = (
        (filename or "").lower().rsplit(".", 1)[-1]
        if filename and "." in filename
        else ""
    )
    return (
        "csv" in ct
        or ct in {"text/plain", "text/tab-separated-values"}
        or "spreadsheet" in ct
        or "excel" in ct
        or "xlsx" in ct
        or "xls" in ct
        or "wordprocessingml.document" in ct
        or ext in {"csv", "tsv", "txt", "xlsx", "xls", "docx"}
    )


def _extract_local(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
) -> ExtractionResult:
    if not _local_extraction_enabled():
        raise ExtractionError(
            "El extractor local no esta habilitado en este contenedor. "
            "Configura HEMOVET_ENABLE_LOCAL_EXTRACTION=1 e instala las dependencias locales."
        )
    from . import extractor

    extraction = extractor.extract_from_file(contents, content_type, filename=filename)
    extraction.cbc = normalize_extracted_payload(extraction.cbc).normalized_data
    return extraction


def _public_warnings(
    warnings: list[str],
    *,
    fallback_used: bool,
) -> list[str]:
    """Remove provider/model diagnostics from warnings returned to clients."""
    public: list[str] = []
    for warning in warnings:
        warning_text = str(warning).strip()
        lowered = warning_text.lower()
        if not warning_text:
            continue
        if any(marker in lowered for marker in _INTERNAL_WARNING_MARKERS):
            continue
        public.append(warning_text)

    if fallback_used and PUBLIC_EXTRACTION_FALLBACK_WARNING not in public:
        public.insert(0, PUBLIC_EXTRACTION_FALLBACK_WARNING)
    return public


def extract_uploaded_file(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
    mode: str | None = "auto",
) -> ExtractionServiceResult:
    """
    Extrae CBC de un archivo subido usando la cadena de fallbacks configurada.
    """
    selected_mode = _validate_mode(mode)
    requested_mode = (mode or "auto").strip().lower()

    if requested_mode == "local":
        extraction = _extract_local(
            contents=contents,
            content_type=content_type,
            filename=filename,
        )
        return ExtractionServiceResult(
            extraction=extraction,
            provider="local",
            mode=selected_mode,
            warnings=[],
        )

    if _prefers_local_extraction(content_type, filename):
        try:
            extraction = _extract_local(
                contents=contents,
                content_type=content_type,
                filename=filename,
            )
            logger.info(
                "extraction.local_first.success filename=%s content_type=%s fields=%s",
                filename or "desconocido",
                content_type or "desconocido",
                len(extraction.cbc),
            )
            return ExtractionServiceResult(
                extraction=extraction,
                provider="local",
                mode=selected_mode,
                fallback_used=False,
                warnings=[],
            )
        except ExtractionError as exc:
            logger.warning(
                "extraction.local_first.failed filename=%s content_type=%s detail=%s",
                filename or "desconocido",
                content_type or "desconocido",
                exc,
            )

    try:
        pipeline_output = extract_hemogram_with_fallbacks(
            contents=contents,
            content_type=content_type,
            filename=filename,
        )
    except ExtractionAttemptError as exc:
        logger.warning(
            "extraction.pipeline.failed code=%s detail=%s",
            exc.error_code,
            exc.message,
        )
        raise ExtractionError(PUBLIC_EXTRACTION_FAILURE_MESSAGE) from exc

    if pipeline_output.extractor_used == "local":
        provider: ExtractionProvider = (
            "local_fallback" if pipeline_output.fallback_used else "local"
        )
    else:
        provider = "gemini"

    if pipeline_output.fallback_used:
        logger.warning(
            "extraction.fallback_used extractor=%s model=%s fields=%s",
            pipeline_output.extractor_used,
            pipeline_output.model_used,
            pipeline_output.valid_fields_count,
        )

    return ExtractionServiceResult(
        extraction=pipeline_output.extraction,
        provider=provider,
        mode=selected_mode,
        fallback_used=pipeline_output.fallback_used,
        warnings=_public_warnings(
            pipeline_output.warnings,
            fallback_used=pipeline_output.fallback_used,
        ),
    )
