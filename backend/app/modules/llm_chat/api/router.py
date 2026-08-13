from __future__ import annotations

import logging
import hashlib
import hmac
from collections.abc import AsyncIterator
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from app.dependencies.auth import get_current_user_id
from app.core.config import settings
from app.modules.llm_chat.api.dependencies import (
    get_analysis_context_repository,
    get_conversation_repository,
    get_send_chat_use_case,
)
from app.modules.llm_chat.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationTurnListResponse,
    ConversationTurnMessageResponse,
    ConversationTurnResponse,
    CancelTurnRequest,
    ChatErrorEnvelope,
    TurnStatusResponse,
    PUBLIC_ROUTE_TRACE_KEYS,
    chat_response_from_result,
)
from app.modules.llm_chat.api.sse import encode_sse
from app.modules.llm_chat.application.dto import ChatCommand, ChatResult
from app.modules.llm_chat.application.availability import unavailable_chat_health
from app.modules.llm_chat.application.services.clinical_context_revision import (
    clinical_context_fingerprint,
)
from app.modules.llm_chat.application.services.assistant_identity import (
    enforce_assistant_identity,
)
from app.modules.llm_chat.domain.exceptions import (
    ChatResourceNotFound,
    ChatRuntimeUnavailable,
    ChatContextRevisionConflict,
    ChatIdempotencyConflict,
    ChatPersistenceError,
    ChatTurnConcurrencyConflict,
    ChatTurnInProgress,
)
from app.modules.llm_chat.domain.value_objects import SafetyAction
from app.modules.llm_chat.domain.provider_contract import (
    ProviderFailureCode,
    is_retryable_provider_failure,
    normalize_provider_failure_code,
)


router = APIRouter(prefix="/chat", tags=["LLM Chat"])
logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")

def _response(result: ChatResult) -> ChatResponse:
    """Use the prevalidated response for live turns and one canonical mapper."""

    if isinstance(result.validated_response, ChatResponse):
        return result.validated_response
    return chat_response_from_result(result)


def _public_turn_state(
    status_value: str,
    retryable: bool,
    processing_stage: str | None,
    error_code: str | None,
) -> str:
    if processing_stage in {
        "pending",
        "generating",
        "validating",
        "repairing",
        "completed",
        "failed_retryable",
        "failed_terminal",
        "cancelled",
        "expired",
    }:
        return processing_stage
    if status_value in {"completed", "refused"}:
        return "completed"
    if status_value == "interrupted":
        return "cancelled" if error_code == "client_cancelled" else "expired"
    if status_value in {"failed", "incomplete"}:
        return "failed_retryable" if retryable else "failed_terminal"
    if status_value == "processing":
        return "generating"
    return "pending"


