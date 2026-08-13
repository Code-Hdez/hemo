from __future__ import annotations

from app.db import queries as db


def save_events(events: list[dict]) -> int:
    return db.save_epidemiology_events(events)


def list_events(limit: int = 5000, offset: int = 0) -> list[dict]:
    return db.list_epidemiology_events(limit=limit, offset=offset)


def delete_events_for_analysis(analysis_id: str) -> int:
    return db.delete_epidemiology_events_for_analysis(analysis_id)


def delete_events_for_pet(pet_id: str) -> int:
    return db.delete_epidemiology_events_for_pet(pet_id)


def current_revision() -> str:
    return db.epidemiology_revision()


def list_analyses() -> list[dict]:
    return db.list_analyses(limit=5000, offset=0)
