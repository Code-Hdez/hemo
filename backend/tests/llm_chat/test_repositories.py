from __future__ import annotations

import asyncio
import json
from decimal import Decimal
import time
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.hematology.models import Analysis, AnalysisParameter
from app.modules.llm_chat.application.services.context_bundle_builder import (
    build_context_bundle,
)
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    ConversationMemory,
    HemogramParameter,
    HemogramStudy,
    PatientContext,
)
from app.modules.llm_chat.domain.entities import ChatMessageRecord
from app.modules.llm_chat.infrastructure.repositories.sqlalchemy_repositories import (
    AnalysisContextNotFound,
    ConversationNotFound,
    NonBlockingSqlAlchemyRepository,
    SqlAlchemyAnalysisContextRepository,
    SqlAlchemyConversationRepository,
)
from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)
from app.modules.llm_chat.domain.exceptions import (
    ChatIdempotencyConflict,
    ChatTurnConcurrencyConflict,
)
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings
from app.modules.users.models import User
from app.modules.pets.models import Pet
from app.modules.llm_chat.models import ChatMessage, ChatSession, ChatTurn, ChatTurnAttempt
from app.core.config import settings as _app_settings

_TEST_CHAT_SETTINGS = GenerationProfileSettings.from_settings(_app_settings)


def repositories():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add_all(
            [
                User(
                    id="user-1",
                    email="one@example.com",
                    hashed_password="hash",
                    role="user",
                ),
                User(
                    id="user-2",
                    email="two@example.com",
                    hashed_password="hash",
                    role="user",
                ),
            ]
        )
        session.commit()
    return (
        factory,
        SqlAlchemyConversationRepository(factory, chat_settings=_TEST_CHAT_SETTINGS),
        SqlAlchemyAnalysisContextRepository(factory),
    )


def test_nonblocking_repository_adapter_keeps_event_loop_progressing() -> None:
    class SlowSynchronousAdapter:
        async def query(self) -> str:
            time.sleep(0.08)
            return "done"

    async def run() -> tuple[str, int]:
        repository = NonBlockingSqlAlchemyRepository(
            SlowSynchronousAdapter(),
            blocking_executor=BoundedBlockingExecutor(max_concurrency=1),
        )
        query = repository.query
        assert callable(query)
        task = asyncio.create_task(query())
        ticks = 0
        while not task.done():
            await asyncio.sleep(0.005)
            ticks += 1
        return str(await task), ticks

    result, ticks = asyncio.run(run())

    assert result == "done"
    assert ticks >= 3


def test_browser_context_index_is_declared_in_orm_metadata() -> None:
    index = next(
        value
        for value in ChatSession.__table__.indexes
        if value.name == "ix_chat_sessions_browser_context"
    )

    assert tuple(column.name for column in index.columns) == (
        "browser_session_hash",
        "context_key",
        "status",
    )


def test_conversation_repository_enforces_owner_and_returns_recent_messages() -> None:
    _, repository, _ = repositories()
    conversation_id = asyncio.run(repository.get_or_create(None, "user-1"))
    message = ChatMessageRecord(
        id=str(uuid4()),
        conversation_id=conversation_id,
        client_message_id=str(uuid4()),
        role="user",
        content="pregunta",
        status="completed",
    )
    asyncio.run(repository.append(message))

    recent = asyncio.run(repository.recent(conversation_id, 6))
    owned = asyncio.run(repository.history(conversation_id, "user-1", limit=20, offset=0))

    assert recent[0].content == "pregunta"
    assert owned[0].content == "pregunta"
    assert owned[0].created_at is not None
    with pytest.raises(ConversationNotFound):
        asyncio.run(repository.get_or_create(conversation_id, "user-2"))
    with pytest.raises(ConversationNotFound):
        asyncio.run(repository.history(conversation_id, "user-2", limit=20, offset=0))


def test_analysis_context_contains_only_clinical_facts_and_requires_owner() -> None:
    factory, _, repository = repositories()
    analysis_id = "analysis-1"
    payload = {
        "pet_name": "No debe salir",
        "residence_label": "No debe salir",
        "lab_values": [
            {"name": "PLT", "value": "90", "unit": "K/µL", "status": "low"}
        ],
        "findings": [{"label": "Patrón plaquetario", "severity": "warn"}],
        "qc_flags": ["Confirmar muestra"],
    }
    with factory() as session:
        session.add(Pet(id="pet-1", owner_id="user-1", name="Luna"))
        session.add(
            Analysis(
                id=analysis_id,
                data=json.dumps(payload),
                user_id="user-1",
                pet_id="pet-1",
            )
        )
        session.commit()

    snapshot = asyncio.run(repository.get_owned_snapshot(analysis_id, "user-1"))

    assert snapshot["analysis_id"] == analysis_id
    assert snapshot["facts"][0]["code"] == "PLT"
    assert snapshot["facts"][0]["reference_origin"] == "unknown"
    prompt_payload = snapshot["clinical_context"].prompt_payload()
    assert "pet_name" not in json.dumps(prompt_payload)
    assert "residence" not in json.dumps(prompt_payload)
    with pytest.raises(AnalysisContextNotFound):
        asyncio.run(repository.get_owned_snapshot(analysis_id, "user-2"))


def test_repository_preserves_critical_and_requires_a_complete_normal_range() -> None:
    critical = SqlAlchemyAnalysisContextRepository._parameter(
        {
            "name": "PLT",
            "value": "20",
            "unit": "K/µL",
            "ref_min": "150",
            "ref_max": "500",
            "status": "critical",
        }
    )
    partial_range = SqlAlchemyAnalysisContextRepository._parameter(
        {
            "name": "WBC",
            "value": "10.4",
            "unit": "10^9/L",
            "ref_max": "17",
            "status": "normal",
        }
    )

    assert critical is not None
    assert critical.flag == "critical"
    assert partial_range is not None
    assert partial_range.flag == "unknown"


def test_history_context_uses_all_owned_normalized_parameters_and_computes_trend() -> None:
    factory, _, repository = repositories()
    with factory() as session:
        session.add(Pet(id="pet-history", owner_id="user-1", name="Luna"))
        session.add_all(
            [
                Analysis(
                    id="analysis-old",
                    data=json.dumps(
                        {
                            "created_at": "2026-03-01",
                            "_case_snapshot": {
                                "metadata": {"analyzer": "Sysmex XN-V"}
                            },
                        }
                    ),
                    user_id="user-1",
                    pet_id="pet-history",
                    laboratory="Laboratorio Central",
                ),
                Analysis(
                    id="analysis-new",
                    data=json.dumps(
                        {
                            "created_at": "2026-04-01",
                            "_case_snapshot": {
                                "metadata": {"analyzer": "Sysmex XN-V"}
                            },
                        }
                    ),
                    user_id="user-1",
                    pet_id="pet-history",
                    laboratory="Laboratorio Central",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                AnalysisParameter(
                    id="parameter-old",
                    analysis_id="analysis-old",
                    ordinal=0,
                    canonical_name="WBC",
                    display_name="Leucocitos",
                    original_name="Leucocitos",
                    numeric_value=18,
                    value_text="18.0",
                    original_unit="10^9/L",
                    normalized_unit="10^9/L",
                    reference_min=6,
                    reference_max=17,
                    reference_origin="laboratory",
                    recorded_flag="high",
                    derived_flag="high",
                    data_origin="document_extraction",
                ),
                AnalysisParameter(
                    id="parameter-new",
                    analysis_id="analysis-new",
                    ordinal=0,
                    canonical_name="WBC",
                    display_name="Leucocitos",
                    original_name="WBC",
                    numeric_value=22.4,
                    value_text="22.4",
                    original_unit="10^9/L",
                    normalized_unit="10^9/L",
                    reference_min=6,
                    reference_max=17,
                    reference_origin="laboratory",
                    recorded_flag="high",
                    derived_flag="high",
                    data_origin="document_extraction",
                ),
            ]
        )
        session.commit()

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="hemogram_history",
            user_id="user-1",
            pet_id="pet-history",
        )
    )

    assert [study.date[:10] for study in context.history] == [
        "2026-03-01",
        "2026-04-01",
    ]
    wbc = next(
        item
        for item in context.computed_facts
        if item.get("fact_type") == "history_parameter" and item.get("code") == "WBC"
    )
    assert wbc["latest"]["value"] == "22.4"
    assert wbc["previous"]["value"] == "18.0"
    assert wbc["direction_from_previous"] == "increased"
    assert wbc["comparison_valid"] is True
    assert wbc["comparison_reasons"] == []
    assert wbc["latest_change_percent"] == "24.4"
    prompt_payload = context.prompt_payload()
    assert prompt_payload["patient"]["pet_id"] == "pet-history"
    assert {
        study["analysis_id"] for study in prompt_payload["hemogram_history"]
    } == {"analysis-old", "analysis-new"}
    assert all(
        study["source_revision"].startswith("sha256:")
        for study in prompt_payload["hemogram_history"]
    )
    assert all(
        study["analyzer"] == "Sysmex XN-V"
        for study in prompt_payload["hemogram_history"]
    )
    prompt_wbc = next(
        trend
        for trend in prompt_payload["historical_trends"]
        if trend["code"] == "WBC"
    )
    assert prompt_wbc["comparison_valid"] is True
    assert prompt_wbc["latest_change_percent"] == "24.4"
    selected = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-new",
        )
    )
    assert selected.selected is not None
    assert selected.selected.study_key == "H1"
    assert [study.study_key for study in selected.history] == ["H1"]
    selected_position = next(
        item
        for item in selected.computed_facts
        if item.get("fact_type") == "selected_study_position"
    )
    assert selected_position["has_previous_study"] is False
    selected_prompt = selected.prompt_payload()
    assert selected_prompt["patient"]["pet_id"] == "pet-history"
    assert selected_prompt["selected_hemogram"]["analysis_id"] == "analysis-new"
    assert "computed_facts" not in selected_prompt
    assert "hemogram_history" not in selected_prompt
    assert selected_prompt["selected_hemogram"]["study_key"] == "H1"
    assert selected_prompt["selected_hemogram"]["parameter_columns"][0] == "canonical_name"
    focused_prompt = selected.prompt_payload(relevant_parameters={"WBC"})
    assert [row[0] for row in focused_prompt["selected_hemogram"]["parameters"]] == ["WBC"]
    assert "hemogram_history" not in focused_prompt
    standalone_prompt = selected.prompt_payload(
        relevant_parameters={"WBC"}, include_history=False
    )
    assert "hemogram_history" not in standalone_prompt
    with pytest.raises(AnalysisContextNotFound):
        asyncio.run(
            repository.get_owned_context(
                context_scope="hemogram_history",
                user_id="user-2",
                pet_id="pet-history",
            )
        )


def _history_study(
    key: str,
    date: str,
    value: str,
    *,
    pet_id: str = "pet-history",
    unit: str = "10^9/L",
    reference_low: str = "6",
    reference_high: str = "17",
    laboratory: str = "Laboratorio Central",
    analyzer: str = "Sysmex XN-V",
    date_origin: str = "laboratory_result",
) -> HemogramStudy:
    number = Decimal(value)
    low = Decimal(reference_low)
    high = Decimal(reference_high)
    flag = "low" if number < low else "high" if number > high else "normal"
    return HemogramStudy(
        analysis_id=f"analysis-{key}",
        study_key=key,
        date=date,
        label="Hemograma",
        laboratory=laboratory,
        analyzer=analyzer,
        pet_id=pet_id,
        date_origin=date_origin,
        parameters=(
            HemogramParameter(
                canonical_name="WBC",
                display_name="Leucocitos",
                original_name="WBC",
                value=number,
                value_text=value,
                unit=unit,
                reference_min=low,
                reference_max=high,
                flag=flag,
                reference_origin="laboratory",
            ),
        ),
        data_origin="document_extraction",
        source_revision=f"revision-{key}",
    )


@pytest.mark.parametrize(
    ("changed", "reason"),
    [
        ({"reference_high": "18"}, "reference_interval_changed"),
        ({"laboratory": "Otro laboratorio"}, "laboratory_changed"),
        ({"analyzer": "Otro analizador"}, "analyzer_changed"),
        ({"unit": "g/dL"}, "incompatible_units"),
        ({"date": "sin-fecha"}, "missing_or_invalid_date"),
        (
            {"date_origin": "record_created_at_fallback"},
            "unverified_date_origin",
        ),
    ],
)
def test_history_comparison_is_blocked_when_provenance_changes(
    changed: dict[str, str],
    reason: str,
) -> None:
    first = _history_study("H1", "2026-01-10", "8.2")
    second_arguments = {
        "key": "H2",
        "date": "2026-06-20",
        "value": "18.1",
        **changed,
    }
    second = _history_study(**second_arguments)

    facts = SqlAlchemyAnalysisContextRepository._history_facts((first, second))
    wbc = next(fact for fact in facts if fact.get("code") == "WBC")

    assert wbc["comparison_valid"] is False
    assert reason in wbc["comparison_reasons"]
    assert "delta_from_previous" not in wbc
    assert "latest_change_percent" not in wbc


def test_history_context_rejects_studies_from_different_patients() -> None:
    with pytest.raises(ValueError, match="clinical_context_cannot_mix_patients"):
        ClinicalContext(
            mode="hemogram_history",
            patient=PatientContext(pet_id="pet-history", name="Luna"),
            history=(
                _history_study("H1", "2026-01-10", "8.2"),
                _history_study(
                    "H2",
                    "2026-06-20",
                    "18.1",
                    pet_id="another-pet",
                ),
            ),
        )


def test_transcript_has_monotonic_turns_and_answers_real_session_questions() -> None:
    factory, repository, _ = repositories()
    conversation_id = asyncio.run(repository.get_or_create(None, "user-1"))

    for index, question in enumerate(
        ["¿Cuál es el WBC?", "¿Y este valor es alto o bajo?"],
        start=1,
    ):
        client_id = f"client-{index}"
        reserved = asyncio.run(
            repository.begin_turn(
                ChatMessageRecord(
                    id=f"user-message-{index}",
                    conversation_id=conversation_id,
                    client_message_id=client_id,
                    role="user",
                    content=question,
                    status="pending",
                    metadata={"context_revision": 1},
                )
            )
        )
        assert reserved is True
        asyncio.run(
            repository.complete_turn(
                ChatMessageRecord(
                    id=f"assistant-message-{index}",
                    conversation_id=conversation_id,
                    client_message_id=client_id,
                    role="assistant",
                    content=f"respuesta {index}",
                    status="completed",
                    metadata={"context_revision": 1},
                ),
                memory_summary="",
                memory_state={},
            )
        )

    transcript = asyncio.run(repository.conversation_turns(conversation_id))
    questions = asyncio.run(repository.user_questions(conversation_id))
    first = asyncio.run(repository.first_user_message(conversation_id))

    assert [(row.turn_index, row.role) for row in transcript] == [
        (1, "user"),
        (1, "assistant"),
        (2, "user"),
        (2, "assistant"),
    ]
    assert [row.content for row in questions] == [
        "¿Cuál es el WBC?",
        "¿Y este valor es alto o bajo?",
    ]
    assert first is not None
    assert first.content == "¿Cuál es el WBC?"
    with factory() as session:
        persisted = list(
            session.scalars(
                select(ChatMessage).where(ChatMessage.session_id == conversation_id)
            )
        )
        chat_session = session.get(ChatSession, conversation_id)
    assert sorted(row.turn_index for row in persisted) == [1, 1, 2, 2]
    assert chat_session is not None
    assert chat_session.next_turn_index == 3


def test_transcript_is_isolated_by_conversation_and_context_revision() -> None:
    _, repository, _ = repositories()
    first_id = asyncio.run(repository.get_or_create(None, "user-1"))
    # get_or_create(None, ...) auto-resolves to the single active
    # conversation matching user_id + context_key (informe_etapa_3: "si hay
    # exactamente una, se reutiliza"); a second, isolated conversation under
    # the same scope requires an explicit force_new=True.
    second_id = asyncio.run(repository.get_or_create(None, "user-1", force_new=True))
    asyncio.run(
        repository.append(
            ChatMessageRecord(
                id="first-session-message",
                conversation_id=first_id,
                client_message_id="first-session-client",
                role="user",
                content="pregunta de la primera sesión",
                status="completed",
            )
        )
    )
    asyncio.run(
        repository.append(
            ChatMessageRecord(
                id="second-session-message",
                conversation_id=second_id,
                client_message_id="second-session-client",
                role="user",
                content="pregunta de la segunda sesión",
                status="completed",
            )
        )
    )

    assert [
        row.content for row in asyncio.run(repository.user_questions(first_id))
    ] == ["pregunta de la primera sesión"]
    assert [
        row.content for row in asyncio.run(repository.user_questions(second_id))
    ] == ["pregunta de la segunda sesión"]

    with pytest.raises(ConversationNotFound):
        asyncio.run(
            repository.get_or_create(
                first_id,
                "user-1",
                context_scope="selected_hemogram",
                pet_id="pet-context",
                analysis_id="analysis-context",
            )
        )
    # Context identity is immutable: the original transcript remains intact,
    # and the selected hemogram receives a separate conversation.
    assert [row.content for row in asyncio.run(repository.user_questions(first_id))] == [
        "pregunta de la primera sesión"
    ]
    selected_id = asyncio.run(
        repository.get_or_create(
            None,
            "user-1",
            context_scope="selected_hemogram",
            pet_id="pet-context",
            analysis_id="analysis-context",
        )
    )
    assert selected_id != first_id
    assert asyncio.run(repository.user_questions(selected_id)) == []


