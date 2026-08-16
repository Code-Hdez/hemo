from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.config import settings
from app.modules.llm_chat.application.dto import ChatResult
from app.modules.llm_chat.application.services.assistant_identity import (
    enforce_assistant_identity,
)
from app.modules.llm_chat.application.services.source_projection import (
    project_citation_sources,
)


ChatScope = Literal[
    "general",
    "selected_hemogram",
    "hemogram_history",
    "uploaded_analysis",
    "historical_analysis",
]
PUBLIC_ROUTE_TRACE_KEYS = frozenset(
    {
        "analysis_loaded",
        "fallback_type",
        "fallback_used",
        "factual_validation",
        "generated_tokens",
        "generation_tokens_per_second",
        "gpu_active",
        "guardrail_reason_code",
        "guardrail_triggered",
        "history_loaded",
        "inference_device",
        "intent_confidence",
        "llm_duration_ms",
        "llm_invoked",
        "mode_requested",
        "model_digest",
        "model_name",
        "model_size_bytes",
        "post_validation_triggered",
        "primary_intent",
        "prompt_tokens",
        "prompt_tokens_per_second",
        "first_validation_reason",
        "provider_call_routes",
        "provider_calls",
        "sources_consulted",
        "provider_metrics",
        "quantization",
        "rag_invoked",
        "rag_requested",
        "rag_used",
        "retrieval_policy",
        "retrieval_status",
        "knowledge_mode",
        "request_id",
        "response_route",
        "retrieval_duration_ms",
        "retrieved_candidates_count",
        "rewrite_triggered",
        "route_selected",
        "secondary_intents",
        "services_executed",
        "size_vram_bytes",
        "sources_after_filter_count",
        "stream_completed",
        "structured_response_type",
        "total_duration_ms",
        "vram_ratio",
    }
)
MessageText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=settings.CHAT_MESSAGE_MAX_CHARS,
    ),
]


class ChatOptions(BaseModel):
    """Reserved for future per-turn client options.

    ``thinking`` was removed from this surface: the qualified generation
    profile fixes it server-side (``OLLAMA_THINK``) and no client input can
    override it. Accepting-but-ignoring it made the public contract lie about
    what a request actually controlled.
    """

    model_config = ConfigDict(extra="forbid")


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_message_id: UUID
    conversation_id: UUID | None = None
    message: MessageText
    context_scope: ChatScope
    analysis_id: str | None = Field(default=None, min_length=1, max_length=64)
    pet_id: str | None = Field(default=None, min_length=1, max_length=64)
    expected_context_revision: int | None = Field(default=None, ge=1)
    options: ChatOptions = Field(default_factory=ChatOptions)

    @model_validator(mode="after")
    def validate_context_reference(self) -> "ChatRequest":
        selected = self.context_scope in {"selected_hemogram", "uploaded_analysis"}
        history = self.context_scope in {"hemogram_history", "historical_analysis"}
        if selected and not self.analysis_id:
            raise ValueError("analysis_id is required for selected hemogram chat")
        if history and not self.pet_id and not self.analysis_id:
            raise ValueError("pet_id is required for hemogram history chat")
        if self.context_scope == "hemogram_history" and self.analysis_id is not None:
            raise ValueError("analysis_id is not allowed for canonical history chat")
        if self.context_scope == "general" and self.analysis_id is not None:
            raise ValueError("analysis_id is not allowed for general chat")
        return self


class TokenUsageResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int


class ChatSourceResponse(BaseModel):
    citation_id: str
    display_title: str
    authors: list[str] = Field(default_factory=list)
    edition: str | None = None
    chapter: str | None = None
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source_type: str
    # Etapa 5, Block E: the source's own language, shown so a citation
    # backing a Spanish answer can honestly say it is not Spanish.
    source_language: str | None = None


class ChatCaseFactResponse(BaseModel):
    parameter: str
    value: str
    fact_id: str | None = None
    code: str | None = None
    analysis_id: str | None = None
    study_key: str | None = None
    study_date: str | None = None
    unit: str | None = None
    status: str | None = None
    reference_min: str | None = None
    reference_max: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    turn_id: str | None = None
    message_id: str
    answer: str
    scope: ChatScope
    case_facts: list[ChatCaseFactResponse]
    sources: list[ChatSourceResponse]
    warnings: list[str]
    safety_action: str
    model: str | None
    usage: TokenUsageResponse
    duration_ms: int
    finish_reason: str
    llm_invoked: bool
    # Etapa 8, Block A: the active success contract admits exactly one value
    # for anything a current turn can produce — application code has
    # guaranteed response_origin="llm" for every completed message since
    # etapa 4. "legacy" is not a value new turns can ever persist; it exists
    # only so a handful of rows written before that stage (originally
    # "safety_fallback"/"legacy_deterministic"/"deterministic_safety_boundary")
    # keep serializing instead of 500ing. The validator below is the single
    # place that mapping happens — no other schema or code path may treat a
    # legacy origin as a distinct, still-meaningful category.
    response_origin: Literal["llm", "legacy"]
    attempt: int = Field(ge=1)
    generation_attempts: int = Field(ge=0)
    stream_mode: Literal["live_validated", "buffered_validated"]
    validation_status: str
    route_trace: dict[str, object] = Field(default_factory=dict)
    context: dict[str, object] = Field(default_factory=dict)

    @field_validator("response_origin", mode="before")
    @classmethod
    def _normalize_legacy_response_origin(cls, value: object) -> object:
        if value in {
            "safety_fallback",
            "legacy_deterministic",
            "deterministic_safety_boundary",
        }:
            return "legacy"
        return value


