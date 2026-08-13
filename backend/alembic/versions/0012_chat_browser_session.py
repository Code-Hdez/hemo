"""Bind chat conversations to an ephemeral browser session."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_chat_browser_session"
down_revision = "0011_chat_context_snapshot"
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
    if not _columns("chat_sessions"):
        return
    if "browser_session_hash" not in _columns("chat_sessions"):
        with op.batch_alter_table("chat_sessions") as batch:
            batch.add_column(sa.Column("browser_session_hash", sa.String(64)))
    if "ix_chat_sessions_browser_session_hash" not in _indexes("chat_sessions"):
        op.create_index(
            "ix_chat_sessions_browser_session_hash",
            "chat_sessions",
            ["browser_session_hash"],
        )
    if "ix_chat_sessions_browser_context" not in _indexes("chat_sessions"):
        # Some installations were stamped from an early chat schema that did
        # not yet contain ``status``. Keep the migration forward-compatible
        # with those legacy databases while retaining the three-column index
        # on every canonical schema.
        index_columns = ["browser_session_hash", "context_key"]
        if "status" in _columns("chat_sessions"):
            index_columns.append("status")
        op.create_index(
            "ix_chat_sessions_browser_context",
            "chat_sessions",
            index_columns,
        )


def downgrade() -> None:
    if not _columns("chat_sessions"):
        return
    indexes = _indexes("chat_sessions")
    if "ix_chat_sessions_browser_context" in indexes:
        op.drop_index("ix_chat_sessions_browser_context", table_name="chat_sessions")
    if "ix_chat_sessions_browser_session_hash" in indexes:
        op.drop_index(
            "ix_chat_sessions_browser_session_hash", table_name="chat_sessions"
        )
    if "browser_session_hash" in _columns("chat_sessions"):
        with op.batch_alter_table("chat_sessions") as batch:
            batch.drop_column("browser_session_hash")
