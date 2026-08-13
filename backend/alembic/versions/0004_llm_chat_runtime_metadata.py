"""Add durable chat runtime and idempotency metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0004_llm_chat_runtime_metadata"
down_revision = "0003_add_pet_profile_fields"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("chat_messages"):
        return
    columns = _columns("chat_messages")
    additions = {
        "client_message_id": sa.Column("client_message_id", sa.String(36), nullable=True),
        "status": sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        "model": sa.Column("model", sa.String(200), nullable=True),
        "prompt_tokens": sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        "completion_tokens": sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        "duration_ms": sa.Column("duration_ms", sa.Integer(), nullable=True),
        "finish_reason": sa.Column("finish_reason", sa.String(50), nullable=True),
    }
    with op.batch_alter_table("chat_messages") as batch:
        for name, column in additions.items():
            if name not in columns:
                batch.add_column(column)
    indexes = {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("chat_messages")
    }
    if "ix_chat_messages_client_message_id" not in indexes:
        op.create_index(
            "ix_chat_messages_client_message_id",
            "chat_messages",
            ["client_message_id"],
        )
    unique_names = {
        value["name"]
        for value in sa.inspect(op.get_bind()).get_unique_constraints("chat_messages")
    }
    if "uq_chat_message_client_role" not in unique_names:
        with op.batch_alter_table("chat_messages") as batch:
            batch.create_unique_constraint(
                "uq_chat_message_client_role",
                ["session_id", "role", "client_message_id"],
            )


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("chat_messages"):
        return
    columns = _columns("chat_messages")
    with op.batch_alter_table("chat_messages") as batch:
        batch.drop_constraint("uq_chat_message_client_role", type_="unique")
        for name in [
            "finish_reason",
            "duration_ms",
            "completion_tokens",
            "prompt_tokens",
            "model",
            "status",
            "client_message_id",
        ]:
            if name in columns:
                batch.drop_column(name)
