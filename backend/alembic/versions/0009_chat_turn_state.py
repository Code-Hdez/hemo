"""Add canonical chat turns and auditable execution attempts."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0009_chat_turn_state"
down_revision = "0008_chat_turn_order"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {
        str(index["name"])
        for index in sa.inspect(op.get_bind()).get_indexes(table)
        if index.get("name")
    }


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("chat_sessions") or not inspector.has_table("chat_messages"):
        return

    if not inspector.has_table("chat_turns"):
        op.create_table(
            "chat_turns",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "session_id",
                sa.String(length=36),
                sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("client_message_id", sa.String(length=36), nullable=False),
            sa.Column("context_revision", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("turn_index", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("error_code", sa.String(length=80), nullable=True),
            sa.Column("retryable", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("user_message_id", sa.String(length=36), nullable=True),
            sa.Column("assistant_message_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "session_id",
                "client_message_id",
                name="uq_chat_turn_session_client",
            ),
            sa.UniqueConstraint(
                "session_id",
                "context_revision",
                "turn_index",
                name="uq_chat_turn_revision_index",
            ),
        )
        op.create_index("ix_chat_turns_session_id", "chat_turns", ["session_id"])
        op.create_index(
            "ix_chat_turns_client_message_id",
            "chat_turns",
            ["client_message_id"],
        )
        op.create_index("ix_chat_turns_status", "chat_turns", ["status"])
        op.create_index(
            "ix_chat_turns_session_revision_index",
            "chat_turns",
            ["session_id", "context_revision", "turn_index"],
        )

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("chat_turn_attempts"):
        op.create_table(
            "chat_turn_attempts",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "turn_id",
                sa.String(length=36),
                sa.ForeignKey("chat_turns.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("attempt_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="processing"),
            sa.Column("error_code", sa.String(length=80), nullable=True),
            sa.Column("response_origin", sa.String(length=40), nullable=True),
            sa.Column("provider", sa.String(length=40), nullable=True),
            sa.Column("model", sa.String(length=200), nullable=True),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("finish_reason", sa.String(length=80), nullable=True),
            sa.Column("validation_reason", sa.String(length=120), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "turn_id",
                "attempt_number",
                name="uq_chat_turn_attempt_number",
            ),
        )
        op.create_index(
            "ix_chat_turn_attempts_turn_id",
            "chat_turn_attempts",
            ["turn_id"],
        )

    if "turn_id" not in _columns("chat_messages"):
        with op.batch_alter_table("chat_messages") as batch:
            batch.add_column(sa.Column("turn_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_chat_messages_turn_id",
                "chat_turns",
                ["turn_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index("ix_chat_messages_turn_id", ["turn_id"])

    _backfill_turns()


def _backfill_turns() -> None:
    connection = op.get_bind()
    messages = sa.table(
        "chat_messages",
        sa.column("id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("turn_id", sa.String),
        sa.column("client_message_id", sa.String),
        sa.column("role", sa.String),
        sa.column("status", sa.String),
        sa.column("model", sa.String),
        sa.column("prompt_tokens", sa.Integer),
        sa.column("completion_tokens", sa.Integer),
        sa.column("duration_ms", sa.Integer),
        sa.column("finish_reason", sa.String),
        sa.column("metadata_json", sa.Text),
        sa.column("context_revision", sa.Integer),
        sa.column("turn_index", sa.Integer),
        sa.column("created_at", sa.DateTime),
    )
    turns = sa.table(
        "chat_turns",
        sa.column("id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("client_message_id", sa.String),
        sa.column("context_revision", sa.Integer),
        sa.column("turn_index", sa.Integer),
        sa.column("status", sa.String),
        sa.column("attempt_count", sa.Integer),
        sa.column("error_code", sa.String),
        sa.column("retryable", sa.Boolean),
        sa.column("user_message_id", sa.String),
        sa.column("assistant_message_id", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
        sa.column("started_at", sa.DateTime),
        sa.column("completed_at", sa.DateTime),
    )
    attempts = sa.table(
        "chat_turn_attempts",
        sa.column("id", sa.String),
        sa.column("turn_id", sa.String),
        sa.column("attempt_number", sa.Integer),
        sa.column("status", sa.String),
        sa.column("error_code", sa.String),
        sa.column("response_origin", sa.String),
        sa.column("provider", sa.String),
        sa.column("model", sa.String),
        sa.column("prompt_tokens", sa.Integer),
        sa.column("completion_tokens", sa.Integer),
        sa.column("duration_ms", sa.Integer),
        sa.column("finish_reason", sa.String),
        sa.column("validation_reason", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("completed_at", sa.DateTime),
    )

    rows = list(
        connection.execute(
            sa.select(messages).where(messages.c.turn_id.is_(None)).order_by(
                messages.c.session_id,
                messages.c.context_revision,
                messages.c.turn_index,
                messages.c.created_at,
                messages.c.id,
            )
        ).mappings()
    )
    grouped: defaultdict[tuple[str, int, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                str(row["session_id"]),
                int(row["context_revision"] or 1),
                int(row["turn_index"] or 1),
            )
        ].append(dict(row))

    for (session_id, revision, turn_index), group in grouped.items():
        user = next((row for row in group if row["role"] == "user"), None)
        assistant = next((row for row in group if row["role"] == "assistant"), None)
        source = user or assistant
        if source is None:
            continue
        client_message_id = str(source.get("client_message_id") or uuid4())
        user_status = str(user.get("status") if user else "")
        assistant_status = str(assistant.get("status") if assistant else "")
        if assistant_status in {"completed", "refused"}:
            status = assistant_status
        elif assistant_status == "failed":
            status = "failed"
        elif user_status in {"failed", "interrupted", "incomplete"}:
            status = user_status
        elif user_status == "pending":
            status = "processing"
        else:
            status = "failed"

        metadata: dict[str, object] = {}
        if assistant:
            try:
                parsed = json.loads(str(assistant.get("metadata_json") or "{}"))
                metadata = parsed if isinstance(parsed, dict) else {}
            except (TypeError, ValueError, json.JSONDecodeError):
                metadata = {}
        route_trace = metadata.get("route_trace")
        route_trace = route_trace if isinstance(route_trace, dict) else {}
        llm_invoked = bool(route_trace.get("llm_invoked") or (assistant and assistant.get("model")))
        response_origin = "llm" if llm_invoked else "legacy_deterministic"
        error_code = None if status in {"completed", "refused"} else str(
            route_trace.get("fallback_type") or (assistant and assistant.get("finish_reason")) or status
        )
        now = source.get("created_at") or datetime.utcnow()
        completed_at = now if status not in {"pending", "processing"} else None
        turn_id = str(uuid4())
        connection.execute(
            turns.insert().values(
                id=turn_id,
                session_id=session_id,
                client_message_id=client_message_id,
                context_revision=revision,
                turn_index=turn_index,
                status=status,
                attempt_count=1,
                error_code=error_code,
                retryable=status in {"failed", "interrupted", "incomplete"},
                user_message_id=(str(user["id"]) if user else None),
                assistant_message_id=(str(assistant["id"]) if assistant else None),
                created_at=now,
                updated_at=now,
                started_at=now,
                completed_at=completed_at,
            )
        )
        connection.execute(
            attempts.insert().values(
                id=str(uuid4()),
                turn_id=turn_id,
                attempt_number=1,
                status=status,
                error_code=error_code,
                response_origin=response_origin,
                provider=None,
                model=(assistant.get("model") if assistant else None),
                prompt_tokens=int((assistant and assistant.get("prompt_tokens")) or 0),
                completion_tokens=int((assistant and assistant.get("completion_tokens")) or 0),
                duration_ms=(assistant.get("duration_ms") if assistant else None),
                finish_reason=(assistant.get("finish_reason") if assistant else None),
                validation_reason=error_code,
                created_at=now,
                completed_at=completed_at,
            )
        )
        for row in group:
            values: dict[str, object] = {"turn_id": turn_id}
            if row["role"] == "user" and status in {"failed", "interrupted", "incomplete"}:
                values["status"] = status
            connection.execute(
                messages.update().where(messages.c.id == row["id"]).values(**values)
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("chat_messages") and "turn_id" in _columns("chat_messages"):
        turn_foreign_key = next(
            (
                foreign_key.get("name")
                for foreign_key in inspector.get_foreign_keys("chat_messages")
                if foreign_key.get("constrained_columns") == ["turn_id"]
            ),
            None,
        )
        with op.batch_alter_table("chat_messages") as batch:
            if "ix_chat_messages_turn_id" in _indexes("chat_messages"):
                batch.drop_index("ix_chat_messages_turn_id")
            # SQLite reflects this foreign key without a name. Dropping the
            # column in batch mode rebuilds the table and removes that unnamed
            # constraint; other engines expose the explicit migration name.
            if turn_foreign_key:
                batch.drop_constraint(str(turn_foreign_key), type_="foreignkey")
            batch.drop_column("turn_id")
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("chat_turn_attempts"):
        op.drop_table("chat_turn_attempts")
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("chat_turns"):
        op.drop_table("chat_turns")
