from __future__ import annotations

import dataclasses
from uuid import uuid4

from app.core.config import settings as _app_settings
from app.modules.llm_chat.application.dto import ChatCommand
from app.modules.llm_chat.application.services.chat_profile_policy import (
    ChatProfilePolicy,
)
from app.modules.llm_chat.application.services.token_budget import input_token_budget
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings
from app.modules.llm_chat.domain.value_objects import (
    SafetyAction,
    SafetyDecision,
    SafetyIntent,
)

_BASE_SETTINGS = GenerationProfileSettings.from_settings(_app_settings)


def _policy(
    *, max_context_tokens: int = 4096, max_output_tokens: int = 512
) -> ChatProfilePolicy:
    reserve = _BASE_SETTINGS.context_reserve_tokens
    max_input = max(1, max_context_tokens - max_output_tokens - reserve)
    settings = dataclasses.replace(
        _BASE_SETTINGS,
        context_length=max_context_tokens,
        general_context_length=None,
        selected_context_length=None,
        history_context_length=None,
        max_input_tokens=max_input,
        num_predict=max_output_tokens,
        repair_context_length=max_context_tokens,
        repair_max_input_tokens=max_input,
        repair_num_predict=max_output_tokens,
    )
    return ChatProfilePolicy(settings=settings)


def _command(
    message: str,
    *,
    context_scope: str = "general",
    analysis_id: str | None = None,
) -> ChatCommand:
    return ChatCommand(
        user_id="user-1",
        client_message_id=str(uuid4()),
        conversation_id=None,
        message=message,
        context_scope=context_scope,
        analysis_id=analysis_id,
    )


def _decision(intent: SafetyIntent = SafetyIntent.EDUCATIONAL_ALLOWED) -> SafetyDecision:
    return SafetyDecision(SafetyAction.ALLOW, intent=intent)


def test_greeting_uses_a_small_generative_profile_without_rag() -> None:
    profile = _policy().select(_command("Hola, buenas"), _decision())

    assert profile.name == "greeting"
    assert profile.use_llm is True
    assert profile.num_predict == 512
    assert profile.num_ctx == 4096


def test_definition_uses_small_rag_budget_and_short_generation() -> None:
    profile = _policy().select(
        _command("¿Qué son las plaquetas?"),
        _decision(),
    )

    assert profile.name == "definition"
    assert profile.rag_fetch_k == _BASE_SETTINGS.retrieval.fetch_k
    assert profile.rag_top_k == _BASE_SETTINGS.retrieval.top_k
    assert profile.rag_max_context_chars == _BASE_SETTINGS.retrieval.max_context_chars
    assert profile.history_limit == _BASE_SETTINGS.memory.history_limit
    assert profile.num_predict == 512
    assert profile.num_ctx == 4096


def test_value_explanation_uses_moderate_profile() -> None:
    profile = _policy().select(
        _command("¿Qué significa tener plaquetas bajas?"),
        _decision(SafetyIntent.RESULT_EXPLANATION_ALLOWED),
    )

    assert profile.name == "value_explanation"
    assert profile.rag_top_k == _BASE_SETTINGS.retrieval.top_k
    assert profile.rag_max_context_chars == _BASE_SETTINGS.retrieval.max_context_chars
    assert profile.num_predict == 512
    assert profile.num_ctx == 4096


def test_general_information_has_room_for_the_structured_response() -> None:
    profile = _policy().select(
        _command(
            "¿Qué información general aporta un hemograma canino y por qué debe "
            "interpretarlo un veterinario?"
        ),
        _decision(),
    )

    assert profile.name == "faq_simple"
    assert profile.num_predict == 512
    assert profile.num_ctx == 4096
    reserve = _BASE_SETTINGS.context_reserve_tokens
    assert (
        input_token_budget(
            num_ctx=profile.num_ctx,
            num_predict=profile.num_predict,
            reserve_tokens=reserve,
            max_input_tokens=profile.num_ctx - profile.num_predict - reserve,
        )
        >= 3200
    )


