from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.shared.dates import utc_now


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index(
            "ix_chat_sessions_browser_context",
            "browser_session_hash",
            "context_key",
            "status",
        ),
        # Created by migration 0011 and still the access path of the logout
        # sweep in ``auth/router`` (auth_session_id + status). Declared here so
        # ``alembic --autogenerate`` stops proposing to drop an index the
        # database really has.
        Index(
            "ix_chat_sessions_auth_context",
            "auth_session_id",
            "context_key",
            "status",
        ),
        # ``list_active`` filters by user_id + status and orders by
        # updated_at. With updated_at in the index the ordering is served by
        # the index itself instead of sorting every conversation the account
        # ever opened.
        Index(
            "ix_chat_sessions_user_status_updated",
            "user_id",
            "status",
            "updated_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    active_pet_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("pets.id", ondelete="SET NULL")
    )
    active_analysis_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="SET NULL")
    )
    active_source_id: Mapped[str | None] = mapped_column(String(200))
    active_topic: Mapped[str | None] = mapped_column(String(300))
    last_mode: Mapped[str] = mapped_column(String(20), default="auto")
    auth_session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    # HMAC of the ephemeral sessionStorage UUID. The raw browser identifier is
    # never persisted, while this boundary prevents a new browser session from
    # resuming conversations tied only to the long-lived auth session.
    browser_session_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    context_key: Mapped[str] = mapped_column(String(200), default="general")
    context_revision: Mapped[int] = mapped_column(Integer, default=1)
    context_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    # Allocated under a row lock by the conversation repository. The counter
    # is monotonic across the conversation's whole lifetime — including
    # across clinical context revision changes — so turn_index remains a
    # single, deterministic transcript order even after a new hemogram or
    # profile snapshot rotates context_revision. It is never reset, because
    # conversational continuity (this ordering) is a distinct concern from
    # clinical-data freshness (context_revision).
    next_turn_index: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
    )
    memory_summary: Mapped[str | None] = mapped_column(Text)
    memory_state_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class ChatTurn(Base):
    """Canonical state for one idempotent user turn.

    Messages are the public transcript.  A turn is the execution state that may
    have several provider attempts without duplicating the user's message.
    """

    __tablename__ = "chat_turns"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "client_message_id",
            name="uq_chat_turn_session_client",
        ),
        UniqueConstraint(
            "session_id",
            "context_revision",
            "turn_index",
            name="uq_chat_turn_revision_index",
        ),
        Index(
            "ix_chat_turns_session_revision_index",
            "session_id",
            "context_revision",
            "turn_index",
        ),
        # turn_index is monotonic across clinical revisions, so every read of
        # the transcript order (``turn_history``) filters on session_id alone
        # and sorts by turn_index. The revision-scoped index above cannot
        # serve that ORDER BY because context_revision sits between the two
        # columns the query actually uses.
        Index(
            "ix_chat_turns_session_turn",
            "session_id",
            "turn_index",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_chat_turn_idempotency_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    client_message_id: Mapped[str] = mapped_column(String(36), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    context_revision: Mapped[int] = mapped_column(Integer, default=1)
    context_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    processing_stage: Mapped[str] = mapped_column(
        String(24), default="pending", server_default="pending", index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    error_code: Mapped[str | None] = mapped_column(String(80))
    retryable: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    user_message_id: Mapped[str | None] = mapped_column(String(36))
    assistant_message_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)


class ChatTurnAttempt(Base):
    """Auditable execution attempt for a chat turn, without storing prompts."""

    __tablename__ = "chat_turn_attempts"
    __table_args__ = (
        UniqueConstraint(
            "turn_id",
            "attempt_number",
            name="uq_chat_turn_attempt_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    turn_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_turns.id", ondelete="CASCADE"), index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="processing")
    processing_stage: Mapped[str] = mapped_column(
        String(24), default="generating", server_default="generating"
    )
    error_code: Mapped[str | None] = mapped_column(String(80))
    response_origin: Mapped[str | None] = mapped_column(String(40))
    provider: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(200))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    finish_reason: Mapped[str | None] = mapped_column(String(80))
    validation_reason: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "role",
            "client_message_id",
            name="uq_chat_message_client_role",
        ),
        UniqueConstraint(
            "session_id",
            "context_revision",
            "turn_index",
            "role",
            name="uq_chat_message_turn_role",
        ),
        Index(
            "ix_chat_messages_session_revision_turn",
            "session_id",
            "context_revision",
            "turn_index",
        ),
        # Recall never scopes to the current clinical revision (see
        # ``load_memory``/``recent``/``conversation_turns``): those queries
        # filter on session_id and order by turn_index, which the
        # revision-scoped index above cannot serve.
        Index(
            "ix_chat_messages_session_turn",
            "session_id",
            "turn_index",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    turn_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("chat_turns.id", ondelete="SET NULL"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    client_message_id: Mapped[str | None] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    model: Mapped[str | None] = mapped_column(String(200))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    finish_reason: Mapped[str | None] = mapped_column(String(50))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    context_revision: Mapped[int] = mapped_column(Integer, default=1)
    turn_index: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RagSource(Base):
    __tablename__ = "rag_sources"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(400))
    source_type: Mapped[str] = mapped_column(String(40))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RagChunk(Base):
    __tablename__ = "rag_chunks"
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("rag_sources.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(400))
    text: Mapped[str] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    clean_text: Mapped[str | None] = mapped_column(Text)
    retrieval_text: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40))
    chunk_type: Mapped[str | None] = mapped_column(String(40))
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    analysis_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="SET NULL"), index=True
    )
    query_text: Mapped[str] = mapped_column(Text)
    resolved_context_json: Mapped[str | None] = mapped_column(Text)
    top_sources_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