def test_selected_context_omitted_pet_preserves_identity_and_revision() -> None:
    factory, repository, _ = repositories()
    conversation_id = asyncio.run(
        repository.get_or_create(
            None,
            "user-1",
            context_scope="selected_hemogram",
            pet_id="pet-context",
            analysis_id="analysis-context",
        )
    )

    refreshed_id = asyncio.run(
        repository.get_or_create(
            conversation_id,
            "user-1",
            context_scope="selected_hemogram",
            analysis_id="analysis-context",
        )
    )

    with factory() as session:
        persisted = session.get(ChatSession, conversation_id)
    assert refreshed_id == conversation_id
    assert persisted is not None
    assert persisted.active_pet_id == "pet-context"
    assert persisted.active_analysis_id == "analysis-context"
    assert persisted.context_key == "pet:pet-context:analysis:analysis-context"
    assert persisted.context_revision == 1


def test_interrupted_turn_is_audited_and_can_be_retried() -> None:
    factory, repository, _ = repositories()
    conversation_id = asyncio.run(repository.get_or_create(None, "user-1"))
    pending = ChatMessageRecord(
        id="interrupted-user-message",
        conversation_id=conversation_id,
        client_message_id="interrupted-client",
        role="user",
        content="¿Qué son las plaquetas?",
        status="pending",
        metadata={"context_revision": 1},
    )
    assert asyncio.run(repository.begin_turn(pending)) is True

    asyncio.run(
        repository.mark_owned_turn_interrupted(
            "user-1",
            "interrupted-client",
        )
    )
    with factory() as session:
        interrupted = session.scalar(
            select(ChatMessage).where(ChatMessage.id == "interrupted-user-message")
        )
        assert interrupted is not None
        assert interrupted.status == "interrupted"

    retry = ChatMessageRecord(
        id="retried-user-message",
        conversation_id=conversation_id,
        client_message_id="interrupted-client",
        role="user",
        content="¿Qué son las plaquetas?",
        status="pending",
        metadata={"context_revision": 1},
    )
    assert asyncio.run(repository.begin_turn(retry)) is True


def test_failed_generated_turn_retries_same_id_without_duplicating_user_message() -> None:
    factory, repository, _ = repositories()
    conversation_id = asyncio.run(repository.get_or_create(None, "user-1"))
    client_id = "invalid-output-client"
    first = ChatMessageRecord(
        id="original-user-message",
        conversation_id=conversation_id,
        client_message_id=client_id,
        role="user",
        content="¿Qué son las plaquetas?",
        status="pending",
        metadata={"context_revision": 1},
    )
    assert asyncio.run(repository.begin_turn(first)) is True
    asyncio.run(
        repository.mark_turn_failed(
            conversation_id,
            client_id,
            error_code="invalid_output_empty_output",
        )
    )

    failed = asyncio.run(
        repository.turn_status(conversation_id, client_id, "user-1")
    )
    assert failed.status == "failed"
    assert failed.retryable is True
    assert failed.error_code == "invalid_output_empty_output"

    retry = ChatMessageRecord(
        id="must-not-create-a-second-user-message",
        conversation_id=conversation_id,
        client_message_id=client_id,
        role="user",
        content="¿Qué son las plaquetas?",
        status="pending",
        metadata={"context_revision": 1},
    )
    assert asyncio.run(repository.begin_turn(retry)) is True
    asyncio.run(
        repository.complete_turn(
            ChatMessageRecord(
                id="generated-assistant-message",
                conversation_id=conversation_id,
                client_message_id=client_id,
                role="assistant",
                content="Las plaquetas participan en la coagulación.",
                status="completed",
                model="qwen-test",
                metadata={
                    "context_revision": 1,
                    "scope": "general",
                    "safety_action": "allow",
                    "llm_invoked": True,
                    "response_origin": "llm",
                    "attempt": 2,
                    "generation_attempts": 1,
                    "stream_mode": "buffered_validated",
                    "validation_status": "passed",
                },
            ),
            memory_summary="",
            memory_state={},
        )
    )

    completed = asyncio.run(
        repository.turn_status(conversation_id, client_id, "user-1")
    )
    assert completed.status == "completed"
    assert completed.retryable is False
    assert completed.attempt == 2
    assert completed.response is not None
    assert completed.response.model == "qwen-test"
    assert completed.response.llm_invoked is True
    with factory() as session:
        messages = list(
            session.scalars(
                select(ChatMessage).where(ChatMessage.session_id == conversation_id)
            )
        )
        attempts = list(session.scalars(select(ChatTurnAttempt)))
        turn = session.scalar(select(ChatTurn))
    assert [(message.role, message.status) for message in messages] == [
        ("user", "completed"),
        ("assistant", "completed"),
    ]
    assert [attempt.status for attempt in attempts] == ["failed", "completed"]
    assert turn is not None and turn.attempt_count == 2


def test_late_result_from_old_attempt_cannot_overwrite_active_retry() -> None:
    factory, repository, _ = repositories()
    conversation_id = asyncio.run(repository.get_or_create(None, "user-1"))
    client_id = "stale-provider-result"
    user_message = ChatMessageRecord(
        id="stale-attempt-user",
        conversation_id=conversation_id,
        client_message_id=client_id,
        role="user",
        content="¿Qué son las plaquetas?",
        status="pending",
        metadata={"context_revision": 1},
    )
    assert asyncio.run(repository.begin_turn(user_message)) is True

    asyncio.run(
        repository.mark_turn_failed(
            conversation_id,
            client_id,
            error_code="provider_timeout",
        )
    )
    assert asyncio.run(repository.begin_turn(user_message)) is True
    assert asyncio.run(
        repository.mark_turn_failed(
            conversation_id,
            client_id,
            error_code="late_attempt_failure",
            expected_attempt=1,
        )
    ) is False

    # complete_turn enforces the compare-and-set itself: a stale attempt
    # raises ChatTurnConcurrencyConflict(reason="attempt_changed") instead of
    # silently discarding the write, so the caller (router) can surface a 409
    # turn_completion_conflict instead of losing the late result silently.
    with pytest.raises(ChatTurnConcurrencyConflict):
        asyncio.run(
            repository.complete_turn(
                ChatMessageRecord(
                    id="late-assistant-attempt-1",
                    conversation_id=conversation_id,
                    client_message_id=client_id,
                    role="assistant",
                    content="respuesta tardía",
                    status="completed",
                    model="qwen-old",
                    metadata={"context_revision": 1, "attempt": 1},
                ),
                memory_summary="memoria tardía",
                memory_state={"source": "attempt-1"},
            )
        )

    active = asyncio.run(repository.turn_status(conversation_id, client_id, "user-1"))
    assert active.status == "processing"
    assert active.attempt == 2
    assert active.response is None
    with factory() as session:
        assert session.get(ChatSession, conversation_id).memory_summary is None
        assert session.scalar(
            select(ChatMessage).where(ChatMessage.role == "assistant")
        ) is None


def test_global_idempotency_redirects_duplicate_new_conversation_to_canonical_turn() -> None:
    factory, repository, _ = repositories()
    first_conversation = asyncio.run(
        repository.get_or_create(None, "user-1", auth_session_id="browser-session")
    )
    duplicate_conversation = asyncio.run(
        repository.get_or_create(None, "user-1", auth_session_id="browser-session")
    )
    assert duplicate_conversation == first_conversation
    client_id = "global-client-message"
    question = "¿Qué son las plaquetas?"
    first = ChatMessageRecord(
        id="global-user-first",
        conversation_id=first_conversation,
        client_message_id=client_id,
        role="user",
        content=question,
        status="pending",
        metadata={"context_revision": 1, "scope": "general"},
    )
    duplicate = ChatMessageRecord(
        id="global-user-duplicate",
        conversation_id=duplicate_conversation,
        client_message_id=client_id,
        role="user",
        content=question,
        status="pending",
        metadata={"context_revision": 1, "scope": "general"},
    )

    reserved = asyncio.run(
        repository.reserve_turn(
            first,
            user_id="user-1",
            auth_session_id="browser-session",
            request_fingerprint="same-request-fingerprint",
            lease_seconds=30,
        )
    )
    raced = asyncio.run(
        repository.reserve_turn(
            duplicate,
            user_id="user-1",
            auth_session_id="browser-session",
            request_fingerprint="same-request-fingerprint",
            lease_seconds=30,
            discard_empty_conversation_on_redirect=True,
        )
    )

    assert reserved.acquired is True
    assert raced.acquired is False
    assert raced.conversation_id == first_conversation
    assert raced.attempt == 1
    with factory() as session:
        assert session.get(ChatSession, duplicate_conversation) is not None
        assert len(list(session.scalars(select(ChatTurn)))) == 1
        assert len(list(session.scalars(select(ChatMessage)))) == 1
        assert len(list(session.scalars(select(ChatTurnAttempt)))) == 1


def test_browser_session_hash_isolates_restore_listing_and_mutation() -> None:
    _, repository, _ = repositories()
    first = asyncio.run(
        repository.get_or_create(
            None,
            "user-1",
            auth_session_id="auth-session",
            browser_session_hash="browser-hash-one",
        )
    )
    restored = asyncio.run(
        repository.get_or_create(
            None,
            "user-1",
            auth_session_id="auth-session",
            browser_session_hash="browser-hash-one",
        )
    )
    # A different browser_session_hash no longer isolates anything: ownership
    # and auto-resolution are scoped by the authenticated user (+ context_key)
    # only (informe_etapa_3: "la única frontera de propiedad es user_id";
    # plan_2 #11: "la conversación debe pertenecer al usuario autenticado, no
    # a un navegador específico"). The single active "general" conversation
    # for user-1 is reused regardless of browser_session_hash.
    second = asyncio.run(
        repository.get_or_create(
            None,
            "user-1",
            auth_session_id="auth-session",
            browser_session_hash="browser-hash-two",
        )
    )

    assert restored == first
    assert second == first
    assert [
        row["id"]
        for row in asyncio.run(
            repository.list_active(
                "user-1",
                "auth-session",
                "browser-hash-one",
            )
        )
    ] == [first]
    assert [
        row["id"]
        for row in asyncio.run(
            repository.list_active(
                "user-1",
                "auth-session",
                "browser-hash-two",
            )
        )
    ] == [first]
    assert (
        asyncio.run(
            repository.get_or_create(
                first,
                "user-1",
                auth_session_id="auth-session",
                browser_session_hash="browser-hash-two",
            )
        )
        == first
    )
    asyncio.run(
        repository.delete_owned(
            first,
            "user-1",
            "auth-session",
            "browser-hash-two",
        )
    )
    assert (
        asyncio.run(
            repository.list_active("user-1", "auth-session", "browser-hash-one")
        )
        == []
    )


