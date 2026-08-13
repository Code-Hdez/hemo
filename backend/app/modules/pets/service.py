"""Pet domain use cases."""

import io
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import settings
from app.modules.gemini_extraction.client import (
    GeminiExtractionError,
    _build_genai_client,
    _extract_json_text,
    _mime_from_filename,
    _wait_until_active,
    get_gemini_config_from_env,
)
from app.modules.files.storage import PetPhotoError, PetPhotoStore
from app.modules.maps.service import (
    ResidenceValidationError,
    build_pet_residence_fields,
)
from app.modules.pets import repository
from app.modules.pets.exceptions import InvalidResidenceError, PetNotFoundError
from app.modules.pets.schemas import PetCreate, PetProfileExtractionResponse
from app.modules.population_surveillance.service import sync_events_for_pet

logger = logging.getLogger("hemovet.pets")
photo_store = PetPhotoStore(settings.PET_MEDIA_DIR, settings.PET_PHOTO_MAX_BYTES)


class PetProfileExtractionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class GeminiPetProfilePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    breed: str | None = None
    birth_year: int | None = None
    sex: str | None = None
    weight_kg: float | str | None = None
    notes: str | None = None
    warnings: list[str] = Field(default_factory=list)


_PET_PROFILE_PROMPT = f"""
Eres un extractor de datos de fichas medicas veterinarias caninas.
Lee la imagen completa y devuelve solamente JSON valido.

Objetivo: completar parcialmente el formulario de creacion de mascota.

Schema:
{{
  "name": string|null,
  "breed": string|null,
  "birth_year": number|null,
  "sex": "Hembra"|"Macho"|null,
  "weight_kg": number|null,
  "notes": string|null,
  "warnings": string[]
}}

Reglas:
- Extrae solo datos visibles en la ficha. No inventes campos ausentes.
- Si aparece edad pero no año de nacimiento, estima birth_year usando el año actual {datetime.now().year} y floor(edad_en_años).
- Si aparece fecha de nacimiento, calcula birth_year desde esa fecha.
- Convierte peso a kg si la ficha muestra libras o gramos.
- `notes` debe incluir solo observaciones útiles de identificación o contexto de la ficha, sin diagnósticos ni tratamiento.
- No devuelvas markdown ni texto fuera del JSON.
"""


def _clean_profile_text(value: Any, *, max_length: int = 150) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split()).strip()
    if not text or text.lower() in {"unknown", "desconocido", "n/a", "na"}:
        return None
    return text[:max_length]


def _normalize_profile_sex(value: Any) -> str | None:
    text = _clean_profile_text(value)
    if not text:
        return None
    lowered = text.lower()
    if lowered.startswith(("h", "f", "female", "femenino")):
        return "Hembra"
    if lowered.startswith(("m", "male", "masculino")):
        return "Macho"
    return None


def _profile_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number == number else None
    text = str(value).replace(",", ".")
    import re

    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def _profile_birth_year(value: Any) -> int | None:
    if not isinstance(value, int):
        return None
    current_year = datetime.now().year
    return value if 1990 <= value <= current_year else None