def test_uploaded_analysis_uses_hemogram_interpretation_profile() -> None:
    profile = _policy().select(
        _command(
            "Explícame este hemograma en palabras simples",
            context_scope="uploaded_analysis",
            analysis_id="analysis-1",
        ),
        _decision(SafetyIntent.RESULT_EXPLANATION_ALLOWED),
    )

    assert profile.name == "hemogram_interpretation"
    assert profile.rag_fetch_k == _BASE_SETTINGS.retrieval.fetch_k
    assert profile.rag_top_k == _BASE_SETTINGS.retrieval.top_k
    assert profile.rag_max_context_chars == _BASE_SETTINGS.retrieval.max_context_chars
    assert profile.num_predict == 512
    assert profile.num_ctx == 4096


def test_hematologic_pattern_has_room_for_a_complete_safe_answer() -> None:
    profile = _policy().select(
        _command(
            "¿Hay un patrón hematológico en este hemograma?",
            context_scope="selected_hemogram",
            analysis_id="analysis-1",
        ),
        _decision(SafetyIntent.HEMATOLOGIC_PATTERN),
    )

    assert profile.name == "hemogram_pattern"
    assert profile.num_predict == 512
    assert profile.num_ctx == 4096


def test_historical_scope_uses_history_comparison_profile() -> None:
    profile = _policy().select(
        _command(
            "Compara este hemograma con el anterior",
            context_scope="historical_analysis",
            analysis_id="analysis-2",
        ),
        _decision(SafetyIntent.RESULT_EXPLANATION_ALLOWED),
    )

    assert profile.name == "history_comparison"
    assert profile.rag_top_k == _BASE_SETTINGS.retrieval.top_k
    assert profile.rag_max_context_chars == _BASE_SETTINGS.retrieval.max_context_chars
    assert profile.history_limit == _BASE_SETTINGS.memory.history_limit
    assert profile.num_predict == 512


def test_non_allowed_safety_decision_uses_generative_guardrail_without_rag() -> None:
    profile = _policy().select(
        _command("¿Qué dosis de antibiótico le doy?"),
        SafetyDecision(
            SafetyAction.REFUSE_DOSE,
            response="No puedo dar dosis.",
            intent=SafetyIntent.DOSAGE_REQUEST_DISALLOWED,
            rule_id="dosage_request",
        ),
    )

    assert profile.name == "safety_guardrail"
    assert profile.use_llm is True
    assert profile.num_predict == 512
    assert profile.num_ctx == 4096


def test_profile_never_exceeds_the_effective_provider_token_limits() -> None:
    profile = _policy(max_output_tokens=128, max_context_tokens=2048).select(
        _command(
            "Interpreta el hemograma completo",
            context_scope="selected_hemogram",
            analysis_id="analysis-1",
        ),
        _decision(SafetyIntent.RESULT_EXPLANATION_ALLOWED),
    )

    assert profile.num_predict == 128
    assert profile.num_ctx == 2048


def test_repair_after_truncation_never_shrinks_the_output_budget() -> None:
    """M-5: un presupuesto de reparación menor que el del intento truncado
    garantiza una segunda truncación y desperdicia la llamada entera."""

    settings = dataclasses.replace(
        _BASE_SETTINGS,
        context_length=16384,
        general_context_length=None,
        selected_context_length=None,
        history_context_length=None,
        max_input_tokens=12000,
        num_predict=1280,
        repair_context_length=None,
        repair_max_input_tokens=None,
        repair_num_predict=1024,
    )
    base = settings.main_profile(
        name="selected_hemogram_main", context_scope="selected_hemogram"
    )

    intact = settings.repair_profile(name="repair", base=base)
    assert intact.num_predict == 1024

    grown = settings.repair_profile(name="repair", base=base, truncated=True)
    assert grown.num_predict == base.num_predict == 1280


def test_clinical_scopes_get_their_own_temperature_override() -> None:
    """La lotería del validador vive en los caminos clínicos: la temperatura
    baja ahí sin tocar el tono del chat general. `is not None`, no `or`:
    un 0.0 configurado es una decisión válida."""

    settings = dataclasses.replace(
        _BASE_SETTINGS,
        general_temperature=None,
        selected_temperature=0.15,
        history_temperature=0.15,
    )

    selected = settings.main_profile(name="m", context_scope="selected_hemogram")
    history = settings.main_profile(name="m", context_scope="hemogram_history")
    general = settings.main_profile(name="m", context_scope="general")

    assert selected.temperature == 0.15
    assert history.temperature == 0.15
    assert general.temperature == settings.temperature