def test_turn_history_uses_real_sqlalchemy_repository_and_browser_scope() -> None:
    _, repository, _ = repositories()
    conversation_id = asyncio.run(
        repository.get_or_create(
            None,
            "user-1",
            auth_session_id="auth-session-one",
            browser_session_hash="browser-hash-one",
        )
    )
    client_message_id = "turn-history-client"
    assert asyncio.run(
        repository.begin_turn(
            ChatMessageRecord(
                id="turn-history-user-message",
                conversation_id=conversation_id,
                client_message_id=client_message_id,
                role="user",
                content="¿Qué son las plaquetas?",
                status="pending",
                metadata={"context_revision": 1, "scope": "general"},
            )
        )
    ) is True
    asyncio.run(
        repository.complete_turn(
            ChatMessageRecord(
                id="turn-history-assistant-message",
                conversation_id=conversation_id,
                client_message_id=client_message_id,
                role="assistant",
                content="Las plaquetas participan en la hemostasia.",
                status="completed",
                model="qwen-test",
                metadata={
                    "context_revision": 1,
                    "scope": "general",
                    "safety_action": "allow",
                    "llm_invoked": True,
                    "response_origin": "llm",
                },
            ),
            memory_summary="",
            memory_state={},
        )
    )

    turns = asyncio.run(
        repository.turn_history(
            conversation_id,
            "user-1",
            limit=20,
            offset=0,
            auth_session_id="auth-session-one",
            browser_session_hash="browser-hash-one",
        )
    )

    assert len(turns) == 1
    assert turns[0]["client_message_id"] == client_message_id
    assert turns[0]["user_message"].content == "¿Qué son las plaquetas?"
    assert turns[0]["response"] is not None
    assert turns[0]["response"].model == "qwen-test"
    # Ownership is the authenticated user only: a different auth_session_id
    # or browser_session_hash (even None) no longer hides the conversation
    # (informe_etapa_3: "quité el rechazo por auth_session_id/
    # browser_session_hash distinto — la única frontera de propiedad es
    # user_id"; plan_2 #11).
    for auth_session_id, browser_session_hash in (
        ("auth-session-two", "browser-hash-one"),
        ("auth-session-one", "browser-hash-two"),
        ("auth-session-one", None),
    ):
        other_scope_turns = asyncio.run(
            repository.turn_history(
                conversation_id,
                "user-1",
                limit=20,
                offset=0,
                auth_session_id=auth_session_id,
                browser_session_hash=browser_session_hash,
            )
        )
        assert len(other_scope_turns) == 1
        assert other_scope_turns[0]["client_message_id"] == client_message_id

    with pytest.raises(ConversationNotFound):
        asyncio.run(
            repository.turn_history(
                conversation_id,
                "user-2",
                limit=20,
                offset=0,
                auth_session_id="auth-session-one",
                browser_session_hash="browser-hash-one",
            )
        )

    assert (
        asyncio.run(
            repository.history(
                conversation_id,
                "user-1",
                limit=20,
                offset=0,
                auth_session_id="auth-session-one",
                browser_session_hash="browser-hash-two",
            )
        )
        != []
    )
    with pytest.raises(ConversationNotFound):
        asyncio.run(
            repository.history(
                conversation_id,
                "user-2",
                limit=20,
                offset=0,
                auth_session_id="auth-session-one",
                browser_session_hash="browser-hash-one",
            )
        )


def test_reusing_global_client_id_for_different_request_is_a_conflict() -> None:
    _, repository, _ = repositories()
    conversation_id = asyncio.run(
        repository.get_or_create(None, "user-1", auth_session_id="browser-session")
    )
    client_id = "conflicting-global-client"
    original = ChatMessageRecord(
        id="conflict-original",
        conversation_id=conversation_id,
        client_message_id=client_id,
        role="user",
        content="¿Qué son las plaquetas?",
        status="pending",
        metadata={"context_revision": 1, "scope": "general"},
    )
    asyncio.run(
        repository.reserve_turn(
            original,
            user_id="user-1",
            auth_session_id="browser-session",
            request_fingerprint="original-fingerprint",
            lease_seconds=30,
        )
    )

    changed = ChatMessageRecord(
        id="conflict-changed",
        conversation_id=conversation_id,
        client_message_id=client_id,
        role="user",
        content="¿Qué es la hemoglobina?",
        status="pending",
        metadata={"context_revision": 1, "scope": "general"},
    )
    with pytest.raises(ChatIdempotencyConflict):
        asyncio.run(
            repository.reserve_turn(
                changed,
                user_id="user-1",
                auth_session_id="browser-session",
                request_fingerprint="changed-fingerprint",
                lease_seconds=30,
            )
        )


def test_numeric_range_overrides_conflicting_recorded_hgb_flag() -> None:
    factory, _, repository = repositories()
    with factory() as session:
        session.add(Pet(id="pet-hgb", owner_id="user-1", name="Luna"))
        session.add(
            Analysis(
                id="analysis-hgb",
                data=json.dumps({"created_at": "2026-07-09"}),
                user_id="user-1",
                pet_id="pet-hgb",
            )
        )
        session.flush()
        session.add(
            AnalysisParameter(
                id="parameter-hgb",
                analysis_id="analysis-hgb",
                ordinal=0,
                canonical_name="HGB",
                display_name="Hemoglobina",
                original_name="HGB",
                numeric_value=19.5,
                value_text="19.5",
                original_unit="g/dL",
                normalized_unit="g/dL",
                reference_min=12,
                reference_max=18,
                reference_origin="laboratory",
                recorded_flag="normal",
                derived_flag="normal",
                data_origin="document_extraction",
            )
        )
        session.commit()

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-hgb",
        )
    )

    assert context.selected is not None
    hgb = context.selected.parameters[0]
    assert hgb.value_text == "19.5"
    assert hgb.reference_min == 12
    assert hgb.reference_max == 18
    assert hgb.flag == "high"
    assert hgb.recorded_flag == "normal"
    assert context.legacy_facts()[0]["status"] == "high"


