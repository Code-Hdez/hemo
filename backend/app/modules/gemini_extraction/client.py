"""
Extracción estructurada de parámetros CBC mediante Google Gemini API.

Envía el archivo (PDF o imagen) como parte multimodal junto a un prompt
estructurado. La respuesta JSON es validada con Pydantic antes de devolverse
como ExtractionResult. Implementa reintentos con backoff exponencial ante
errores transitorios de la API.

API pública
-----------
extract_with_gemini(contents, content_type, filename) -> ExtractionResult
    Lanza GeminiExtractionError si Gemini no está configurado o falla.
inspect_gemini_runtime()                               -> dict
    Diagnóstico de conectividad sin exponer la clave.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import settings
from app.modules.hematology.cbc_fields import (
    CBC_FIELD_DEFINITIONS,
    normalize_visible_cbc_values,
)
from app.modules.hematology.extraction_types import (
    ExtractionResult,
    coerce_lab_number,
)

logger = logging.getLogger("hemovet.gemini")

GEMINI_DEFAULT_MODEL = "gemini-3.1-flash-lite"

_CANONICAL_CBC_FIELDS = [field.key for field in CBC_FIELD_DEFINITIONS]
LabScalar = float | str | None


class GeminiExtractionError(RuntimeError):
    """Error semantico del extractor Gemini."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass(frozen=True)
class GeminiExtractionConfig:
    api_key: str | None
    model: str = GEMINI_DEFAULT_MODEL
    timeout_seconds: float = 90.0
    file_poll_seconds: float = 2.0
    file_poll_max_attempts: int = 30
    inline_text_max_bytes: int = 200_000

    @property
    def configured(self) -> bool:
        return bool((self.api_key or "").strip())


@dataclass
class GeminiExtractionOutput:
    extraction: ExtractionResult
    warnings: list[str] = field(default_factory=list)


class GeminiCbcValues(BaseModel):
    model_config = ConfigDict(extra="ignore")

    WBC: LabScalar = Field(
        default=None, description="White blood cells absolute count."
    )
    RBC: LabScalar = Field(default=None, description="Red blood cells absolute count.")
    HGB: LabScalar = Field(default=None, description="Hemoglobin.")
    HCT: LabScalar = Field(default=None, description="Hematocrit or PCV.")
    MCV: LabScalar = None
    MCH: LabScalar = None
    MCHC: LabScalar = None
    RDW: LabScalar = None
    Platelets: LabScalar = Field(default=None, description="Platelet count, PLT.")
    MPV: LabScalar = None
    PDW: LabScalar = None
    PCT: LabScalar = Field(default=None, description="Plateletcrit.")
    Reticulocytes: LabScalar = None
    Reticulocytes_pct: LabScalar = None
    Neutrophils: LabScalar = None
    Neutrophils_pct: LabScalar = None
    Lymphocytes: LabScalar = None
    Lymphocytes_pct: LabScalar = None
    Monocytes: LabScalar = None
    Monocytes_pct: LabScalar = None
    Eosinophils: LabScalar = None
    Eosinophils_pct: LabScalar = None
    Basophils: LabScalar = None
    Basophils_pct: LabScalar = None


class GeminiMetadataValues(BaseModel):
    model_config = ConfigDict(extra="ignore")

    patient_name: str | None = None
    pet_owner: str | None = None
    clinic: str | None = None
    species: str | None = None
    breed: str | None = None
    gender: str | None = None
    date_receipt: str | None = None
    date_result: str | None = None
    age_str: str | None = None
    age_years: LabScalar = None
    location: str | None = None


class GeminiExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cbc: GeminiCbcValues
    metadata: GeminiMetadataValues = Field(default_factory=GeminiMetadataValues)
    comments: str | None = None
    warnings: list[str] = Field(default_factory=list)


ClientFactory = Callable[[GeminiExtractionConfig], Any]


def _env_or_setting(name: str, default: Any) -> Any:
    value = os.getenv(name)
    if value is not None and value.strip():
        return value
    return getattr(settings, name, default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env_or_setting(name, default))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env_or_setting(name, default))
    except ValueError:
        return default


