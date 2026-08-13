"""Runtime configuration for hemogram extraction fallbacks."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.modules.gemini_extraction.constants import (
    OPENROUTER_DEFAULT_BASE_URL,
    OPENROUTER_GEMMA_DEFAULT_MODEL,
    OPENROUTER_NEMOTRON_DEFAULT_MODEL,
)


@dataclass(frozen=True, slots=True)
class HemogramExtractionSettings:
    openrouter_extraction_enabled: bool
    openrouter_api_key: str | None
    openrouter_base_url: str
    openrouter_gemma_model: str
    openrouter_nemotron_model: str
    openrouter_http_referer: str | None
    openrouter_x_title: str | None
    openrouter_gemma_timeout_seconds: float
    openrouter_nemotron_timeout_seconds: float
    gemini_extraction_timeout_seconds: float
    local_extraction_timeout_seconds: float
    total_timeout_seconds: float
    min_valid_fields: int


def _env_or_setting(name: str, default: Any) -> Any:
    value = os.getenv(name)
    if value is not None and value.strip():
        return value
    return getattr(settings, name, default)


def _optional_str(name: str, default: str | None = None) -> str | None:
    value = _env_or_setting(name, default)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float(name: str, default: float) -> float:
    try:
        return float(_env_or_setting(name, default))
    except (TypeError, ValueError):
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(_env_or_setting(name, default))
    except (TypeError, ValueError):
        return default


def _bool(name: str, default: bool) -> bool:
    value = _env_or_setting(name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def get_extraction_settings() -> HemogramExtractionSettings:
    return HemogramExtractionSettings(
        openrouter_extraction_enabled=_bool("OPENROUTER_EXTRACTION_ENABLED", False),
        openrouter_api_key=_optional_str("OPENROUTER_API_KEY"),
        openrouter_base_url=str(
            _env_or_setting("OPENROUTER_BASE_URL", OPENROUTER_DEFAULT_BASE_URL)
        ).rstrip("/"),
        openrouter_gemma_model=str(
            _env_or_setting("OPENROUTER_GEMMA_MODEL", OPENROUTER_GEMMA_DEFAULT_MODEL)
        ),
        openrouter_nemotron_model=str(
            _env_or_setting(
                "OPENROUTER_NEMOTRON_MODEL",
                OPENROUTER_NEMOTRON_DEFAULT_MODEL,
            )
        ),
        openrouter_http_referer=_optional_str("OPENROUTER_HTTP_REFERER"),
        openrouter_x_title=_optional_str(
            "OPENROUTER_X_TITLE", "hemogramas-proyectoICC"
        ),
        openrouter_gemma_timeout_seconds=_float("OPENROUTER_GEMMA_TIMEOUT_SECONDS", 20),
        openrouter_nemotron_timeout_seconds=_float(
            "OPENROUTER_NEMOTRON_TIMEOUT_SECONDS", 20
        ),
        gemini_extraction_timeout_seconds=_float(
            "GEMINI_EXTRACTION_TIMEOUT_SECONDS", 30
        ),
        local_extraction_timeout_seconds=_float("LOCAL_EXTRACTION_TIMEOUT_SECONDS", 20),
        total_timeout_seconds=_float("HEMOGRAM_EXTRACTION_TOTAL_TIMEOUT_SECONDS", 60),
        min_valid_fields=_int("HEMOGRAM_MIN_VALID_FIELDS", 8),
    )
