from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import inspect
import json
import math
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import asc, case, desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.modules.hematology.cbc_fields import (
    canonical_cbc_clinical_code,
    cbc_clinical_display_label,
)
from app.modules.hematology.models import Analysis, AnalysisParameter
from app.modules.llm_chat.application.dto import ChatResult
from app.modules.llm_chat.application.services.assistant_identity import (
    enforce_assistant_identity,
)
from app.modules.llm_chat.application.services.clinical_response import (
    project_public_case_facts,
)
from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    ConversationMemory,
    HemogramParameter,
    HemogramStudy,
    PatientContext,
    clinical_fact_id,
    normalize_clinical_unit,
)
from app.modules.llm_chat.domain.entities import (
    ChatMessageRecord,
    ChatTurnReservation,
    ChatTurnSnapshot,
    RetrievedChunk,
    TokenUsage,
)
from app.modules.llm_chat.domain.exceptions import (
    ChatIdempotencyConflict,
    ChatPersistenceError,
    ChatResourceNotFound,
    ChatTurnConcurrencyConflict,
)
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings
from app.modules.llm_chat.domain.value_objects import ResponseOrigin, SafetyAction, TurnStatus
from app.modules.llm_chat.models import (
    ChatMessage,
    ChatSession,
    ChatTurn,
    ChatTurnAttempt,
)
from app.modules.pets.models import Pet
from app.shared.dates import parse_iso_datetime, utc_now


class ConversationNotFound(ChatResourceNotFound):
    pass


class AnalysisContextNotFound(ChatResourceNotFound):
    pass


class NonBlockingSqlAlchemyRepository:
    """Offload complete synchronous SQLAlchemy adapter calls from the event loop.

    The existing persistence adapters expose async ports but intentionally own
    short, synchronous SQLAlchemy transactions. Running a transaction piecemeal
    in different threads would violate Session affinity, so this boundary runs
    the complete coroutine (including nested repository calls) in one worker
    event loop. The shared bounded executor supplies backpressure and keeps a
    cancelled HTTP request from releasing capacity while its transaction is
    still finishing.
    """

    def __init__(
        self,
        delegate: object,
        *,
        blocking_executor: BoundedBlockingExecutor,
    ) -> None:
        self._delegate = delegate
        self._blocking_executor = blocking_executor

    @property
    def delegate(self) -> object:
        return self._delegate

    def __getattr__(self, name: str) -> object:
        target = getattr(self._delegate, name)
        if not inspect.iscoroutinefunction(target):
            return target

        async def offloaded(*args: object, **kwargs: object) -> object:
            return await self._blocking_executor.run(
                _run_repository_coroutine,
                target,
                args,
                kwargs,
            )

        return offloaded


def _run_repository_coroutine(
    function: Callable[..., Awaitable[object]],
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> object:
    return asyncio.run(function(*args, **kwargs))


# Ceilings for the reads on the chat hot path. They are deliberately module
# constants and not settings: they are not a product knob but the point past
# which a query stops being bounded work per turn, and every one of them is
# above what the prompt or the conversation switcher can consume anyway.
#
# Automatic conversation resolution only needs to know whether exactly one
# active conversation matches the authorized scope; two rows already prove
# ambiguity, and this query holds a FOR UPDATE lock while it runs.
_CONVERSATION_RESOLUTION_CANDIDATES = 2
# The conversation switcher lists the most recently used conversations. An
# account that never deletes anything would otherwise pay for its whole
# history on every page load.
_ACTIVE_CONVERSATION_LIMIT = 50
# History mode compares recent studies. Loading a pet's entire archive plus
# every normalized parameter row of it, on each turn, is unbounded work for
# facts that cannot fit in the prompt.
_HISTORY_STUDY_LIMIT = 24

_STATUS_LABELS = {
    "normal": "normal",
    "low": "bajo",
    "high": "alto",
    "critical": "crítico",
    "info": "informativo",
    "warn": "requiere revisión",
    "danger": "marcado",
    "review": "requiere revisión",
}


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    cleaned = " ".join(str(value).replace("\x00", "").split())
    if not cleaned or cleaned.casefold() in {"none", "null", "nan", "undefined"}:
        return None
    return cleaned


def _finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _format_number(value: object) -> str | None:
    number = _finite_number(value)
    if number is None:
        return _clean_text(value)
    return f"{number:g}"


def _compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value not in (None, "", [])}


class SqlAlchemyConversationRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        chat_settings: GenerationProfileSettings,
    ) -> None:
        self.session_factory = session_factory
        self.chat_settings = chat_settings

    async def get_or_create(
        self,
        conversation_id: str | None,
        user_id: str,
        *,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
        context_scope: str = "general",
        pet_id: str | None = None,
        analysis_id: str | None = None,
        context_fingerprint: str | None = None,
        force_new: bool = False,
    ) -> str:
        now = utc_now()
        with self.session_factory() as session:
            # No global expiry sweep here anymore. ``expires_at`` is a soft
            # staleness signal that narrows automatic resolution/listing
            # below; it must never hard-delete a ``ChatSession`` row, because
            # that cascades (ondelete="CASCADE") to every ``ChatMessage``/
            # ``ChatTurn`` and permanently destroys the transcript this
            # method is supposed to be resuming (contexto_1/contexto_2: a
            # conversation "expiring after an hour" must not mean its
            # PostgreSQL transcript is gone).
            if conversation_id:
                row = self._locked_conversation(session, conversation_id)
                # Ownership is the authenticated user and the authorized
                # clinical scope (context_key, below) — never the browser/tab
                # session. A conversation_id is an explicit, authoritative
                # continuation request; it must not be rejected only because
                # the user is on a different device or tab than before.
                if row.user_id != user_id:
                    raise ConversationNotFound
                if row.auth_session_id is None and auth_session_id:
                    row.auth_session_id = auth_session_id
                if row.browser_session_hash is None and browser_session_hash:
                    row.browser_session_hash = browser_session_hash
                # A policy route may intentionally skip loading clinical data. In
                # that case the command can omit a pet/analysis reference that is
                # already part of the durable conversation identity. Treating an
                # omitted value as an explicit context change would rotate the
                # revision and reject the same request as stale immediately after.
                preserve_missing = row.last_mode == context_scope
                effective_pet_id = (
                    pet_id
                    if pet_id is not None or not preserve_missing
                    else row.active_pet_id
                )
                effective_analysis_id = (
                    analysis_id
                    if analysis_id is not None or not preserve_missing
                    else row.active_analysis_id
                )
                context_key = self._context_key(
                    context_scope,
                    effective_pet_id,
                    effective_analysis_id,
                )
                if row.context_key != context_key:
                    # A conversation is bound to one clinical authorization
                    # scope. Reusing its id for another pet/mode/analysis would
                    # make prior memory a cross-context data source.
                    raise ConversationNotFound
                if (
                    context_fingerprint
                    and row.context_fingerprint
                    and row.context_fingerprint != context_fingerprint
                ):
                    # Only the clinical context revision rotates here. The
                    # conversation itself (transcript, summary, active topic)
                    # is a distinct identity that a new hemogram/profile
                    # snapshot must not erase or hide. ``next_turn_index`` is
                    # deliberately left untouched too, so turn_index stays a
                    # single monotonic ordering key across every clinical
                    # revision of this conversation instead of colliding
                    # with an earlier revision's indices.
                    row.context_revision = int(row.context_revision or 1) + 1
                if context_fingerprint:
                    row.context_fingerprint = context_fingerprint
                row.active_pet_id = effective_pet_id
                row.active_analysis_id = effective_analysis_id
                row.last_mode = context_scope
                row.updated_at = now
                row.expires_at = now + timedelta(
                    seconds=self.chat_settings.memory.session_ttl_seconds
                )
                # An explicit continuation of an owned conversation is activity:
                # it must undo whatever closed it (the logout sweep in
                # ``auth/router``, the TTL sweep in ``db.retention``). Without
                # this, refreshing ``expires_at`` on a row left at
                # status='closed'/'expired' would revive the conversation for
                # the chat but keep it invisible in ``list_active`` forever,
                # which filters on status.
                row.status = "active"
                self._commit(session, "refresh_conversation")
                return row.id
            context_key = self._context_key(context_scope, pet_id, analysis_id)
            existing = None
            if not force_new:
                # Automatic resolution is scoped by the authenticated user and
                # the authorized clinical scope only — never by browser/tab
                # session (contexto_1/contexto_2, plan invariant). If more
                # than one active, non-expired conversation matches, do not
                # guess which one the caller means: fall through and start a
                # new conversation instead of silently attaching to the
                # wrong transcript.
                candidates = list(
                    session.scalars(
                        select(ChatSession)
                        .where(
                            ChatSession.user_id == user_id,
                            ChatSession.context_key == context_key,
                            ChatSession.status == "active",
                            (
                                ChatSession.expires_at.is_(None)
                                | (ChatSession.expires_at > now)
                            ),
                        )
                        .order_by(desc(ChatSession.updated_at))
                        .limit(_CONVERSATION_RESOLUTION_CANDIDATES)
                        .with_for_update()
                    )
                )
                existing = candidates[0] if len(candidates) == 1 else None
            if existing is not None:
                if (
                    context_fingerprint
                    and existing.context_fingerprint
                    and existing.context_fingerprint != context_fingerprint
                ):
                    existing.context_revision = int(existing.context_revision or 1) + 1
                if context_fingerprint:
                    existing.context_fingerprint = context_fingerprint
                if auth_session_id:
                    existing.auth_session_id = auth_session_id
                if browser_session_hash:
                    existing.browser_session_hash = browser_session_hash
                existing.updated_at = now
                existing.expires_at = now + timedelta(
                    seconds=self.chat_settings.memory.session_ttl_seconds
                )
                self._commit(session, "restore_context_conversation")
                return existing.id
            new_id = str(uuid4())
            session.add(
                ChatSession(
                    id=new_id,
                    user_id=user_id,
                    auth_session_id=auth_session_id,
                    browser_session_hash=browser_session_hash,
                    active_pet_id=pet_id,
                    active_analysis_id=analysis_id,
                    last_mode=context_scope,
                    context_key=context_key,
                    context_revision=1,
                    context_fingerprint=context_fingerprint,
                    next_turn_index=1,
                    status="active",
                    expires_at=now
                    + timedelta(seconds=self.chat_settings.memory.session_ttl_seconds),
                    created_at=now,
                    updated_at=now,
                )
            )
            self._commit(session, "create_conversation")
            return new_id

    async def context_revision(self, conversation_id: str) -> int:
        with self.session_factory() as session:
            row = session.get(ChatSession, conversation_id)
            if row is None:
                raise ConversationNotFound
            return int(row.context_revision or 1)

    async def load_memory(
        self,
        conversation_id: str,
        *,
        recent_limit: int = 16,
    ) -> ConversationMemory:
        with self.session_factory() as session:
            row = session.get(ChatSession, conversation_id)
            if row is None:
                raise ConversationNotFound
            revision = int(row.context_revision or 1)
            # Recall is intentionally NOT scoped to the current clinical
            # revision: a new hemogram/profile snapshot changes what is
            # factually authorized (revision bumps above), but it must not
            # hide the prior dialogue of the same authorized conversation.
            # turn_index is monotonic across revisions (see get_or_create),
            # so ordering stays correct once revisions are mixed back in.
            messages = list(
                session.scalars(
                    select(ChatMessage)
                    .where(
                        ChatMessage.session_id == conversation_id,
                        ChatMessage.status.in_(["completed", "refused"]),
                    )
                    .order_by(*self._message_order(descending=True))
                    .limit(recent_limit)
                )
            )
            try:
                state = json.loads(row.memory_state_json or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                state = {}
            return ConversationMemory(
                summary=row.memory_summary or "",
                state=state if isinstance(state, dict) else {},
                recent_messages=tuple(self._record(item) for item in reversed(messages)),
                context_revision=revision,
                conversation_revision=1,
            )

    async def begin_turn(self, message: ChatMessageRecord) -> bool:
        """Compatibility wrapper for callers scoped to an existing conversation."""
        reservation = self._reserve_turn(
            message,
            idempotency_key=self._digest(
                "legacy-conversation",
                message.conversation_id,
                message.client_message_id,
            ),
            request_fingerprint=self._digest(
                message.content,
                message.metadata.get("scope"),
                message.metadata.get("context_revision"),
            ),
            lease_seconds=(
                self.chat_settings.runtime.total_timeout_seconds
                + self.chat_settings.memory.turn_lease_grace_seconds
            ),
            discard_empty_conversation_on_redirect=False,
        )
        return reservation.acquired

    async def reserve_turn(
        self,
        message: ChatMessageRecord,
        *,
        user_id: str,
        auth_session_id: str | None,
        browser_session_hash: str | None = None,
        request_fingerprint: str,
        lease_seconds: float,
        discard_empty_conversation_on_redirect: bool = False,
    ) -> ChatTurnReservation:
        """Atomically reserve a globally idempotent turn for one auth scope."""
        owner_scope = (
            f"browser:{browser_session_hash}"
            if browser_session_hash
            else (auth_session_id or f"legacy:{user_id}")
        )
        return self._reserve_turn(
            message,
            idempotency_key=self._digest(
                user_id,
                owner_scope,
                message.client_message_id,
            ),
            request_fingerprint=request_fingerprint,
            lease_seconds=lease_seconds,
            discard_empty_conversation_on_redirect=discard_empty_conversation_on_redirect,
        )

    def _reserve_turn(
        self,
        message: ChatMessageRecord,
        *,
        idempotency_key: str,
        request_fingerprint: str,
        lease_seconds: float,
        discard_empty_conversation_on_redirect: bool,
    ) -> ChatTurnReservation:
        """Synchronous transaction behind both reservation entry points."""
        revision = int(message.metadata.get("context_revision") or 1)
        with self.session_factory() as session:
            conversation = self._locked_conversation(session, message.conversation_id)
            if int(conversation.context_revision or 1) != revision:
                raise ConversationNotFound
            turn = session.scalar(
                select(ChatTurn)
                .where(ChatTurn.idempotency_key == idempotency_key)
                .with_for_update()
            )
            now = utc_now()
            lease_expires_at = now + timedelta(seconds=max(1.0, float(lease_seconds)))
            retryable_states = {
                TurnStatus.FAILED.value,
                TurnStatus.INTERRUPTED.value,
                TurnStatus.INCOMPLETE.value,
            }
            if turn is not None:
                existing = session.scalar(
                    select(ChatMessage).where(
                        ChatMessage.turn_id == turn.id,
                        ChatMessage.role == "user",
                    )
                )
                if (
                    turn.request_fingerprint != request_fingerprint
                    or existing is None
                    or existing.content != message.content
                ):
                    raise ChatIdempotencyConflict(
                        conversation_id=turn.session_id,
                        attempt=int(turn.attempt_count or 1),
                    )
                stale_before = now - timedelta(
                    seconds=(
                        self.chat_settings.runtime.total_timeout_seconds
                        + self.chat_settings.memory.turn_lease_grace_seconds
                    )
                )
                lease_expired = bool(
                    turn.lease_expires_at is not None
                    and turn.lease_expires_at <= now
                ) or bool(
                    turn.lease_expires_at is None
                    and turn.started_at is not None
                    and turn.started_at <= stale_before
                )
                if (
                    turn.status in {
                        TurnStatus.PENDING.value,
                        TurnStatus.PROCESSING.value,
                    }
                    and lease_expired
                ):
                    self._finish_turn_attempt(
                        session,
                        turn,
                        status=TurnStatus.INTERRUPTED.value,
                        error_code="stale_processing_lease",
                    )
                if turn.status not in retryable_states:
                    self._discard_redirected_empty_conversation(
                        session,
                        incoming=conversation,
                        canonical_session_id=turn.session_id,
                        enabled=discard_empty_conversation_on_redirect,
                    )
                    self._commit(session, "read_existing_turn")
                    return self._reservation(turn, acquired=False)
                canonical = self._locked_conversation(session, turn.session_id)
                self._discard_redirected_empty_conversation(
                    session,
                    incoming=conversation,
                    canonical_session_id=turn.session_id,
                    enabled=discard_empty_conversation_on_redirect,
                )
                turn.attempt_count = int(turn.attempt_count or 0) + 1
                turn.status = TurnStatus.PROCESSING.value
                turn.processing_stage = "generating"
                turn.error_code = None
                turn.retryable = False
                turn.started_at = now
                turn.completed_at = None
                turn.lease_expires_at = lease_expires_at
                turn.updated_at = now
                existing.status = "pending"
                session.add(
                    ChatTurnAttempt(
                        id=str(uuid4()),
                        turn_id=turn.id,
                        attempt_number=turn.attempt_count,
                        status=TurnStatus.PROCESSING.value,
                        processing_stage="generating",
                        created_at=now,
                    )
                )
                canonical.updated_at = now
            else:
                existing = session.scalar(
                    select(ChatMessage).where(
                        ChatMessage.session_id == message.conversation_id,
                        ChatMessage.client_message_id == message.client_message_id,
                        ChatMessage.role == "user",
                    )
                )
                if existing is not None and existing.status not in retryable_states:
                    raise ChatIdempotencyConflict(conversation_id=message.conversation_id)
                turn_index = (
                    int(existing.turn_index)
                    if existing is not None
                    else self._allocate_turn_index(conversation)
                )
                turn = ChatTurn(
                    id=str(uuid4()),
                    session_id=message.conversation_id,
                    client_message_id=message.client_message_id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    context_revision=revision,
                    context_fingerprint=str(
                        message.metadata.get("context_fingerprint") or ""
                    )
                    or None,
                    turn_index=turn_index,
                    status=TurnStatus.PROCESSING.value,
                    processing_stage="generating",
                    attempt_count=1,
                    retryable=False,
                    user_message_id=(existing.id if existing is not None else message.id),
                    created_at=now,
                    updated_at=now,
                    started_at=now,
                    lease_expires_at=lease_expires_at,
                )
                session.add(turn)
                try:
                    # The turn row is flushed early to obtain its id, so a
                    # duplicate turn fails here and not at commit. Both write
                    # points resolve the race identically.
                    session.flush()
                except IntegrityError as exc:
                    return self._raced_turn_reservation(
                        session,
                        conversation_id=message.conversation_id,
                        client_message_id=message.client_message_id,
                        idempotency_key=idempotency_key,
                        request_fingerprint=request_fingerprint,
                        cause=exc,
                    )
                if existing is None:
                    existing = ChatMessage(
                        id=message.id,
                        session_id=message.conversation_id,
                        turn_id=turn.id,
                        client_message_id=message.client_message_id,
                        role="user",
                        content=message.content,
                        status="pending",
                        metadata_json=json.dumps(message.metadata, ensure_ascii=False),
                        context_revision=revision,
                        turn_index=turn_index,
                        created_at=now,
                    )
                    session.add(existing)
                else:
                    existing.turn_id = turn.id
                    existing.status = "pending"
                session.add(
                    ChatTurnAttempt(
                        id=str(uuid4()),
                        turn_id=turn.id,
                        attempt_number=1,
                        status=TurnStatus.PROCESSING.value,
                        processing_stage="generating",
                        created_at=now,
                    )
                )
            try:
                session.commit()
            except IntegrityError as exc:
                return self._raced_turn_reservation(
                    session,
                    conversation_id=message.conversation_id,
                    client_message_id=message.client_message_id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    cause=exc,
                )
            except SQLAlchemyError as exc:
                session.rollback()
                raise ChatPersistenceError("reserve_turn") from exc
        return self._reservation(turn, acquired=True)

    def _raced_turn_reservation(
        self,
        session: Session,
        *,
        conversation_id: str,
        client_message_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        cause: IntegrityError,
    ) -> ChatTurnReservation:
        """Report a lost unique-key race as a conflict, never as a 500.

        ``chat_turns`` carries three unique keys, and the one that rejected the
        insert is not necessarily the idempotency key. Two tabs of the same
        user send the same client_message_id under different browser scopes,
        so they derive *different* idempotency keys while
        ``uq_chat_turn_session_client`` still rejects the second insert.
        Searching only for our own key found nothing there and declared a
        persistence failure for what is an ordinary duplicate turn, so the
        second tab received a 500 instead of the 409 it can act on.
        """
        session.rollback()
        raced = session.scalar(
            select(ChatTurn).where(ChatTurn.idempotency_key == idempotency_key)
        ) or session.scalar(
            select(ChatTurn).where(
                ChatTurn.session_id == conversation_id,
                ChatTurn.client_message_id == client_message_id,
            )
        )
        if raced is None:
            raise ChatPersistenceError("reserve_turn_integrity") from cause
        if raced.request_fingerprint != request_fingerprint:
            raise ChatIdempotencyConflict(
                conversation_id=raced.session_id,
                attempt=int(raced.attempt_count or 1),
            )
        return self._reservation(raced, acquired=False)

    async def mark_turn_failed(
        self,
        conversation_id: str,
        client_message_id: str,
        *,
        error_code: str = "technical_error",
        expected_attempt: int | None = None,
    ) -> bool:
        with self.session_factory() as session:
            turn = session.scalar(
                select(ChatTurn)
                .where(
                    ChatTurn.session_id == conversation_id,
                    ChatTurn.client_message_id == client_message_id,
                )
                .with_for_update()
            )
            row = session.scalar(
                select(ChatMessage).where(
                    ChatMessage.session_id == conversation_id,
                    ChatMessage.client_message_id == client_message_id,
                    ChatMessage.role == "user",
                )
            )
            if (
                turn is not None
                and expected_attempt is not None
                and int(turn.attempt_count or 1) != int(expected_attempt)
            ):
                return False
            if turn is not None and turn.status not in {
                TurnStatus.COMPLETED.value,
                TurnStatus.REFUSED.value,
            }:
                self._finish_turn_attempt(
                    session,
                    turn,
                    status=TurnStatus.FAILED.value,
                    error_code=error_code,
                )
            if row is not None and row.status not in {"completed", "refused"}:
                row.status = TurnStatus.FAILED.value
            if turn is not None or row is not None:
                self._commit(session, "mark_turn_failed")
                return True
        return False

    async def mark_turn_stage(
        self,
        conversation_id: str,
        client_message_id: str,
        *,
        stage: str,
        expected_attempt: int | None = None,
    ) -> bool:
        allowed = {"pending", "generating", "validating", "repairing"}
        if stage not in allowed:
            raise ValueError("invalid_turn_stage")
        with self.session_factory() as session:
            turn = session.scalar(
                select(ChatTurn)
                .where(
                    ChatTurn.session_id == conversation_id,
                    ChatTurn.client_message_id == client_message_id,
                )
                .with_for_update()
            )
            if turn is None or turn.status not in {
                TurnStatus.PENDING.value,
                TurnStatus.PROCESSING.value,
            }:
                return False
            if (
                expected_attempt is not None
                and int(turn.attempt_count or 1) != int(expected_attempt)
            ):
                return False
            turn.processing_stage = stage
            turn.updated_at = utc_now()
            attempt = self._latest_attempt(session, turn.id)
            if attempt is not None:
                attempt.processing_stage = stage
            self._commit(session, "mark_turn_stage")
            return True

    async def mark_turn_incomplete(
        self,
        conversation_id: str,
        client_message_id: str,
        *,
        error_code: str = "incomplete_output",
        expected_attempt: int | None = None,
    ) -> bool:
        with self.session_factory() as session:
            turn = session.scalar(
                select(ChatTurn)
                .where(
                    ChatTurn.session_id == conversation_id,
                    ChatTurn.client_message_id == client_message_id,
                )
                .with_for_update()
            )
            if turn is None or turn.status in {
                TurnStatus.COMPLETED.value,
                TurnStatus.REFUSED.value,
            }:
                return False
            if (
                expected_attempt is not None
                and int(turn.attempt_count or 1) != int(expected_attempt)
            ):
                return False
            self._finish_turn_attempt(
                session,
                turn,
                status=TurnStatus.INCOMPLETE.value,
                error_code=error_code,
            )
            row = session.scalar(
                select(ChatMessage).where(
                    ChatMessage.session_id == conversation_id,
                    ChatMessage.client_message_id == client_message_id,
                    ChatMessage.role == "user",
                )
            )
            if row is not None:
                row.status = TurnStatus.INCOMPLETE.value
            self._commit(session, "mark_turn_incomplete")
            return True

    async def mark_owned_turn_failed(
        self,
        user_id: str,
        client_message_id: str,
        *,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
        error_code: str = "technical_error",
        conversation_id: str | None = None,
        expected_attempt: int | None = None,
    ) -> bool:
        """Clean up a pending reservation even when a total timeout cancels the use case."""
        with self.session_factory() as session:
            query = (
                select(ChatTurn)
                .join(ChatSession, ChatTurn.session_id == ChatSession.id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatTurn.client_message_id == client_message_id,
                    ChatTurn.status.in_(["pending", "processing"]),
                )
                .with_for_update()
            )
            if auth_session_id:
                query = query.where(ChatSession.auth_session_id == auth_session_id)
            if browser_session_hash:
                query = query.where(
                    ChatSession.browser_session_hash == browser_session_hash
                )
            else:
                query = query.where(ChatSession.browser_session_hash.is_(None))
            if conversation_id:
                query = query.where(ChatTurn.session_id == conversation_id)
            turn = session.scalar(query)
            if turn is None:
                return False
            if (
                expected_attempt is not None
                and int(turn.attempt_count or 1) != int(expected_attempt)
            ):
                return False
            self._finish_turn_attempt(
                session,
                turn,
                status=TurnStatus.FAILED.value,
                error_code=error_code,
            )
            row = session.scalar(
                select(ChatMessage).where(
                    ChatMessage.turn_id == turn.id,
                    ChatMessage.role == "user",
                )
            )
            if row is not None:
                row.status = TurnStatus.FAILED.value
            self._commit(session, "mark_owned_turn_failed")
            return True

    async def mark_owned_turn_interrupted(
        self,
        user_id: str,
        client_message_id: str,
        *,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
        conversation_id: str | None = None,
        expected_attempt: int | None = None,
        error_code: str = "client_disconnected",
    ) -> bool:
        """Record client disconnects distinctly while keeping the turn retryable."""
        with self.session_factory() as session:
            query = (
                select(ChatTurn)
                .join(ChatSession, ChatTurn.session_id == ChatSession.id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatTurn.client_message_id == client_message_id,
                    ChatTurn.status.in_(["pending", "processing", "interrupted"]),
                )
                .with_for_update()
            )
            if auth_session_id:
                query = query.where(ChatSession.auth_session_id == auth_session_id)
            if browser_session_hash:
                query = query.where(
                    ChatSession.browser_session_hash == browser_session_hash
                )
            else:
                query = query.where(ChatSession.browser_session_hash.is_(None))
            if conversation_id:
                query = query.where(ChatTurn.session_id == conversation_id)
            turn = session.scalar(query)
            if turn is None:
                return False
            if (
                expected_attempt is not None
                and int(turn.attempt_count or 1) != int(expected_attempt)
            ):
                return False
            if turn.status == TurnStatus.INTERRUPTED.value:
                if error_code == "client_cancelled" and turn.error_code != error_code:
                    turn.error_code = error_code
                    attempt = self._latest_attempt(session, turn.id)
                    if attempt is not None:
                        attempt.error_code = error_code
                        attempt.validation_reason = error_code
                    self._commit(session, "update_cancel_reason")
                return True
            self._finish_turn_attempt(
                session,
                turn,
                status=TurnStatus.INTERRUPTED.value,
                error_code=error_code,
            )
            row = session.scalar(
                select(ChatMessage).where(
                    ChatMessage.turn_id == turn.id,
                    ChatMessage.role == "user",
                )
            )
            if row is not None:
                row.status = TurnStatus.INTERRUPTED.value
            self._commit(session, "mark_owned_turn_interrupted")
            return True

    async def complete_turn(
        self,
        message: ChatMessageRecord,
        *,
        memory_summary: str,
        memory_state: dict[str, Any],
    ) -> None:
        payload = dict(message.metadata)
        payload["sources"] = [self._source_dict(source) for source in message.sources]
        revision = int(payload.get("context_revision") or 1)
        expected_attempt = max(1, int(payload.get("attempt") or 1))
        with self.session_factory() as session:
            try:
                conversation = self._locked_conversation(
                    session,
                    message.conversation_id,
                )
            except ConversationNotFound as exc:
                session.rollback()
                raise ChatTurnConcurrencyConflict(
                    conversation_id=message.conversation_id,
                    attempt=expected_attempt,
                    reason="conversation_missing_during_completion",
                ) from exc
            if int(conversation.context_revision or 1) != revision:
                session.rollback()
                raise ChatTurnConcurrencyConflict(
                    conversation_id=message.conversation_id,
                    attempt=expected_attempt,
                    reason="context_revision_changed",
                )
            user_row = session.scalar(
                select(ChatMessage).where(
                    ChatMessage.session_id == message.conversation_id,
                    ChatMessage.client_message_id == message.client_message_id,
                    ChatMessage.role == "user",
                    ChatMessage.context_revision == revision,
                )
            )
            if user_row is None:
                session.rollback()
                raise ChatTurnConcurrencyConflict(
                    conversation_id=message.conversation_id,
                    attempt=expected_attempt,
                    reason="user_message_missing_during_completion",
                )
            turn = session.scalar(
                select(ChatTurn)
                .where(
                    ChatTurn.session_id == message.conversation_id,
                    ChatTurn.client_message_id == message.client_message_id,
                    ChatTurn.context_revision == revision,
                )
                .with_for_update()
            )
            if turn is None:
                session.rollback()
                raise ChatTurnConcurrencyConflict(
                    conversation_id=message.conversation_id,
                    attempt=expected_attempt,
                    reason="turn_missing_during_completion",
                )
            if expected_attempt != int(turn.attempt_count or 1):
                # A timed-out provider call may finish after a newer retry has
                # acquired the turn. Never let that stale execution overwrite
                # the canonical state or the newer attempt's memory.
                session.rollback()
                raise ChatTurnConcurrencyConflict(
                    conversation_id=message.conversation_id,
                    attempt=expected_attempt,
                    reason="attempt_changed",
                )
            if turn.status in {
                TurnStatus.COMPLETED.value,
                TurnStatus.REFUSED.value,
            }:
                session.rollback()
                raise ChatTurnConcurrencyConflict(
                    conversation_id=message.conversation_id,
                    attempt=expected_attempt,
                    reason="turn_already_terminal",
                )
            if turn.status not in {
                TurnStatus.PENDING.value,
                TurnStatus.PROCESSING.value,
            }:
                session.rollback()
                raise ChatTurnConcurrencyConflict(
                    conversation_id=message.conversation_id,
                    attempt=expected_attempt,
                    reason="turn_state_changed",
                )
            if message.status not in {
                TurnStatus.COMPLETED.value,
                TurnStatus.REFUSED.value,
            }:
                failure_status = (
                    message.status
                    if message.status
                    in {
                        TurnStatus.FAILED.value,
                        TurnStatus.INTERRUPTED.value,
                        TurnStatus.INCOMPLETE.value,
                    }
                    else TurnStatus.FAILED.value
                )
                self._finish_turn_attempt(
                    session,
                    turn,
                    status=failure_status,
                    error_code=message.finish_reason or failure_status,
                )
                user_row.status = failure_status
                self._commit(session, "complete_failed_turn")
                return
            session.add(
                ChatMessage(
                    id=message.id,
                    session_id=message.conversation_id,
                    turn_id=turn.id,
                    client_message_id=message.client_message_id,
                    role="assistant",
                    content=message.content,
                    status=message.status,
                    model=message.model,
                    prompt_tokens=message.usage.prompt_tokens,
                    completion_tokens=message.usage.completion_tokens,
                    duration_ms=message.duration_ms,
                    finish_reason=message.finish_reason,
                    metadata_json=json.dumps(payload, ensure_ascii=False),
                    context_revision=revision,
                    turn_index=user_row.turn_index,
                    created_at=utc_now(),
                )
            )
            user_row.status = "completed"
            now = utc_now()
            turn.status = message.status
            turn.processing_stage = "completed"
            turn.retryable = False
            turn.error_code = None
            turn.assistant_message_id = message.id
            turn.updated_at = now
            turn.completed_at = now
            turn.lease_expires_at = None
            attempt = self._latest_attempt(session, turn.id)
            if attempt is not None:
                attempt.status = message.status
                attempt.processing_stage = "completed"
                attempt.error_code = None
                attempt.response_origin = str(
                    payload.get("response_origin")
                    or (
                        ResponseOrigin.LLM.value
                        if message.model
                        else ResponseOrigin.SAFETY_FALLBACK.value
                    )
                )
                attempt.provider = str(payload.get("provider") or "") or None
                attempt.model = message.model
                attempt.prompt_tokens = message.usage.prompt_tokens
                attempt.completion_tokens = message.usage.completion_tokens
                attempt.duration_ms = message.duration_ms
                attempt.finish_reason = message.finish_reason
                attempt.validation_reason = str(
                    payload.get("validation_reason") or ""
                ) or None
                attempt.completed_at = now
            conversation.memory_summary = memory_summary or None
            conversation.memory_state_json = json.dumps(memory_state, ensure_ascii=False)
            conversation.updated_at = utc_now()
            self._commit(session, "complete_turn")

    async def append(self, message: ChatMessageRecord) -> None:
        payload = dict(message.metadata)
        payload["sources"] = [self._source_dict(source) for source in message.sources]
        with self.session_factory() as session:
            conversation = self._locked_conversation(session, message.conversation_id)
            revision = int(
                message.metadata.get("context_revision")
                or conversation.context_revision
                or 1
            )
            if int(conversation.context_revision or 1) != revision:
                raise ConversationNotFound
            sibling = session.scalar(
                select(ChatMessage).where(
                    ChatMessage.session_id == message.conversation_id,
                    ChatMessage.client_message_id == message.client_message_id,
                    ChatMessage.context_revision == revision,
                )
            )
            turn_index = (
                int(sibling.turn_index)
                if sibling is not None
                else self._allocate_turn_index(conversation)
            )
            session.add(
                ChatMessage(
                    id=message.id,
                    session_id=message.conversation_id,
                    client_message_id=message.client_message_id,
                    role=message.role,
                    content=message.content,
                    status=message.status,
                    model=message.model,
                    prompt_tokens=message.usage.prompt_tokens,
                    completion_tokens=message.usage.completion_tokens,
                    duration_ms=message.duration_ms,
                    finish_reason=message.finish_reason,
                    metadata_json=json.dumps(payload, ensure_ascii=False),
                    context_revision=revision,
                    turn_index=turn_index,
                    created_at=utc_now(),
                )
            )
            self._commit(session, "append_message")

    async def recent(
        self, conversation_id: str, limit: int
    ) -> list[ChatMessageRecord]:
        with self.session_factory() as session:
            conversation = session.get(ChatSession, conversation_id)
            if conversation is None:
                raise ConversationNotFound
            # Not scoped to the current clinical revision — see load_memory.
            # Only completed/refused turns: a message that never passed
            # validation or was never confirmed must not enter memory as if
            # it were part of the real dialogue.
            rows = list(
                session.scalars(
                    select(ChatMessage)
                    .where(
                        ChatMessage.session_id == conversation_id,
                        ChatMessage.status.in_(["completed", "refused"]),
                    )
                    .order_by(*self._message_order(descending=True))
                    .limit(limit)
                )
            )
        return [self._record(row) for row in reversed(rows)]

    async def history(
        self,
        conversation_id: str,
        user_id: str,
        *,
        limit: int,
        offset: int,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
    ) -> list[ChatMessageRecord]:
        with self.session_factory() as session:
            conversation = session.get(ChatSession, conversation_id)
            # Ownership is the authenticated user, not the browser/tab
            # session (see get_or_create).
            if conversation is None or conversation.user_id != user_id:
                raise ConversationNotFound
            # Not scoped to the current clinical revision — the full
            # transcript of this authorized conversation remains retrievable
            # regardless of how many times its clinical data changed.
            rows = list(
                session.scalars(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == conversation_id)
                    .order_by(*self._message_order())
                    .offset(offset)
                    .limit(limit)
                )
            )
        return [self._record(row) for row in rows]

    async def conversation_turns(
        self,
        conversation_id: str,
        *,
        context_revision: int | None = None,
        roles: tuple[str, ...] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ChatMessageRecord]:
        """Return the persisted transcript for this conversation.

        Not scoped to the current clinical context revision by default: the
        dialogue survives a hemogram/profile change (see ``get_or_create``).
        Pass an explicit ``context_revision`` to narrow to messages created
        under that one clinical revision specifically.

        This is the source of truth for questions about the conversation itself;
        callers do not need to infer prior questions from a lossy prompt summary.
        Ownership is established by ``get_or_create`` before this method is used.
        """
        with self.session_factory() as session:
            conversation = session.get(ChatSession, conversation_id)
            if conversation is None:
                raise ConversationNotFound
            query = (
                select(ChatMessage)
                .where(
                    ChatMessage.session_id == conversation_id,
                    ChatMessage.status.in_(["completed", "refused"]),
                )
                .order_by(*self._message_order())
                .offset(max(0, int(offset)))
            )
            if context_revision is not None:
                query = query.where(
                    ChatMessage.context_revision == int(context_revision)
                )
            if roles:
                query = query.where(ChatMessage.role.in_(roles))
            if limit is not None:
                query = query.limit(max(0, int(limit)))
            rows = list(session.scalars(query))
        return [self._record(row) for row in rows]

    async def turn_history(
        self,
        conversation_id: str,
        user_id: str,
        *,
        limit: int,
        offset: int,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return canonical turns and transcript rows in one authorized query.

        Not scoped to the current clinical revision — see ``conversation_turns``.
        Ownership is the authenticated user, not the browser/tab session.
        """
        with self.session_factory() as session:
            conversation = session.get(ChatSession, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise ConversationNotFound
            turns = list(
                session.scalars(
                    select(ChatTurn)
                    .where(ChatTurn.session_id == conversation_id)
                    .order_by(asc(ChatTurn.turn_index), asc(ChatTurn.created_at))
                    .offset(max(0, int(offset)))
                    .limit(max(1, int(limit)))
                )
            )
            turn_ids = [turn.id for turn in turns]
            messages = (
                list(
                    session.scalars(
                        select(ChatMessage)
                        .where(ChatMessage.turn_id.in_(turn_ids))
                        .order_by(*self._message_order())
                    )
                )
                if turn_ids
                else []
            )
            by_turn: dict[str, dict[str, ChatMessage]] = {}
            for message in messages:
                if message.turn_id:
                    by_turn.setdefault(message.turn_id, {})[message.role] = message

            result: list[dict[str, Any]] = []
            for turn in turns:
                rows = by_turn.get(turn.id, {})
                user_message = rows.get("user")
                if user_message is None:
                    continue
                assistant = rows.get("assistant")
                result.append(
                    {
                        "turn_id": turn.id,
                        "conversation_id": conversation_id,
                        "client_message_id": turn.client_message_id,
                        "context_revision": int(turn.context_revision or 1),
                        "turn_index": int(turn.turn_index),
                        "status": turn.status,
                        "attempt": int(turn.attempt_count or 1),
                        "retryable": bool(turn.retryable),
                        "processing_stage": turn.processing_stage,
                        "error_code": turn.error_code,
                        "user_message": self._record(user_message),
                        "response": (
                            self._chat_result(assistant)
                            if assistant is not None
                            and assistant.status in {
                                TurnStatus.COMPLETED.value,
                                TurnStatus.REFUSED.value,
                            }
                            else None
                        ),
                        "updated_at": turn.updated_at,
                    }
                )
            return result

    async def first_user_message(
        self,
        conversation_id: str,
        *,
        context_revision: int | None = None,
    ) -> ChatMessageRecord | None:
        rows = await self.conversation_turns(
            conversation_id,
            context_revision=context_revision,
            roles=("user",),
            limit=1,
        )
        return rows[0] if rows else None

    async def user_questions(
        self,
        conversation_id: str,
        *,
        context_revision: int | None = None,
        limit: int | None = None,
    ) -> list[ChatMessageRecord]:
        return await self.conversation_turns(
            conversation_id,
            context_revision=context_revision,
            roles=("user",),
            limit=limit,
        )

    async def list_active(
        self,
        user_id: str,
        auth_session_id: str | None,
        browser_session_hash: str | None = None,
    ) -> list[dict[str, Any]]:
        # Ownership is the authenticated user, not the browser/tab session —
        # a user must see every one of their active conversations regardless
        # of which device/tab they are currently using (see get_or_create).
        now = utc_now()
        with self.session_factory() as session:
            query = select(ChatSession).where(
                ChatSession.user_id == user_id,
                ChatSession.status == "active",
                (ChatSession.expires_at.is_(None) | (ChatSession.expires_at > now)),
            )
            rows = list(
                session.scalars(
                    query.order_by(desc(ChatSession.updated_at)).limit(
                        _ACTIVE_CONVERSATION_LIMIT
                    )
                )
            )
        return [self._session_payload(row) for row in rows]

    async def delete_owned(
        self,
        conversation_id: str,
        user_id: str,
        auth_session_id: str | None,
        browser_session_hash: str | None = None,
    ) -> None:
        # Ownership is the authenticated user, not the browser/tab session
        # (see get_or_create).
        with self.session_factory() as session:
            row = session.get(ChatSession, conversation_id)
            if row is None or row.user_id != user_id:
                raise ConversationNotFound
            session.delete(row)
            self._commit(session, "delete_conversation")

    async def get_completed_response(
        self, conversation_id: str, client_message_id: str
    ) -> ChatResult | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(ChatMessage).where(
                    ChatMessage.session_id == conversation_id,
                    ChatMessage.client_message_id == client_message_id,
                    ChatMessage.role == "assistant",
                    ChatMessage.status.in_(["completed", "refused"]),
                )
            )
        if row is None:
            return None
        return self._chat_result(row)

    def _chat_result(self, row: ChatMessage) -> ChatResult:
        metadata = json.loads(row.metadata_json or "{}")
        route_trace = dict(metadata.get("route_trace") or {})
        sources = [self._source(value) for value in metadata.get("sources", [])]
        return ChatResult(
            conversation_id=row.session_id,
            turn_id=row.turn_id,
            message_id=row.id,
            answer=enforce_assistant_identity(row.content),
            scope=str(metadata.get("scope") or "general"),
            case_facts=project_public_case_facts(metadata.get("case_facts")),
            sources=sources,
            warnings=[
                str(value)
                for value in metadata.get("warnings", [])
                if isinstance(value, str) and value.strip()
            ],
            safety_action=SafetyAction(
                metadata.get("safety_action") or SafetyAction.ALLOW.value
            ),
            model=row.model,
            usage=TokenUsage(row.prompt_tokens, row.completion_tokens),
            duration_ms=row.duration_ms or 0,
            finish_reason=row.finish_reason or "stop",
            llm_invoked=bool(
                metadata.get("llm_invoked")
                if "llm_invoked" in metadata
                else route_trace.get("llm_invoked") or row.model
            ),
            response_origin=str(
                metadata.get("response_origin")
                or ("llm" if row.model else "legacy_deterministic")
            ),
            attempt=max(1, int(metadata.get("attempt") or 1)),
            generation_attempts=max(
                0,
                int(metadata.get("generation_attempts") or (1 if row.model else 0)),
            ),
            stream_mode=str(metadata.get("stream_mode") or "buffered_validated"),
            validation_status=str(metadata.get("validation_status") or "passed"),
            route_trace=route_trace,
            context=dict(metadata.get("context") or {}),
        )

    async def turn_status(
        self,
        conversation_id: str,
        client_message_id: str,
        user_id: str,
        *,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
    ) -> ChatTurnSnapshot:
        with self.session_factory() as session:
            query = (
                select(ChatTurn)
                .join(ChatSession, ChatTurn.session_id == ChatSession.id)
                .where(
                    ChatTurn.session_id == conversation_id,
                    ChatTurn.client_message_id == client_message_id,
                    ChatSession.user_id == user_id,
                )
            )
            if auth_session_id:
                query = query.where(
                    (ChatSession.auth_session_id.is_(None))
                    | (ChatSession.auth_session_id == auth_session_id)
                )
            if browser_session_hash:
                query = query.where(
                    ChatSession.browser_session_hash == browser_session_hash
                )
            else:
                query = query.where(ChatSession.browser_session_hash.is_(None))
            turn = session.scalar(query)
        if turn is None:
            raise ConversationNotFound
        response = None
        if turn.status in {
            TurnStatus.COMPLETED.value,
            TurnStatus.REFUSED.value,
        }:
            response = await self.get_completed_response(
                conversation_id,
                client_message_id,
            )
        return ChatTurnSnapshot(
            conversation_id=conversation_id,
            client_message_id=client_message_id,
            status=turn.status,
            attempt=int(turn.attempt_count or 1),
            retryable=bool(turn.retryable),
            error_code=turn.error_code,
            response=response,
            turn_id=turn.id,
            processing_stage=turn.processing_stage,
            context_revision=max(1, int(turn.context_revision or 1)),
        )

    async def current_attempt(
        self,
        conversation_id: str,
        client_message_id: str,
    ) -> int:
        with self.session_factory() as session:
            value = session.scalar(
                select(ChatTurn.attempt_count).where(
                    ChatTurn.session_id == conversation_id,
                    ChatTurn.client_message_id == client_message_id,
                )
            )
        return max(1, int(value or 1))

    @staticmethod
    def _latest_attempt(session: Session, turn_id: str) -> ChatTurnAttempt | None:
        return session.scalar(
            select(ChatTurnAttempt)
            .where(ChatTurnAttempt.turn_id == turn_id)
            .order_by(desc(ChatTurnAttempt.attempt_number))
            .limit(1)
        )

    @classmethod
    def _finish_turn_attempt(
        cls,
        session: Session,
        turn: ChatTurn,
        *,
        status: str,
        error_code: str | None,
    ) -> None:
        now = utc_now()
        turn.status = status
        turn.processing_stage = cls._public_processing_stage(
            status,
            retryable=status in {
                TurnStatus.FAILED.value,
                TurnStatus.INTERRUPTED.value,
                TurnStatus.INCOMPLETE.value,
            },
            error_code=error_code,
        )
        turn.error_code = error_code
        turn.retryable = status in {
            TurnStatus.FAILED.value,
            TurnStatus.INTERRUPTED.value,
            TurnStatus.INCOMPLETE.value,
        }
        turn.updated_at = now
        turn.completed_at = now
        turn.lease_expires_at = None
        attempt = cls._latest_attempt(session, turn.id)
        if attempt is not None and attempt.status in {
            TurnStatus.PENDING.value,
            TurnStatus.PROCESSING.value,
        }:
            attempt.status = status
            attempt.processing_stage = turn.processing_stage
            attempt.error_code = error_code
            attempt.validation_reason = error_code
            attempt.completed_at = now

    @staticmethod
    def _public_processing_stage(
        status: str,
        *,
        retryable: bool,
        error_code: str | None,
    ) -> str:
        if status in {TurnStatus.COMPLETED.value, TurnStatus.REFUSED.value}:
            return "completed"
        if status == TurnStatus.INTERRUPTED.value:
            return "cancelled" if error_code == "client_cancelled" else "expired"
        if status == TurnStatus.INCOMPLETE.value or retryable:
            return "failed_retryable"
        if status == TurnStatus.FAILED.value:
            return "failed_terminal"
        if status == TurnStatus.PROCESSING.value:
            return "generating"
        return "pending"

    @staticmethod
    def _source_dict(source: RetrievedChunk) -> dict[str, Any]:
        return {
            "id": source.id,
            "source_id": source.source_id,
            "title": source.title,
            "heading_path": source.heading_path,
            "source_path": source.source_path,
            "score": source.score,
            "authors": list(source.authors),
            "edition": source.edition,
            "chapter": source.chapter,
            "section": source.section,
            "page_start": source.page_start,
            "page_end": source.page_end,
            "source_type": source.source_type,
            "generation_use_allowed": source.generation_use_allowed,
            "citation_allowed": source.citation_allowed,
            "source_language": source.source_language,
        }

    @staticmethod
    def _source(value: dict[str, Any]) -> RetrievedChunk:
        payload = dict(value)
        payload["authors"] = tuple(payload.get("authors") or ())
        return RetrievedChunk(text="", **payload)

    def _record(self, row: ChatMessage) -> ChatMessageRecord:
        metadata = json.loads(row.metadata_json or "{}")
        return ChatMessageRecord(
            id=row.id,
            conversation_id=row.session_id,
            client_message_id=row.client_message_id or row.id,
            role=row.role,
            content=row.content,
            status=row.status,
            model=row.model,
            usage=TokenUsage(row.prompt_tokens, row.completion_tokens),
            duration_ms=row.duration_ms,
            finish_reason=row.finish_reason,
            sources=[self._source(value) for value in metadata.get("sources", [])],
            metadata=metadata,
            created_at=row.created_at,
            turn_index=row.turn_index,
        )

    @staticmethod
    def _locked_conversation(session: Session, conversation_id: str) -> ChatSession:
        row = session.scalar(
            select(ChatSession)
            .where(ChatSession.id == conversation_id)
            .with_for_update()
        )
        if row is None:
            raise ConversationNotFound
        return row

    @staticmethod
    def _allocate_turn_index(conversation: ChatSession) -> int:
        turn_index = max(1, int(conversation.next_turn_index or 1))
        conversation.next_turn_index = turn_index + 1
        return turn_index

    @staticmethod
    def _digest(*values: object) -> str:
        canonical = "\x1f".join(str(value or "") for value in values)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _commit(session: Session, operation: str) -> None:
        try:
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise ChatPersistenceError(operation) from exc

    @staticmethod
    def _reservation(
        turn: ChatTurn,
        *,
        acquired: bool,
    ) -> ChatTurnReservation:
        return ChatTurnReservation(
            conversation_id=turn.session_id,
            client_message_id=turn.client_message_id,
            status=turn.status,
            attempt=max(1, int(turn.attempt_count or 1)),
            acquired=acquired,
            retryable=bool(turn.retryable),
            context_revision=max(1, int(turn.context_revision or 1)),
            error_code=turn.error_code,
            turn_id=turn.id,
            processing_stage=turn.processing_stage,
            context_fingerprint=turn.context_fingerprint,
        )

    @staticmethod
    def _discard_redirected_empty_conversation(
        session: Session,
        *,
        incoming: ChatSession,
        canonical_session_id: str,
        enabled: bool,
    ) -> None:
        if not enabled or incoming.id == canonical_session_id:
            return
        has_turn = session.scalar(
            select(ChatTurn.id).where(ChatTurn.session_id == incoming.id).limit(1)
        )
        has_message = session.scalar(
            select(ChatMessage.id).where(ChatMessage.session_id == incoming.id).limit(1)
        )
        if has_turn is None and has_message is None:
            session.delete(incoming)

    @staticmethod
    def _message_order(*, descending: bool = False) -> tuple[Any, ...]:
        role_order = case(
            (ChatMessage.role == "user", 0),
            (ChatMessage.role == "assistant", 1),
            else_=2,
        )
        direction = desc if descending else asc
        return (
            direction(ChatMessage.turn_index),
            direction(role_order),
            direction(ChatMessage.created_at),
            direction(ChatMessage.id),
        )

    @staticmethod
    def _context_key(
        context_scope: str,
        pet_id: str | None,
        analysis_id: str | None,
    ) -> str:
        if context_scope == "selected_hemogram":
            return f"pet:{pet_id or 'unknown'}:analysis:{analysis_id or 'unknown'}"
        if context_scope == "hemogram_history":
            return f"pet:{pet_id or 'unknown'}:history"
        # General mode may now optionally authorize a pet profile (etapa 2).
        # Without the pet in the key, "general chat about Fido" and "general
        # chat about Rex" would share one context_key and could mix one pet's
        # profile/memory into the other's conversation.
        return f"general:pet:{pet_id}" if pet_id else "general"

    @staticmethod
    def _session_payload(row: ChatSession) -> dict[str, Any]:
        return {
            "id": row.id,
            "mode": row.last_mode,
            "pet_id": row.active_pet_id,
            "analysis_id": row.active_analysis_id,
            "context_revision": int(row.context_revision or 1),
            "context_key": row.context_key,
            "context_fingerprint": row.context_fingerprint,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "expires_at": row.expires_at,
        }


class SqlAlchemyAnalysisContextRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    async def get_owned_context(
        self,
        *,
        context_scope: str,
        user_id: str,
        analysis_id: str | None = None,
        pet_id: str | None = None,
    ) -> ClinicalContext:
        if context_scope == "general":
            if not pet_id:
                return ClinicalContext(mode="general")
            return await self._general_context(pet_id, user_id)
        if context_scope == "selected_hemogram":
            if not analysis_id:
                raise AnalysisContextNotFound
            return await self._selected_context(analysis_id, user_id)
        if context_scope == "hemogram_history":
            resolved_pet_id = pet_id
            if not resolved_pet_id and analysis_id:
                resolved_pet_id = await self._owned_pet_id_for_analysis(
                    analysis_id, user_id
                )
            if not resolved_pet_id:
                raise AnalysisContextNotFound
            return await self._history_context(resolved_pet_id, user_id)
        raise AnalysisContextNotFound

    async def get_owned_snapshot(self, analysis_id: str, user_id: str) -> dict[str, Any]:
        """Compatibility adapter for older callers."""
        context = await self._selected_context(analysis_id, user_id)
        return {
            "analysis_id": analysis_id,
            "pet_id": context.pet_id,
            "facts": context.legacy_facts(),
            "clinical_context": context,
        }

    async def get_owned_history(self, pet_id: str, user_id: str) -> dict[str, Any]:
        context = await self._history_context(pet_id, user_id)
        return {
            "pet_id": pet_id,
            "facts": context.legacy_facts(),
            "clinical_context": context,
        }

    async def _selected_context(
        self, analysis_id: str, user_id: str
    ) -> ClinicalContext:
        with self.session_factory() as session:
            result = session.execute(
                select(Analysis, Pet)
                .join(Pet, Analysis.pet_id == Pet.id)
                .where(
                    Analysis.id == analysis_id,
                    Analysis.user_id == user_id,
                    Pet.owner_id == user_id,
                )
            ).first()
            if result is None:
                raise AnalysisContextNotFound
            selected_row, pet = result
            rows = [selected_row]
            parameter_rows = list(
                session.scalars(
                    select(AnalysisParameter)
                    .where(AnalysisParameter.analysis_id == selected_row.id)
                    .order_by(asc(AnalysisParameter.ordinal))
                )
            )
        if selected_row.pet_id != pet.id:
            raise AnalysisContextNotFound
        studies = self._build_studies(rows, parameter_rows)
        study = next(
            (item for item in studies if item.analysis_id == selected_row.id),
            None,
        )
        if study is None:
            raise AnalysisContextNotFound
        return ClinicalContext(
            mode="selected_hemogram",
            patient=self._patient(pet),
            selected=study,
            # Selected mode authorizes exactly one analysis. Longitudinal
            # comparisons require the explicit history scope.
            history=(study,),
            computed_facts=tuple(
                [self._selected_study_fact(studies, study)]
            ),
            warnings=self._context_warnings(studies),
        )

    async def _general_context(self, pet_id: str, user_id: str) -> ClinicalContext:
        """Load only the authorized pet profile for general-mode chat.

        General mode never authorizes hemograms: unlike ``_history_context``,
        this deliberately does not query ``Analysis`` at all, even though the
        pet may have studies. A user in general scope asked about their pet,
        not a hemogram; loading analyses here would silently widen the
        authorized scope past what the API contract for this mode allows.
        """
        with self.session_factory() as session:
            pet = session.scalar(
                select(Pet).where(Pet.id == pet_id, Pet.owner_id == user_id)
            )
        if pet is None:
            raise AnalysisContextNotFound
        return ClinicalContext(mode="general", patient=self._patient(pet))

    async def _history_context(self, pet_id: str, user_id: str) -> ClinicalContext:
        with self.session_factory() as session:
            pet = session.scalar(
                select(Pet).where(Pet.id == pet_id, Pet.owner_id == user_id)
            )
            if pet is None:
                raise AnalysisContextNotFound
            # Newest first so the ceiling keeps the clinically relevant end of
            # the archive; ``_build_studies`` restores chronological order and
            # re-keys the studies (H1..Hn) from the study date afterwards.
            # ``created_at`` and not ``performed_at`` because the latter is
            # nullable, and NULL ordering under DESC would put undated rows
            # ahead of real studies.
            rows = list(
                session.scalars(
                    select(Analysis)
                    .where(
                        Analysis.pet_id == pet_id,
                        Analysis.user_id == user_id,
                    )
                    .order_by(desc(Analysis.created_at), desc(Analysis.id))
                    .limit(_HISTORY_STUDY_LIMIT)
                )
            )
            analysis_ids = [row.id for row in rows]
            parameter_rows = (
                list(
                    session.scalars(
                        select(AnalysisParameter)
                        .where(AnalysisParameter.analysis_id.in_(analysis_ids))
                        .order_by(
                            asc(AnalysisParameter.analysis_id),
                            asc(AnalysisParameter.ordinal),
                        )
                    )
                )
                if analysis_ids
                else []
            )
        if not rows:
            raise AnalysisContextNotFound
        studies = self._build_studies(rows, parameter_rows)
        return ClinicalContext(
            mode="hemogram_history",
            patient=self._patient(pet),
            history=studies,
            computed_facts=tuple(self._history_facts(studies)),
            warnings=self._context_warnings(studies),
        )

    def _build_studies(
        self,
        rows: list[Analysis],
        parameter_rows: list[AnalysisParameter],
    ) -> tuple[HemogramStudy, ...]:
        parameters_by_analysis: dict[str, list[AnalysisParameter]] = {}
        for parameter in parameter_rows:
            parameters_by_analysis.setdefault(parameter.analysis_id, []).append(parameter)
        unordered = [
            self._study(
                row,
                self._json(row.data),
                "pending",
                parameters_by_analysis.get(row.id, []),
            )
            for row in rows
        ]
        unordered.sort(key=_study_sort_key)
        return tuple(
            HemogramStudy(
                analysis_id=study.analysis_id,
                study_key=f"H{index}",
                date=study.date,
                label=study.label,
                laboratory=study.laboratory,
                parameters=study.parameters,
                pet_id=study.pet_id,
                analyzer=study.analyzer,
                date_origin=study.date_origin,
                observations=study.observations,
                quality_flags=study.quality_flags,
                extraction_confidence=study.extraction_confidence,
                data_origin=study.data_origin,
                source_revision=study.source_revision,
                classifier_outcome=study.classifier_outcome,
            )
            for index, study in enumerate(unordered, start=1)
        )

    async def _owned_pet_id_for_analysis(
        self, analysis_id: str, user_id: str
    ) -> str | None:
        with self.session_factory() as session:
            result = session.execute(
                select(Analysis.pet_id, Pet.owner_id)
                .join(Pet, Analysis.pet_id == Pet.id)
                .where(Analysis.id == analysis_id, Analysis.user_id == user_id)
            ).first()
        if result is None or result.owner_id != user_id:
            raise AnalysisContextNotFound
        return str(result.pet_id) if result.pet_id else None

    @staticmethod
    def _json(payload: str) -> dict[str, Any]:
        try:
            value = json.loads(payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _patient(pet: Pet) -> PatientContext:
        age = None
        if pet.birth_year:
            age = max(0, datetime.utcnow().year - int(pet.birth_year))
        notes = _clean_text(pet.notes)
        if notes is not None and len(notes) > 500:
            notes = notes[:500].rstrip()
        # Residence is consented data: only surface it once the owner has
        # explicitly granted consent, and only the approximate zone/label —
        # never the exact coordinates stored on the same row.
        has_residence_consent = pet.residence_consent_at is not None
        return PatientContext(
            pet_id=pet.id,
            name=pet.name,
            breed=_clean_text(pet.breed),
            sex=_clean_text(pet.sex),
            age_years=age,
            birth_year=int(pet.birth_year) if pet.birth_year else None,
            weight_kg=_finite_number(pet.weight_kg),
            notes=notes,
            residence_zone_code=(
                _clean_text(pet.residence_zone_code)
                if has_residence_consent
                else None
            ),
            residence_label=(
                _clean_text(pet.residence_label) if has_residence_consent else None
            ),
        )

    def _study(
        self,
        row: Analysis,
        data: dict[str, Any],
        study_key: str,
        normalized_parameters: list[AnalysisParameter] | None = None,
    ) -> HemogramStudy:
        snapshot = data.get("_case_snapshot")
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        classifier_outcome = snapshot.get("classifier_outcome")
        classifier_outcome = (
            classifier_outcome if isinstance(classifier_outcome, dict) else None
        )
        if classifier_outcome is None:
            # ``classifier_outcome`` was added to the case snapshot after
            # analyses were already being stored, so rows written before it
            # keep the very same ML result under the snapshot's root keys
            # (``active_labels``/``probabilities``). Reading only the nested
            # key made the assistant blind to a classification the database
            # actually holds: a stored study carrying
            # PATRON_ANEMIA_NO_REGENERATIVA reached the prompt with
            # ml_finding_count=0, so the chat could not use the label its own
            # ML engine had produced. Projecting the legacy shape here fixes
            # every already-stored analysis without a data migration, and
            # nothing is invented — absent labels stay absent.
            classifier_outcome = _classifier_outcome_from_legacy_snapshot(
                snapshot, data
            )
        metadata = snapshot.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        values = data.get("lab_values")
        values = values if isinstance(values, list) else snapshot.get("lab_values") or []
        normalized_parameters = normalized_parameters or []
        parameters = (
            tuple(
                parameter
                for row_parameter in normalized_parameters
                for parameter in [self._normalized_parameter(row_parameter)]
                if parameter is not None
            )
            if normalized_parameters
            else tuple(
                parameter
                for value in values
                if isinstance(value, dict)
                for parameter in [self._parameter(value)]
                if parameter is not None
            )
        )
        date_candidates = (
            (
                row.performed_at.isoformat() if row.performed_at else None,
                "performed_at",
            ),
            (_clean_text(metadata.get("date_result")), "laboratory_result"),
            (_clean_text(snapshot.get("created_at")), "extracted_snapshot"),
            (_clean_text(data.get("created_at")), "analysis_payload"),
            (row.created_at.isoformat(), "record_created_at_fallback"),
        )
        date, date_origin = next(
            (candidate, origin)
            for candidate, origin in date_candidates
            if candidate is not None
        )
        laboratory = (
            _clean_text(row.laboratory)
            or _clean_text(data.get("laboratory"))
            or _clean_text(metadata.get("clinic"))
            or _clean_text(data.get("clinic_name"))
        )
        analyzer = (
            _clean_text(data.get("analyzer"))
            or _clean_text(data.get("analyzer_name"))
            or _clean_text(snapshot.get("analyzer"))
            or _clean_text(metadata.get("analyzer"))
            or _clean_text(metadata.get("analyzer_name"))
            or _clean_text(metadata.get("equipment"))
        )
        observations: list[str] = []
        for value in (
            snapshot.get("instrument_comments"),
            data.get("summary"),
        ):
            cleaned = _clean_text(value)
            if cleaned and cleaned not in observations:
                observations.append(cleaned)
        for finding in data.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            cleaned = _clean_text(finding.get("detail")) or _clean_text(
                finding.get("label")
            )
            if cleaned and cleaned not in observations:
                observations.append(cleaned)
        quality_flags = tuple(
            cleaned
            for item in (data.get("qc_flags") or snapshot.get("qc_labels") or [])
            for cleaned in [_clean_text(item)]
            if cleaned
        )
        # The column only — never the snapshot's or the payload's
        # ``confidence``, which are both ``prediction.confidence`` from the ML
        # classifier. This value is emitted as fact_type
        # "extraction_confidence", which the prompt describes as how well the
        # document was digitised, so a confident classification over a badly
        # read PDF was presented as a reliable extraction. With no real
        # extraction figure the fact is simply not emitted
        # (``_quality_findings`` skips None) instead of being invented.
        confidence = _finite_number(row.extraction_confidence)
        return HemogramStudy(
            analysis_id=row.id,
            study_key=study_key,
            date=date,
            label=_clean_text(data.get("name")) or f"Hemograma del {date}",
            laboratory=laboratory,
            parameters=parameters,
            pet_id=_clean_text(row.pet_id),
            analyzer=analyzer,
            date_origin=date_origin,
            observations=tuple(observations),
            quality_flags=quality_flags,
            extraction_confidence=confidence,
            data_origin=_clean_text(row.data_origin) or "analysis_database",
            source_revision=_analysis_source_revision(
                row,
                data,
                normalized_parameters,
            ),
            classifier_outcome=classifier_outcome,
        )

    @staticmethod
    def _normalized_parameter(
        value: AnalysisParameter,
    ) -> HemogramParameter | None:
        numeric = value.numeric_value
        if numeric is None:
            return None
        canonical = _canonical_code(value.canonical_name)
        recorded = (_clean_text(value.recorded_flag) or "").casefold() or None
        reference_min = (
            Decimal(value.reference_min) if value.reference_min is not None else None
        )
        reference_max = (
            Decimal(value.reference_max) if value.reference_max is not None else None
        )
        # Structured numeric data is the sole source of truth. Recorded and
        # migrated flags are provenance only and may never override the range.
        flag = _derive_flag(
            Decimal(numeric),
            reference_min,
            reference_max,
            recorded_flag=recorded,
        )
        notes = _clean_text(value.notes)
        if recorded and recorded != flag:
            contradiction = (
                f"La clasificación registrada ({recorded}) no coincide con la derivada "
                f"del valor y rango ({flag}); verificar el documento original."
            )
            notes = f"{notes} {contradiction}".strip() if notes else contradiction
        reference_origin = (
            _clean_text(value.reference_origin) or "unknown"
        ).casefold()
        if reference_origin not in {
            "laboratory",
            "validated_catalog",
            "system_default_legacy",
            "unknown",
        }:
            reference_origin = "unknown"
        return HemogramParameter(
            canonical_name=canonical,
            display_name=(
                cbc_clinical_display_label(canonical)
                or _clean_text(value.display_name)
                or canonical
            ),
            original_name=_clean_text(value.original_name) or value.canonical_name,
            value=Decimal(value.numeric_value),
            value_text=_clean_text(value.value_text) or format(value.numeric_value, "f"),
            unit=_clean_text(value.normalized_unit or value.original_unit),
            reference_min=reference_min,
            reference_max=reference_max,
            flag=flag,  # type: ignore[arg-type]
            recorded_flag=recorded,
            reference_origin=reference_origin,  # type: ignore[arg-type]
            extraction_confidence=_finite_number(value.extraction_confidence),
            notes=notes,
        )

    @staticmethod
    def _parameter(value: dict[str, Any]) -> HemogramParameter | None:
        original_name = _clean_text(
            value.get("original_name") or value.get("original_label") or value.get("name")
        )
        numeric = _decimal(value.get("value"))
        if original_name is None or numeric is None:
            return None
        canonical = _canonical_code(original_name)
        display = (
            cbc_clinical_display_label(canonical)
            or _clean_text(value.get("display_name") or value.get("label"))
            or original_name
        )
        reference_min = _decimal(value.get("ref_min"))
        reference_max = _decimal(value.get("ref_max"))
        status = (_clean_text(value.get("status")) or "").casefold() or None
        status_origin = (_clean_text(value.get("status_origin")) or "").casefold()
        recorded = (
            (_clean_text(value.get("recorded_flag")) or "").casefold()
            or (status if status_origin == "recorded" else None)
        )
        flag = _derive_flag(
            numeric,
            reference_min,
            reference_max,
            recorded_flag=recorded or status,
        )
        reference_origin = _reference_origin(value, reference_min, reference_max)
        notes = _clean_text(value.get("notes") or value.get("comment"))
        if recorded and recorded != flag:
            contradiction = (
                f"La clasificación registrada ({recorded}) no coincide con la calculada "
                f"a partir del valor y rango disponibles ({flag}); verificar el documento original."
            )
            notes = f"{notes} {contradiction}".strip() if notes else contradiction
        raw = value.get("value")
        value_text = _clean_text(raw) or format(numeric, "f")
        return HemogramParameter(
            canonical_name=canonical,
            display_name=display,
            original_name=original_name,
            value=numeric,
            value_text=value_text,
            unit=_clean_text(value.get("unit")),
            reference_min=reference_min,
            reference_max=reference_max,
            flag=flag,  # type: ignore[arg-type]
            recorded_flag=recorded,
            reference_origin=reference_origin,  # type: ignore[arg-type]
            extraction_confidence=_finite_number(
                value.get("extraction_confidence")
                if value.get("extraction_confidence") is not None
                else value.get("confidence")
            ),
            notes=notes,
        )

    @staticmethod
    def _history_facts(
        studies: tuple[HemogramStudy, ...],
    ) -> list[dict[str, Any]]:
        if not studies:
            return []
        series: dict[str, list[tuple[HemogramStudy, HemogramParameter]]] = {}
        for study in studies:
            for parameter in study.parameters:
                series.setdefault(parameter.canonical_name, []).append((study, parameter))
        facts: list[dict[str, Any]] = [
            {
                "fact_type": "history_inventory",
                "study_count": len(studies),
                "pet_id": studies[0].pet_id,
                "analysis_ids": [study.analysis_id for study in studies],
                "oldest_date": studies[0].date,
                "latest_date": studies[-1].date,
            }
        ]
        for code, values in sorted(series.items()):
            reasons = _history_comparison_reasons(values)
            comparison_valid = not reasons
            latest_study, latest = values[-1]
            units = {
                normalize_clinical_unit(parameter.unit)
                for _, parameter in values
                if parameter.unit
            }
            reference_intervals = {
                (parameter.reference_min, parameter.reference_max)
                for _, parameter in values
            }
            laboratories = {
                study.laboratory.casefold()
                for study, _ in values
                if study.laboratory
            }
            analyzers = {
                study.analyzer.casefold()
                for study, _ in values
                if study.analyzer
            }
            fact: dict[str, Any] = {
                "fact_type": "history_parameter",
                "code": code,
                "display_name": latest.display_name,
                "occurrences": len(values),
                # ``comparable`` is retained for current consumers while the
                # explicit fields below carry the stronger contract.
                "comparable": comparison_valid,
                "comparison_valid": comparison_valid,
                "comparison_reasons": reasons,
                "reason": _history_reason_text(reasons),
                "unit": latest.unit,
                "unit_changed": len(units) > 1,
                "reference_interval_changed": len(reference_intervals) > 1,
                "laboratory_changed": len(laboratories) > 1,
                "analyzer_changed": len(analyzers) > 1,
                "observations": [
                    _history_observation(study, parameter)
                    for study, parameter in values
                ],
                "latest": _history_observation(latest_study, latest),
            }
            if comparison_valid:
                highest_study, highest = max(values, key=lambda item: item[1].value)
                fact["highest"] = _history_observation(highest_study, highest)
                previous_study, previous = values[-2]
                delta = latest.value - previous.value
                fact["previous"] = _history_observation(previous_study, previous)
                fact["delta_from_previous"] = format(delta, "f")
                direction = (
                    "increased"
                    if delta > 0
                    else "decreased"
                    if delta < 0
                    else "unchanged"
                )
                fact["direction_from_previous"] = direction
                fact["trend"] = {
                    "increased": "increasing",
                    "decreased": "decreasing",
                    "unchanged": "stable",
                }[direction]
                fact["latest_change_percent"] = (
                    format(
                        ((delta / abs(previous.value)) * Decimal("100")).quantize(
                            Decimal("0.1")
                        ),
                        "f",
                    )
                    if previous.value != 0
                    else None
                )
                fact["percent_change_available"] = previous.value != 0
            facts.append(fact)
        return facts

    @staticmethod
    def _selected_study_fact(
        studies: tuple[HemogramStudy, ...],
        selected: HemogramStudy,
    ) -> dict[str, Any]:
        index = next(
            (position for position, study in enumerate(studies) if study.analysis_id == selected.analysis_id),
            0,
        )
        previous = studies[index - 1] if index > 0 else None
        return _compact_dict(
            {
                "fact_type": "selected_study_position",
                "selected_study_key": selected.study_key,
                "selected_date": selected.date,
                "previous_study_key": previous.study_key if previous else None,
                "previous_date": previous.date if previous else None,
                "has_previous_study": previous is not None,
            }
        )

    @staticmethod
    def _context_warnings(studies: tuple[HemogramStudy, ...]) -> tuple[str, ...]:
        warnings: list[str] = []
        if any(
            parameter.reference_origin == "system_default_legacy"
            for study in studies
            for parameter in study.parameters
        ):
            warnings.append(
                "Algunos rangos provienen del catálogo de referencia legado de HemoVet, "
                "no de un intervalo confirmado del laboratorio."
            )
        if any(
            parameter.extraction_confidence is not None
            and parameter.extraction_confidence < 0.7
            for study in studies
            for parameter in study.parameters
        ):
            warnings.append(
                "Hay valores con confianza de extracción baja; conviene verificarlos en el documento."
            )
        return tuple(warnings)


def _canonical_code(value: str) -> str:
    return canonical_cbc_clinical_code(value)


def _study_sort_key(study: HemogramStudy) -> tuple[datetime, str]:
    # Invalid or legacy date text remains deterministic without being mistaken
    # for a clinically comparable parsed date.
    return (parse_iso_datetime(study.date) or datetime.min, study.analysis_id)


def _classifier_outcome_from_legacy_snapshot(
    snapshot: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, Any] | None:
    """Project a pre-``classifier_outcome`` snapshot into the current shape.

    Mirrors what ``build_case_snapshot`` writes today, reading the same ML
    result from the root keys those older rows already carry. QC labels stay
    excluded from the clinical set exactly as the writer does.

    Three states, because "the engine found nothing" and "the engine never
    ran" are different things to tell a user about their pet:

    - keys absent entirely: the row predates the field, so there is no ML
      output to report at all (``None``).
    - keys present but no scores: ``build_case_snapshot`` writes
      ``active_labels``/``probabilities`` unconditionally, leaving them empty
      when the classifier produced no prediction. Reporting that as
      NO_TARGET_PATTERN_DETECTED would state a negative result the model
      never produced, so it maps to the writer's own honest sentinel.
    - scored with no clinical label: the engine did run and found no target
      pattern, which is the verdict a normal hemogram deserves and the one
      the assistant could not previously give.
    """

    raw_labels = snapshot.get("active_labels")
    raw_probabilities = snapshot.get("probabilities")
    if not isinstance(raw_labels, list) and not isinstance(raw_probabilities, dict):
        return None
    active_labels = [
        text
        for label in (raw_labels if isinstance(raw_labels, list) else [])
        if (text := str(label or "").strip())
    ]
    probabilities = raw_probabilities if isinstance(raw_probabilities, dict) else {}
    clinical_labels = [
        label for label in active_labels if not label.startswith("QC_")
    ]
    if clinical_labels:
        status = "CLASSIFIED"
    elif probabilities or active_labels:
        # Either scores or any emitted label — including a QC-only one —
        # prove the classifier evaluated this study.
        status = "NO_TARGET_PATTERN_DETECTED"
    else:
        status = "LEGACY_INCOMPLETE"
    return {
        "classification_status": status,
        "active_labels": clinical_labels,
        "probabilities": probabilities,
        "model_version": data.get("model_version"),
        "policy_version": data.get("policy_version"),
        "schema_version": data.get("schema_version"),
        "uploaded_at": snapshot.get("created_at"),
    }


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def _derive_flag(
    value: Decimal,
    low: Decimal | None,
    high: Decimal | None,
    *,
    recorded_flag: str | None = None,
) -> str:
    # A laboratory's critical thresholds are not represented by the ordinary
    # reference interval. Preserve an explicit critical flag instead of
    # silently degrading it to merely high/low.
    if str(recorded_flag or "").strip().casefold() == "critical":
        return "critical"
    if low is not None and value < low:
        return "low"
    if high is not None and value > high:
        return "high"
    # A value is normal only when both sides of the interval are known. With a
    # one-sided range we can prove an excursion, but not normality.
    if low is not None and high is not None:
        return "normal"
    return "unknown"


def _analysis_source_revision(
    row: Analysis,
    data: dict[str, Any],
    normalized_parameters: list[AnalysisParameter],
) -> str:
    snapshot = data.get("_case_snapshot")
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    metadata = snapshot.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    explicit = (
        _clean_text(data.get("source_revision"))
        or _clean_text(snapshot.get("source_revision"))
        or _clean_text(metadata.get("source_revision"))
        or _clean_text(data.get("revision"))
    )
    if explicit:
        return explicit
    parameter_payload = [
        {
            "ordinal": parameter.ordinal,
            "code": parameter.canonical_name,
            "value": str(parameter.numeric_value),
            "unit": parameter.normalized_unit or parameter.original_unit,
            "reference_min": str(parameter.reference_min),
            "reference_max": str(parameter.reference_max),
            "reference_origin": parameter.reference_origin,
            "recorded_flag": parameter.recorded_flag,
            "data_origin": parameter.data_origin,
        }
        for parameter in normalized_parameters
    ]
    canonical = json.dumps(
        {
            "schema": "analysis-source-v1",
            "analysis_id": row.id,
            "data_origin": row.data_origin,
            "performed_at": row.performed_at.isoformat() if row.performed_at else None,
            "laboratory": row.laboratory,
            "data": data,
            "parameters": parameter_payload,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _reference_origin(
    value: dict[str, Any],
    low: Decimal | None,
    high: Decimal | None,
) -> str:
    explicit = (_clean_text(value.get("reference_origin") or value.get("range_origin")) or "").casefold()
    aliases = {
        "lab": "laboratory",
        "laboratorio": "laboratory",
        "laboratory": "laboratory",
        "validated_catalog": "validated_catalog",
        "system_default_legacy": "system_default_legacy",
        "unknown": "unknown",
    }
    if explicit in aliases:
        return aliases[explicit]
    if value.get("laboratory_reference") is True:
        return "laboratory"
    if low is not None or high is not None:
        return "system_default_legacy"
    return "unknown"


def _history_comparison_reasons(
    values: list[tuple[HemogramStudy, HemogramParameter]],
) -> list[str]:
    reasons: list[str] = []
    if len(values) < 2:
        reasons.append("insufficient_observations")
        return reasons

    analysis_ids = [study.analysis_id for study, _ in values]
    if len(analysis_ids) != len(set(analysis_ids)):
        reasons.append("duplicate_analysis")
    pet_ids = {study.pet_id for study, _ in values if study.pet_id}
    if len(pet_ids) > 1:
        reasons.append("mixed_patient")

    parsed_dates = [parse_iso_datetime(study.date) for study, _ in values]
    if any(value is None for value in parsed_dates):
        reasons.append("missing_or_invalid_date")
    elif any(
        current <= previous
        for previous, current in zip(parsed_dates, parsed_dates[1:], strict=False)
        if previous is not None and current is not None
    ):
        reasons.append("non_chronological_dates")
    if any(
        study.date_origin in {"unknown", "record_created_at_fallback"}
        for study, _ in values
    ):
        reasons.append("unverified_date_origin")

    units = [normalize_clinical_unit(parameter.unit) for _, parameter in values]
    if any(not unit for unit in units):
        reasons.append("missing_unit")
    elif len(set(units)) > 1:
        reasons.append("incompatible_units")

    intervals = [
        (parameter.reference_min, parameter.reference_max)
        for _, parameter in values
    ]
    if any(low is None or high is None for low, high in intervals):
        reasons.append("missing_reference_interval")
    elif len(set(intervals)) > 1:
        reasons.append("reference_interval_changed")

    laboratories = {
        study.laboratory.casefold()
        for study, _ in values
        if study.laboratory
    }
    if len(laboratories) > 1:
        reasons.append("laboratory_changed")
    analyzers = {
        study.analyzer.casefold()
        for study, _ in values
        if study.analyzer
    }
    if len(analyzers) > 1:
        reasons.append("analyzer_changed")
    origins = {
        study.data_origin.casefold()
        for study, _ in values
        if study.data_origin and study.data_origin != "unknown"
    }
    if len(origins) > 1:
        reasons.append("data_origin_changed")
    if any(
        not study.source_revision or study.source_revision == "unknown"
        for study, _ in values
    ):
        reasons.append("unknown_source_revision")
    return reasons


def _history_observation(
    study: HemogramStudy,
    parameter: HemogramParameter,
) -> dict[str, Any]:
    return _compact_dict(
        {
            "fact_id": clinical_fact_id(study.analysis_id, parameter.canonical_name),
            "pet_id": study.pet_id,
            "analysis_id": study.analysis_id,
            "study_key": study.study_key,
            "date": study.date,
            "date_origin": study.date_origin,
            "value": parameter.value_text,
            "unit": parameter.unit,
            "flag": parameter.flag,
            "reference_min": (
                format(parameter.reference_min, "f")
                if parameter.reference_min is not None
                else None
            ),
            "reference_max": (
                format(parameter.reference_max, "f")
                if parameter.reference_max is not None
                else None
            ),
            "reference_origin": parameter.reference_origin,
            "laboratory": study.laboratory,
            "analyzer": study.analyzer,
            "data_origin": study.data_origin,
            "source_revision": study.source_revision,
        }
    )


def _history_reason_text(reasons: list[str]) -> str | None:
    if not reasons:
        return None
    labels = {
        "insufficient_observations": "se necesitan al menos dos observaciones",
        "duplicate_analysis": "el mismo análisis aparece más de una vez",
        "mixed_patient": "las observaciones pertenecen a pacientes diferentes",
        "missing_or_invalid_date": "falta una fecha válida",
        "non_chronological_dates": "las fechas no forman una secuencia cronológica",
        "unverified_date_origin": "la fecha no procede del estudio clínico",
        "missing_unit": "falta la unidad",
        "incompatible_units": "las unidades son incompatibles",
        "missing_reference_interval": "falta un intervalo de referencia completo",
        "reference_interval_changed": "cambió el intervalo de referencia",
        "laboratory_changed": "cambió el laboratorio",
        "analyzer_changed": "cambió el analizador",
        "data_origin_changed": "cambió el origen del dato",
        "unknown_source_revision": "se desconoce la revisión de la fuente",
    }
    return "; ".join(labels.get(reason, reason) for reason in reasons)
