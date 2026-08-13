"""Persistence reads for a pet's hematology history."""

from typing import Any

from app.db import queries


def list_for_owner(
    owner_id: str,
    *,
    pet_id: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    return queries.list_analysis_records_for_user(
        owner_id,
        pet_id=pet_id,
        limit=limit,
        offset=offset,
    )


def get(analysis_id: str) -> dict[str, Any] | None:
    return queries.get_analysis(analysis_id)


def get_pet(pet_id: str) -> dict[str, Any] | None:
    return queries.get_pet(pet_id)
