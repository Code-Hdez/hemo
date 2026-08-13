"""Bind chat memory to authenticated context revisions."""

from alembic import op
import sqlalchemy as sa


revision = "0006_chat_context_memory"
down_revision = "0005_user_onboarding_tour_state"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("chat_sessions"):
        columns = _columns("chat_sessions")
        additions = {
            "auth_session_id": sa.Column("auth_session_id", sa.String(36), nullable=True),
            "context_key": sa.Column(
                "context_key", sa.String(200), nullable=False, server_default="general"
            ),
            "context_revision": sa.Column(
                "context_revision", sa.Integer(), nullable=False, server_default="1"
            ),
            "memory_summary": sa.Column("memory_summary", sa.Text(), nullable=True),
            "memory_state_json": sa.Column("memory_state_json", sa.Text(), nullable=True),
            "status": sa.Column(
                "status", sa.String(20), nullable=False, server_default="active"
            ),
            "expires_at": sa.Column("expires_at", sa.DateTime(), nullable=True),
        }
        with op.batch_alter_table("chat_sessions") as batch:
            for name, column in additions.items():
                if name not in columns:
                    batch.add_column(column)
        indexes = {
            index["name"] for index in sa.inspect(op.get_bind()).get_indexes("chat_sessions")
        }
        if "ix_chat_sessions_auth_session_id" not in indexes:
            op.create_index(
                "ix_chat_sessions_auth_session_id",
                "chat_sessions",
                ["auth_session_id"],
            )
        if "ix_chat_sessions_expires_at" not in indexes:
            op.create_index(
                "ix_chat_sessions_expires_at", "chat_sessions", ["expires_at"]
            )

    if inspector.has_table("chat_messages"):
        columns = _columns("chat_messages")
        if "context_revision" not in columns:
            with op.batch_alter_table("chat_messages") as batch:
                batch.add_column(
                    sa.Column(
                        "context_revision",
                        sa.Integer(),
                        nullable=False,
                        server_default="1",
                    )
                )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("chat_messages") and "context_revision" in _columns(
        "chat_messages"
    ):
        with op.batch_alter_table("chat_messages") as batch:
            batch.drop_column("context_revision")

    if inspector.has_table("chat_sessions"):
        indexes = {
            index["name"] for index in sa.inspect(op.get_bind()).get_indexes("chat_sessions")
        }
        if "ix_chat_sessions_expires_at" in indexes:
            op.drop_index("ix_chat_sessions_expires_at", table_name="chat_sessions")
        if "ix_chat_sessions_auth_session_id" in indexes:
            op.drop_index(
                "ix_chat_sessions_auth_session_id", table_name="chat_sessions"
            )
        columns = _columns("chat_sessions")
        with op.batch_alter_table("chat_sessions") as batch:
            for name in [
                "expires_at",
                "status",
                "memory_state_json",
                "memory_summary",
                "context_revision",
                "context_key",
                "auth_session_id",
            ]:
                if name in columns:
                    batch.drop_column(name)
