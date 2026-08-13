"""OpenRouter chat-completions extractor for CBC data."""

from __future__ import annotations

import logging
import time
import base64
from dataclasses import dataclass
from typing import Any

import httpx

from app.modules.gemini_extraction.constants import EXTRACTION_PROMPT_FIELDS
from app.modules.gemini_extraction.normalizer import normalize_extracted_payload
from app.modules.gemini_extraction.schemas import ExtractionAttemptError
from app.modules.gemini_extraction.utils.file_text_extraction import (
    extract_text_from_file,
    is_image,
)
from app.modules.gemini_extraction.utils.json_repair import loads_llm_json
from app.modules.hematology.extraction_types import ExtractionResult

logger = logging.getLogger("hemovet.extraction.openrouter")


def build_hemogram_extraction_prompt(content: str) -> str:
    fields_json = ",\n  ".join(
        f'"{field}": {{"value": null, "unit": null, "raw_label": null, '
        '"reference_min": null, "reference_max": null, "flag": null, "confidence": 0}}'
        for field in EXTRACTION_PROMPT_FIELDS
    )
    return f"""
Eres un sistema experto en extraccion de datos de hemogramas caninos. Recibiras texto, tablas o contenido proveniente de un archivo clinico.
Extrae unicamente los parametros hematologicos requeridos por el sistema.

Devuelve exclusivamente JSON valido. No uses Markdown. No expliques nada.

Campos canonicos requeridos:
{", ".join(EXTRACTION_PROMPT_FIELDS)}.

Reglas:
- No inventes valores.
- Si un campo no aparece, usa null.
- Extrae el resultado del paciente. Si el documento muestra un rango junto al resultado,
  conserva sus limites en reference_min y reference_max; de lo contrario usa null.
- Conserva unidades cuando esten disponibles.
- Reconoce alias en espanol e ingles.
- Convierte coma decimal a punto decimal.
- Devuelve valores numericos como numeros, no como strings.
- Ignora curvas, thresholds, alarmas e interpretaciones.
- Si existen RDW-CV y RDW-SD, prioriza RDW-CV.
- Si existen PDW-CV y PDW-SD, prioriza PDW-CV.

Formato exacto:
{{
  {fields_json}
}}

Contenido a analizar:
<<<HEMOGRAM_CONTENT
{content[:30000]}
HEMOGRAM_CONTENT>>>
""".strip()


@dataclass(slots=True)
class OpenRouterExtractor:
    name: str
    model: str
    api_key: str | None
    base_url: str
    timeout_seconds: float
    http_referer: str | None = None
    x_title: str | None = None
    client_factory: Any | None = None

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ExtractionAttemptError(
                "OPENROUTER_NOT_CONFIGURED",
                "OPENROUTER_API_KEY no esta configurada.",
            )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.x_title:
            headers["X-Title"] = self.x_title
        return headers

    def _client(self) -> httpx.Client:
        if self.client_factory is not None:
            return self.client_factory(timeout=self.timeout_seconds)
        return httpx.Client(timeout=self.timeout_seconds)

    def extract(
        self,
        *,
        contents: bytes,
        content_type: str,
        filename: str | None,
    ) -> ExtractionResult:
        started = time.perf_counter()
        image_input = is_image(content_type, filename)
        try:
            text = extract_text_from_file(
                contents=contents,
                content_type=content_type,
                filename=filename,
            )
        except ExtractionAttemptError:
            if not image_input:
                raise
            text = ""
        if not text.strip() and not image_input:
            raise ExtractionAttemptError(
                "OPENROUTER_EMPTY_INPUT",
                "No se pudo obtener texto del archivo para OpenRouter.",
            )

        prompt = build_hemogram_extraction_prompt(
            text or "El contenido principal esta en la imagen adjunta."
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": _message_content_for_file(
                        prompt=prompt,
                        contents=contents,
                        content_type=content_type,
                        filename=filename,
                    ),
                }
            ],
            "temperature": 0,
            "max_tokens": 1200,
        }

        try:
            with self._client() as client:
                response = client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                response_json = response.json()
        except httpx.TimeoutException as exc:
            raise ExtractionAttemptError(
                "OPENROUTER_TIMEOUT",
                f"OpenRouter {self.model} excedio el timeout.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            status_code = (
                exc.response.status_code if exc.response is not None else "unknown"
            )
            raise ExtractionAttemptError(
                "OPENROUTER_HTTP_ERROR",
                f"OpenRouter {self.model} devolvio HTTP {status_code}.",
            ) from exc
        except httpx.HTTPError as exc:
            raise ExtractionAttemptError(
                "OPENROUTER_CONNECTION_ERROR",
                f"No se pudo conectar con OpenRouter {self.model}.",
            ) from exc
        except ValueError as exc:
            raise ExtractionAttemptError(
                "OPENROUTER_INVALID_RESPONSE",
                "OpenRouter devolvio una respuesta no JSON.",
            ) from exc

        content = _extract_message_content(response_json)
        raw_payload = loads_llm_json(content)
        normalized = normalize_extracted_payload(raw_payload)
        if not normalized.normalized_data:
            raise ExtractionAttemptError(
                "OPENROUTER_NO_CBC_FIELDS",
                f"OpenRouter {self.model} no encontro valores CBC numericos.",
            )

        logger.info(
            "openrouter.extraction.complete extractor=%s model=%s duration_ms=%s fields=%s",
            self.name,
            self.model,
            round((time.perf_counter() - started) * 1000),
            len(normalized.normalized_data),
        )
        return ExtractionResult(
            cbc=normalized.normalized_data,
            metadata={"species": "Canino"},
            comments=None,
            parameter_details=normalized.parameter_details,
        )


def _extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ExtractionAttemptError(
            "OPENROUTER_EMPTY_RESPONSE",
            "OpenRouter no devolvio choices.",
        )
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        if content.strip():
            return content
    if isinstance(content, list):
        parts = [
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        joined = "\n".join(part for part in parts if part.strip())
        if joined.strip():
            return joined
    raise ExtractionAttemptError(
        "OPENROUTER_EMPTY_RESPONSE",
        "OpenRouter devolvio contenido vacio.",
    )


def _message_content_for_file(
    *,
    prompt: str,
    contents: bytes,
    content_type: str,
    filename: str | None,
) -> str | list[dict[str, Any]]:
    if not is_image(content_type, filename):
        return prompt
    mime_type = _image_mime_type(content_type, filename)
    encoded = base64.b64encode(contents).decode("ascii")
    return [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
        },
    ]


def _image_mime_type(content_type: str, filename: str | None) -> str:
    ct = (content_type or "").lower().strip()
    if ct.startswith("image/"):
        return ct
    suffix = (filename or "").lower().rsplit(".", 1)[-1]
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "webp": "image/webp",
    }.get(suffix, "image/jpeg")
