from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.modules.llm_chat.domain.entities import RetrievedChunk, TokenUsage
from app.modules.llm_chat.domain.value_objects import SafetyAction


@runtime_checkable
class ValidatedPublicResponse(Protocol):
    """Framework-neutral surface of an already validated API response model."""

    def model_dump(self, *, mode: str = "python") -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class ChatCommand:
    user_id: str
    client_message_id: str
    conversation_id: str | None
    message: str
    context_scope: str
    analysis_id: str | None
    pet_id: str | None = None
    auth_session_id: str | None = None
    browser_session_hash: str | None = None
    expected_context_revision: int | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class ChatResult:
    conversation_id: str
    message_id: str
    answer: str
    scope: str
    case_facts: list[dict[str, object]]
    sources: list[RetrievedChunk]
    warnings: list[str]
    safety_action: SafetyAction
    model: str | None
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: int = 0
    finish_reason: str = "stop"
    llm_invoked: bool = True
    response_origin: str = "llm"
    attempt: int = 1
    generation_attempts: int = 1
    stream_mode: str = "buffered_validated"
    validation_status: str = "passed"
    route_trace: dict[str, object] = field(default_factory=dict)
    context: dict[str, object] = field(default_factory=dict)
    turn_id: str | None = None
    # Opaque API-layer model produced by an injected mapper before commit.
    # The application does not depend on Pydantic; the router returns this
    # exact validated object after persistence succeeds.
    validated_response: ValidatedPublicResponse | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    validated_payload: dict[str, object] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )
