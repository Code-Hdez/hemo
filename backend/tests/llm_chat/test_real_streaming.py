from __future__ import annotations

import dataclasses

import asyncio
from uuid import uuid4

import pytest

from app.core.config import settings as _app_settings
from app.modules.llm_chat.api.schemas import chat_response_from_result
from app.modules.llm_chat.application.dto import ChatCommand
from app.modules.llm_chat.application.services.chat_profile_policy import ChatProfilePolicy
from app.modules.llm_chat.application.services.conversation_memory import ConversationMemoryService
from app.modules.llm_chat.application.services.output_sanitizer import OutputSanitizer
from app.modules.llm_chat.application.services.output_validator import OutputValidator
from app.modules.llm_chat.application.services.prompt_builder import PromptBuilder
from app.modules.llm_chat.application.services.retrieval_service import (
    RetrievalOutcome,
)
from app.modules.llm_chat.application.services.safety_policy import SafetyPolicy
from app.modules.llm_chat.application.services.token_budget import TokenCounter
from app.modules.llm_chat.application.use_cases.send_chat_message import (
    SendChatMessageUseCase,
)
from app.modules.llm_chat.domain.entities import (
    ModelStreamChunk,
    RetrievedChunk,
    TokenUsage,
)
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings

_TEST_CHAT_SETTINGS = dataclasses.replace(
    GenerationProfileSettings.from_settings(_app_settings),
    structured_output_enabled=False,
)


class ConversationStore:
    def __init__(self) -> None:
        self.conversation_id = str(uuid4())
        self.conversation_ids: dict[str, str] = {}
        self.messages = []

    async def get_or_create(
        self,
        conversation_id,
        user_id,
        *,
        auth_session_id=None,
        browser_session_hash=None,
        context_scope="general",
        pet_id=None,
        analysis_id=None,
        context_fingerprint=None,
        force_new=False,
    ):
        if conversation_id:
            return conversation_id
        return self.conversation_ids.setdefault(user_id, str(uuid4()))

    async def get_completed_response(self, conversation_id, client_message_id):
        return None

    async def append(self, message):
        self.messages.append(message)

    async def complete_turn(self, message, *, memory_summary: str, memory_state: dict) -> None:
        self.messages.append(message)

    async def recent(self, conversation_id, limit):
        return [
            message
            for message in self.messages
            if message.conversation_id == conversation_id
        ][-limit:]


class GeneralContext:
    async def get_owned_snapshot(self, analysis_id, user_id):
        return {"facts": []}


class OneSourceRetriever:
    async def retrieve(self, query, **kwargs):
        return RetrievalOutcome(available=True, chunks=[
            RetrievedChunk(
                id="chunk-1",
                text="Las plaquetas participan en la hemostasia.",
                source_id="source-1",
                title="Hematología veterinaria",
                heading_path="Plaquetas",
                source_path="source.md",
                score=0.9,
            )
        ])


class PausingStreamingLLM:
    model_name = "qwen-test"

    def __init__(
        self,
        *,
        first_text: str = "Las plaquetas participan en la hemostasia.",
        second_text: str = " También ayudan a formar el tapón plaquetario.",
    ) -> None:
        self.release = asyncio.Event()
        self.finished = False
        self.cancelled = False
        self.first_text = first_text
        self.second_text = second_text

    async def stream(self, request):
        try:
            yield ModelStreamChunk(
                text=self.first_text,
                model=self.model_name,
            )
            await self.release.wait()
            yield ModelStreamChunk(
                text=self.second_text,
                model=self.model_name,
            )
            yield ModelStreamChunk(
                text="\n[[EVIDENCE_USED:S1]]",
                model=self.model_name,
            )
            self.finished = True
            yield ModelStreamChunk(
                done=True,
                model=self.model_name,
                usage=TokenUsage(prompt_tokens=20, completion_tokens=14),
                duration_ms=25,
                finish_reason="stop",
            )
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class MultiplexStreamingLLM:
    model_name = "qwen-test"

    async def stream(self, request):
        name = "Luna" if "Luna" in request.user_prompt else "Toby"
        yield ModelStreamChunk(text=f"Respuesta para {name}. ", model=self.model_name)
        await asyncio.sleep(0)
        yield ModelStreamChunk(
            text="Es exclusivamente educativa.\n[[EVIDENCE_USED:S1]]",
            model=self.model_name,
        )
        yield ModelStreamChunk(
            done=True,
            model=self.model_name,
            usage=TokenUsage(prompt_tokens=20, completion_tokens=8),
            duration_ms=10,
        )


def build_streaming_use_case(llm: PausingStreamingLLM) -> SendChatMessageUseCase:
    return SendChatMessageUseCase(
        conversations=ConversationStore(),
        analysis_context=GeneralContext(),
        retriever=OneSourceRetriever(),
        llm=llm,
        safety=SafetyPolicy(),
        prompts=PromptBuilder(token_counter=TokenCounter()),
        output_sanitizer=OutputSanitizer(),
        output_validator=OutputValidator(),
        generation_settings=_TEST_CHAT_SETTINGS,
        public_response_builder=chat_response_from_result,
        chat_profiles=ChatProfilePolicy(settings=_TEST_CHAT_SETTINGS),
        memory_service=ConversationMemoryService(settings=_TEST_CHAT_SETTINGS.memory, token_counter=TokenCounter()),
        generation_limiter=asyncio.Semaphore(_TEST_CHAT_SETTINGS.runtime.max_concurrent_generations),
    )