_RUNTIME_ERRORS: dict[str, tuple[int, str, int | None, str]] = {
    "generation_queue_timeout": (
        status.HTTP_429_TOO_MANY_REQUESTS,
        "retry_same_turn",
        2000,
        "capacity",
    ),
    "chat_total_timeout": (
        status.HTTP_504_GATEWAY_TIMEOUT,
        "retry_same_turn",
        1000,
        "timeout",
    ),
    ProviderFailureCode.LLM_PROVIDER_CONNECT_TIMEOUT.value: (
        status.HTTP_504_GATEWAY_TIMEOUT,
        "retry_same_turn",
        1000,
        "timeout",
    ),
    ProviderFailureCode.LLM_PROVIDER_READ_TIMEOUT.value: (
        status.HTTP_504_GATEWAY_TIMEOUT,
        "retry_same_turn",
        1000,
        "timeout",
    ),
    ProviderFailureCode.LLM_PROVIDER_OVERLOADED.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "retry_same_turn",
        2000,
        "capacity",
    ),
    ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "retry_same_turn",
        2000,
        "provider",
    ),
    ProviderFailureCode.LLM_PROVIDER_INVALID_RESPONSE.value: (
        status.HTTP_502_BAD_GATEWAY,
        "none",
        0,
        "provider",
    ),
    ProviderFailureCode.LLM_PROVIDER_IDENTITY_UNVERIFIED.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "none",
        None,
        "provider",
    ),
    ProviderFailureCode.LLM_PROVIDER_MODEL_MISMATCH.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "none",
        None,
        "provider",
    ),
    ProviderFailureCode.LLM_PROVIDER_DIGEST_MISMATCH.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "none",
        None,
        "provider",
    ),
    ProviderFailureCode.LLM_PROVIDER_QUANTIZATION_MISMATCH.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "none",
        None,
        "provider",
    ),
    ProviderFailureCode.LLM_PROVIDER_REVISION_MISMATCH.value: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "none",
        None,
        "provider",
    ),
    "generation_contract_failed": (
        status.HTTP_502_BAD_GATEWAY,
        "retry_same_turn",
        0,
        "validation",
    ),
    "generation_repair_failed": (
        status.HTTP_502_BAD_GATEWAY,
        "retry_same_turn",
        0,
        "validation",
    ),
    "invalid_model_output": (
        status.HTTP_502_BAD_GATEWAY,
        "retry_same_turn",
        0,
        "validation",
    ),
    "model_output_truncated": (
        status.HTTP_502_BAD_GATEWAY,
        "retry_same_turn",
        0,
        "validation",
    ),
    "context_budget_exceeded": (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "start_new_conversation",
        0,
        "validation",
    ),
}

_RUNTIME_MESSAGES = {
    "generation_queue_timeout": "El asistente está atendiendo otra solicitud. Puedes reintentar esta misma pregunta.",
    "chat_total_timeout": "La respuesta tardó más de lo permitido. Puedes reintentar esta misma pregunta.",
    ProviderFailureCode.LLM_PROVIDER_CONNECT_TIMEOUT.value: "No fue posible conectar a tiempo con el asistente. Puedes reintentar esta misma pregunta.",
    ProviderFailureCode.LLM_PROVIDER_READ_TIMEOUT.value: "El asistente no terminó la respuesta a tiempo. Puedes reintentar esta misma pregunta.",
    ProviderFailureCode.LLM_PROVIDER_OVERLOADED.value: "El asistente está temporalmente saturado. Puedes reintentar esta misma pregunta.",
    ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value: "El asistente está temporalmente no disponible. Tu pregunta se conservó para reintentarla.",
    ProviderFailureCode.LLM_PROVIDER_INVALID_RESPONSE.value: "El proveedor de generación devolvió una respuesta inválida y no se mostró contenido.",
    ProviderFailureCode.LLM_PROVIDER_IDENTITY_UNVERIFIED.value: "No se pudo verificar el runtime autorizado del asistente.",
    ProviderFailureCode.LLM_PROVIDER_MODEL_MISMATCH.value: "El runtime del asistente no corresponde al modelo autorizado.",
    ProviderFailureCode.LLM_PROVIDER_DIGEST_MISMATCH.value: "El runtime del asistente no corresponde a la revisión autorizada.",
    ProviderFailureCode.LLM_PROVIDER_QUANTIZATION_MISMATCH.value: "El runtime del asistente no corresponde a la cuantización autorizada.",
    ProviderFailureCode.LLM_PROVIDER_REVISION_MISMATCH.value: "El runtime del asistente no corresponde a la revisión publicada.",
    "generation_contract_failed": "La respuesta no cumplió el contrato estructurado y no se mostró contenido.",
    "generation_repair_failed": "La reparación no cumplió el contrato estructurado y no se mostró contenido.",
    "invalid_model_output": "La respuesta del modelo no superó la validación clínica y de seguridad.",
    "model_output_truncated": "El modelo produjo una respuesta truncada y no se guardó como válida.",
    "context_budget_exceeded": "La evidencia imprescindible no cabe de forma segura en el contexto del modelo.",
}


