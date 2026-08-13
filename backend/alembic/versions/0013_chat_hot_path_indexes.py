"""Index the chat hot path by the columns its queries actually use."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_chat_hot_path_indexes"
down_revision = "0012_chat_browser_session"
branch_labels = None
depends_on = None


# Every recall query filters on session_id and orders by turn_index, and
# ``list_active`` filters on user_id + status and orders by updated_at. The
# pre-existing composite indexes put context_revision between session_id and
# turn_index, so they can satisfy the WHERE but never the ORDER BY.
_INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    ("ix_chat_messages_session_turn", "chat_messages", ["session_id", "turn_index"]),
    ("ix_chat_turns_session_turn", "chat_turns", ["session_id", "turn_index"]),
    (
        "ix_chat_sessions_user_status_updated",
        "chat_sessions",
        ["user_id", "status", "updated_at"],
    ),
)


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
    for name, table_name, columns in _INDEXES:
        existing_columns = _columns(table_name)
        if not existing_columns:
            continue
        # Installations stamped from an early chat schema may predate one of
        # these columns; skip instead of failing the whole upgrade, exactly as
        # migrations 0011/0012 do for ``status``.
        if not set(columns) <= existing_columns:
            continue
        if name in _indexes(table_name):
            continue
        op.create_index(name, table_name, columns)


def downgrade() -> None:
    for name, table_name, _ in reversed(_INDEXES):
        if name in _indexes(table_name):
            op.drop_index(name, table_name=table_name)
