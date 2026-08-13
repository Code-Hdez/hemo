from __future__ import annotations

import dataclasses
from decimal import Decimal

from app.core.config import settings as _app_settings
from app.modules.llm_chat.application.services.conversation_memory import (
    ConversationMemoryService,
)
from app.modules.llm_chat.application.services.token_budget import TokenCounter
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    ConversationMemory,
    HemogramParameter,
    HemogramStudy,
    PatientContext,
    ResolvedQuestion,
)
from app.modules.llm_chat.domain.entities import ChatMessageRecord
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings

_BASE_MEMORY_SETTINGS = GenerationProfileSettings.from_settings(_app_settings).memory


def _memory_service(*, recent_turns: int, summary_max_chars: int | None = None) -> (
    ConversationMemoryService
):
    overrides: dict[str, object] = {"history_limit": recent_turns}
    if summary_max_chars is not None:
        overrides["summary_max_chars"] = summary_max_chars
    settings = dataclasses.replace(_BASE_MEMORY_SETTINGS, **overrides)
    return ConversationMemoryService(settings=settings, token_counter=TokenCounter())


def _context() -> ClinicalContext:
    study = HemogramStudy(
        analysis_id="analysis-2026-07-09",
        study_key="H1",
        date="2026-07-09",
        label="Hemograma 9 de julio",
        laboratory="Laboratorio veterinario",
        parameters=(
            HemogramParameter(
                canonical_name="WBC",
                display_name="Leucocitos",
                original_name="WBC",
                value=Decimal("10.4"),
                value_text="10.4",
                unit="×10³/µL",
                reference_min=Decimal("5.5"),
                reference_max=Decimal("16.9"),
                flag="normal",
                reference_origin="laboratory",
            ),
        ),
    )
    return ClinicalContext(
        mode="selected_hemogram",
        patient=PatientContext(pet_id="pet-1", name="Luna"),
        selected=study,
        history=(study,),
    )


def _resolved(question: str) -> ResolvedQuestion:
    return ResolvedQuestion(
        original=question,
        standalone=question,
        is_follow_up=False,
        referenced_parameter="WBC",
    )


def test_memory_keeps_literal_first_question_and_structured_clinical_values() -> None:
    service = _memory_service(recent_turns=2)
    first_question = "¿Cuai es el nibel de leucositos?"
    summary, state = service.update(
        memory=ConversationMemory(),
        clinical=_context(),
        user_message=first_question,
        assistant_message="WBC: 10.4 ×10³/µL.",
        resolved=_resolved(first_question),
    )
    _, state = service.update(
        memory=ConversationMemory(summary=summary, state=state),
        clinical=_context(),
        user_message="¿Y este valor es alto o bajo?",
        assistant_message="Está dentro del rango.",
        resolved=_resolved("¿Y este valor es alto o bajo?"),
    )

    assert state["first_user_question"] == first_question
    assert state["recent_user_questions"] == [
        first_question,
        "¿Y este valor es alto o bajo?",
    ]
    assert state["user_question_count"] == 2
    snapshot = state["clinical_facts"]["WBC"]
    assert snapshot["species"] == "canine"
    assert snapshot["studies"] == [
        {
            "study_id": "analysis-2026-07-09",
            "study_key": "H1",
            "date": "2026-07-09",
            "parameters": [
                {
                    "code": "WBC",
                    "value": "10.4",
                    "unit": "×10³/µL",
                    "reference_min": "5.5",
                    "reference_max": "16.9",
                    "classification": "normal",
                    "range_source": "laboratory",
                }
            ],
        }
    ]


def test_summary_deduplicates_evicted_rows_without_cutting_clinical_facts() -> None:
    service = _memory_service(recent_turns=1, summary_max_chars=500)
    prior = tuple(
        ChatMessageRecord(
            id=f"message-{index}",
            conversation_id="conversation-1",
            client_message_id=f"client-{index}",
            role="user" if index % 2 == 0 else "assistant",
            content=f"turno {index}: WBC 10.4 ×10³/µL el 2026-07-09",
            status="completed",
            turn_index=(index // 2) + 1,
        )
        for index in range(6)
    )
    question = "¿Qué recuerdas?"
    summary, state = service.update(
        memory=ConversationMemory(recent_messages=prior),
        clinical=_context(),
        user_message=question,
        assistant_message="Recuerdo los turnos de esta sesión.",
        resolved=_resolved(question),
    )
    repeated_summary, repeated_state = service.update(
        memory=ConversationMemory(
            summary=summary,
            state=state,
            recent_messages=prior,
        ),
        clinical=_context(),
        user_message="continúa",
        assistant_message="continúo",
        resolved=_resolved("continúa"),
    )

    assert "WBC 10.4 ×10³/µL el 2026-07-09" in summary
    assert repeated_summary == summary
    assert len(repeated_state["summarized_message_ids"]) == 6
