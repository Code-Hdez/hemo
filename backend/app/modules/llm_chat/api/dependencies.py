from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status

from app.modules.llm_chat.domain.ports import ConversationRepository
from app.modules.llm_chat.domain.provider_contract import ProviderFailureCode


async def get_chat_container(request: Request) -> Any:
    container = getattr(request.app.state, "llm_chat", None)
    if container is None:
        request_id = str(uuid4())
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value,
                "message": "El asistente está temporalmente no disponible.",
                "detail": "La aplicación principal continúa disponible.",
                "category": "provider",
                "retryable": True,
                "recovery_action": "retry_same_turn",
                "request_id": request_id,
                "client_message_id": "unknown",
                "retry_after_ms": 2000,
                "http_status": status.HTTP_503_SERVICE_UNAVAILABLE,
            },
        )
    return container


async def get_send_chat_use_case(container: Any = Depends(get_chat_container)) -> Any:
    # Etapa 8, Block B: fail closed before generation using the same
    # canonical availability authority /chat/health reports, read from a
    # short-lived cache rather than a second per-turn identity probe. A RAG
    # outage never reaches this branch — chat_ready is independent of it.
    ready, code = await container.cached_chat_readiness()
    if not ready:
        request_id = str(uuid4())
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": code or ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value,
                "message": "El asistente está temporalmente no disponible.",
                "detail": "Consulta el estado del proveedor antes de reintentar.",
                "category": "provider",
                "retryable": True,
                "recovery_action": "retry_same_turn",
                "request_id": request_id,
                "client_message_id": "unknown",
                "retry_after_ms": 2000,
                "http_status": status.HTTP_503_SERVICE_UNAVAILABLE,
            },
        )
    return container.send_chat


async def get_conversation_repository(
    container: Any = Depends(get_chat_container),
) -> ConversationRepository:
    return container.conversations


async def get_analysis_context_repository(
    container: Any = Depends(get_chat_container),
) -> Any:
    return getattr(container, "analysis_context", container.send_chat.analysis_context)