def _runtime_code(exc: ChatRuntimeUnavailable) -> str:
    raw = getattr(exc, "code", str(exc)).strip()
    provider_code = normalize_provider_failure_code(raw)
    if provider_code is not None:
        return provider_code.value
    if raw.startswith("invalid_output_") or raw == "stream_final_mismatch":
        return "invalid_model_output"
    if raw == "incomplete_output":
        return "model_output_truncated"
    if raw in _RUNTIME_ERRORS:
        return raw
    return ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value


def _public_persisted_error_code(code: str | None) -> str | None:
    if code is None:
        return None
    provider_code = normalize_provider_failure_code(code)
    return provider_code.value if provider_code is not None else code


def _public_stream_error(data: dict[str, object]) -> dict[str, object]:
    """Normalize provider errors yielded by the application stream boundary."""

    raw_code = str(data.get("code") or "").strip()
    provider_code = normalize_provider_failure_code(raw_code)
    if raw_code == SafetyAction.TECHNICAL_ERROR.value:
        provider_code = ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE
    if provider_code is None:
        return data
    code = provider_code.value
    http_status, recovery_action, retry_after_ms, category = _RUNTIME_ERRORS[code]
    message = _RUNTIME_MESSAGES[code]
    return {
        **data,
        "code": code,
        "message": message,
        "detail": message,
        "category": category,
        "retryable": is_retryable_provider_failure(code),
        "recovery_action": recovery_action,
        "retry_after_ms": retry_after_ms,
        "http_status": http_status,
    }


def _error_envelope(
    request: ChatRequest,
    *,
    code: str,
    message: str,
    http_status: int,
    retryable: bool,
    recovery_action: str,
    request_id: str,
    category: str,
    detail: str | None = None,
    conversation_id: str | None = None,
    turn_id: str | None = None,
    attempt: int | None = None,
    retry_after_ms: int | None = None,
) -> ChatErrorEnvelope:
    return ChatErrorEnvelope(
        code=code,
        message=message,
        detail=detail or message,
        category=category,
        retryable=retryable,
        recovery_action=recovery_action,
        request_id=request_id,
        client_message_id=str(request.client_message_id),
        conversation_id=(
            conversation_id
            if conversation_id is not None
            else str(request.conversation_id)
            if request.conversation_id
            else None
        ),
        turn_id=turn_id,
        attempt=attempt,
        retry_after_ms=retry_after_ms,
        http_status=http_status,
    )


def _runtime_envelope(
    request: ChatRequest,
    exc: ChatRuntimeUnavailable,
    *,
    request_id: str,
) -> ChatErrorEnvelope:
    code = _runtime_code(exc)
    http_status, recovery_action, retry_after_ms, category = _RUNTIME_ERRORS.get(
        code,
        (status.HTTP_502_BAD_GATEWAY, "retry_same_turn", 0, "provider"),
    )
    message = _RUNTIME_MESSAGES.get(
        code,
        "La respuesta del modelo no superó la validación de seguridad. Puedes reintentarla.",
    )
    return _error_envelope(
        request,
        code=code,
        message=message,
        http_status=http_status,
        retryable=recovery_action == "retry_same_turn",
        recovery_action=recovery_action,
        request_id=request_id,
        category=category,
        conversation_id=exc.conversation_id,
        attempt=exc.attempt,
        retry_after_ms=retry_after_ms,
    )


def _resource_envelope(request: ChatRequest, *, request_id: str) -> ChatErrorEnvelope:
    return _error_envelope(
        request,
        code="resource_not_found",
        message="La conversación o el contexto solicitado ya no está disponible.",
        http_status=status.HTTP_404_NOT_FOUND,
        retryable=False,
        recovery_action="choose_context",
        request_id=request_id,
        category="authorization",
    )


