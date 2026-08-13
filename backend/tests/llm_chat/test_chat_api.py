from __future__ import annotations

import asyncio
import json
from dataclasses import replace as dataclass_replace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.core.security import create_access_token
from app.dependencies.auth import get_current_user_id
from app.modules.llm_chat.api.dependencies import get_send_chat_use_case
from app.modules.llm_chat.api.dependencies import get_conversation_repository
from app.modules.llm_chat.api.router import _public_route_trace, router
from app.modules.llm_chat.api.schemas import ChatRequest, chat_response_from_result
from app.modules.llm_chat.application.dto import ChatResult
from app.modules.llm_chat.domain.entities import (
    ChatTurnSnapshot,
    ChatMessageRecord,
    RetrievedChunk,
    TokenUsage,
)
from app.modules.llm_chat.domain.exceptions import ChatResourceNotFound
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.value_objects import SafetyAction


def _with_validated_response(result: ChatResult) -> ChatResult:
    """Mirror SendChatMessageUseCase._with_validated_public_response for fakes.

    Etapa 8, Block A/E: router.chat() now returns ``result.validated_response``
    directly instead of building it after the fact — the use case is the
    single place that materializes and validates the public contract, before
    persistence. Any fake standing in for the use case must populate it the
    same way, or the router has nothing to return.
    """

    return dataclass_replace(result, validated_response=chat_response_from_result(result))


class FakeSendChat:
    async def execute(self, command):
        assert command.user_id == "user-1"
        result = ChatResult(
            conversation_id=command.conversation_id or str(uuid4()),
            turn_id=str(uuid4()),
            message_id=str(uuid4()),
            answer="Respuesta educativa.",
            scope=command.context_scope,
            case_facts=[{"parameter": "WBC", "value": "10.4"}],
            sources=[
                RetrievedChunk(
                    id="chunk-1",
                    text="Texto interno no expuesto en source schema",
                    source_id="source-1",
                    title="Fuente",
                    heading_path="Plaquetas",
                    source_path="test.md",
                    score=0.82,
                )
            ],
            warnings=["Advertencia"],
            safety_action=SafetyAction.ALLOW,
            model="qwen3:4b",
            usage=TokenUsage(prompt_tokens=20, completion_tokens=5),
            duration_ms=15,
            finish_reason="stop",
        )
        return _with_validated_response(result)


class DeterministicBoundarySendChat:
    """Mirrors what send_chat_message.py's general-scope deterministic_
    boundary short circuit actually persists (response_origin=
    "deterministic_safety_boundary") — confirmed live in production
    (2026-08-04): every such answer crashed with a raw, code-less HTTP 500
    at response serialization (router._response -> ChatResponse Pydantic
    model), because that literal was never added to response_origin's
    Literal type. That crash happens outside chat()'s try/except, so it
    never got the JSON error envelope other failures get.
    """

    async def execute(self, command):
        result = ChatResult(
            conversation_id=command.conversation_id or str(uuid4()),
            turn_id=str(uuid4()),
            message_id=str(uuid4()),
            answer=(
                "Esta consulta queda fuera del ámbito de HemoVet. Puedo "
                "ayudarte con hemogramas caninos y hematología veterinaria."
            ),
            scope=command.context_scope,
            case_facts=[],
            sources=[],
            warnings=[],
            safety_action=SafetyAction.REFUSE_OUT_OF_SCOPE,
            model=None,
            usage=TokenUsage(),
            duration_ms=0,
            finish_reason="deterministic_boundary",
            llm_invoked=False,
            response_origin="deterministic_safety_boundary",
        )
        return _with_validated_response(result)