def get_gemini_config_from_env() -> GeminiExtractionConfig:
    """Carga configuracion Gemini desde variables de entorno."""
    return GeminiExtractionConfig(
        api_key=_env_or_setting("GEMINI_API_KEY", None),
        model=_env_or_setting("GEMINI_MODEL", GEMINI_DEFAULT_MODEL),
        timeout_seconds=_env_float("GEMINI_TIMEOUT_SECONDS", 90.0),
        file_poll_seconds=_env_float("GEMINI_FILE_POLL_SECONDS", 2.0),
        file_poll_max_attempts=_env_int("GEMINI_FILE_POLL_MAX_ATTEMPTS", 30),
        inline_text_max_bytes=_env_int("GEMINI_INLINE_TEXT_MAX_BYTES", 200_000),
    )


def _gemini_dependency_available() -> bool:
    try:
        from google import genai as _genai  # noqa: F401
        from google.genai import types as _types  # noqa: F401
    except Exception:
        return False
    return True


def inspect_gemini_runtime() -> dict[str, Any]:
    """Diagnostico sin exponer secretos ni hacer llamadas de generacion."""
    config = get_gemini_config_from_env()
    dependency_available = _gemini_dependency_available()
    if not config.configured:
        status = "disabled"
    elif not dependency_available:
        status = "missing_dependency"
    else:
        status = "configured"

    return {
        "status": status,
        "configured": config.configured,
        "dependency_available": dependency_available,
        "model": config.model,
        "timeout_seconds": config.timeout_seconds,
        "file_poll_seconds": config.file_poll_seconds,
        "file_poll_max_attempts": config.file_poll_max_attempts,
    }


def _build_genai_client(config: GeminiExtractionConfig) -> Any:
    if not config.configured:
        raise GeminiExtractionError(
            "GEMINI_NOT_CONFIGURED",
            "GEMINI_API_KEY no esta configurada.",
        )

    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise GeminiExtractionError(
            "GEMINI_DEPENDENCY_MISSING",
            "La dependencia google-genai no esta instalada.",
        ) from exc

    timeout_ms = int(max(config.timeout_seconds, 1.0) * 1000)
    http_options = types.HttpOptions(timeout=timeout_ms)
    return genai.Client(api_key=config.api_key, http_options=http_options)


