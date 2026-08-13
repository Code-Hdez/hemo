"""Persistence operations required by the authentication domain."""

from typing import Any

from app.db import queries


def get_by_email(email: str) -> dict[str, Any] | None:
    return queries.get_user_by_email(email)


def get_by_id(user_id: str) -> dict[str, Any] | None:
    return queries.get_user_by_id(user_id)


def create(
    *,
    user_id: str,
    email: str,
    hashed_password: str,
    full_name: str | None,
) -> None:
    queries.create_user(
        user_id=user_id,
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
    )


def update_onboarding_tour(
    *, user_id: str, status: str, version: str
) -> dict[str, Any] | None:
    return queries.update_user_onboarding_tour(
        user_id=user_id,
        status=status,
        version=version,
    )
