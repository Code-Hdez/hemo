"""Add global idempotency and attempt leases to chat turns."""

from __future__ import annotations

import hashlib

from alembic import op
import sqlalchemy as sa


revision = "0010_chat_turn_leases"
down_revision = "0009_chat_turn_state"
branch_labels = None
depends_on = None


def _digest(*values: object) -> str:
    canonical = "\x1f".join(str(value or "") for value in values)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("chat_turns"):
        return
    columns = {column["name"] for column in inspector.get_columns("chat_turns")}
    with op.batch_alter_table("chat_turns") as batch:
        if "idempotency_key" not in columns:
            batch.add_column(sa.Column("idempotency_key", sa.String(64), nullable=True))
        if "request_fingerprint" not in columns:
            batch.add_column(sa.Column("request_fingerprint", sa.String(64), nullable=True))
        if "lease_expires_at" not in columns:
            batch.add_column(sa.Column("lease_expires_at", sa.DateTime(), nullable=True))

    connection = op.get_bind()
    sessions = sa.table(
        "chat_sessions",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("auth_session_id", sa.String),
        sa.column("context_key", sa.String),
    )
    turns = sa.table(
        "chat_turns",
        sa.column("id", sa.String),
        sa.column("session_id", sa.String),
        sa.column("client_message_id", sa.String),
        sa.column("context_revision", sa.Integer),
        sa.column("idempotency_key", sa.String),
        sa.column("request_fingerprint", sa.String),
    )
    messages = sa.table(
        "chat_messages",
        sa.column("turn_id", sa.String),
        sa.column("role", sa.String),
        sa.column("content", sa.Text),
    )
    rows = list(connection.execute(
        sa.select(
            turns.c.id,
            turns.c.client_message_id,
            turns.c.context_revision,
            sessions.c.user_id,
            sessions.c.auth_session_id,
            sessions.c.context_key,
            messages.c.content,
        )
        .select_from(turns.join(sessions, turns.c.session_id == sessions.c.id))
        .outerjoin(
            messages,
            sa.and_(messages.c.turn_id == turns.c.id, messages.c.role == "user"),
        )
        .order_by(turns.c.id)
    ).mappings())
    used_turn_ids: set[str] = set()
    used_idempotency_keys: set[str] = set()
    for row in rows:
        turn_id = str(row["id"])
        if turn_id in used_turn_ids:
            continue
        used_turn_ids.add(turn_id)
        owner = row["auth_session_id"] or f"legacy:{row['user_id']}"
        idempotency_key = _digest(row["user_id"], owner, row["client_message_id"])
        # Older deployments scoped client IDs only to a conversation. Preserve
        # every historical turn while establishing the new global uniqueness
        # contract; newly reserved turns always use the unsuffixed digest.
        if idempotency_key in used_idempotency_keys:
            idempotency_key = _digest(idempotency_key, turn_id)
            while idempotency_key in used_idempotency_keys:
                idempotency_key = _digest(idempotency_key, turn_id)
        used_idempotency_keys.add(idempotency_key)
        connection.execute(
            turns.update()
            .where(turns.c.id == row["id"])
            .values(
                idempotency_key=idempotency_key,
                request_fingerprint=_digest(
                    row["content"],
                    row["context_key"],
                    row["context_revision"],
                ),
            )
        )

    inspector = sa.inspect(op.get_bind())
    existing_indexes = {
        index["name"]
        for index in inspector.get_indexes("chat_turns")
        if index.get("name")
    }
    existing_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("chat_turns")
        if constraint.get("name")
    }
    with op.batch_alter_table("chat_turns") as batch:
        batch.alter_column("idempotency_key", existing_type=sa.String(64), nullable=False)
        batch.alter_column("request_fingerprint", existing_type=sa.String(64), nullable=False)
        if "uq_chat_turn_idempotency_key" not in existing_constraints:
            batch.create_unique_constraint(
                "uq_chat_turn_idempotency_key",
                ["idempotency_key"],
            )
        if "ix_chat_turns_lease_expires_at" not in existing_indexes:
            batch.create_index("ix_chat_turns_lease_expires_at", ["lease_expires_at"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("chat_turns"):
        return
    columns = {column["name"] for column in inspector.get_columns("chat_turns")}
    with op.batch_alter_table("chat_turns") as batch:
        indexes = {index["name"] for index in inspector.get_indexes("chat_turns")}
        constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("chat_turns")
            if constraint.get("name")
        }
        if "ix_chat_turns_lease_expires_at" in indexes:
            batch.drop_index("ix_chat_turns_lease_expires_at")
        if "uq_chat_turn_idempotency_key" in constraints:
            batch.drop_constraint("uq_chat_turn_idempotency_key", type_="unique")
        for column in ("lease_expires_at", "request_fingerprint", "idempotency_key"):
            if column in columns:
                batch.drop_column(column)
