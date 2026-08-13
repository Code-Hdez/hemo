from __future__ import annotations

import pytest

from app.core.availability import (
    AVAILABILITY_CONTRACT_VERSION,
    ChatAvailability,
    ProviderAvailability,
    RagAvailability,
    ReadinessSnapshot,
    liveness_payload,
)


def ready_provider() -> ProviderAvailability:
    return ProviderAvailability(
        provider="ollama",
        model="qwen3:4b-instruct-2507-q4_K_M",
        ready=True,
        identity_verified=True,
    )


def unavailable_provider() -> ProviderAvailability:
    return ProviderAvailability(
        provider="ollama",
        model="qwen3:4b-instruct-2507-q4_K_M",
        ready=False,
        code="LLM_PROVIDER_UNAVAILABLE",
        retryable=True,
        identity_verified=None,
    )


def chat_availability(
    provider: ProviderAvailability,
    *,
    rag_required: bool = True,
    rag_ready: bool = True,
) -> ChatAvailability:
    return ChatAvailability(
        provider=provider,
        module_ready=True,
        rag_required=rag_required,
        chroma_ready=rag_ready,
        collection_ready=rag_ready,
        rag_index_ready=rag_ready,
    )


def test_liveness_does_not_probe_or_inherit_dependency_state() -> None:
    payload = liveness_payload()

    assert payload == {
        "contract_version": AVAILABILITY_CONTRACT_VERSION,
        "probe": "liveness",
        "status": "ok",
        "alive": True,
    }


def test_gpu_off_keeps_core_ready_and_degrades_only_chat() -> None:
    snapshot = ReadinessSnapshot(
        database_ready=True,
        local_model_required=False,
        local_model_ready=False,
        chat=chat_availability(unavailable_provider()),
    )

    payload = snapshot.to_public_dict()
    # A chat PROVIDER outage now fails chat_ready outright (fail-closed),
    # not merely "degraded": only an independently-degradable RAG shortfall
    # with a ready provider still reports "degraded" (see
    # ChatAvailability.status / d6979f76).
    assert payload["status"] == "fail"
    assert payload["core_ready"] is True
    assert payload["chat_ready"] is False
    assert payload["provider_ready"] is False
    assert "LLM_PROVIDER_NOT_READY" in payload["codes"]

    chat_payload = snapshot.chat.to_public_dict()
    assert chat_payload["probe"] == "chat_availability"
    assert chat_payload["provider"]["probe"] == "provider_availability"  # type: ignore[index]
    assert chat_payload["rag"]["probe"] == "rag_availability"  # type: ignore[index]


def test_ready_provider_and_required_rag_make_the_whole_release_ready() -> None:
    snapshot = ReadinessSnapshot(
        database_ready=True,
        local_model_required=False,
        local_model_ready=False,
        chat=chat_availability(ready_provider()),
    )

    assert snapshot.status.value == "ok"
    assert snapshot.core_ready is True
    assert snapshot.chat_ready is True
    assert snapshot.codes == ()


def test_database_failure_is_the_core_failure_boundary() -> None:
    snapshot = ReadinessSnapshot(
        database_ready=False,
        local_model_required=False,
        local_model_ready=False,
        chat=chat_availability(ready_provider()),
    )

    assert snapshot.status.value == "fail"
    assert snapshot.core_ready is False
    assert snapshot.chat_ready is False
    assert "DATABASE_NOT_READY" in snapshot.codes


def test_required_rag_failure_degrades_chat_without_failing_core() -> None:
    snapshot = ReadinessSnapshot(
        database_ready=True,
        local_model_required=False,
        local_model_ready=False,
        chat=chat_availability(ready_provider(), rag_ready=False),
    )

    assert snapshot.status.value == "degraded"
    assert snapshot.core_ready is True
    # RAG is an independently degradable capability: chat_ready no longer
    # factors in RAG readiness at all, so a required-but-unready RAG index
    # degrades quality/status without taking chat_ready down (see
    # ChatAvailability.chat_ready / d6979f76).
    assert snapshot.chat_ready is True
    assert {"CHROMA_NOT_READY", "RAG_NOT_READY"} <= set(snapshot.codes)


def test_invalid_provider_identity_uses_only_the_public_provider_taxonomy() -> None:
    provider = ProviderAvailability(
        provider="test-provider",
        model="qwen3:4b-instruct-2507-q4_K_M",
        ready=False,
        code="LLM_PROVIDER_DIGEST_MISMATCH",
        retryable=False,
        identity_verified=False,
    )
    snapshot = ReadinessSnapshot(
        database_ready=True,
        local_model_required=False,
        local_model_ready=False,
        chat=chat_availability(provider),
    )

    assert "LLM_PROVIDER_IDENTITY_INVALID" in snapshot.codes
    assert all("OLLAMA" not in code for code in snapshot.codes)


def test_disabled_rag_is_not_a_readiness_dependency() -> None:
    chat = chat_availability(
        ready_provider(),
        rag_required=False,
        rag_ready=False,
    )

    assert chat.rag_ready is True
    assert chat.chat_ready is True
    assert chat.codes == ()


def test_rag_contract_rejects_an_index_without_its_collection() -> None:
    with pytest.raises(ValueError, match="requires Chroma and its collection"):
        RagAvailability(
            required=True,
            chroma_ready=True,
            collection_ready=False,
            index_ready=True,
        )