def _conflict_envelope(
    request: ChatRequest,
    exc: (
        ChatContextRevisionConflict
        | ChatTurnInProgress
        | ChatIdempotencyConflict
        | ChatTurnConcurrencyConflict
    ),
    *,
    request_id: str,
) -> ChatErrorEnvelope:
    in_progress = isinstance(exc, ChatTurnInProgress)
    idempotency_conflict = isinstance(exc, ChatIdempotencyConflict)
    completion_conflict = isinstance(exc, ChatTurnConcurrencyConflict)
    return _error_envelope(
        request,
        code=(
            "turn_in_progress"
            if in_progress
            else "turn_completion_conflict"
            if completion_conflict
            else "idempotency_conflict"
            if idempotency_conflict
            else "context_revision_conflict"
        ),
        message=(
            "Este turno todavía se está procesando. Espera su estado antes de volver a enviarlo."
            if in_progress
            else "El turno cambió mientras se guardaba la respuesta. Consulta su estado canónico."
            if completion_conflict
            else "El identificador de este mensaje ya pertenece a otra pregunta o contexto."
            if idempotency_conflict
            else "El contexto de la conversación cambió. Inicia un chat compatible con el contexto activo."
        ),
        http_status=status.HTTP_409_CONFLICT,
        retryable=in_progress or completion_conflict,
        recovery_action=(
            "poll_turn"
            if in_progress or completion_conflict
            else "start_new_conversation"
        ),
        request_id=request_id,
        category="conflict",
        conversation_id=getattr(exc, "conversation_id", None),
        attempt=getattr(exc, "attempt", None),
        retry_after_ms=1000 if in_progress or completion_conflict else None,
    )


@router.get("/health")
async def chat_health(request: Request) -> dict[str, object]:
    container = getattr(request.app.state, "llm_chat", None)
    if container is None:
        return unavailable_chat_health(
            rag_required=settings.RAG_ENABLED,
            provider_name=settings.CHAT_LLM_PROVIDER,
            model=(
                settings.OLLAMA_MODEL
                if settings.CHAT_LLM_PROVIDER == "ollama"
                else settings.OPENAI_COMPATIBLE_MODEL
            ),
            embedding_model=settings.RAG_EMBEDDING_MODEL,
        )
    return await container.health()


@router.get("/health/provider")
async def provider_health(request: Request) -> dict[str, object]:
    """Expose only the sanitized remote-provider availability contract."""

    payload = await chat_health(request)
    provider = payload.get("provider")
    return provider if isinstance(provider, dict) else {}


@router.get("/health/rag")
async def rag_health(request: Request) -> dict[str, object]:
    """Expose RAG readiness independently from provider availability."""

    payload = await chat_health(request)
    rag = payload.get("rag")
    return rag if isinstance(rag, dict) else {}


def _command(
    request: ChatRequest,
    user_id: str,
    auth_session_id: str | None = None,
    browser_session_hash: str | None = None,
    request_id: str | None = None,
) -> ChatCommand:
    return ChatCommand(
        user_id=user_id,
        client_message_id=str(request.client_message_id),
        conversation_id=(
            str(request.conversation_id) if request.conversation_id else None
        ),
        message=request.message,
        context_scope=request.context_scope,
        analysis_id=request.analysis_id,
        pet_id=request.pet_id,
        auth_session_id=auth_session_id,
        browser_session_hash=browser_session_hash,
        expected_context_revision=request.expected_context_revision,
        request_id=request_id,
    )


