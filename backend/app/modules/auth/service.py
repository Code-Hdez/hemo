"""Authentication use cases independent from FastAPI routing."""

import uuid
from typing import Any

from app.modules.auth import compat as security
from app.modules.auth import repository
from app.modules.auth.schemas import TokenResponse, UserResponse


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


def to_response(user: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        created_at=user["created_at"],
        role=user.get("role", "user"),
        onboarding_tour_status=user.get("onboarding_tour_status", "pending"),
        onboarding_tour_version=user.get("onboarding_tour_version"),
        onboarding_tour_dismissed_at=user.get("onboarding_tour_dismissed_at"),
    )


def register_user(*, email: str, password: str, full_name: str | None) -> UserResponse:
    if repository.get_by_email(email) is not None:
        raise EmailAlreadyRegisteredError

    user_id = str(uuid.uuid4())
    repository.create(
        user_id=user_id,
        email=email,
        hashed_password=security.hash_password(password),
        full_name=full_name,
    )
    user = repository.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError
    return to_response(user)


def authenticate(email: str, password: str) -> TokenResponse:
    user = repository.get_by_email(email)
    if user is None or not security.verify_password(password, user["hashed_password"]):
        raise InvalidCredentialsError
    return TokenResponse(
        access_token=security.create_access_token({"sub": user["id"]}),
        token_type="bearer",
    )


def get_user(user_id: str) -> UserResponse:
    user = repository.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError
    return to_response(user)


def update_onboarding_tour(
    user_id: str, *, status: str, version: str
) -> UserResponse:
    user = repository.update_onboarding_tour(
        user_id=user_id,
        status=status,
        version=version,
    )
    if user is None:
        raise UserNotFoundError
    return to_response(user)
