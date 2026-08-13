from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("HEMOVET_ENABLE_LOCAL_ML", "0")

from app.application import health
from app.main import app


def test_health_and_versioned_routes_have_a_stable_contract() -> None:
    paths = set(app.openapi()["paths"])
    assert {
        "/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me/onboarding-tour",
        "/api/v1/pets",
        "/api/v1/pets/{pet_id}/photo",
        "/api/v1/epidemiology/points",
        "/api/v1/surveillance/report",
        "/api/v1/chat",
        "/api/v1/extract",
        "/api/v1/predict/batch",
    } <= paths

    response = health()
    assert response["status"] == "ok"
    assert response["schema_version"]