def _public_route_trace(trace: dict[str, object]) -> dict[str, object]:
    """Project operational metadata without exposing internal evidence IDs.

    chat_response_from_result() applies this same allowlist when building the
    REST/history response; this thin wrapper reuses the identical canonical
    set so any router-local projection (e.g. SSE payloads) stays in lockstep
    rather than defining a second copy of the policy.
    """

    return {
        key: value for key, value in trace.items() if key in PUBLIC_ROUTE_TRACE_KEYS
    }


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    http_request: Request,
    http_response: Response,
    user_id: str = Depends(get_current_user_id),
    use_case=Depends(get_send_chat_use_case),
) -> ChatResponse:
    request_id = str(uuid4())
    http_response.headers["X-Request-ID"] = request_id
    browser_session_hash = _browser_session_hash(http_request)
    try:
        result = await use_case.execute(
            _command(
                request,
                user_id,
                _auth_session_id(http_request, user_id),
                browser_session_hash,
                request_id,
            )
        )
    except ChatResourceNotFound as exc:
        envelope = _resource_envelope(request, request_id=request_id)
        raise HTTPException(
            status_code=envelope.http_status,
            detail=envelope.model_dump(mode="json"),
        ) from exc
    except ChatRuntimeUnavailable as exc:
        envelope = _runtime_envelope(request, exc, request_id=request_id)
        raise HTTPException(
            status_code=envelope.http_status,
            detail=envelope.model_dump(mode="json"),
        ) from exc
    except (
        ChatContextRevisionConflict,
        ChatTurnInProgress,
        ChatIdempotencyConflict,
        ChatTurnConcurrencyConflict,
    ) as exc:
        envelope = _conflict_envelope(request, exc, request_id=request_id)
        raise HTTPException(
            status_code=envelope.http_status,
            detail=envelope.model_dump(mode="json"),
        ) from exc
    except ChatPersistenceError as exc:
        logger.exception("llm_chat.persistence_error request_id=%s", request_id)
        envelope = _error_envelope(
            request,
            code="persistence_error",
            message="No se pudo guardar el estado del turno de forma segura.",
            detail="Consulta el estado antes de volver a enviar la pregunta.",
            category="persistence",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=True,
            recovery_action="poll_turn",
            request_id=request_id,
        )
        raise HTTPException(
            status_code=envelope.http_status,
            detail=envelope.model_dump(mode="json"),
        ) from exc
    except Exception as exc:
        logger.exception("llm_chat.unexpected_error request_id=%s", request_id)
        envelope = _error_envelope(
            request,
            code="unexpected_error",
            message="El turno terminó por un error inesperado.",
            detail="Consulta el estado del turno antes de reenviar la pregunta.",
            category="unexpected",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            retryable=True,
            recovery_action="poll_turn",
            request_id=request_id,
        )
        raise HTTPException(
            status_code=envelope.http_status,
            detail=envelope.model_dump(mode="json"),
        ) from exc
    if result.safety_action is SafetyAction.TECHNICAL_ERROR:
        envelope = _error_envelope(
            request,
            code=ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value,
            message="El asistente está temporalmente no disponible.",
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            retryable=True,
            recovery_action="retry_same_turn",
            request_id=request_id,
            category="provider",
            retry_after_ms=1000,
        )
        raise HTTPException(
            status_code=envelope.http_status,
            detail=envelope.model_dump(mode="json"),
        )
    return cast(ChatResponse, result.validated_response)