def _decode_text(contents: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return contents.decode(encoding)
        except UnicodeDecodeError:
            continue
    return contents.decode("utf-8", errors="replace")


def _extension(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


def _looks_like_excel(content_type: str, filename: str | None) -> bool:
    ext = _extension(filename)
    ct = (content_type or "").lower()
    return ext in {".xlsx", ".xls"} or "spreadsheet" in ct or "excel" in ct


def _looks_like_text_table(content_type: str, filename: str | None) -> bool:
    ext = _extension(filename)
    ct = (content_type or "").lower()
    return ext in {".csv", ".txt", ".tsv"} or ct in {
        "text/csv",
        "text/plain",
        "text/tab-separated-values",
    }


def _looks_like_pdf(content_type: str, filename: str | None) -> bool:
    return _extension(filename) == ".pdf" or (content_type or "").lower().strip() == "application/pdf"


def _mime_from_filename(content_type: str, filename: str | None) -> str:
    ct = (content_type or "").lower().strip()
    if ct and "/" in ct and ct != "application/octet-stream":
        return ct

    ext = _extension(filename)
    return {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
        ".webp": "image/webp",
        ".csv": "text/plain",
        ".txt": "text/plain",
        ".tsv": "text/plain",
    }.get(ext, "application/octet-stream")


def _excel_to_text(contents: bytes) -> str:
    try:
        import pandas as pd  # noqa: PLC0415

        sheets = pd.read_excel(io.BytesIO(contents), sheet_name=None)
    except Exception as exc:
        raise GeminiExtractionError(
            "GEMINI_TABULAR_CONVERSION_ERROR",
            f"No se pudo convertir el Excel a texto: {exc}",
        ) from exc

    parts: list[str] = []
    for sheet_name, df in sheets.items():
        parts.append(f"Sheet: {sheet_name}")
        parts.append(df.to_csv(index=False))
    return "\n".join(parts)


def _pdf_to_text(contents: bytes) -> str | None:
    try:
        import pdfplumber  # noqa: PLC0415
    except Exception:
        return None

    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception:
        return None

    text = "\n\n".join(page.strip() for page in pages if page.strip()).strip()
    return text or None


def _prepare_file_for_gemini(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
) -> tuple[bytes, str, str]:
    """Convierte formatos tabulares a texto y conserva documentos visuales."""
    if _looks_like_excel(content_type, filename):
        text = _excel_to_text(contents)
        return text.encode("utf-8"), "text/plain", f"{filename or 'hemograma'}.txt"

    if _looks_like_text_table(content_type, filename):
        text = _decode_text(contents)
        return text.encode("utf-8"), "text/plain", filename or "hemograma.txt"

    if _looks_like_pdf(content_type, filename):
        text = _pdf_to_text(contents)
        if text and len(text) >= 120:
            prompt_text = (
                f"Texto extraído localmente del PDF {filename or 'hemograma.pdf'}.\n"
                "Respeta las reglas del prompt de extracción y no inventes valores.\n\n"
                f"{text}"
            )
            return (
                prompt_text.encode("utf-8"),
                "text/plain",
                f"{filename or 'hemograma.pdf'}.txt",
            )

    return (
        contents,
        _mime_from_filename(content_type, filename),
        filename or "hemograma",
    )


def _can_send_inline_text(file_bytes: bytes, mime_type: str, config: GeminiExtractionConfig) -> bool:
    return (
        mime_type == "text/plain"
        and config.inline_text_max_bytes > 0
        and len(file_bytes) <= config.inline_text_max_bytes
    )


def _state_name(gemini_file: Any) -> str | None:
    state = getattr(gemini_file, "state", None)
    if state is None:
        return None
    name = getattr(state, "name", None)
    return str(name or state).upper()


def _wait_until_active(
    client: Any, gemini_file: Any, config: GeminiExtractionConfig
) -> Any:
    for _ in range(max(config.file_poll_max_attempts, 1)):
        state = _state_name(gemini_file)
        if state is None or "ACTIVE" in state:
            return gemini_file
        if "FAILED" in state:
            raise GeminiExtractionError(
                "GEMINI_FILE_PROCESSING_FAILED",
                "Gemini no pudo procesar el archivo subido.",
            )
        if "PROCESSING" not in state:
            return gemini_file
        time.sleep(max(config.file_poll_seconds, 0.1))
        gemini_file = client.files.get(name=gemini_file.name)

    raise GeminiExtractionError(
        "GEMINI_FILE_PROCESSING_TIMEOUT",
        "Gemini tardo demasiado procesando el archivo subido.",
    )


def _extract_json_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
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
    return text


def _parse_gemini_payload(raw_text: str) -> GeminiExtractionPayload:
    json_text = _extract_json_text(raw_text)
    try:
        return GeminiExtractionPayload.model_validate_json(json_text)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        raise GeminiExtractionError(
            "GEMINI_INVALID_JSON",
            "Gemini no devolvio JSON estructurado valido.",
        ) from exc


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _payload_to_extraction(payload: GeminiExtractionPayload) -> ExtractionResult:
    cbc = normalize_visible_cbc_values(payload.cbc.model_dump())

    metadata_age_years = coerce_lab_number(payload.metadata.age_years)
    age_years = metadata_age_years

    if not cbc:
        raise GeminiExtractionError(
            "GEMINI_NO_CBC_FIELDS",
            "Gemini no encontro valores numericos del hemograma.",
        )

    metadata = {
        "patient_name": _clean_string(payload.metadata.patient_name),
        "pet_owner": _clean_string(payload.metadata.pet_owner),
        "clinic": _clean_string(payload.metadata.clinic),
        "species": _clean_string(payload.metadata.species) or "Canino",
        "breed": _clean_string(payload.metadata.breed),
        "gender": _clean_string(payload.metadata.gender),
        "date_receipt": _clean_string(payload.metadata.date_receipt),
        "date_result": _clean_string(payload.metadata.date_result),
        "age_str": _clean_string(payload.metadata.age_str),
        "age_years": str(age_years) if age_years is not None else None,
        "location": _clean_string(payload.metadata.location or payload.metadata.clinic),
    }

    comments = _clean_string(payload.comments)
    return ExtractionResult(cbc=cbc, metadata=metadata, comments=comments)


_GEMINI_HEMOGRAM_PROMPT = f"""
Eres un extractor de datos de hemogramas caninos. Lee el archivo completo y
devuelve solamente JSON valido con el schema solicitado.

Reglas estrictas:
- Extrae solo valores CBC/hematologia presentes en el documento.
- No diagnostiques, no interpretes clinicamente y no expliques.
- No inventes valores ausentes ni infieras datos que no aparecen.
- Devuelve exactamente los 24 parametros hematologicos visibles en `cbc`.
- Usa null para cada parametro ausente.
- Campos canonicos de `cbc`: {", ".join(_CANONICAL_CBC_FIELDS)}.
- `age_years` no es parametro visible del hemograma; si aparece, colocalo en metadata.age_years.
- Devuelve numeros puros sin unidades ni flags. Ejemplos: "0.02*" => 0.02,
  "*0.02" => 0.02, "<5" => 5, "1,25" => 1.25.
- Si hay porcentajes y valores absolutos, coloca cada uno en su campo correcto.
- Si hay varios pacientes o muestras, usa la primera muestra completa del archivo.
- En metadata, conserva fechas como aparecen en el documento.
- No incluyas markdown, comentarios ni texto fuera del JSON.
"""


class GeminiExtractor:
    """Cliente de extraccion CBC con Gemini."""

    def __init__(
        self,
        config: GeminiExtractionConfig | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.config = config or get_gemini_config_from_env()
        self._client_factory = client_factory or _build_genai_client

    def extract(
        self,
        *,
        contents: bytes,
        content_type: str,
        filename: str | None,
    ) -> GeminiExtractionOutput:
        client = self._client_factory(self.config)
        file_bytes, mime_type, upload_name = _prepare_file_for_gemini(
            contents=contents,
            content_type=content_type,
            filename=filename,
        )

        warnings: list[str] = []
        uploaded_file = None
        try:
            if _can_send_inline_text(file_bytes, mime_type, self.config):
                contents_payload: list[Any] = [
                    _GEMINI_HEMOGRAM_PROMPT,
                    (
                        f"Archivo: {upload_name}\n"
                        "Contenido extraido localmente:\n"
                        "<<<HEMOGRAM_CONTENT\n"
                        f"{file_bytes.decode('utf-8', errors='replace')}\n"
                        "HEMOGRAM_CONTENT>>>"
                    ),
                ]
            else:
                file_obj = io.BytesIO(file_bytes)
                file_obj.name = upload_name
                uploaded_file = client.files.upload(
                    file=file_obj,
                    config={"mime_type": mime_type},
                )
                uploaded_file = _wait_until_active(client, uploaded_file, self.config)
                contents_payload = [uploaded_file, _GEMINI_HEMOGRAM_PROMPT]

            response = client.models.generate_content(
                model=self.config.model,
                contents=contents_payload,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": GeminiExtractionPayload,
                },
            )
            payload = _parse_gemini_payload(str(getattr(response, "text", "") or ""))
            extraction = _payload_to_extraction(payload)
            warnings.extend(str(w).strip() for w in payload.warnings if str(w).strip())
            return GeminiExtractionOutput(extraction=extraction, warnings=warnings)
        except GeminiExtractionError:
            raise
        except Exception as exc:
            logger.exception("gemini.extraction.error")
            raise GeminiExtractionError(
                "GEMINI_EXTRACTION_ERROR",
                f"Gemini no pudo extraer el hemograma: {exc}",
            ) from exc
        finally:
            if uploaded_file is not None and getattr(uploaded_file, "name", None):
                try:
                    client.files.delete(name=uploaded_file.name)
                except Exception as exc:
                    logger.warning(
                        "gemini.file.delete_failed name=%s error=%s",
                        uploaded_file.name,
                        exc,
                    )


def extract_with_gemini(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
    config: GeminiExtractionConfig | None = None,
) -> GeminiExtractionOutput:
    return GeminiExtractor(config=config).extract(
        contents=contents,
        content_type=content_type,
        filename=filename,
    )
