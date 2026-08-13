from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import RegisterRequest


@pytest.mark.parametrize("full_name", ["Ana Pérez", "José Manuel", "María-José", "O'Neil"])
def test_register_request_accepts_valid_full_names(full_name: str) -> None:
    request = RegisterRequest(
        full_name=full_name,
        email="owner@example.com",
        password="Demo1234",
    )

    assert request.full_name == full_name


@pytest.mark.parametrize("full_name", ["Ana123", "123", "Dueño!!!", "🐶", "   "])
def test_register_request_rejects_invalid_full_names(full_name: str) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(
            full_name=full_name,
            email="owner@example.com",
            password="Demo1234",
        )