@router.post("/stream", response_class=StreamingResponse)
async def stream_chat(
    request: ChatRequest,
    http_request: Request,
    user_id: str = Depends(get_current_user_id),
    use_case=Depends(get_send_chat_use_case),
) -> StreamingResponse:
    request_id = str(uuid4())
    # Validate the ephemeral browser boundary before committing SSE headers.
    # Otherwise a malformed identifier would surface as a truncated stream
    # instead of the normal typed HTTP validation response.
    browser_session_hash = _browser_session_hash(http_request)

    async def events() -> AsyncIterator[str]:
        identity: dict[str, object] = {
            "request_id": request_id,
            "client_message_id": str(request.client_message_id),
        }
        if request.conversation_id is not None:
            identity["conversation_id"] = str(request.conversation_id)
        sequence = 0
        terminal_emitted = False
        disconnected = False

        def event_payload(data: dict[str, object]) -> dict[str, object]:
            """Normalize every public SSE event at the HTTP trust boundary."""

            nonlocal sequence
            for key in ("conversation_id", "turn_id", "attempt", "context_revision"):
                value = data.get(key)
                if value is not None:
                    identity[key] = value
            normalized = dict(data)
            for key, value in identity.items():
                if normalized.get(key) is None:
                    normalized[key] = value
            sequence += 1
            normalized["sequence"] = sequence
            return normalized

        def terminal_error(envelope: ChatErrorEnvelope) -> dict[str, object]:
            return event_payload(envelope.model_dump(mode="json", exclude_none=True))

        command = _command(
            request,
            user_id,
            _auth_session_id(http_request, user_id),
            browser_session_hash,
            request_id,
        )
        # SendChatMessageUseCase.stream() is the single SSE producer: it
        # relays the same status-event lifecycle _run() emits internally
        # (start/context_ready/retrieval_completed/generation_started/...),
        # then appends the terminal final/done pair once the same commit
        # that REST reads from has already succeeded. There is exactly one
        # SSE protocol; no buffered-execute-then-fabricate-events fallback.
        stream = use_case.stream(command)
        try:
            async for event, data in stream:
                if await http_request.is_disconnected():
                    disconnected = True
                    break
                if event == "error":
                    data = _public_stream_error(data)
                yield encode_sse(event, event_payload(data))
                if event in {"done", "error"}:
                    terminal_emitted = True
                    break
        except ChatResourceNotFound:
            terminal_emitted = True
            yield encode_sse(
                "error",
                terminal_error(_resource_envelope(request, request_id=request_id)),
            )
        except ChatRuntimeUnavailable as exc:
            terminal_emitted = True
            yield encode_sse(
                "error",
                terminal_error(
                    _runtime_envelope(request, exc, request_id=request_id)
                ),
            )
        except (
            ChatContextRevisionConflict,
            ChatTurnInProgress,
            ChatIdempotencyConflict,
            ChatTurnConcurrencyConflict,
        ) as exc:
            terminal_emitted = True
            yield encode_sse(
                "error",
                terminal_error(
                    _conflict_envelope(request, exc, request_id=request_id)
                ),
            )
        except ChatPersistenceError:
            logger.exception(
                "llm_chat.stream_persistence_error request_id=%s", request_id
            )
            envelope = _error_envelope(
                request,
                code="persistence_error",
                message="No se pudo guardar el estado del turno de forma segura.",
                detail="Consulta el estado antes de volver a enviar la pregunta.",
                category="persistence",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                retryable=True,
                recovery_action="poll_turn",
                request_id=request_id,
                conversation_id=str(identity.get("conversation_id") or "") or None,
                turn_id=str(identity.get("turn_id") or "") or None,
                attempt=(
                    int(identity["attempt"])
                    if isinstance(identity.get("attempt"), int)
                    else None
                ),
            )
            terminal_emitted = True
            yield encode_sse("error", terminal_error(envelope))
        except Exception:
            logger.exception(
                "llm_chat.stream_unhandled_error request_id=%s", request_id
            )
            envelope = _error_envelope(
                request,
                code="stream_processing_error",
                message="El flujo terminó por un error inesperado. Puedes consultar el estado del turno.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                retryable=True,
                recovery_action="poll_turn",
                request_id=request_id,
                category="unexpected",
                retry_after_ms=500,
                conversation_id=str(identity.get("conversation_id") or "") or None,
                turn_id=str(identity.get("turn_id") or "") or None,
                attempt=(
                    int(identity["attempt"])
                    if isinstance(identity.get("attempt"), int)
                    else None
                ),
            )
            terminal_emitted = True
            yield encode_sse("error", terminal_error(envelope))
        finally:
            closer = getattr(stream, "aclose", None)
            if closer is not None:
                await closer()
        if not terminal_emitted and not disconnected:
            envelope = _error_envelope(
                request,
                code="stream_incomplete",
                message="El flujo terminó sin un evento final verificable.",
                detail="Consulta el estado del turno antes de reenviar la pregunta.",
                category="transport",
                http_status=status.HTTP_502_BAD_GATEWAY,
                retryable=True,
                recovery_action="poll_turn",
                request_id=request_id,
                conversation_id=str(identity.get("conversation_id") or "") or None,
                turn_id=str(identity.get("turn_id") or "") or None,
                attempt=(
                    int(identity["attempt"])
                    if isinstance(identity.get("attempt"), int)
                    else None
                ),
            )
            yield encode_sse("error", terminal_error(envelope))
        return

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationHistoryResponse,
)
async def conversation_messages(
    conversation_id: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    conversations=Depends(get_conversation_repository),
) -> ConversationHistoryResponse:
    try:
        records = await conversations.history(
            conversation_id,
            user_id,
            limit=limit,
            offset=offset,
            auth_session_id=_auth_session_id(request, user_id),
            browser_session_hash=_browser_session_hash(request),
        )
    except ChatResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La conversación solicitada no está disponible.",
        ) from exc
    return ConversationHistoryResponse(
        items=[
            ConversationMessageResponse(
                id=record.id,
                role=record.role,
                content=(
                    enforce_assistant_identity(record.content)
                    if record.role == "assistant"
                    else record.content
                ),
                status=record.status,
                created_at=record.created_at,
                context=dict(record.metadata.get("context") or {}),
            )
            for record in records
        ],
        limit=limit,
        offset=offset,
    )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    body: ConversationCreateRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    conversations=Depends(get_conversation_repository),
    analysis_context=Depends(get_analysis_context_repository),
) -> ConversationResponse:
    mode = _canonical_scope(body.context_scope)
    try:
        clinical = await analysis_context.get_owned_context(
            context_scope=mode,
            user_id=user_id,
            analysis_id=body.analysis_id,
            pet_id=body.pet_id,
        )
        conversation_id = await conversations.get_or_create(
            None,
            user_id,
            auth_session_id=_auth_session_id(request, user_id),
            browser_session_hash=_browser_session_hash(request),
            context_scope=clinical.mode,
            pet_id=clinical.pet_id,
            analysis_id=clinical.analysis_id,
            context_fingerprint=clinical_context_fingerprint(clinical),
            force_new=True,
        )
        rows = await conversations.list_active(
            user_id,
            _auth_session_id(request, user_id),
            _browser_session_hash(request),
        )
    except ChatResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El contexto solicitado no está disponible.",
        ) from exc
    row = next(item for item in rows if item["id"] == conversation_id)
    return ConversationResponse(**row)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    conversations=Depends(get_conversation_repository),
) -> ConversationListResponse:
    rows = await conversations.list_active(
        user_id,
        _auth_session_id(request, user_id),
        _browser_session_hash(request),
    )
    return ConversationListResponse(items=[ConversationResponse(**row) for row in rows])


