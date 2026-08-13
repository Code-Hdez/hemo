from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Protocol

from app.modules.llm_chat.application.services.conversation_memory import normalize_text
from app.modules.llm_chat.domain.clinical import ConversationMemory, ResolvedQuestion
from app.modules.llm_chat.domain.entities import ChatMessageRecord


class ConversationFactRepository(Protocol):
    async def conversation_turns(
        self,
        conversation_id: str,
        *,
        context_revision: int | None = None,
        roles: tuple[str, ...] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ChatMessageRecord]: ...

    async def recent(
        self,
        conversation_id: str,
        limit: int,
    ) -> list[ChatMessageRecord]: ...


# Every fact this resolver reports sits at one of the two ends of the
# transcript: the opening question and the answer paired with it, or the
# recent exchanges the user means by "what have I asked" / "what did you say".
# Two bounded windows answer the same questions as the full transcript while
# keeping the cost per turn constant instead of growing with the length of the
# conversation.
_OPENING_TURN_WINDOW = 8
_RECENT_TURN_WINDOW = 40


@dataclass(frozen=True, slots=True)
class ConversationFacts:
    query_kind: str
    first_question: str | None
    first_answer: str | None
    questions: tuple[str, ...]
    latest_answer: str | None

    def prompt_payload(self) -> dict[str, object]:
        return {
            "query_kind": self.query_kind,
            "first_question": self.first_question,
            "first_answer": self.first_answer,
            "questions": list(self.questions),
            "latest_answer": self.latest_answer,
            "question_count": len(self.questions),
        }


class ConversationFactResolver:
    """Resolve transcript facts while leaving all user-facing prose to the LLM."""

    _first_answer = re.compile(
        r"\b(que|cual).{0,20}(respondiste|respuesta|contestaste|dijiste).{0,25}"
        r"(primera pregunta|primero)\b|"
        r"\b(respondiste|respuesta|contestaste|dijiste).{0,25}primera pregunta\b"
    )
    _first_question = re.compile(
        r"\b(primera pregunta|pregunte primero|primero te pregunte)\b"
    )
    _latest_answer = re.compile(
        r"\b(que me dijiste|dijiste antes|mencionamos anteriormente|ultima respuesta)\b"
    )

    async def resolve(
        self,
        *,
        repository: ConversationFactRepository,
        conversation_id: str,
        memory: ConversationMemory,
        question: ResolvedQuestion,
    ) -> ConversationFacts:
        # No context_revision filter: "what was my first question" must find
        # the true first question of this authorized conversation even after
        # a hemogram/profile change rotated the clinical revision since then.
        opening = await repository.conversation_turns(
            conversation_id, limit=_OPENING_TURN_WINDOW
        )
        latest = await repository.recent(conversation_id, _RECENT_TURN_WINDOW)
        turns = self._merged_window(opening, latest)
        users = [turn for turn in turns if turn.role == "user"]
        assistants = [turn for turn in turns if turn.role == "assistant"]
        first = users[0] if users else None
        first_answer = self._paired_answer(turns, first)
        normalized = normalize_text(question.original)
        query_kind = (
            "first_answer"
            if self._first_answer.search(normalized)
            else "first_question"
            if self._first_question.search(normalized)
            else "latest_answer"
            if self._latest_answer.search(normalized)
            else "question_list"
        )
        return ConversationFacts(
            query_kind=query_kind,
            first_question=(first.content if first is not None else None),
            first_answer=(first_answer.content if first_answer is not None else None),
            questions=tuple(turn.content for turn in users),
            latest_answer=(assistants[-1].content if assistants else None),
        )

    @staticmethod
    def _merged_window(
        opening: list[ChatMessageRecord],
        latest: list[ChatMessageRecord],
    ) -> list[ChatMessageRecord]:
        """Splice both ascending windows into one ascending transcript view.

        They overlap completely for short conversations, so de-duplication by
        message id — not concatenation — is what keeps a two-turn chat
        reporting two questions instead of four.
        """
        seen = {turn.id for turn in opening}
        return [
            *opening,
            *(turn for turn in latest if turn.id not in seen),
        ]

    @staticmethod
    def _paired_answer(
        turns: list[ChatMessageRecord],
        question: ChatMessageRecord | None,
    ) -> ChatMessageRecord | None:
        if question is None:
            return None
        return next(
            (
                turn
                for turn in turns
                if turn.role == "assistant"
                and turn.turn_index is not None
                and turn.turn_index == question.turn_index
            ),
            None,
        )