class FakeConversations:
    last_history_browser_session_hash: str | None = None
    last_turn_history_browser_session_hash: str | None = None

    def __init__(self) -> None:
        self.cancelled_attempt: int | None = None

    async def history(
        self,
        conversation_id,
        user_id,
        *,
        limit,
        offset,
        auth_session_id=None,
        browser_session_hash=None,
    ):
        type(self).last_history_browser_session_hash = browser_session_hash
        if conversation_id == "not-owned":
            raise ChatResourceNotFound
        assert conversation_id == "conversation-1"
        assert user_id == "user-1"
        assert (limit, offset) == (20, 0)
        return [
            ChatMessageRecord(
                id="message-1",
                conversation_id=conversation_id,
                client_message_id="client-1",
                role="assistant",
                content="Respuesta guardada.",
                status="completed",
            )
        ]

    async def turn_status(self, conversation_id, client_message_id, user_id, **_kwargs):
        assert (conversation_id, client_message_id, user_id) == (
            "conversation-1",
            "client-1",
            "user-1",
        )
        result = await FakeSendChat().execute(
            type(
                "Command",
                (),
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "context_scope": "general",
                },
            )()
        )
        return ChatTurnSnapshot(
            conversation_id=conversation_id,
            client_message_id=client_message_id,
            status="interrupted" if self.cancelled_attempt is not None else "completed",
            attempt=2,
            retryable=self.cancelled_attempt is not None,
            error_code="client_cancelled" if self.cancelled_attempt is not None else None,
            response=None if self.cancelled_attempt is not None else result,
        )

    async def turn_history(
        self,
        conversation_id,
        user_id,
        *,
        limit,
        offset,
        auth_session_id,
        browser_session_hash=None,
    ):
        type(self).last_turn_history_browser_session_hash = browser_session_hash
        assert (conversation_id, user_id, limit, offset) == (
            "conversation-1",
            "user-1",
            100,
            0,
        )
        result = await FakeSendChat().execute(
            type(
                "Command",
                (),
                {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "context_scope": "general",
                },
            )()
        )
        return [
            {
                "conversation_id": conversation_id,
                "client_message_id": "client-1",
                "context_revision": 1,
                "turn_index": 1,
                "status": "completed",
                "attempt": 2,
                "retryable": False,
                "error_code": None,
                "user_message": ChatMessageRecord(
                    id="user-message-1",
                    conversation_id=conversation_id,
                    client_message_id="client-1",
                    role="user",
                    content="¿Qué son las plaquetas?",
                    status="completed",
                ),
                "response": result,
                "updated_at": None,
            }
        ]

    async def mark_owned_turn_interrupted(
        self,
        user_id,
        client_message_id,
        *,
        auth_session_id,
        browser_session_hash=None,
        conversation_id,
        expected_attempt,
        error_code,
    ):
        assert (user_id, client_message_id, conversation_id, error_code) == (
            "user-1",
            "client-1",
            "conversation-1",
            "client_cancelled",
        )
        self.cancelled_attempt = expected_attempt
        return True


class FailingSendChat:
    async def execute(self, command):
        raise ChatRuntimeUnavailable(
            "provider_timeout",
            conversation_id=command.conversation_id,
            attempt=2 if command.conversation_id else None,
        )

    async def stream(self, command):
        # Etapa 8, Block E: stream_chat() always drives use_case.stream() now
        # ("no buffered-execute-then-fabricate-events fallback" — router.py),
        # so a fake simulating an immediate provider failure must raise from
        # its own async generator instead of relying on execute() being
        # called. Raises before any yield, so this is reported at sequence 1.
        raise ChatRuntimeUnavailable(
            "provider_timeout",
            conversation_id=command.conversation_id,
            attempt=2 if command.conversation_id else None,
        )
        yield  # pragma: no cover - unreachable, keeps this an async generator


class ProviderAbsentSendChat:
    async def execute(self, command):
        raise ChatRuntimeUnavailable(
            "ollama_unavailable",
            conversation_id=command.conversation_id,
            attempt=1,
        )