@router.get(
    "/conversations/{conversation_id}/turns",
    response_model=ConversationTurnListResponse,
)
async def conversation_turns(
    conversation_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
    conversations=Depends(get_conversation_repository),
) -> ConversationTurnListResponse:
    try:
        rows = await conversations.turn_history(
            conversation_id,
            user_id,
            limit=limit,
            offset=offset,
            auth_session_id=_auth_session_id(request, user_id),
            browser_session_hash=_browser_session_hash(request),
        )
    except ChatResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La conversación solicitada no está disponible.",
        ) from exc
    return ConversationTurnListResponse(
        items=[
            ConversationTurnResponse(
                turn_id=row.get("turn_id"),
                conversation_id=row["conversation_id"],
                client_message_id=row["client_message_id"],
                context_revision=row["context_revision"],
                turn_index=row["turn_index"],
                status=row["status"],
                attempt=row["attempt"],
                retryable=row["retryable"],
                state=_public_turn_state(
                    row["status"],
                    row["retryable"],
                    row.get("processing_stage"),
                    row.get("error_code"),
                ),
                processing_stage=row.get("processing_stage"),
                error_code=_public_persisted_error_code(row["error_code"]),
                user_message=ConversationTurnMessageResponse(
                    id=row["user_message"].id,
                    content=row["user_message"].content,
                    status=row["user_message"].status,
                    created_at=row["user_message"].created_at,
                ),
                response=(
                    _response(row["response"]) if row["response"] is not None else None
                ),
                updated_at=row["updated_at"],
            )
            for row in rows
        ],
        limit=limit,
        offset=offset,
    )