def command(message: str = "¿Qué son las plaquetas?") -> ChatCommand:
    return ChatCommand(
        user_id="user-1",
        client_message_id=str(uuid4()),
        conversation_id=None,
        message=message,
        context_scope="general",
        analysis_id=None,
    )


async def events_through_first_delta(stream):
    # There is no more per-token "delta" event (etapa 8: the old "delta"
    # relabeled the complete, already-validated answer as if it were a
    # streaming increment — contexto_2.md's audit finding). The buffered
    # answer now arrives once, as "final", sharing its payload with "done".
    events = []
    while True:
        event = await anext(stream)
        events.append(event)
        if event[0] == "final":
            return events


def assert_complete_stream_contract(events) -> None:
    assert events[0][0] == "start"
    assert events[-1][0] == "done"
    assert [data["sequence"] for _, data in events] == list(range(1, len(events) + 1))
    trace = events[0][1]
    for _, data in events:
        assert data["request_id"] == trace["request_id"]
        assert data["conversation_id"] == trace["conversation_id"]
        assert data["turn_id"] == trace["turn_id"]
        assert data["client_message_id"] == trace["client_message_id"]
        assert data["attempt"] == trace["attempt"]
    assert events[-1][1]["state"] == "completed"
    assert events[-1][1]["processing_stage"] == "completed"


def test_low_risk_stream_buffers_until_complete_validation_and_done_is_exact() -> None:
    async def scenario():
        llm = PausingStreamingLLM(
            first_text="¡Hola! Soy HemoVet.",
            second_text=" Puedo ayudarte a comprender un hemograma canino.",
        )
        stream = build_streaming_use_case(llm).stream(command("Hola"))

        pending_delta = asyncio.create_task(events_through_first_delta(stream))
        await asyncio.sleep(0.05)
        assert pending_delta.done() is False
        assert llm.finished is False

        llm.release.set()
        prefix = await asyncio.wait_for(pending_delta, timeout=1)
        first = prefix[-1][1]
        assert llm.finished is True
        assert first["answer"] == (
            "¡Hola! Soy HemoVet. Puedo ayudarte a comprender un hemograma canino."
        )

        remaining = [event async for event in stream]
        all_events = prefix + remaining
        assert_complete_stream_contract(all_events)
        done = next(data for event, data in remaining if event == "done")
        # "final" and "done" are computed once and share one payload object
        # (etapa 8, Block F) — no second, divergent sanitization pass.
        assert done["answer"] == first["answer"]
        assert llm.finished is True

    asyncio.run(scenario())


def test_concurrent_streams_never_receive_the_other_users_tokens() -> None:
    async def scenario():
        use_case = build_streaming_use_case(PausingStreamingLLM())
        use_case.llm = MultiplexStreamingLLM()
        use_case.generation_limiter = asyncio.Semaphore(2)

        async def collect(user_id: str, name: str):
            current = command()
            current = ChatCommand(
                user_id=user_id,
                client_message_id=current.client_message_id,
                conversation_id=None,
                message=f"¿Qué son las plaquetas? Caso {name}",
                context_scope="general",
                analysis_id=None,
            )
            return [event async for event in use_case.stream(current)]

        luna_events, toby_events = await asyncio.gather(
            collect("user-luna", "Luna"),
            collect("user-toby", "Toby"),
        )
        assert_complete_stream_contract(luna_events)
        assert_complete_stream_contract(toby_events)
        luna = "".join(
            str(data["answer"]) for event, data in luna_events if event == "final"
        )
        toby = "".join(
            str(data["answer"]) for event, data in toby_events if event == "final"
        )
        assert "Luna" in luna and "Toby" not in luna
        assert "Toby" in toby and "Luna" not in toby

    asyncio.run(scenario())


def test_closing_sse_iterator_cancels_provider_generation() -> None:
    async def scenario():
        llm = PausingStreamingLLM()
        stream = build_streaming_use_case(llm).stream(command("Hola"))

        while True:
            event, data = await anext(stream)
            # "generation_started" is emitted immediately before the first
            # provider call (etapa 8, Block E) — there is no
            # status/stage="generating" event anymore.
            if event == "generation_started":
                break
        await asyncio.sleep(0)
        await stream.aclose()
        await asyncio.sleep(0)

        assert llm.finished is False
        assert llm.cancelled is True

    asyncio.run(scenario())


def test_wrong_greeting_never_exposes_clinical_text_before_contract_failure() -> None:
    async def scenario():
        llm = PausingStreamingLLM()
        llm.release.set()
        stream = build_streaming_use_case(llm).stream(command("Hola"))
        events = []
        with pytest.raises(
            ChatRuntimeUnavailable,
            match="invalid_output_intent_mismatch_greeting",
        ):
            async for event in stream:
                events.append(event)

        assert all(event != "delta" for event, _ in events)
        assert all("plaquetas" not in str(data).casefold() for _, data in events)

    asyncio.run(scenario())


def test_clinical_route_buffers_tokens_until_validation() -> None:
    async def scenario():
        llm = PausingStreamingLLM()
        stream = build_streaming_use_case(llm).stream(command())
        delta_task = asyncio.create_task(events_through_first_delta(stream))
        await asyncio.sleep(0.05)
        assert delta_task.done() is False

        llm.release.set()
        prefix = await asyncio.wait_for(delta_task, timeout=1)
        first = prefix[-1][1]
        remaining = [event async for event in stream]
        assert_complete_stream_contract(prefix + remaining)
        done = next(data for event, data in remaining if event == "done")
        assert first["answer"] == done["answer"]

    asyncio.run(scenario())