def chat_response_from_result(result: ChatResult) -> ChatResponse:
    """Materialize the complete public contract from an application result."""

    citations = project_citation_sources(result.sources)
    return ChatResponse(
        conversation_id=result.conversation_id,
        turn_id=result.turn_id,
        message_id=result.message_id,
        answer=enforce_assistant_identity(result.answer),
        scope=result.scope,
        case_facts=[ChatCaseFactResponse(**fact) for fact in result.case_facts],
        sources=[ChatSourceResponse(**source.as_dict()) for source in citations],
        warnings=result.warnings,
        safety_action=result.safety_action.value,
        model=result.model,
        usage=TokenUsageResponse(
            prompt_tokens=result.usage.prompt_tokens,
            completion_tokens=result.usage.completion_tokens,
        ),
        duration_ms=result.duration_ms,
        finish_reason=result.finish_reason,
        llm_invoked=result.llm_invoked,
        response_origin=result.response_origin,
        attempt=result.attempt,
        generation_attempts=result.generation_attempts,
        stream_mode=result.stream_mode,
        validation_status=result.validation_status,
        route_trace={
            key: value
            for key, value in result.route_trace.items()
            if key in PUBLIC_ROUTE_TRACE_KEYS
        },
        context=result.context,
    )


class ConversationMessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    status: str
    created_at: datetime | None
    context: dict[str, object] = Field(default_factory=dict)


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_scope: ChatScope
    analysis_id: str | None = Field(default=None, min_length=1, max_length=64)
    pet_id: str | None = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_context_reference(self) -> "ConversationCreateRequest":
        ChatRequest(
            client_message_id=UUID("00000000-0000-0000-0000-000000000001"),
            message="crear conversación",
            context_scope=self.context_scope,
            analysis_id=self.analysis_id,
            pet_id=self.pet_id,
        )
        return self


class ConversationResponse(BaseModel):
    id: str
    mode: str
    pet_id: str | None = None
    analysis_id: str | None = None
    context_revision: int
    context_key: str | None = None
    context_fingerprint: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    expires_at: datetime | None = None


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]


class ConversationHistoryResponse(BaseModel):
    items: list[ConversationMessageResponse]
    limit: int
    offset: int


class ConversationTurnMessageResponse(BaseModel):
    id: str
    content: str
    status: str
    created_at: datetime | None = None


class ConversationTurnResponse(BaseModel):
    turn_id: str | None = None
    conversation_id: str
    client_message_id: str
    context_revision: int = Field(ge=1)
    turn_index: int = Field(ge=1)
    status: Literal[
        "pending",
        "processing",
        "completed",
        "refused",
        "failed",
        "interrupted",
        "incomplete",
    ]
    attempt: int = Field(ge=1)
    retryable: bool
    state: Literal[
        "pending",
        "generating",
        "validating",
        "repairing",
        "completed",
        "failed_retryable",
        "failed_terminal",
        "cancelled",
        "expired",
    ]
    processing_stage: str | None = None
    error_code: str | None = None
    user_message: ConversationTurnMessageResponse
    response: ChatResponse | None = None
    updated_at: datetime | None = None


class ConversationTurnListResponse(BaseModel):
    items: list[ConversationTurnResponse]
    limit: int
    offset: int


class CancelTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt: int = Field(ge=1)


class TurnStatusResponse(BaseModel):
    turn_id: str | None = None
    conversation_id: str
    client_message_id: str
    status: Literal[
        "pending",
        "processing",
        "completed",
        "refused",
        "failed",
        "interrupted",
        "incomplete",
    ]
    attempt: int = Field(ge=1)
    retryable: bool
    state: Literal[
        "pending",
        "generating",
        "validating",
        "repairing",
        "completed",
        "failed_retryable",
        "failed_terminal",
        "cancelled",
        "expired",
    ]
    processing_stage: str | None = None
    error_code: str | None = None
    response: ChatResponse | None = None


class ChatErrorEnvelope(BaseModel):
    code: str
    message: str
    detail: str
    category: Literal[
        "provider",
        "timeout",
        "capacity",
        "conflict",
        "validation",
        "persistence",
        "transport",
        "cancellation",
        "authorization",
        "unexpected",
    ]
    retryable: bool
    recovery_action: Literal[
        "retry_same_turn",
        "poll_turn",
        "start_new_conversation",
        "choose_context",
        "none",
    ]
    request_id: str
    client_message_id: str
    # Qué comprobación rechazó la generación que acabó en este error terminal.
    #
    # El `code` público es un vocabulario cerrado a propósito: todo lo que el
    # validador rechaza colapsa en `invalid_model_output`. Eso está bien para el
    # contrato del cliente y fue exactamente lo que dejó ciega la medición: los
    # turnos que fallan de forma terminal son los MÁS difíciles del corpus, y
    # eran justo los que llegaban sin motivo. En `puerta3j`, 6 de los 10 fallos
    # de contrato no tenían nombre por esto.
    #
    # Es un dato del servidor, derivado de `OutputValidation.reason`, y viaja
    # saneado contra un patrón cerrado — nunca texto del proveedor.
    first_validation_reason: str | None = None
    conversation_id: str | None = None
    turn_id: str | None = None
    attempt: int | None = Field(default=None, ge=1)
    retry_after_ms: int | None = Field(default=None, ge=0)
    http_status: int
