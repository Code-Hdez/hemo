from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

# Connections reserved for the synchronous HTTP endpoints (hemograms, pets,
# auth, ``db/queries``) that share this engine with the chat. It matches the
# historical QueuePool default, so those endpoints keep exactly the capacity
# they had before the chat's blocking executor existed.
_SYNC_ENDPOINT_CONNECTIONS = 5

_engine_options: dict[str, object] = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    _engine_options.update(
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # The chat offloads whole transactions to a bounded thread pool of up to
    # CHAT_DB_BLOCKING_MAX_CONCURRENCY workers, each holding its own
    # connection for the duration of the transaction. On the QueuePool
    # defaults (5 + 10) a saturated chat could consume the entire pool and
    # leave the synchronous hemogram endpoints waiting on pool checkout, so
    # size the steady-state pool for both populations instead. The overflow
    # absorbs bursts (retries, background sweeps) without becoming a second
    # permanent pool.
    _engine_options.update(
        pool_size=settings.CHAT_DB_BLOCKING_MAX_CONCURRENCY + _SYNC_ENDPOINT_CONNECTIONS,
        max_overflow=settings.CHAT_DB_BLOCKING_MAX_CONCURRENCY,
    )

engine = create_engine(settings.DATABASE_URL, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
