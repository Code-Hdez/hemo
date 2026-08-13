"""Small JSON extraction helpers for LLM responses."""

from __future__ import annotations

import json
from typing import Any

from app.modules.gemini_extraction.schemas import ExtractionAttemptError


def extract_json_object_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        raise ExtractionAttemptError(
            "EMPTY_RESPONSE", "La respuesta del modelo esta vacia."
        )

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]

    raise ExtractionAttemptError(
        "JSON_NOT_FOUND",
        "La respuesta textual no contiene un objeto JSON parseable.",
    )


def loads_llm_json(raw_text: str) -> dict[str, Any]:
    json_text = extract_json_object_text(raw_text)
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ExtractionAttemptError(
            "INVALID_JSON",
            "El modelo devolvio JSON invalido.",
        ) from exc
    if not isinstance(payload, dict):
        raise ExtractionAttemptError(
            "INVALID_JSON_SHAPE",
            "El JSON extraido no es un objeto.",
        )
    return payload
