from __future__ import annotations

import ast
import os
import json
from pathlib import Path
import subprocess
import sys

import sqlalchemy as sa


def test_alembic_revision_identifiers_fit_postgresql_version_table() -> None:
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    revision_ids: list[str] = []
    for path in versions_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "revision"
                for target in node.targets
            ):
                continue
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                revision_ids.append(node.value.value)
    assert revision_ids
    assert all(len(revision_id) <= 32 for revision_id in revision_ids)


def test_alembic_upgrade_creates_current_schema(tmp_path) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": database_url,
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "PYTHONPATH": "backend",
    }
    # Make the cwd resilient: tests may run with pytest invoked from backend
    # or from repository root. Prefer the repository's 'backend' directory
    # when present, otherwise use the current working directory.
    backend_cwd = os.path.join(os.getcwd(), "backend")
    cwd_param = backend_cwd if os.path.isdir(backend_cwd) else os.getcwd()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=cwd_param,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    inspector = sa.inspect(sa.create_engine(database_url))
    assert {
        "users",
        "pets",
        "analyses",
        "analysis_parameters",
        "chat_sessions",
        "chat_messages",
        "chat_turns",
        "chat_turn_attempts",
        "epidemiology_events",
    }.issubset(
        inspector.get_table_names()
    )
    assert "role" in {column["name"] for column in inspector.get_columns("users")}
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert {
        "onboarding_tour_status",
        "onboarding_tour_version",
        "onboarding_tour_dismissed_at",
    } <= user_columns
    analysis_columns = {
        column["name"] for column in inspector.get_columns("analyses")
    }
    assert {
        "performed_at",
        "laboratory",
        "extraction_confidence",
        "data_origin",
    } <= analysis_columns
    session_columns = {
        column["name"] for column in inspector.get_columns("chat_sessions")
    }
    assert {
        "auth_session_id",
        "context_key",
        "context_revision",
        "next_turn_index",
        "memory_summary",
        "memory_state_json",
        "expires_at",
    } <= session_columns
    message_columns = {
        column["name"] for column in inspector.get_columns("chat_messages")
    }
    assert {"context_revision", "turn_index", "turn_id"} <= message_columns
    turn_columns = {
        column["name"] for column in inspector.get_columns("chat_turns")
    }
    assert {
        "idempotency_key",
        "request_fingerprint",
        "lease_expires_at",
    } <= turn_columns
    assert "uq_chat_turn_idempotency_key" in {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("chat_turns")
    }
    assert "ix_chat_turns_lease_expires_at" in {
        index["name"] for index in inspector.get_indexes("chat_turns")
    }


def test_existing_schema_can_be_stamped_then_upgraded(tmp_path) -> None:
    database_path = tmp_path / "existing.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = sa.create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(254) NOT NULL, "
                "hashed_password TEXT NOT NULL, full_name VARCHAR(200), created_at DATETIME NOT NULL, "
                "is_active BOOLEAN NOT NULL)"
            )
        )
    env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": database_url,
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "PYTHONPATH": "backend",
    }
    for arguments in (
        ["stamp", "0001_current_schema"],
        ["upgrade", "head"],
    ):
        backend_cwd = os.path.join(os.getcwd(), "backend")
        cwd_param = backend_cwd if os.path.isdir(backend_cwd) else os.getcwd()
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", *arguments],
            cwd=cwd_param,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    user_columns = {column["name"] for column in sa.inspect(engine).get_columns("users")}
    assert "role" in user_columns
    assert {
        "onboarding_tour_status",
        "onboarding_tour_version",
        "onboarding_tour_dismissed_at",
    } <= user_columns


def test_clinical_parameter_migration_backfills_legacy_values_truthfully(
    tmp_path,
) -> None:
    database_path = tmp_path / "legacy-analysis.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": database_url,
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "PYTHONPATH": "backend",
    }
    backend_cwd = os.path.join(os.getcwd(), "backend")
    cwd_param = backend_cwd if os.path.isdir(backend_cwd) else os.getcwd()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "alembic.ini",
            "upgrade",
            "0006_chat_context_memory",
        ],
        cwd=cwd_param,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    engine = sa.create_engine(database_url)
    payload = {
        "id": "legacy-1",
        "created_at": "2026-03-14T10:00:00",
        "confidence": 0.91,
        "extraction_provider": "local",
        "lab_values": [
            {
                "name": "WBC",
                "value": "22.4",
                "unit": "x10³/µL",
                "status": "high",
                "ref_min": 6.0,
                "ref_max": 17.0,
            }
        ],
    }
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO analyses (id, data, created_at, user_id, pet_id, data_origin) "
                "VALUES (:id, :data, :created_at, NULL, NULL, 'unknown')"
            ),
            {
                "id": "legacy-1",
                "data": json.dumps(payload),
                "created_at": "2026-03-14 10:00:00",
            },
        )

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=cwd_param,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    with engine.connect() as connection:
        row = connection.execute(
            sa.text(
                "SELECT canonical_name, numeric_value, reference_min, reference_max, "
                "reference_origin, derived_flag, data_origin "
                "FROM analysis_parameters WHERE analysis_id = 'legacy-1'"
            )
        ).mappings().one()

    assert row["canonical_name"] == "WBC"
    assert float(row["numeric_value"]) == 22.4
    assert float(row["reference_min"]) == 6.0
    assert float(row["reference_max"]) == 17.0
    assert row["reference_origin"] == "system_default_legacy"
    assert row["derived_flag"] == "high"
    assert row["data_origin"] == "legacy_json"