class TechnicalErrorSendChat:
    async def execute(self, command):
        return ChatResult(
            conversation_id=command.conversation_id or str(uuid4()),
            message_id=str(uuid4()),
            answer=(
                "El asistente no pudo completar la respuesta por un problema técnico. "
                "Intenta de nuevo."
            ),
            scope=command.context_scope,
            case_facts=[],
            sources=[],
            warnings=[],
            safety_action=SafetyAction.TECHNICAL_ERROR,
            model="qwen3:4b",
            usage=TokenUsage(prompt_tokens=20, completion_tokens=0),
            duration_ms=15,
            finish_reason="blocked_empty_output",
        )

    async def stream(self, command):
        result = await self.execute(command)
        yield (
            "error",
            {
                "code": "technical_error",
                "message": "Ollama no respondió.",
                "detail": "Ollama no respondió.",
                "category": "provider",
                "retryable": True,
                "recovery_action": "retry_same_turn",
                "http_status": 503,
                "conversation_id": result.conversation_id,
            },
        )


class StreamingSendChat:
    async def stream(self, command):
        assert command.user_id == "user-1"
        conversation_id = command.conversation_id or str(uuid4())
        turn_id = str(uuid4())
        trace = {
            "request_id": command.request_id,
            "conversation_id": conversation_id,
            "turn_id": turn_id,
            "client_message_id": command.client_message_id,
            "attempt": 1,
            "context_revision": 1,
        }
        yield ("turn", {**trace, "status": "processing"})
        yield ("status", {**trace, "stage": "validating"})
        yield ("status", {**trace, "stage": "generating"})
        yield ("delta", {**trace, "text": "Respuesta "})
        yield ("delta", {**trace, "text": "educativa."})
        yield (
            "done",
            {
                **trace,
                "message_id": str(uuid4()),
                "answer": "Respuesta educativa.",
                "scope": command.context_scope,
                "case_facts": [],
                "sources": [],
                "warnings": ["Advertencia"],
                "safety_action": SafetyAction.ALLOW.value,
                "model": "qwen3:4b",
                "usage": {"prompt_tokens": 20, "completion_tokens": 5},
                "duration_ms": 15,
                "finish_reason": "stop",
                "state": "completed",
                "processing_stage": "completed",
                # Etapa 8, Block E/F: the real use case's "done"/"final" SSE
                # payload is built from ChatResult.validated_payload — the
                # same chat_response_from_result() output REST returns, which
                # already applies PUBLIC_ROUTE_TRACE_KEYS. router.py's own
                # _public_route_trace() is unused dead code on this path now
                # (kept only so this module's import of it stays valid — see
                # f9875de5); a use-case fake must hand the router pre-filtered
                # data, matching what a real turn actually produces.
                "route_trace": {"primary_intent": "greeting"},
            },
        )


class IncompleteStreamingSendChat:
    async def stream(self, command):
        trace = {
            "request_id": command.request_id,
            "conversation_id": command.conversation_id or str(uuid4()),
            "turn_id": str(uuid4()),
            "client_message_id": command.client_message_id,
            "attempt": 1,
        }
        yield ("turn", {**trace, "status": "processing"})
        yield ("status", {**trace, "stage": "generating"})


class FailingStreamingSendChat:
    async def stream(self, command):
        conversation_id = command.conversation_id or str(uuid4())
        trace = {
            "request_id": command.request_id,
            "conversation_id": conversation_id,
            "turn_id": str(uuid4()),
            "client_message_id": command.client_message_id,
            "attempt": 2,
        }
        yield ("turn", {**trace, "status": "processing"})
        raise ChatRuntimeUnavailable(
            "provider_timeout",
            conversation_id=conversation_id,
            attempt=2,
        )


