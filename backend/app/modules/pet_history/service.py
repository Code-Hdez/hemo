"""Authorization and response shaping for analysis history."""

from typing import Any

from app.modules.pet_history import repository
from app.shared.analysis_output import scrub_hidden_labels


class AnalysisNotFoundError(Exception):
    pass


class AuthenticationRequiredError(Exception):
    pass


class AnalysisAccessDeniedError(Exception):
    pass


def _attach_pet_context(record: dict[str, Any], user_id: str | None) -> dict[str, Any]:
    item = dict(record)
    pet_id = item.get("_pet_id")
    if not pet_id or user_id is None:
        return item
    pet = repository.get_pet(str(pet_id))
    if pet is None or pet.get("owner_id") != user_id:
        return item
    item.update(
        pet_id=pet.get("id"),
        pet_name=pet.get("name"),
        residence_zone_code=pet.get("residence_zone_code"),
        residence_label=pet.get("residence_label"),
    )
    return item


def _public(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def list_history(
    owner_id: str | None,
    *,
    pet_id: str | None,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    if owner_id is None:
        return []
    records = repository.list_for_owner(
        owner_id,
        pet_id=pet_id,
        limit=limit,
        offset=offset,
    )
    return [
        scrub_hidden_labels(_public(_attach_pet_context(record, owner_id)))
        for record in records
    ]


def get_analysis(analysis_id: str, owner_id: str | None) -> dict[str, Any]:
    record = repository.get(analysis_id)
    if record is None:
        raise AnalysisNotFoundError
    record_owner_id = record.get("_user_id")
    if record_owner_id and owner_id is None:
        raise AuthenticationRequiredError
    if record_owner_id and record_owner_id != owner_id:
        raise AnalysisAccessDeniedError
    if record_owner_id is None and owner_id is None:
        raise AnalysisNotFoundError
    return scrub_hidden_labels(_public(_attach_pet_context(record, owner_id)))