def test_ml_label_stored_before_classifier_outcome_still_reaches_the_assistant() -> None:
    """A stored ML classification must not be invisible to the chat.

    ``classifier_outcome`` was added to the case snapshot after analyses were
    already being written, so rows created earlier keep the identical ML
    result under the snapshot's root keys. Reading only the nested key made
    the assistant blind to a classification the database really holds: the
    production study carrying PATRON_ANEMIA_NO_REGENERATIVA reached the
    prompt with zero ML findings, so the chat could not use the label its own
    ML engine had produced. This pins the legacy shape observed in that row.
    """
    factory, _, repository = repositories()
    payload = {
        "created_at": "2026-04-02",
        "model_version": "4.0.0",
        "lab_values": [
            {"name": "HCT", "value": "35.5", "unit": "%", "status": "low"}
        ],
        "_case_snapshot": {
            "snapshot_type": "analysis",
            "limited_context": False,
            # Exactly the production shape: the ML result lives at the root
            # and there is no "classifier_outcome" key at all.
            "active_labels": ["PATRON_ANEMIA_NO_REGENERATIVA"],
            "qc_labels": [],
            "probabilities": {"PATRON_ANEMIA_NO_REGENERATIVA": 0.91},
        },
    }
    with factory() as session:
        session.add(Pet(id="pet-ml", owner_id="user-1", name="test"))
        session.add(
            Analysis(
                id="analysis-ml",
                data=json.dumps(payload),
                user_id="user-1",
                pet_id="pet-ml",
            )
        )
        session.commit()

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-ml",
        )
    )

    assert context.selected is not None
    outcome = context.selected.classifier_outcome
    assert outcome is not None
    assert outcome["active_labels"] == ["PATRON_ANEMIA_NO_REGENERATIVA"]
    assert outcome["classification_status"] == "CLASSIFIED"
    assert outcome["probabilities"]["PATRON_ANEMIA_NO_REGENERATIVA"] == 0.91
    assert outcome["model_version"] == "4.0.0"


def _analysis_with_snapshot(
    factory,
    *,
    pet_id: str,
    analysis_id: str,
    snapshot: dict | None,
) -> None:
    payload: dict = {"created_at": "2026-04-02", "lab_values": []}
    if snapshot is not None:
        payload["_case_snapshot"] = snapshot
    with factory() as session:
        session.add(Pet(id=pet_id, owner_id="user-1", name="test"))
        session.add(
            Analysis(
                id=analysis_id,
                data=json.dumps(payload),
                user_id="user-1",
                pet_id=pet_id,
            )
        )
        session.commit()


def test_explicitly_empty_ml_labels_report_that_no_pattern_was_detected() -> None:
    """"The model found nothing" must stay distinct from "the field is absent".

    A normal hemogram is stored with ``active_labels: []`` and the scores that
    produced them — the ML engine ran and detected no target pattern.
    Reporting that as "no classification at all" made it indistinguishable
    from a row written before the field existed, and left the assistant
    unable to state the classifier found nothing.

    The scores are what prove the engine ran: an empty ``probabilities`` means
    it produced no prediction, which is a third state and not a negative
    result (see ``_classifier_outcome_from_legacy_snapshot``).
    """
    factory, _, repository = repositories()
    _analysis_with_snapshot(
        factory,
        pet_id="pet-empty",
        analysis_id="analysis-empty",
        snapshot={"active_labels": [], "probabilities": {"PATRON_HEMOLISIS_MCHC": 0.02}},
    )

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-empty",
        )
    )

    assert context.selected is not None
    outcome = context.selected.classifier_outcome
    assert outcome is not None
    assert outcome["classification_status"] == "NO_TARGET_PATTERN_DETECTED"
    assert outcome["active_labels"] == []


def test_only_qc_labels_still_report_no_target_pattern_detected() -> None:
    """QC labels are not clinical patterns, exactly as the snapshot writer does."""
    factory, _, repository = repositories()
    _analysis_with_snapshot(
        factory,
        pet_id="pet-qc",
        analysis_id="analysis-qc",
        snapshot={"active_labels": ["QC_PLATELET_CLUMPS"], "probabilities": {}},
    )

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-qc",
        )
    )

    assert context.selected is not None
    outcome = context.selected.classifier_outcome
    assert outcome is not None
    assert outcome["classification_status"] == "NO_TARGET_PATTERN_DETECTED"
    assert outcome["active_labels"] == []


def test_snapshot_predating_the_ml_fields_reports_no_outcome_at_all() -> None:
    """Without the keys there is no ML verdict to report, and none is invented."""
    factory, _, repository = repositories()
    _analysis_with_snapshot(
        factory,
        pet_id="pet-legacy",
        analysis_id="analysis-legacy",
        snapshot={"snapshot_type": "analysis"},
    )

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-legacy",
        )
    )

    assert context.selected is not None
    assert context.selected.classifier_outcome is None


def test_no_pattern_detected_reaches_the_prompt_as_an_ml_finding() -> None:
    """The whole point of the distinction: the assistant can cite the verdict."""
    factory, _, repository = repositories()
    _analysis_with_snapshot(
        factory,
        pet_id="pet-bundle",
        analysis_id="analysis-bundle",
        snapshot={"active_labels": [], "probabilities": {"PATRON_HEMOLISIS_MCHC": 0.02}},
    )

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-bundle",
        )
    )
    bundle = build_context_bundle(
        context,
        memory=ConversationMemory(context_revision=1),
        context_revision=1,
    )

    assert [
        (finding.fact_type, finding.value) for finding in bundle.ml_findings
    ] == [("ml_classification_status", "NO_TARGET_PATTERN_DETECTED")]


