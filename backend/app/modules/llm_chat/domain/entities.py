from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.modules.llm_chat.domain.generation_config import OllamaKeepAlive, ProfileKind
from app.modules.llm_chat.domain.response_plan import (
    KnowledgeMode,
    RetrievalPolicy,
    RetrievalStatus,
)


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    source_id: str
    source_path: str
    source_hash: str
    title: str
    language: str
    species: str
    version: str
    status: str
    body: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    id: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class VectorCandidate:
    id: str
    text: str
    metadata: dict[str, Any]
    semantic_score: float


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    text: str
    source_id: str
    title: str
    heading_path: str
    source_path: str
    score: float
    authors: tuple[str, ...] = ()
    edition: str | None = None
    chapter: str | None = None
    section: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    source_type: str = "book"
    # Etapa 5, Block E: eligibility for generation context and eligibility
    # for a public citation are distinct permissions. A chunk can be valid,
    # trustworthy context for the model to read even when editorial policy
    # does not allow showing it as a citation; ``generation_use_allowed``
    # gates the former, ``citation_allowed`` only the latter. Neither flag
    # controls the other.
    generation_use_allowed: bool = True
    citation_allowed: bool = True
    # Original document language (Block B/E) so the model and the citation
    # projection can both know a source is not Spanish without that fact
    # ever being used to reject the chunk.
    source_language: str | None = None


@dataclass(frozen=True, slots=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """One capability the model may invoke, in provider-neutral form.

    The shape a tool-calling runtime needs is the same everywhere — a name, a
    sentence saying when to reach for it, and a JSON Schema for its arguments —
    so it lives here rather than in either client.

    Their existence is the architectural change: today every authorized value
    travels in the prompt whether the question needs it or not, which is why a
    turn costs 7.363 prompt tokens and 7 seconds before the first word. A tool
    lets the model ask for what it actually needs, and lets it reach a study
    that was never preselected.
    """

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A tool the model asked for, as the provider reported it."""

    name: str
    arguments: dict[str, Any]
    call_id: str = ""


@dataclass(frozen=True, slots=True)
class ToolResult:
    """What executing a tool produced, on its way back to the model.

    ``authorized_facts`` is the load-bearing field. A tool that returns a
    patient's values does not merely inform the answer, it *authorizes* them:
    what it returned becomes the fact registry the output validators check
    claims against. That keeps the clinical guarantee exactly where it was —
    every stated value traceable to an authorized record — while removing the
    requirement that the record be in the prompt before the question is read.
    """

    call_id: str
    name: str
    content: str
    authorized_facts: tuple[dict[str, Any], ...] = ()
    error: str | None = None


# Vocabulario de rutas de generación. Vive en el dominio porque describe el
# flujo del turno, no el transporte: la infraestructura lo importa para
# etiquetar cada POST, y el caso de uso para marcar desde dónde nace la
# petición. Hoy existen cinco; el objetivo del rediseño es que solo quede
# ``GENERATION_ROUTE_MAIN``.
GENERATION_ROUTE_MAIN = "main"
GENERATION_ROUTE_REPAIR = "repair"
GENERATION_ROUTE_STEER = "steer"
GENERATION_ROUTE_LAST_RESORT = "last_resort"
GENERATION_ROUTE_TOOL = "tool"

GENERATION_ROUTES = frozenset(
    {
        GENERATION_ROUTE_MAIN,
        GENERATION_ROUTE_REPAIR,
        GENERATION_ROUTE_STEER,
        GENERATION_ROUTE_LAST_RESORT,
        GENERATION_ROUTE_TOOL,
    }
)


@dataclass(frozen=True, slots=True)
class ModelRequest:
    system_prompt: str
    user_prompt: str
    thinking: bool
    model: str
    profile_name: str
    profile_kind: ProfileKind
    num_predict: int
    num_ctx: int
    max_input_tokens: int
    context_reserve_tokens: int
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    timeout_seconds: float
    keep_alive: OllamaKeepAlive
    retrieval_policy: RetrievalPolicy = RetrievalPolicy.NONE
    retrieval_status: RetrievalStatus = RetrievalStatus.NOT_REQUESTED
    knowledge_mode: KnowledgeMode = KnowledgeMode.PARAMETRIC
    prompt_stats: dict[str, object] = field(default_factory=dict)
    retained_source_ids: tuple[str, ...] = ()
    # JSON Schema requested from the external runtime.  Keeping the schema on
    # the domain request lets the application require structured generation
    # without coupling the use case to Ollama's ``format`` field or OpenAI's
    # ``response_format`` extension.
    response_schema: dict[str, Any] | None = None
    # Opaque operational identifier propagated as an HTTP header. It never
    # becomes part of the prompt or persisted clinical content.
    correlation_id: str | None = None
    # Tools offered for this request, and the transcript of the ones already
    # called in it. Empty on every request that does not use them, which keeps
    # the previous behaviour byte-identical while the new flow is switched off.
    tools: tuple[ToolDefinition, ...] = ()
    tool_exchanges: tuple[tuple[ToolCall, ToolResult], ...] = ()
    # Desde qué ruta del turno nace esta petición. Solo se usa para contar y
    # segregar la telemetría: el adaptador no cambia de comportamiento según su
    # valor. El defecto mantiene byte-idéntico a todo llamante que no lo fije.
    generation_route: str = GENERATION_ROUTE_MAIN


@dataclass(frozen=True, slots=True)
class ModelResponse:
    text: str
    model: str
    usage: TokenUsage
    duration_ms: int
    finish_reason: str
    provider_metrics: dict[str, Any] = field(default_factory=dict)
    # Non-empty when the model asked for tools instead of answering. The turn
    # runs them and calls back; ``text`` is normally empty in that case.
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelStreamChunk:
    text: str = ""
    done: bool = False
    model: str | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: int = 0
    finish_reason: str = "stop"
    provider_metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChatMessageRecord:
    id: str
    conversation_id: str
    client_message_id: str
    role: str
    content: str
    status: str
    model: str | None = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: int | None = None
    finish_reason: str | None = None
    sources: list[RetrievedChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    turn_index: int | None = None


@dataclass(frozen=True, slots=True)
class ChatTurnSnapshot:
    conversation_id: str
    client_message_id: str
    status: str
    attempt: int
    retryable: bool
    error_code: str | None = None
    response: Any | None = None
    turn_id: str | None = None
    processing_stage: str | None = None
    context_revision: int = 1


@dataclass(frozen=True, slots=True)
class ChatTurnReservation:
    """Result of atomically reserving one idempotent chat turn."""

    conversation_id: str
    client_message_id: str
    status: str
    attempt: int
    acquired: bool
    retryable: bool
    context_revision: int
    error_code: str | None = None
    turn_id: str | None = None
    processing_stage: str | None = None
    context_fingerprint: str | None = None
