from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import retention
from app.db.base import Base
from app.modules.llm_chat.models import (
    ChatMessage,
    ChatSession,
    ChatTurn,
    ChatTurnAttempt,
    RetrievalEvent,
)
from app.modules.users.models import User

_NOW = datetime(2026, 8, 6, 12, 0, 0)


@pytest.fixture()
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            User(id="user-1", email="one@example.com", hashed_password="h", role="user")
        )
        session.commit()
    return factory


def _conversation(session: Session, conversation_id: str, expires_at: datetime) -> None:
    session.add(
        ChatSession(
            id=conversation_id,
            user_id="user-1",
            context_key="general",
            status="active",
            expires_at=expires_at,
            created_at=_NOW - timedelta(days=2),
            updated_at=_NOW - timedelta(days=2),
        )
    )


def _turn(
    session: Session,
    turn_id: str,
    conversation_id: str,
    status: str,
    turn_index: int = 1,
) -> None:
    session.add(
        ChatTurn(
            id=turn_id,
            session_id=conversation_id,
            client_message_id=f"client-{turn_id}",
            idempotency_key=f"idem-{turn_id}",
            request_fingerprint=f"fp-{turn_id}",
            turn_index=turn_index,
            status=status,
            attempt_count=3,
            created_at=_NOW - timedelta(days=90),
            updated_at=_NOW - timedelta(days=90),
        )
    )


def _attempt(
    session: Session,
    attempt_id: str,
    turn_id: str,
    *,
    number: int,
    status: str,
    created_at: datetime,
) -> None:
    session.add(
        ChatTurnAttempt(
            id=attempt_id,
            turn_id=turn_id,
            attempt_number=number,
            status=status,
            created_at=created_at,
        )
    )


def test_expired_conversation_is_closed_and_its_transcript_survives(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _conversation(session, "expired", _NOW - timedelta(minutes=1))
        _conversation(session, "alive", _NOW + timedelta(hours=1))
        session.add(
            ChatMessage(
                id="m1",
                session_id="expired",
                role="user",
                content="hola",
                turn_index=1,
                created_at=_NOW - timedelta(days=2),
            )
        )
        _turn(session, "t1", "expired", "completed")
        session.commit()

    with session_factory() as session:
        report = retention.run_retention(session, now=_NOW)

    assert report.closed_conversations == 1
    with session_factory() as session:
        assert session.get(ChatSession, "expired").status == "expired"
        assert session.get(ChatSession, "alive").status == "active"
        # The invariant this sweep must not break: closing does not cascade.
        assert session.get(ChatMessage, "m1") is not None
        assert session.get(ChatTurn, "t1") is not None


def test_conversation_without_ttl_is_never_closed(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        session.add(
            ChatSession(
                id="no-ttl",
                user_id="user-1",
                context_key="general",
                status="active",
                expires_at=None,
                created_at=_NOW,
                updated_at=_NOW,
            )
        )
        session.commit()

    with session_factory() as session:
        assert retention.run_retention(session, now=_NOW).closed_conversations == 0
    with session_factory() as session:
        assert session.get(ChatSession, "no-ttl").status == "active"


def test_purge_removes_old_finished_attempts_but_keeps_the_turn_and_the_live_one(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _conversation(session, "c1", _NOW + timedelta(hours=1))
        _turn(session, "t1", "c1", "completed")
        _turn(session, "t2", "c1", "processing", turn_index=2)
        _attempt(
            session, "a-old", "t1", number=1, status="failed",
            created_at=_NOW - timedelta(days=31),
        )
        _attempt(
            session, "a-recent", "t1", number=2, status="completed",
            created_at=_NOW - timedelta(days=29),
        )
        _attempt(
            session, "a-inflight", "t2", number=1, status="processing",
            created_at=_NOW - timedelta(days=40),
        )
        session.commit()

    with session_factory() as session:
        report = retention.run_retention(session, now=_NOW, attempt_retention_days=30)

    assert report.deleted_turn_attempts == 1
    with session_factory() as session:
        assert session.get(ChatTurnAttempt, "a-old") is None
        assert session.get(ChatTurnAttempt, "a-recent") is not None
        # ``_latest_attempt`` may still have to close this one.
        assert session.get(ChatTurnAttempt, "a-inflight") is not None
        assert session.get(ChatTurn, "t1").attempt_count == 3


def test_purge_deletes_old_retrieval_events(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _conversation(session, "c1", _NOW + timedelta(hours=1))
        for event_id, age_days in (("old", 91), ("recent", 89)):
            session.add(
                RetrievalEvent(
                    id=event_id,
                    session_id="c1",
                    user_id="user-1",
                    query_text="que significa el hematocrito bajo",
                    created_at=_NOW - timedelta(days=age_days),
                )
            )
        session.commit()

    with session_factory() as session:
        report = retention.run_retention(session, now=_NOW, retrieval_retention_days=90)

    assert report.deleted_retrieval_events == 1
    with session_factory() as session:
        assert session.get(RetrievalEvent, "old") is None
        assert session.get(RetrievalEvent, "recent") is not None


def test_batching_deletes_every_matching_row(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _conversation(session, "c1", _NOW + timedelta(hours=1))
        _turn(session, "t1", "c1", "completed")
        for number in range(1, 8):
            _attempt(
                session, f"a{number}", "t1", number=number, status="completed",
                created_at=_NOW - timedelta(days=60),
            )
        session.commit()

    with session_factory() as session:
        report = retention.run_retention(session, now=_NOW, batch_size=2)

    assert report.deleted_turn_attempts == 7
    with session_factory() as session:
        assert session.scalars(select(ChatTurnAttempt.id)).all() == []


def test_dry_run_counts_without_touching_anything(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        _conversation(session, "expired", _NOW - timedelta(minutes=1))
        _turn(session, "t1", "expired", "completed")
        _attempt(
            session, "a-old", "t1", number=1, status="failed",
            created_at=_NOW - timedelta(days=31),
        )
        session.add(
            RetrievalEvent(
                id="old",
                session_id="expired",
                user_id="user-1",
                query_text="hola",
                created_at=_NOW - timedelta(days=200),
            )
        )
        session.commit()

    with session_factory() as session:
        report = retention.run_retention(session, now=_NOW, dry_run=True)

    assert (
        report.closed_conversations,
        report.deleted_turn_attempts,
        report.deleted_retrieval_events,
    ) == (1, 1, 1)
    with session_factory() as session:
        assert session.get(ChatSession, "expired").status == "active"
        assert session.get(ChatTurnAttempt, "a-old") is not None
        assert session.get(RetrievalEvent, "old") is not None