@router.post(
    "/conversations/{conversation_id}/turns/{client_message_id}/cancel",
    response_model=TurnStatusResponse,
)
async def cancel_conversation_turn(
    conversation_id: str,
    client_message_id: str,
    body: CancelTurnRequest,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    conversations=Depends(get_conversation_repository),
) -> TurnStatusResponse:
    try:
        await conversations.mark_owned_turn_interrupted(
            user_id,
            client_message_id,
            auth_session_id=_auth_session_id(request, user_id),
            browser_session_hash=_browser_session_hash(request),
            conversation_id=conversation_id,
            expected_attempt=body.attempt,
            error_code="client_cancelled",
        )
        snapshot = await conversations.turn_status(
            conversation_id,
            client_message_id,
            user_id,
            auth_session_id=_auth_session_id(request, user_id),
            browser_session_hash=_browser_session_hash(request),
        )
    except ChatResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El turno solicitado no está disponible.",
        ) from exc
    return TurnStatusResponse(
        turn_id=snapshot.turn_id,
        conversation_id=snapshot.conversation_id,
        client_message_id=snapshot.client_message_id,
        status=snapshot.status,
        attempt=snapshot.attempt,
        retryable=snapshot.retryable,
        state=_public_turn_state(
            snapshot.status,
            snapshot.retryable,
            snapshot.processing_stage,
            snapshot.error_code,
        ),
        processing_stage=snapshot.processing_stage,
        error_code=_public_persisted_error_code(snapshot.error_code),
        response=(
            _response(snapshot.response) if snapshot.response is not None else None
        ),
    )


@router.get(
    "/conversations/{conversation_id}/turns/{client_message_id}",
    response_model=TurnStatusResponse,
)
async def conversation_turn_status(
    conversation_id: str,
    client_message_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    conversations=Depends(get_conversation_repository),
) -> TurnStatusResponse:
    try:
        snapshot = await conversations.turn_status(
            conversation_id,
            client_message_id,
            user_id,
            auth_session_id=_auth_session_id(request, user_id),
            browser_session_hash=_browser_session_hash(request),
        )
    except ChatResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El turno solicitado no está disponible.",
        ) from exc
    return TurnStatusResponse(
        turn_id=snapshot.turn_id,
        conversation_id=snapshot.conversation_id,
        client_message_id=snapshot.client_message_id,
        status=snapshot.status,
        attempt=snapshot.attempt,
        retryable=snapshot.retryable,
        state=_public_turn_state(
            snapshot.status,
            snapshot.retryable,
            snapshot.processing_stage,
            snapshot.error_code,
        ),
        processing_stage=snapshot.processing_stage,
        error_code=_public_persisted_error_code(snapshot.error_code),
        response=(
            _response(snapshot.response) if snapshot.response is not None else None
        ),
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    conversations=Depends(get_conversation_repository),
) -> Response:
    try:
        await conversations.delete_owned(
            conversation_id,
            user_id,
            _auth_session_id(request, user_id),
            _browser_session_hash(request),
        )
    except ChatResourceNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La conversación solicitada no está disponible.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _auth_session_id(request: Request, user_id: str) -> str:
    return str(getattr(request.state, "auth_session_id", None) or f"legacy-{user_id}")[
        :36
    ]


def _browser_session_hash(request: Request) -> str | None:
    raw = str(request.headers.get("X-HemoVet-Browser-Session-ID") or "").strip()
    if not raw:
        if settings.CHAT_REQUIRE_BROWSER_SESSION_ID:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="X-HemoVet-Browser-Session-ID is required.",
            )
        return None
    try:
        parsed = UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-HemoVet-Browser-Session-ID must be a UUID.",
        ) from exc
    if parsed.version != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="X-HemoVet-Browser-Session-ID must be a UUIDv4.",
        )
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        str(parsed).encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def _canonical_scope(scope: str) -> str:
    return {
        "uploaded_analysis": "selected_hemogram",
        "historical_analysis": "hemogram_history",
    }.get(scope, scope)
