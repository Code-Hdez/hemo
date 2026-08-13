from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("APP_ENV", "test")
os.environ.pop("DATABASE_URL", None)
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("HEMOVET_ENABLE_LOCAL_ML", "0")

from app.db import queries as db  # noqa: E402
from app.modules.auth import service as auth_service  # noqa: E402


def _reset_memory_db() -> None:
    db.DATABASE_URL = None
    db._use_db = False
    db._engine = None
    db._memory_analyses.clear()
    db._memory_users.clear()
    db._memory_pets.clear()
    db._memory_breeds.clear()
    db._memory_dashboard_metrics.clear()
    db._memory_epidemiology_events.clear()


def test_registered_users_default_to_pending_tour_state() -> None:
    _reset_memory_db()

    user = auth_service.register_user(
        email="owner@example.com",
        password="Demo1234",
        full_name="Owner",
    )

    assert user.onboarding_tour_status == "pending"
    assert user.onboarding_tour_version is None
    assert user.onboarding_tour_dismissed_at is None


def test_authenticated_user_can_mark_tour_skipped() -> None:
    _reset_memory_db()
    db.create_user("owner-1", "owner@example.com", "hashed", "Owner")

    user = auth_service.update_onboarding_tour(
        "owner-1",
        status="skipped",
        version="hemovet4-main-v1",
    )

    assert user.onboarding_tour_status == "skipped"
    assert user.onboarding_tour_version == "hemovet4-main-v1"
    assert user.onboarding_tour_dismissed_at
    assert db.get_user_by_id("owner-1")["onboarding_tour_status"] == "skipped"
