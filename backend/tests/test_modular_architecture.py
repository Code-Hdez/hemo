from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("HEMOVET_ENABLE_LOCAL_ML", "0")


def test_application_exposes_only_versioned_domain_routes() -> None:
    from app.main import app

    paths = set(app.openapi()["paths"])

    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me/onboarding-tour" in paths
    assert "/api/v1/pets" in paths
    assert "/api/v1/history" in paths
    assert "/api/v1/analyze/confirmed" in paths
    assert "/api/v1/chat" in paths
    assert "/api/v1/model/quality" in paths
    assert "/api/v1/residence/zones" in paths
    assert "/api/v1/epidemiology/points" in paths
    assert "/api/v1/surveillance/report" in paths
    assert "/health" in paths
    assert "/api/auth/login" not in paths
    assert "/api/epidemiological" not in paths


def test_runtime_configuration_requires_database_and_secret_outside_tests() -> None:
    from pydantic import ValidationError

    from app.core.config import Settings

    try:
        Settings(APP_ENV="production", DATABASE_URL="", SECRET_KEY="")
    except ValidationError:
        return
    raise AssertionError(
        "Production settings must reject empty DATABASE_URL and SECRET_KEY"
    )
