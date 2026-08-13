"""Pet persistence boundary."""

from typing import Any

from app.db import queries


def list_breeds() -> list[str]:
    return queries.list_breeds()


def list_for_owner(owner_id: str) -> list[dict[str, Any]]:
    return queries.list_pets(owner_id)


def get(pet_id: str) -> dict[str, Any] | None:
    return queries.get_pet(pet_id)


def create(**fields: Any) -> dict[str, Any]:
    return queries.create_pet(**fields)


def update(pet_id: str, **fields: Any) -> dict[str, Any] | None:
    return queries.update_pet(pet_id, **fields)


def set_photo(pet_id: str, key: str | None) -> dict[str, Any] | None:
    return queries.set_pet_profile_photo_key(pet_id, key)


def delete(pet_id: str) -> None:
    queries.delete_pet(pet_id)


def list_analyses(owner_id: str, pet_id: str) -> list[dict[str, Any]]:
    return queries.list_analysis_records_for_user(
        owner_id,
        pet_id=pet_id,
        limit=5000,
        offset=0,
    )


def delete_surveillance_events(pet_id: str) -> None:
    queries.delete_epidemiology_events_for_pet(pet_id)
