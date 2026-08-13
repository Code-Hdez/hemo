"""Read model for dashboard aggregates."""

from typing import Any

from app.db import queries


def get_metric(key: str) -> dict[str, Any] | None:
    return queries.get_dashboard_metric(key)


def save_metric(key: str, payload: dict[str, Any]) -> None:
    queries.save_dashboard_metric(key, payload)


def list_analyses() -> list[dict[str, Any]]:
    return queries.list_analyses(limit=5000, offset=0)


def count_pet_breeds() -> list[tuple[str, int]]:
    return queries.count_pet_breeds()