def build_app(
    *,
    authenticated: bool,
    failing_chat: bool = False,
    technical_chat: bool = False,
    streaming_chat: bool = False,
    incomplete_stream: bool = False,
    failing_stream: bool = False,
    deterministic_boundary_chat: bool = False,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def fake_use_case():
        if incomplete_stream:
            return IncompleteStreamingSendChat()
        if failing_stream:
            return FailingStreamingSendChat()
        if streaming_chat:
            return StreamingSendChat()
        if failing_chat:
            return FailingSendChat()
        if technical_chat:
            return TechnicalErrorSendChat()
        if deterministic_boundary_chat:
            return DeterministicBoundarySendChat()
        return FakeSendChat()

    async def fake_conversations() -> FakeConversations:
        return FakeConversations()

    app.dependency_overrides[get_send_chat_use_case] = fake_use_case
    app.dependency_overrides[get_conversation_repository] = fake_conversations
    if authenticated:
        async def fake_user() -> str:
            return "user-1"

        app.dependency_overrides[get_current_user_id] = fake_user
    return app


def build_provider_absent_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    class DegradedContainer:
        send_chat = ProviderAbsentSendChat()
        conversations = FakeConversations()

        async def health(self) -> dict[str, object]:
            return {
                "contract_version": "hemovet.availability/v1",
                "probe": "chat_availability",
                "status": "degraded",
                "chat_ready": False,
                "module_ready": True,
                "provider_ready": False,
                "llm_ready": False,
                "rag_required": True,
                "rag_ready": True,
                "chroma_ready": True,
                "collection_ready": True,
                "codes": ["LLM_PROVIDER_UNAVAILABLE"],
                "provider": {
                    "contract_version": "hemovet.availability/v1",
                    "probe": "provider_availability",
                    "status": "unavailable",
                    "provider": "ollama",
                    "model": "qwen3:4b",
                    "ready": False,
                    "code": "LLM_PROVIDER_UNAVAILABLE",
                    "retryable": True,
                    "identity_verified": None,
                },
                "rag": {
                    "contract_version": "hemovet.availability/v1",
                    "probe": "rag_availability",
                    "status": "ready",
                    "required": True,
                    "ready": True,
                    "chroma_ready": True,
                    "collection_ready": True,
                    "index_ready": True,
                    "codes": [],
                },
            }

        async def cached_chat_readiness(self) -> tuple[bool, str | None]:
            # Etapa 8, Block B: get_send_chat_use_case() fails closed on this
            # before generation now (api/dependencies.py), reading it from
            # the same authority /chat/health reports rather than a second
            # per-turn probe. Mirrors ChatContainer.cached_chat_readiness
            # (composition.py) by deriving from this fake's own health().
            payload = await self.health()
            ready = bool(payload.get("chat_ready"))
            code = None
            if not ready:
                provider = payload.get("provider")
                code = provider.get("code") if isinstance(provider, dict) else None
            return ready, code

    app.state.llm_chat = DegradedContainer()

    async def fake_user() -> str:
        return "user-1"

    app.dependency_overrides[get_current_user_id] = fake_user
    return app


async def post(
    app: FastAPI,
    path: str,
    payload: dict[str, object],
    *,
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies=cookies,
    ) as client:
        return await client.post(path, json=payload, headers=headers)


async def get(
    app: FastAPI,
    path: str,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, headers=headers)


def payload() -> dict[str, object]:
    return {
        "client_message_id": str(uuid4()),
        "conversation_id": None,
        "message": "¿Qué son las plaquetas?",
        "context_scope": "general",
        "analysis_id": None,
        # Etapa 7: ChatOptions.thinking was removed entirely and the model
        # now forbids unknown fields (api/schemas.py) — a "thinking" key
        # here would 422 the request before it ever reaches the handler.
        "options": {},
    }


def parse_sse(response: httpx.Response) -> list[tuple[str, dict[str, object]]]:
    parsed: list[tuple[str, dict[str, object]]] = []
    for block in response.text.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = json.loads(
            next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        )
        parsed.append((event, data))
    return parsed


def assert_stream_contract(
    events: list[tuple[str, dict[str, object]]],
    *,
    client_message_id: str,
) -> None:
    assert events
    assert events[-1][0] in {"done", "error"}
    assert [data["sequence"] for _, data in events] == list(range(1, len(events) + 1))
    request_ids = {data["request_id"] for _, data in events}
    assert len(request_ids) == 1
    assert all(data["client_message_id"] == client_message_id for _, data in events)
    turn = next((data for event, data in events if event == "turn"), None)
    if turn is not None:
        for _, data in events:
            assert data["conversation_id"] == turn["conversation_id"]
            assert data["turn_id"] == turn["turn_id"]
            assert data["attempt"] == turn["attempt"]


def test_server_ignores_client_thinking_option() -> None:
    """Etapa 7: thinking is no longer a client-controlled option at all.

    ChatOptions dropped the field and now forbids unknown keys (extra=
    "forbid"), and ChatCommand has no ``thinking`` attribute for _command()
    to populate — the qualified generation profile fixes it server-side.
    A client sending "thinking" is rejected outright rather than silently
    ignored.
    """
    with pytest.raises(ValidationError):
        ChatRequest(
            client_message_id=uuid4(),
            conversation_id=None,
            message="¿Qué son las plaquetas?",
            context_scope="general",
            analysis_id=None,
            options={"thinking": True},
        )


def test_chat_requires_authentication() -> None:
    response = asyncio.run(
        post(build_app(authenticated=False), "/api/v1/chat", payload())
    )

    assert response.status_code == 401


def test_chat_rejects_malformed_ephemeral_browser_session_id() -> None:
    response = asyncio.run(
        post(
            build_app(authenticated=True),
            "/api/v1/chat",
            payload(),
            headers={"X-HemoVet-Browser-Session-ID": "not-a-uuid"},
        )
    )

    assert response.status_code == 422


def test_chat_requires_ephemeral_browser_session_when_enabled(monkeypatch) -> None:
    from app.modules.llm_chat.api import router as chat_router

    monkeypatch.setattr(chat_router.settings, "CHAT_REQUIRE_BROWSER_SESSION_ID", True)

    response = asyncio.run(
        post(build_app(authenticated=True), "/api/v1/chat", payload())
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "X-HemoVet-Browser-Session-ID is required."
    )


def test_stream_accepts_http_only_session_cookie() -> None:
    response = asyncio.run(
        post(
            # Etapa 8, Block E: stream_chat() always drives use_case.stream()
            # now (no buffered-execute fallback), so the fake must implement
            # it too — streaming_chat=True selects StreamingSendChat.
            build_app(authenticated=False, streaming_chat=True),
            "/api/v1/chat/stream",
            payload(),
            cookies={"hemovet_session": create_access_token("user-1")},
        )
    )

    assert response.status_code == 200
    assert "event: done" in response.text


def test_stream_prefers_browser_session_cookie_over_stale_bearer() -> None:
    response = asyncio.run(
        post(
            build_app(authenticated=False, streaming_chat=True),
            "/api/v1/chat/stream",
            payload(),
            cookies={"hemovet_session": create_access_token("user-1")},
            headers={"Authorization": "Bearer token-obsoleto"},
        )
    )

    assert response.status_code == 200


def test_chat_returns_new_public_contract_without_document_text() -> None:
    response = asyncio.run(
        post(build_app(authenticated=True), "/api/v1/chat", payload())
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Respuesta educativa."
    assert body["safety_action"] == "allow"
    assert body["usage"] == {"prompt_tokens": 20, "completion_tokens": 5}
    assert body["case_facts"][0]["parameter"] == "WBC"
    assert body["case_facts"][0]["value"] == "10.4"
    assert body["warnings"] == ["Advertencia"]
    assert body["llm_invoked"] is True
    assert body["response_origin"] == "llm"
    assert body["generation_attempts"] == 1
    assert body["route_trace"] == {}
    assert body["sources"][0] == {
        "citation_id": "S1",
        "display_title": "Fuente",
        "authors": [],
        "edition": None,
        "chapter": None,
        "section": "Plaquetas",
        "page_start": None,
        "page_end": None,
        "source_type": "book",
        # Etapa 5, Block E: source_language was added to ChatSourceResponse
        # so a citation backing a Spanish answer can honestly say it isn't
        # Spanish; the fake source above never sets it, so it serializes null.
        "source_language": None,
    }
    assert "id" not in body["sources"][0]
    assert "source_path" not in body["sources"][0]
    assert "score" not in body["sources"][0]
    assert "text" not in body["sources"][0]


def test_deterministic_boundary_response_origin_serializes_without_500() -> None:
    """Regression test confirmed live against production (2026-08-04): a
    misclassified general-scope message ("Cual es la capital de Francia?",
    parsed as a value request by the intent classifier, then routed to the
    out-of-scope deterministic boundary) reliably returned a raw, code-less
    HTTP 500 "Internal Server Error" — not the normal JSON error envelope.

    Root cause: send_chat_message.py's deterministic_boundary short circuit
    persists response_origin="deterministic_safety_boundary", a literal
    that was never added to ChatResponse.response_origin's Literal type
    (api/schemas.py) or to the ResponseOrigin enum. router._response()
    builds ChatResponse(**...) AFTER chat()'s try/except block, so the
    resulting pydantic.ValidationError escaped every handler in that
    function and fell through to FastAPI's bare default 500.
    """
    response = asyncio.run(
        post(
            build_app(authenticated=True, deterministic_boundary_chat=True),
            "/api/v1/chat",
            payload(),
        )
    )

    assert response.status_code == 200
    body = response.json()
    # Etapa 8, Block A: the fix landed as a normalization, not a new Literal
    # member — ChatResponse.response_origin admits only "llm" or "legacy"
    # now, and a field_validator maps any pre-etapa-8 literal (including
    # "deterministic_safety_boundary") to "legacy" before validation, so it
    # serializes instead of raising. See schemas.py's ChatResponse docstring.
    assert body["response_origin"] == "legacy"
    assert body["safety_action"] == "refuse_out_of_scope"
    assert body["llm_invoked"] is False


def test_public_route_trace_excludes_internal_fact_claim_and_chunk_ids() -> None:
    trace = _public_route_trace(
        {
            "request_id": "request-1",
            "primary_intent": "selected_value",
            "retrieved_candidates_count": 8,
            "verified_fact_ids": ["fact_private_1"],
            "claim_ids": ["claim_internal_1"],
            "retrieved_chunk_ids": ["book_internal_chunk_1"],
            "retrieval_scores": [0.98],
            "studies_used": ["analysis-private-1"],
        }
    )

    assert trace == {
        "request_id": "request-1",
        "primary_intent": "selected_value",
        "retrieved_candidates_count": 8,
    }


def test_stream_emits_status_before_validated_delta_and_done() -> None:
    request_payload = payload()
    response = asyncio.run(
        post(
            # Etapa 8, Block E: stream_chat() always drives use_case.stream()
            # now (no buffered-execute fallback) — needs a fake that
            # implements it, hence streaming_chat=True (StreamingSendChat).
            build_app(authenticated=True, streaming_chat=True),
            "/api/v1/chat/stream",
            request_payload,
        )
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"
    events = parse_sse(response)
    assert_stream_contract(
        events,
        client_message_id=str(request_payload["client_message_id"]),
    )
    names = [event for event, _ in events]
    assert names.index("status") < names.index("delta") < names.index("done")
    assert next(data for event, data in events if event == "done")["answer"] == (
        "Respuesta educativa."
    )


def test_stream_forwards_incremental_deltas_from_use_case() -> None:
    request_payload = payload()
    response = asyncio.run(
        post(
            build_app(authenticated=True, streaming_chat=True),
            "/api/v1/chat/stream",
            request_payload,
        )
    )

    assert response.status_code == 200
    events = parse_sse(response)
    assert_stream_contract(
        events,
        client_message_id=str(request_payload["client_message_id"]),
    )
    deltas = [data["text"] for event, data in events if event == "delta"]
    assert deltas == ["Respuesta ", "educativa."]
    done = next(data for event, data in events if event == "done")
    assert done["route_trace"] == {"primary_intent": "greeting"}


def test_stream_runtime_error_reports_technical_message() -> None:
    request_payload = payload()
    request_payload["conversation_id"] = str(uuid4())
    response = asyncio.run(
        post(
            build_app(authenticated=True, failing_chat=True),
            "/api/v1/chat/stream",
            request_payload,
        )
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    error_event = response.text.split("event: error", maxsplit=1)[1]
    data_line = next(
        line.removeprefix("data: ")
        for line in error_event.splitlines()
        if line.startswith("data: ")
    )
    error = json.loads(data_line)
    assert error == {
        "code": "LLM_PROVIDER_READ_TIMEOUT",
        "message": "El asistente no terminó la respuesta a tiempo. Puedes reintentar esta misma pregunta.",
        "detail": "El asistente no terminó la respuesta a tiempo. Puedes reintentar esta misma pregunta.",
        "category": "timeout",
        "retryable": True,
        "recovery_action": "retry_same_turn",
        "request_id": error["request_id"],
        "client_message_id": request_payload["client_message_id"],
        "conversation_id": request_payload["conversation_id"],
        "attempt": 2,
        "retry_after_ms": 1000,
        "http_status": 504,
        "sequence": 1,
    }
    assert error["request_id"] != error["client_message_id"]
    assert_stream_contract(
        parse_sse(response),
        client_message_id=str(request_payload["client_message_id"]),
    )


def test_stream_error_after_reservation_keeps_turn_identity_and_sequence() -> None:
    request_payload = payload()
    response = asyncio.run(
        post(
            build_app(authenticated=True, failing_stream=True),
            "/api/v1/chat/stream",
            request_payload,
        )
    )

    events = parse_sse(response)
    assert [event for event, _ in events] == ["turn", "error"]
    assert_stream_contract(
        events,
        client_message_id=str(request_payload["client_message_id"]),
    )
    assert events[-1][1]["code"] == "LLM_PROVIDER_READ_TIMEOUT"
    assert events[-1][1]["turn_id"] == events[0][1]["turn_id"]


def test_stream_without_terminal_event_is_closed_with_structured_error() -> None:
    request_payload = payload()
    response = asyncio.run(
        post(
            build_app(authenticated=True, incomplete_stream=True),
            "/api/v1/chat/stream",
            request_payload,
        )
    )

    events = parse_sse(response)
    assert [event for event, _ in events] == ["turn", "status", "error"]
    assert_stream_contract(
        events,
        client_message_id=str(request_payload["client_message_id"]),
    )
    assert events[-1][1]["code"] == "stream_incomplete"
    assert events[-1][1]["recovery_action"] == "poll_turn"


def test_stream_validation_error_is_not_emitted_as_a_normal_answer() -> None:
    response = asyncio.run(
        post(
            build_app(authenticated=True, technical_chat=True),
            "/api/v1/chat/stream",
            payload(),
        )
    )

    assert response.status_code == 200
    events = parse_sse(response)
    assert [event for event, _ in events] == ["error"]
    assert events[0][1]["code"] == "LLM_PROVIDER_UNAVAILABLE"
    assert events[0][1]["message"].startswith("El asistente está temporalmente")
    assert "ollama" not in response.text.casefold()
    assert "event: delta" not in response.text
    assert "event: done" not in response.text


def test_non_stream_validation_error_returns_service_unavailable() -> None:
    response = asyncio.run(
        post(
            build_app(authenticated=True, technical_chat=True),
            "/api/v1/chat",
            payload(),
        )
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["message"] == "El asistente está temporalmente no disponible."
    assert detail["code"] == "LLM_PROVIDER_UNAVAILABLE"
    assert detail["recovery_action"] == "retry_same_turn"


def test_provider_absence_returns_generic_503_but_keeps_history_accessible() -> None:
    app = build_provider_absent_app()
    request_payload = payload()
    request_payload["conversation_id"] = "123e4567-e89b-42d3-a456-426614174000"

    unavailable = asyncio.run(post(app, "/api/v1/chat", request_payload))
    history = asyncio.run(
        get(app, "/api/v1/chat/conversations/conversation-1/messages")
    )

    assert unavailable.status_code == 503
    detail = unavailable.json()["detail"]
    assert detail["code"] == "LLM_PROVIDER_UNAVAILABLE"
    assert detail["retryable"] is True
    assert "ollama" not in detail["message"].casefold()
    assert history.status_code == 200
    assert history.json()["items"][0]["content"] == "Respuesta guardada."


def test_provider_and_rag_health_contracts_are_independent() -> None:
    app = build_provider_absent_app()

    provider = asyncio.run(get(app, "/api/v1/chat/health/provider"))
    rag = asyncio.run(get(app, "/api/v1/chat/health/rag"))

    assert provider.status_code == 200
    assert provider.json()["probe"] == "provider_availability"
    assert provider.json()["ready"] is False
    assert provider.json()["code"] == "LLM_PROVIDER_UNAVAILABLE"
    assert rag.status_code == 200
    assert rag.json()["probe"] == "rag_availability"
    assert rag.json()["ready"] is True


def test_turn_status_returns_canonical_attempt_and_completed_response() -> None:
    response = asyncio.run(
        get(
            build_app(authenticated=True),
            "/api/v1/chat/conversations/conversation-1/turns/client-1",
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["attempt"] == 2
    assert body["retryable"] is False
    assert body["state"] == "completed"
    assert body["response"]["llm_invoked"] is True


def test_conversation_turn_history_returns_canonical_turns_for_reload() -> None:
    response = asyncio.run(
        get(
            build_app(authenticated=True),
            "/api/v1/chat/conversations/conversation-1/turns",
        )
    )

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 100
    assert body["offset"] == 0
    assert body["items"][0]["client_message_id"] == "client-1"
    assert body["items"][0]["user_message"]["content"] == "¿Qué son las plaquetas?"
    assert body["items"][0]["state"] == "completed"
    assert body["items"][0]["response"]["llm_invoked"] is True


def test_conversation_turn_history_propagates_browser_session_hash() -> None:
    browser_session_id = "123e4567-e89b-42d3-a456-426614174000"
    FakeConversations.last_turn_history_browser_session_hash = None

    response = asyncio.run(
        get(
            build_app(authenticated=True),
            "/api/v1/chat/conversations/conversation-1/turns",
            headers={"X-HemoVet-Browser-Session-ID": browser_session_id},
        )
    )

    assert response.status_code == 200
    stored = FakeConversations.last_turn_history_browser_session_hash
    assert stored is not None
    assert len(stored) == 64
    assert browser_session_id not in stored


def test_browser_cancel_marks_the_exact_attempt_as_retryable() -> None:
    response = asyncio.run(
        post(
            build_app(authenticated=True),
            "/api/v1/chat/conversations/conversation-1/turns/client-1/cancel",
            {"attempt": 2},
        )
    )

    assert response.status_code == 200
    assert response.json() == {
        "turn_id": None,
        "conversation_id": "conversation-1",
        "client_message_id": "client-1",
        "status": "interrupted",
        "attempt": 2,
        "retryable": True,
        "state": "cancelled",
        "processing_stage": None,
        "error_code": "client_cancelled",
        "response": None,
    }


def test_conversation_history_requires_owner_and_returns_public_messages() -> None:
    response = asyncio.run(
        get(
            build_app(authenticated=True),
            "/api/v1/chat/conversations/conversation-1/messages",
        )
    )

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "id": "message-1",
            "role": "assistant",
            "content": "Respuesta guardada.",
                "status": "completed",
                "created_at": None,
                "context": {},
            }
    ]


def test_conversation_history_propagates_ephemeral_browser_boundary() -> None:
    browser_session_id = "123e4567-e89b-42d3-a456-426614174000"
    FakeConversations.last_history_browser_session_hash = None

    response = asyncio.run(
        get(
            build_app(authenticated=True),
            "/api/v1/chat/conversations/conversation-1/messages",
            headers={"X-HemoVet-Browser-Session-ID": browser_session_id},
        )
    )

    assert response.status_code == 200
    stored = FakeConversations.last_history_browser_session_hash
    assert stored is not None
    assert len(stored) == 64
    assert browser_session_id not in stored


def test_conversation_history_hides_unowned_resources_as_not_found() -> None:
    response = asyncio.run(
        get(
            build_app(authenticated=True),
            "/api/v1/chat/conversations/not-owned/messages",
        )
    )

    assert response.status_code == 404
