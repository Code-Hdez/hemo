"""Add deterministic per-revision ordering to chat transcripts."""

from __future__ import annotations

from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision = "0008_chat_turn_order"
down_revision = "0007_analysis_parameters"
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


def _unique_constraints(table: str) -> set[str]:
    return {
        str(constraint["name"])
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(table)
        if constraint.get("name")
    }


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not (
        inspector.has_table("chat_sessions")
        and inspector.has_table("chat_messages")
    ):
        return

    if "next_turn_index" not in _columns("chat_sessions"):
        with op.batch_alter_table("chat_sessions") as batch:
            batch.add_column(
                sa.Column(
                    "next_turn_index",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                )
            )

    if "turn_index" not in _columns("chat_messages"):
        with op.batch_alter_table("chat_messages") as batch:
            batch.add_column(sa.Column("turn_index", sa.Integer(), nullable=True))

    connection = op.get_bind()
    messages = sa.table(
        "chat_messages",
        sa.column("id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("client_message_id", sa.String),
        sa.column("context_revision", sa.Integer),
        sa.column("turn_index", sa.Integer),
        sa.column("created_at", sa.DateTime),
    )
    sessions = sa.table(
        "chat_sessions",
        sa.column("id", sa.String),
        sa.column("context_revision", sa.Integer),
        sa.column("next_turn_index", sa.Integer),
    )

    rows = connection.execute(
        sa.select(
            messages.c.id,
            messages.c.session_id,
            messages.c.client_message_id,
            messages.c.context_revision,
            messages.c.created_at,
        ).order_by(
            messages.c.session_id,
            messages.c.context_revision,
            messages.c.created_at,
            messages.c.id,
        )
    ).mappings()
    next_by_revision: defaultdict[tuple[str, int], int] = defaultdict(lambda: 1)
    paired_turns: dict[tuple[str, int, str], int] = {}
    for row in rows:
        session_id = str(row["session_id"])
        context_revision = int(row["context_revision"] or 1)
        group = (session_id, context_revision)
        client_message_id = str(row["client_message_id"] or "")
        pair_key = (session_id, context_revision, client_message_id)
        turn_index = paired_turns.get(pair_key) if client_message_id else None
        if turn_index is None:
            turn_index = next_by_revision[group]
            next_by_revision[group] = turn_index + 1
            if client_message_id:
                paired_turns[pair_key] = turn_index
        connection.execute(
            messages.update()
            .where(messages.c.id == row["id"])
            .values(turn_index=turn_index)
        )

    for row in connection.execute(
        sa.select(sessions.c.id, sessions.c.context_revision)
    ).mappings():
        group = (str(row["id"]), int(row["context_revision"] or 1))
        connection.execute(
            sessions.update()
            .where(sessions.c.id == row["id"])
            .values(next_turn_index=next_by_revision[group])
        )

    with op.batch_alter_table("chat_sessions") as batch:
        batch.alter_column(
            "next_turn_index",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="1",
        )
    with op.batch_alter_table("chat_messages") as batch:
        batch.alter_column(
            "turn_index",
            existing_type=sa.Integer(),
            nullable=False,
            server_default="1",
        )

    if "ix_chat_messages_session_revision_turn" not in _indexes("chat_messages"):
        op.create_index(
            "ix_chat_messages_session_revision_turn",
            "chat_messages",
            ["session_id", "context_revision", "turn_index"],
        )
    if "uq_chat_message_turn_role" not in _unique_constraints("chat_messages"):
        with op.batch_alter_table("chat_messages") as batch:
            batch.create_unique_constraint(
                "uq_chat_message_turn_role",
                ["session_id", "context_revision", "turn_index", "role"],
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("chat_messages"):
        if "ix_chat_messages_session_revision_turn" in _indexes("chat_messages"):
            op.drop_index(
                "ix_chat_messages_session_revision_turn",
                table_name="chat_messages",
            )
        with op.batch_alter_table("chat_messages") as batch:
            if "uq_chat_message_turn_role" in _unique_constraints("chat_messages"):
                batch.drop_constraint("uq_chat_message_turn_role", type_="unique")
            if "turn_index" in _columns("chat_messages"):
                batch.drop_column("turn_index")
    if inspector.has_table("chat_sessions") and "next_turn_index" in _columns(
        "chat_sessions"
    ):
        with op.batch_alter_table("chat_sessions") as batch:
            batch.drop_column("next_turn_index")
