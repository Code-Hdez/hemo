"""HTTP contracts for pets."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_NAME_CONNECTORS = {"-", "'", "’"}


def _valid_name_token(token: str) -> bool:
    if not token or token[0] in _NAME_CONNECTORS or token[-1] in _NAME_CONNECTORS:
        return False
    previous_was_connector = False
    for character in token:
        if character in _NAME_CONNECTORS:
            if previous_was_connector:
                return False
            previous_was_connector = True
            continue
        if not character.isalpha():
            return False
        previous_was_connector = False
    return True


def _valid_proper_name(value: str) -> bool:
    return all(_valid_name_token(token) for token in value.split())


class PetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    breed: str | None = Field(default=None, max_length=150)
    birth_year: int | None = Field(default=None, ge=1990, le=datetime.now().year)
    sex: Literal["Hembra", "Macho"] | None = None
    weight_kg: float | None = Field(default=None, ge=0.5, le=120)
    notes: str | None = Field(default=None, max_length=2000)
    residence_zone_code: str | None = None
    residence_lat: float | None = Field(default=None, ge=-90, le=90)
    residence_lng: float | None = Field(default=None, ge=-180, le=180)
    residence_source: Literal["address", "pin", "catalog"] | None = None
    residence_consent: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        clean = " ".join(value.split())
        if len(clean) < 2:
            raise ValueError("Escribe un nombre de al menos 2 caracteres.")
        if not _valid_proper_name(clean):
            raise ValueError("El nombre no puede contener números ni símbolos.")
        return clean


class PetResponse(PetCreate):
    id: str
    owner_id: str
    created_at: str
    residence_label: str | None = None
    residence_precision: str | None = None
    residence_consent: bool = False
    photo_url: str | None = None


class PetProfileExtractionResponse(BaseModel):
    source: Literal["gemini"] = "gemini"
    name: str | None = None
    breed: str | None = None
    birth_year: int | None = Field(default=None, ge=1990, le=datetime.now().year)
    sex: Literal["Hembra", "Macho"] | None = None
    weight_kg: float | None = Field(default=None, ge=0.5, le=120)
    notes: str | None = Field(default=None, max_length=2000)
    detected_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