def test_chat_turn_order_migration_pairs_existing_user_and_assistant_rows(
    tmp_path,
) -> None:
    database_path = tmp_path / "legacy-chat-order.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = sa.create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE chat_sessions ("
                "id VARCHAR(36) PRIMARY KEY, context_revision INTEGER NOT NULL DEFAULT 1)"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE chat_messages ("
                "id VARCHAR(36) PRIMARY KEY, session_id VARCHAR(36) NOT NULL, "
                "client_message_id VARCHAR(36), role VARCHAR(20) NOT NULL, "
                "context_revision INTEGER NOT NULL DEFAULT 1, created_at DATETIME NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_sessions (id, context_revision) VALUES ('chat-1', 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_messages "
                "(id, session_id, client_message_id, role, context_revision, created_at) "
                "VALUES "
                "('m1', 'chat-1', 'client-1', 'user', 1, '2026-07-09 10:00:00'), "
                "('m2', 'chat-1', 'client-1', 'assistant', 1, '2026-07-09 10:00:01'), "
                "('m3', 'chat-1', 'client-2', 'user', 1, '2026-07-09 10:00:02')"
            )
        )

    env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": database_url,
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "PYTHONPATH": "backend",
    }
    backend_cwd = os.path.join(os.getcwd(), "backend")
    cwd_param = backend_cwd if os.path.isdir(backend_cwd) else os.getcwd()
    for arguments in (
        ["stamp", "0007_analysis_parameters"],
        ["upgrade", "0008_chat_turn_order"],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", *arguments],
            cwd=cwd_param,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT id, turn_index FROM chat_messages "
                "ORDER BY created_at, id"
            )
        ).mappings().all()
        next_turn_index = connection.execute(
            sa.text(
                "SELECT next_turn_index FROM chat_sessions WHERE id = 'chat-1'"
            )
        ).scalar_one()

    assert [(row["id"], row["turn_index"]) for row in rows] == [
        ("m1", 1),
        ("m2", 1),
        ("m3", 2),
    ]
    assert next_turn_index == 3


def test_chat_turn_lease_migration_preserves_legacy_duplicate_client_ids(
    tmp_path,
) -> None:
    database_path = tmp_path / "legacy-duplicate-client-id.db"
    database_url = f"sqlite+pysqlite:///{database_path}"
    engine = sa.create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "CREATE TABLE chat_sessions ("
                "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36), "
                "auth_session_id VARCHAR(36), context_key VARCHAR(200) NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE chat_turns ("
                "id VARCHAR(36) PRIMARY KEY, session_id VARCHAR(36) NOT NULL, "
                "client_message_id VARCHAR(36) NOT NULL, context_revision INTEGER NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "CREATE TABLE chat_messages ("
                "id VARCHAR(36) PRIMARY KEY, turn_id VARCHAR(36), role VARCHAR(20) NOT NULL, "
                "content TEXT NOT NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_sessions "
                "(id, user_id, auth_session_id, context_key) VALUES "
                "('session-1', 'user-1', 'auth-1', 'general'), "
                "('session-2', 'user-1', 'auth-1', 'selected:analysis-1')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_turns "
                "(id, session_id, client_message_id, context_revision) VALUES "
                "('turn-1', 'session-1', 'client-duplicate', 1), "
                "('turn-2', 'session-2', 'client-duplicate', 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_messages (id, turn_id, role, content) VALUES "
                "('message-1', 'turn-1', 'user', 'Primera pregunta'), "
                "('message-2', 'turn-2', 'user', 'Segunda pregunta')"
            )
        )

    env = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": database_url,
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "PYTHONPATH": "backend",
    }
    backend_cwd = os.path.join(os.getcwd(), "backend")
    cwd_param = backend_cwd if os.path.isdir(backend_cwd) else os.getcwd()
    for arguments in (
        ["stamp", "0009_chat_turn_state"],
        ["upgrade", "head"],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", *arguments],
            cwd=cwd_param,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT id, idempotency_key, request_fingerprint "
                "FROM chat_turns ORDER BY id"
            )
        ).mappings().all()

    assert len(rows) == 2
    assert rows[0]["idempotency_key"] != rows[1]["idempotency_key"]
    assert all(len(row["idempotency_key"]) == 64 for row in rows)
    assert all(len(row["request_fingerprint"]) == 64 for row in rows)