def test_classifier_confidence_is_never_reported_as_extraction_confidence() -> None:
    """The chat labels this number as digitisation quality of the document.

    ``confidence`` in the payload and in the case snapshot is
    ``prediction.confidence``, the ML classifier's. Falling back to it filled
    fact_type "extraction_confidence" — presented to the model as how well the
    PDF was read — with a number about something else entirely. Absent a real
    extraction confidence the fact is simply not emitted.
    """
    factory, _, repository = repositories()
    _analysis_with_snapshot(
        factory,
        pet_id="pet-conf",
        analysis_id="analysis-conf",
        snapshot={"confidence": 0.94, "active_labels": [], "probabilities": {}},
    )

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-conf",
        )
    )
    bundle = build_context_bundle(
        context,
        memory=ConversationMemory(context_revision=1),
        context_revision=1,
    )

    assert context.selected is not None
    assert context.selected.extraction_confidence is None
    assert not [
        finding
        for finding in bundle.quality_findings
        if finding.fact_type == "extraction_confidence"
    ]


def test_stored_extraction_confidence_still_reaches_the_assistant() -> None:
    """Dropping the fallback must not silence a genuine extraction confidence."""
    factory, _, repository = repositories()
    _analysis_with_snapshot(
        factory,
        pet_id="pet-real-conf",
        analysis_id="analysis-real-conf",
        snapshot={"active_labels": [], "probabilities": {}},
    )
    with factory() as session:
        session.get(Analysis, "analysis-real-conf").extraction_confidence = 0.62
        session.commit()

    context = asyncio.run(
        repository.get_owned_context(
            context_scope="selected_hemogram",
            user_id="user-1",
            analysis_id="analysis-real-conf",
        )
    )

    assert context.selected is not None
    assert context.selected.extraction_confidence == 0.62


def test_resuming_a_closed_conversation_makes_it_listable_again() -> None:
    """The TTL sweep and logout close conversations; resuming one is activity.

    ``get_or_create`` already revives a closed conversation for the chat by
    pushing ``expires_at`` forward, so leaving ``status`` closed would keep it
    working while permanently hidden from the user's own list.
    """
    factory, repository, _ = repositories()
    conversation_id = asyncio.run(
        repository.get_or_create(None, "user-1", context_scope="general")
    )
    with factory() as session:
        session.get(ChatSession, conversation_id).status = "expired"
        session.commit()

    resumed = asyncio.run(
        repository.get_or_create(conversation_id, "user-1", context_scope="general")
    )
    listed = asyncio.run(repository.list_active("user-1", None))

    assert resumed == conversation_id
    assert [item["id"] for item in listed] == [conversation_id]


def _reserve_from_tab(
    repository,
    conversation_id: str,
    *,
    message_id: str,
    browser_session_hash: str,
    request_fingerprint: str,
    content: str = "¿Qué significan las plaquetas bajas?",
):
    return asyncio.run(
        repository.reserve_turn(
            ChatMessageRecord(
                id=message_id,
                conversation_id=conversation_id,
                client_message_id="shared-client-message",
                role="user",
                content=content,
                status="pending",
                metadata={"context_revision": 1, "scope": "general"},
            ),
            user_id="user-1",
            auth_session_id="auth-session",
            browser_session_hash=browser_session_hash,
            request_fingerprint=request_fingerprint,
            lease_seconds=30,
        )
    )


def _two_tabs_racing_the_same_client_message_id(repository) -> str:
    """Leave a retryable turn behind so the second tab reaches the insert.

    Both tabs share one conversation and one client_message_id but derive
    different idempotency keys, because the key is scoped by browser session.
    """
    conversation_id = asyncio.run(
        repository.get_or_create(
            None,
            "user-1",
            auth_session_id="auth-session",
            browser_session_hash="tab-a",
        )
    )
    reserved = _reserve_from_tab(
        repository,
        conversation_id,
        message_id="message-tab-a",
        browser_session_hash="tab-a",
        request_fingerprint="same-request",
    )
    assert reserved.acquired is True
    assert asyncio.run(
        repository.mark_turn_failed(conversation_id, "shared-client-message")
    )
    return conversation_id


def test_duplicate_client_message_id_across_tabs_is_a_conflict_not_a_500() -> None:
    """uq_chat_turn_session_client must not surface as a persistence failure.

    The second tab's idempotency key does not exist, so the post-rollback
    lookup found nothing and raised ChatPersistenceError — a 500 for what is
    the same user retrying the same message from another tab.
    """
    _, repository, _ = repositories()
    conversation_id = _two_tabs_racing_the_same_client_message_id(repository)

    raced = _reserve_from_tab(
        repository,
        conversation_id,
        message_id="message-tab-b",
        browser_session_hash="tab-b",
        request_fingerprint="same-request",
    )

    assert raced.acquired is False
    assert raced.conversation_id == conversation_id


def test_duplicate_client_message_id_with_another_request_is_an_idempotency_conflict() -> None:
    """A different request behind the same client id is still a 409, not a 500."""
    _, repository, _ = repositories()
    conversation_id = _two_tabs_racing_the_same_client_message_id(repository)

    with pytest.raises(ChatIdempotencyConflict):
        _reserve_from_tab(
            repository,
            conversation_id,
            message_id="message-tab-b",
            browser_session_hash="tab-b",
            request_fingerprint="another-request",
            content="Otra pregunta distinta",
        )


def test_hot_path_indexes_are_declared_in_orm_metadata() -> None:
    """The recall queries filter by session_id and order by turn_index."""
    declared = {
        (index.name, tuple(column.name for column in index.columns))
        for table in (ChatMessage, ChatTurn, ChatSession)
        for index in table.__table__.indexes
    }

    assert ("ix_chat_messages_session_turn", ("session_id", "turn_index")) in declared
    assert ("ix_chat_turns_session_turn", ("session_id", "turn_index")) in declared
    assert (
        "ix_chat_sessions_user_status_updated",
        ("user_id", "status", "updated_at"),
    ) in declared
    # Created by migration 0011; declaring it keeps --autogenerate from
    # proposing to drop an index the database really has.
    assert (
        "ix_chat_sessions_auth_context",
        ("auth_session_id", "context_key", "status"),
    ) in declared
