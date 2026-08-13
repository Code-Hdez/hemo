from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.modules.llm_chat.application.dto import ChatCommand
from app.modules.llm_chat.domain.generation_config import (
    EffectiveGenerationProfile,
    GenerationProfileSettings,
)
from app.modules.llm_chat.domain.value_objects import (
    SafetyAction,
    SafetyDecision,
    SafetyIntent,
)


@dataclass(frozen=True, slots=True)
class ChatProfile:
    name: str
    use_llm: bool
    generation: EffectiveGenerationProfile
    rag_fetch_k: int
    rag_top_k: int
    rag_max_context_chars: int
    history_limit: int
    min_score: float

    @property
    def num_predict(self) -> int:
        return self.generation.num_predict

    @property
    def num_ctx(self) -> int:
        return self.generation.num_ctx


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in folded if not unicodedata.combining(char))


class ChatProfilePolicy:
    _greeting = re.compile(
        r"^\s*(hola|buenas|buenos dias|buenas tardes|buenas noches|saludos)"
        r"(?:[,\s]+(buenas|buenos dias|buenas tardes|buenas noches))?[.!¡!?\s]*$"
    )
    _capabilities = re.compile(
        r"\b(que puedes hacer|como me puedes ayudar|para que sirve este chat)\b"
    )
    _definition = re.compile(
        r"\b(que\s+(?:es|son)|definicion|funcion|para\s+que\s+sirve(?:n)?)\b"
    )
    _history = re.compile(r"\b(compara|comparar|anterior|historial|evolucion)\b")
    _full_study = re.compile(
        r"\b(hemograma completo|todo el hemograma|todos los valores|"
        r"interpretacion completa|interpreta el hemograma)\b"
    )
    _hematologic_pattern = re.compile(r"\bpatron(?:es)?\s+hematologic[oa]s?\b")

    def __init__(
        self,
        *,
        settings: GenerationProfileSettings,
    ) -> None:
        self.settings = settings

    def select(
        self,
        command: ChatCommand,
        decision: SafetyDecision,
        *,
        boundary_only: bool = False,
    ) -> ChatProfile:
        if decision.action is not SafetyAction.ALLOW:
            # ``boundary_only`` is the pre-generation guard's SHORT_CIRCUIT:
            # the turn writes a policy boundary and nothing else, so it is
            # sized for one. Other non-ALLOW turns keep the full profile —
            # a clarification or an insufficient-evidence answer still
            # discusses the case.
            return self._profile(
                command, name="safety_guardrail", boundary_only=boundary_only
            )

        normalized = _normalize(command.message)
        if self._greeting.search(normalized):
            return self._profile(command, name="greeting")
        if self._capabilities.search(normalized):
            return self._profile(command, name="faq_simple")
        if decision.intent is SafetyIntent.SOURCE_OR_BIBLIOGRAPHY_REQUEST:
            return self._profile(command, name="source_bibliography")
        if command.context_scope in {
            "historical_analysis",
            "hemogram_history",
        } or self._history.search(normalized):
            return self._profile(command, name="history_comparison")
        if command.analysis_id or command.context_scope in {
            "uploaded_analysis",
            "selected_hemogram",
        }:
            full_study = bool(self._full_study.search(normalized))
            hematologic_pattern = (
                decision.intent is SafetyIntent.HEMATOLOGIC_PATTERN
                or bool(self._hematologic_pattern.search(normalized))
            )
            return self._profile(
                command,
                name=(
                    "hemogram_full_interpretation"
                    if full_study
                    else "hemogram_pattern"
                    if hematologic_pattern
                    else "hemogram_interpretation"
                ),
            )
        if (
            self._definition.search(normalized)
            or decision.intent is SafetyIntent.ALLOWED_CBC_CONCEPT_WITH_TYPOS
        ):
            return self._profile(command, name="definition")
        if decision.intent is SafetyIntent.RESULT_EXPLANATION_ALLOWED:
            return self._profile(command, name="value_explanation")
        return self._profile(command, name="faq_simple")

    def _profile(
        self,
        command: ChatCommand,
        *,
        name: str,
        boundary_only: bool = False,
    ) -> ChatProfile:
        retrieval = self.settings.retrieval
        build = (
            self.settings.boundary_profile
            if boundary_only
            else self.settings.main_profile
        )
        return ChatProfile(
            name=name,
            use_llm=True,
            generation=build(
                name=name,
                context_scope=command.context_scope,
            ),
            rag_fetch_k=retrieval.fetch_k,
            rag_top_k=retrieval.top_k,
            rag_max_context_chars=retrieval.max_context_chars,
            history_limit=self.settings.memory.history_limit,
            min_score=retrieval.min_relevance_score,
        )
