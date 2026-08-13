from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.modules.pets.schemas import PetCreate
from app.modules.pets import service as pets_service


def test_pet_create_rejects_invalid_profile_values() -> None:
    with pytest.raises(ValidationError):
        PetCreate(
            name="<script>alert(1)</script>",
            birth_year=datetime.now().year + 1,
            sex="INVALID_SEX",
            weight_kg=-5,
        )


@pytest.mark.parametrize("name", ["Max123", "123", "Firulais!!!", "@@@", "🐶", "   "])
def test_pet_create_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValidationError):
        PetCreate(name=name)


@pytest.mark.parametrize("name", ["Max", "Niña", "Dulce María", "Rocky-Jr", "O'Neil"])
def test_pet_create_accepts_valid_names(name: str) -> None:
    assert PetCreate(name=name).name == name


def test_pet_create_accepts_valid_profile_and_trims_name() -> None:
    pet = PetCreate(
        name="  Lucas  ",
        birth_year=2020,
        sex="Macho",
        weight_kg=12.5,
    )

    assert pet.name == "Lucas"


def test_pet_profile_payload_maps_to_form_suggestion() -> None:
    response = pets_service._profile_response_from_payload(
        pets_service.GeminiPetProfilePayload(
            name=" Luna ",
            breed="Mestizo",
            birth_year=datetime.now().year - 4,
            sex="female",
            weight_kg="18,4 kg",
            notes="Control anual.",
        )
    )

    assert response.name == "Luna"
    assert response.sex == "Hembra"
    assert response.weight_kg == 18.4
    assert "nombre" in response.detected_fields
