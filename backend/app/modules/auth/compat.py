from __future__ import annotations

from datetime import timedelta

from app.core.security import (
    create_access_token as _create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.dependencies.auth import (
    get_current_user_id,
    get_optional_user_id,
    oauth2_scheme,
)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    return _create_access_token(str(data["sub"]), expires_delta)


def decode_token(token: str) -> dict:
    return {"sub": decode_access_token(token)}


__all__ = [
    "create_access_token",
    "decode_token",
    "get_current_user_id",
    "get_optional_user_id",
    "hash_password",
    "verify_password",
    "oauth2_scheme",
]
