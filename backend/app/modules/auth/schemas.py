"""HTTP contracts for authentication endpoints."""

from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator

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


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if not any(character.isupper() for character in value):
            raise ValueError("La contraseña debe contener al menos una mayúscula")
        if not any(character.isdigit() for character in value):
            raise ValueError("La contraseña debe contener al menos un número")
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        clean = " ".join(value.split())
        if len(clean) < 2:
            raise ValueError("El nombre completo es obligatorio.")
        if not _valid_proper_name(clean):
            raise ValueError("El nombre completo no puede contener números ni símbolos.")
        return clean


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    created_at: str
    role: Literal["user", "admin"] = "user"
    onboarding_tour_status: Literal["pending", "completed", "skipped"] = "pending"
    onboarding_tour_version: str | None = None
    onboarding_tour_dismissed_at: str | None = None


class OnboardingTourUpdateRequest(BaseModel):
    status: Literal["completed", "skipped"]
    version: str
