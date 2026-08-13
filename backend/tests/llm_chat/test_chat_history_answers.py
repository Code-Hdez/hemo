from __future__ import annotations

import asyncio

from app.modules.llm_chat.application.services.conversation_facts import (
    ConversationFactResolver,
)
from app.modules.llm_chat.domain.clinical import ConversationMemory, ResolvedQuestion
from app.modules.llm_chat.domain.entities import ChatMessageRecord


def record(role: str, content: str, turn: int) -> ChatMessageRecord:
    return ChatMessageRecord(
        id=f"{role}-{turn}",
        conversation_id="conversation-1",
        client_message_id=f"client-{turn}",
        role=role,
        content=content,
        status="completed",
        turn_index=turn,
    )


class TranscriptRepository:
    def __init__(self) -> None:
        self.turns = [
            record("user", "¿Hay un patrón hematológico?", 1),
            record("assistant", "Respuesta generada para el primer turno.", 1),
            record("user", "¿Qué valor tienen los leucocitos?", 2),
            record("assistant", "WBC: 10.4 ×10³/µL.", 2),
        ]

    async def conversation_turns(self, *_args, limit: int | None = None, **_kwargs):
        return list(self.turns) if limit is None else list(self.turns[:limit])

    async def recent(self, _conversation_id: str, limit: int):
        return list(self.turns[-limit:])


def resolved(question: str) -> ResolvedQuestion:
    return ResolvedQuestion(
        original=question,
        standalone=question,
        is_follow_up=False,
    )


def facts_for(question: str):
    return asyncio.run(
        ConversationFactResolver().resolve(
            repository=TranscriptRepository(),
            conversation_id="conversation-1",
            memory=ConversationMemory(context_revision=1),
            question=resolved(question),
        )
    )


def test_first_question_is_a_structured_fact_from_the_real_transcript() -> None:
    facts = facts_for("¿Cuál fue la primera pregunta que te hice?")

    assert facts.query_kind == "first_question"
    assert facts.first_question == "¿Hay un patrón hematológico?"


def test_question_list_keeps_real_questions_in_stable_order() -> None:
    facts = facts_for("Dime todo lo que recuerdas de este chat")

    assert facts.query_kind == "question_list"
    assert facts.questions == (
        "¿Hay un patrón hematológico?",
        "¿Qué valor tienen los leucocitos?",
    )


def test_first_answer_is_not_confused_with_the_first_question() -> None:
    facts = facts_for("¿Y qué me respondiste a la primera pregunta?")

    assert facts.query_kind == "first_answer"
    assert facts.first_question == "¿Hay un patrón hematológico?"
    assert facts.first_answer == "Respuesta generada para el primer turno."


def test_latest_answer_is_exposed_as_data_not_preformatted_prose() -> None:
    facts = facts_for("¿Qué me dijiste antes?")

    assert facts.query_kind == "latest_answer"
    assert facts.latest_answer == "WBC: 10.4 ×10³/µL."
    assert facts.prompt_payload()["question_count"] == 2


class LongTranscriptRepository(TranscriptRepository):
    """A conversation longer than either bounded window."""

    def __init__(self, turn_count: int = 60) -> None:
        self.turns = [
            item
            for turn in range(1, turn_count + 1)
            for item in (
                record("user", f"Pregunta {turn}", turn),
                record("assistant", f"Respuesta {turn}", turn),
            )
        ]


def test_bounded_windows_still_reach_both_ends_of_a_long_conversation() -> None:
    """The transcript is no longer loaded whole, but neither end is lost."""
    facts = asyncio.run(
        ConversationFactResolver().resolve(
            repository=LongTranscriptRepository(),
            conversation_id="conversation-1",
            memory=ConversationMemory(context_revision=1),
            question=resolved("¿Cuál fue la primera pregunta que te hice?"),
        )
    )

    assert facts.first_question == "Pregunta 1"
    assert facts.first_answer == "Respuesta 1"
    assert facts.latest_answer == "Respuesta 60"
    assert len(facts.questions) < 60
