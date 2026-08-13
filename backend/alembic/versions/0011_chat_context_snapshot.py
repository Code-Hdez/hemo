"""Persist clinical context fingerprints and turn processing stages."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_chat_context_snapshot"
down_revision = "0010_chat_turn_leases"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {str(index["name"]) for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if _columns("chat_sessions"):
        columns = _columns("chat_sessions")
        with op.batch_alter_table("chat_sessions") as batch:
            if "context_fingerprint" not in columns:
                batch.add_column(sa.Column("context_fingerprint", sa.String(64)))
        if "ix_chat_sessions_context_fingerprint" not in _indexes("chat_sessions"):
            op.create_index(
                "ix_chat_sessions_context_fingerprint",
                "chat_sessions",
                ["context_fingerprint"],
            )
        if "ix_chat_sessions_auth_context" not in _indexes("chat_sessions"):
            index_columns = ["auth_session_id", "context_key"]
            if "status" in _columns("chat_sessions"):
                index_columns.append("status")
            op.create_index(
                "ix_chat_sessions_auth_context",
                "chat_sessions",
                index_columns,
            )

    if _columns("chat_turns"):
        columns = _columns("chat_turns")
        with op.batch_alter_table("chat_turns") as batch:
            if "context_fingerprint" not in columns:
                batch.add_column(sa.Column("context_fingerprint", sa.String(64)))
            if "processing_stage" not in columns:
                batch.add_column(
                    sa.Column(
                        "processing_stage",
                        sa.String(24),
                        nullable=False,
                        server_default="pending",
                    )
                )
        if "ix_chat_turns_context_fingerprint" not in _indexes("chat_turns"):
            op.create_index(
                "ix_chat_turns_context_fingerprint",
                "chat_turns",
                ["context_fingerprint"],
            )
        if "ix_chat_turns_processing_stage" not in _indexes("chat_turns"):
            op.create_index(
                "ix_chat_turns_processing_stage",
                "chat_turns",
                ["processing_stage"],
            )
        columns = _columns("chat_turns")
        if "status" in columns:
            failed_clause = (
                "WHEN status = 'failed' AND retryable THEN 'failed_retryable' "
                if "retryable" in columns
                else ""
            )
            op.execute(
                sa.text(
                    "UPDATE chat_turns SET processing_stage = CASE "
                    "WHEN status IN ('completed', 'refused') THEN 'completed' "
                    f"{failed_clause}"
                    "WHEN status = 'failed' THEN 'failed_terminal' "
                    "WHEN status = 'interrupted' THEN 'cancelled' "
                    "WHEN status = 'incomplete' THEN 'failed_retryable' "
                    "WHEN status = 'processing' THEN 'generating' "
                    "ELSE 'pending' END"
                )
            )

    if _columns("chat_turn_attempts"):
        columns = _columns("chat_turn_attempts")
        with op.batch_alter_table("chat_turn_attempts") as batch:
            if "processing_stage" not in columns:
                batch.add_column(
                    sa.Column(
                        "processing_stage",
                        sa.String(24),
                        nullable=False,
                        server_default="generating",
                    )
                )


def downgrade() -> None:
    if _columns("chat_turn_attempts") and "processing_stage" in _columns(
        "chat_turn_attempts"
    ):
        with op.batch_alter_table("chat_turn_attempts") as batch:
            batch.drop_column("processing_stage")

    if _columns("chat_turns"):
        indexes = _indexes("chat_turns")
        if "ix_chat_turns_processing_stage" in indexes:
            op.drop_index("ix_chat_turns_processing_stage", table_name="chat_turns")
        if "ix_chat_turns_context_fingerprint" in indexes:
            op.drop_index("ix_chat_turns_context_fingerprint", table_name="chat_turns")
        columns = _columns("chat_turns")
        with op.batch_alter_table("chat_turns") as batch:
            if "processing_stage" in columns:
                batch.drop_column("processing_stage")
            if "context_fingerprint" in columns:
                batch.drop_column("context_fingerprint")

    if _columns("chat_sessions"):
        indexes = _indexes("chat_sessions")
        if "ix_chat_sessions_auth_context" in indexes:
            op.drop_index("ix_chat_sessions_auth_context", table_name="chat_sessions")
        if "ix_chat_sessions_context_fingerprint" in indexes:
            op.drop_index(
                "ix_chat_sessions_context_fingerprint", table_name="chat_sessions"
            )
        if "context_fingerprint" in _columns("chat_sessions"):
            with op.batch_alter_table("chat_sessions") as batch:
                batch.drop_column("context_fingerprint")
