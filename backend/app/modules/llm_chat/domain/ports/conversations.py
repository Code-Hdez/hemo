"""Technology-neutral persistence contract for an active chat session."""

from __future__ import annotations

from typing import Any, Protocol

from app.modules.llm_chat.domain.clinical import ConversationMemory
from app.modules.llm_chat.domain.entities import (
    ChatMessageRecord,
    ChatTurnReservation,
    ChatTurnSnapshot,
)


class ConversationRepository(Protocol):
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
    ) -> str: ...

    async def get_completed_response(
        self,
        conversation_id: str,
        client_message_id: str,
    ) -> Any | None: ...

    async def load_memory(
        self,
        conversation_id: str,
        *,
        recent_limit: int = 16,
    ) -> ConversationMemory: ...

    async def begin_turn(self, message: ChatMessageRecord) -> bool: ...

    async def reserve_turn(
        self,
        message: ChatMessageRecord,
        *,
        user_id: str,
        auth_session_id: str | None,
        browser_session_hash: str | None,
        request_fingerprint: str,
        lease_seconds: float,
        discard_empty_conversation_on_redirect: bool = False,
    ) -> ChatTurnReservation: ...

    async def current_attempt(
        self,
        conversation_id: str,
        client_message_id: str,
    ) -> int: ...

    async def complete_turn(
        self,
        message: ChatMessageRecord,
        *,
        memory_summary: str,
        memory_state: dict[str, Any],
    ) -> None: ...

    async def append(self, message: ChatMessageRecord) -> None: ...

    async def mark_turn_failed(
        self,
        conversation_id: str,
        client_message_id: str,
        *,
        error_code: str = "technical_error",
        expected_attempt: int | None = None,
    ) -> bool: ...

    async def mark_turn_incomplete(
        self,
        conversation_id: str,
        client_message_id: str,
        *,
        error_code: str,
        expected_attempt: int | None = None,
    ) -> bool: ...

    async def mark_turn_stage(
        self,
        conversation_id: str,
        client_message_id: str,
        *,
        stage: str,
        expected_attempt: int | None = None,
    ) -> bool: ...

    async def recent(
        self,
        conversation_id: str,
        limit: int,
    ) -> list[ChatMessageRecord]: ...

    async def conversation_turns(
        self,
        conversation_id: str,
        *,
        context_revision: int | None = None,
        roles: tuple[str, ...] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ChatMessageRecord]: ...

    async def first_user_message(
        self,
        conversation_id: str,
        *,
        context_revision: int | None = None,
    ) -> ChatMessageRecord | None: ...

    async def user_questions(
        self,
        conversation_id: str,
        *,
        context_revision: int | None = None,
        limit: int | None = None,
    ) -> list[ChatMessageRecord]: ...

    async def history(
        self,
        conversation_id: str,
        user_id: str,
        *,
        limit: int,
        offset: int,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
    ) -> list[ChatMessageRecord]: ...

    async def turn_history(
        self,
        conversation_id: str,
        user_id: str,
        *,
        limit: int,
        offset: int,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def list_active(
        self,
        user_id: str,
        auth_session_id: str | None,
        browser_session_hash: str | None = None,
    ) -> list[dict[str, Any]]: ...

    async def delete_owned(
        self,
        conversation_id: str,
        user_id: str,
        auth_session_id: str | None,
        browser_session_hash: str | None = None,
    ) -> None: ...

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
    ) -> bool: ...

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
    ) -> bool: ...

    async def turn_status(
        self,
        conversation_id: str,
        client_message_id: str,
        user_id: str,
        *,
        auth_session_id: str | None = None,
        browser_session_hash: str | None = None,
    ) -> ChatTurnSnapshot: ...
