from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.modules.llm_chat.api.schemas import ChatRequest


def test_general_chat_rejects_analysis_id() -> None:
    with pytest.raises(ValidationError, match="analysis_id"):
        ChatRequest(
            client_message_id=uuid4(),
            message="¿Qué son las plaquetas?",
            context_scope="general",
            analysis_id="abc123",
        )


def test_selected_chat_requires_analysis_id() -> None:
    with pytest.raises(ValidationError, match="analysis_id"):
        ChatRequest(
            client_message_id=uuid4(),
            message="Explícame este resultado",
            context_scope="uploaded_analysis",
        )


def test_history_chat_requires_pet_id_and_forbids_analysis_in_canonical_mode() -> None:
    with pytest.raises(ValidationError, match="pet_id"):
        ChatRequest(
            client_message_id=uuid4(),
            message="Compara los resultados",
            context_scope="historical_analysis",
        )
    request = ChatRequest(
        client_message_id=uuid4(),
        message="Compara los resultados",
        context_scope="historical_analysis",
        pet_id="pet-1",
    )
    assert request.pet_id == "pet-1"
    with pytest.raises(ValidationError, match="analysis_id"):
        ChatRequest(
            client_message_id=uuid4(),
            message="Compara los resultados",
            context_scope="hemogram_history",
            pet_id="pet-1",
            analysis_id="analysis-1",
        )


def test_chat_request_strips_message_and_forbids_unknown_options() -> None:
    # ChatOptions no longer accepts "thinking" (or any field): the qualified
    # generation profile fixes it server-side and no client input can
    # override it, so every key is now forbidden — not just unrecognized
    # ones like "temperature" below.
    request = ChatRequest(
        client_message_id=uuid4(),
        message="  ¿Qué es el hematocrito?  ",
        context_scope="general",
    )

    assert request.message == "¿Qué es el hematocrito?"

    with pytest.raises(ValidationError, match="temperature"):
        ChatRequest(
            client_message_id=uuid4(),
            message="¿Qué es el hematocrito?",
            context_scope="general",
            options={"temperature": 0.9},
        )


def test_chat_message_limit_comes_from_runtime_settings() -> None:
    with pytest.raises(ValidationError, match="too_long"):
        ChatRequest(
            client_message_id=uuid4(),
            message="x" * (settings.CHAT_MESSAGE_MAX_CHARS + 1),
            context_scope="general",
        )