def _supported_profile_file(content_type: str, filename: str | None) -> bool:
    ct = (content_type or "").lower()
    suffix = Path(filename or "").suffix.lower()
    return ct.startswith("image/") or suffix in {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def _profile_response_from_payload(payload: GeminiPetProfilePayload) -> PetProfileExtractionResponse:
    name = _clean_profile_text(payload.name, max_length=100)
    breed = _clean_profile_text(payload.breed)
    sex = _normalize_profile_sex(payload.sex)
    birth_year = _profile_birth_year(payload.birth_year)
    weight = _profile_number(payload.weight_kg)
    if weight is not None and not 0.5 <= weight <= 120:
        weight = None
    notes = _clean_profile_text(payload.notes, max_length=2000)
    warnings = [
        warning
        for warning in (_clean_profile_text(item, max_length=240) for item in payload.warnings)
        if warning
    ]
    detected_fields = [
        label
        for label, value in (
            ("nombre", name),
            ("raza", breed),
            ("año de nacimiento", birth_year),
            ("sexo", sex),
            ("peso", weight),
            ("notas", notes),
        )
        if value is not None
    ]
    return PetProfileExtractionResponse(
        name=name,
        breed=breed,
        birth_year=birth_year,
        sex=sex,  # type: ignore[arg-type]
        weight_kg=weight,
        notes=notes,
        detected_fields=detected_fields,
        warnings=warnings,
    )


def to_public(pet: dict[str, Any]) -> dict[str, Any]:
    result = dict(pet)
    result["photo_url"] = photo_store.public_url(result.pop("profile_photo_key", None))
    return result


def require_owned_pet(pet_id: str, owner_id: str) -> dict[str, Any]:
    pet = repository.get(pet_id)
    if pet is None or pet["owner_id"] != owner_id:
        raise PetNotFoundError
    return pet


def residence_fields(body: PetCreate) -> dict[str, Any]:
    try:
        fields = build_pet_residence_fields(
            zone_code=body.residence_zone_code,
            lat=body.residence_lat,
            lng=body.residence_lng,
            source=body.residence_source,
            consent=body.residence_consent,
        )
    except ResidenceValidationError as exc:
        raise InvalidResidenceError(str(exc)) from exc
    if not fields.get("residence_consent_at"):
        raise InvalidResidenceError(
            "Registra la dirección de residencia o marca una zona aproximada en el mapa."
        )
    return fields


def list_pets(owner_id: str) -> list[dict[str, Any]]:
    return [to_public(pet) for pet in repository.list_for_owner(owner_id)]


def create_pet(body: PetCreate, owner_id: str) -> dict[str, Any]:
    pet = repository.create(
        pet_id=str(uuid.uuid4()),
        owner_id=owner_id,
        name=body.name,
        breed=body.breed,
        birth_year=body.birth_year,
        sex=body.sex,
        weight_kg=body.weight_kg,
        notes=body.notes,
        **residence_fields(body),
    )
    return to_public(pet)


def get_pet(pet_id: str, owner_id: str) -> dict[str, Any]:
    return to_public(require_owned_pet(pet_id, owner_id))


def update_pet(pet_id: str, body: PetCreate, owner_id: str) -> dict[str, Any]:
    require_owned_pet(pet_id, owner_id)
    residence_changed = any(
        field in body.model_fields_set
        for field in (
            "residence_zone_code",
            "residence_lat",
            "residence_lng",
            "residence_source",
            "residence_consent",
        )
    )
    location_fields = residence_fields(body) if residence_changed else {}
    updated = repository.update(
        pet_id,
        name=body.name,
        breed=body.breed,
        birth_year=body.birth_year,
        sex=body.sex,
        weight_kg=body.weight_kg,
        notes=body.notes,
        **location_fields,
    )
    if updated is None:
        raise PetNotFoundError
    if residence_changed:
        analyses = repository.list_analyses(owner_id, pet_id)
        event_count = sync_events_for_pet(updated, analyses)
        logger.info(
            "epidemiology.pet_residence_sync pet_id=%s analyses=%d events=%d consent=%s",
            pet_id,
            len(analyses),
            event_count,
            updated.get("residence_consent"),
        )
    return to_public(updated)


async def save_photo(
    pet_id: str,
    file: UploadFile,
    owner_id: str,
) -> dict[str, Any]:
    pet = require_owned_pet(pet_id, owner_id)
    previous_key = pet.get("profile_photo_key")
    try:
        new_key = await photo_store.save(file)
    finally:
        await file.close()
    try:
        updated = repository.set_photo(pet_id, new_key)
    except Exception:
        photo_store.delete(new_key)
        raise
    if updated is None:
        photo_store.delete(new_key)
        raise PetNotFoundError
    photo_store.delete(previous_key)
    return to_public(updated)


def delete_photo(pet_id: str, owner_id: str) -> dict[str, Any]:
    pet = require_owned_pet(pet_id, owner_id)
    previous_key = pet.get("profile_photo_key")
    updated = repository.set_photo(pet_id, None)
    if updated is None:
        raise PetNotFoundError
    photo_store.delete(previous_key)
    return to_public(updated)


def delete_pet(pet_id: str, owner_id: str) -> None:
    pet = require_owned_pet(pet_id, owner_id)
    repository.delete_surveillance_events(pet_id)
    repository.delete(pet_id)
    photo_store.delete(pet.get("profile_photo_key"))


def extract_profile_from_file(
    *, contents: bytes, content_type: str, filename: str | None
) -> PetProfileExtractionResponse:
    if len(contents) > settings.HEMOGRAM_FILE_MAX_BYTES:
        raise PetProfileExtractionError(413, "La ficha no puede superar 10 MiB.")
    if not _supported_profile_file(content_type, filename):
        raise PetProfileExtractionError(
            422, "Sube una imagen JPG, PNG, WebP o TIFF de la ficha medica."
        )

    config = get_gemini_config_from_env()
    if not config.configured:
        raise PetProfileExtractionError(503, "Gemini no esta configurado en el servidor.")

    uploaded_file = None
    try:
        client = _build_genai_client(config)
        file_obj = io.BytesIO(contents)
        file_obj.name = filename or "ficha-mascota"
        uploaded_file = client.files.upload(
            file=file_obj,
            config={"mime_type": _mime_from_filename(content_type, filename)},
        )
        uploaded_file = _wait_until_active(client, uploaded_file, config)
        response = client.models.generate_content(
            model=config.model,
            contents=[uploaded_file, _PET_PROFILE_PROMPT],
            config={
                "response_mime_type": "application/json",
                "response_schema": GeminiPetProfilePayload,
            },
        )
        payload = GeminiPetProfilePayload.model_validate_json(
            _extract_json_text(str(getattr(response, "text", "") or ""))
        )
        return _profile_response_from_payload(payload)
    except (GeminiExtractionError, ValidationError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("pet.profile_extraction.failed filename=%s error=%s", filename, exc)
        raise PetProfileExtractionError(
            422, "No fue posible leer datos de mascota desde la ficha."
        ) from exc
    except Exception as exc:
        logger.exception("pet.profile_extraction.unexpected")
        raise PetProfileExtractionError(
            500, "Error al analizar la ficha de la mascota."
        ) from exc
    finally:
        if uploaded_file is not None and getattr(uploaded_file, "name", None):
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception as exc:
                logger.warning(
                    "pet.profile_extraction.file_delete_failed name=%s error=%s",
                    uploaded_file.name,
                    exc,
                )


__all__ = ["PetPhotoError", "PetProfileExtractionError", "photo_store"]
