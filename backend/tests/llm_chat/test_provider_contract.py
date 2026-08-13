from __future__ import annotations

import pytest

from app.modules.llm_chat.domain.provider_contract import (
    LLM_PROVIDER_CONTRACT_VERSION,
    PROVIDER_CORRELATION_HEADER,
    ProviderApiFlavor,
    ProviderFailureCode,
    ProviderTimeoutPolicy,
    RemoteLLMProviderContract,
    is_retryable_provider_failure,
    normalize_provider_failure_code,
)
from app.modules.llm_chat.api.router import _RUNTIME_ERRORS


def timeout_policy() -> ProviderTimeoutPolicy:
    return ProviderTimeoutPolicy(
        connect_seconds=3,
        read_seconds=75,
        write_seconds=15,
        pool_seconds=5,
        stream_deadline_seconds=150,
        heartbeat_seconds=15,
    )


def test_remote_provider_contract_is_private_versioned_and_sanitized() -> None:
    contract = RemoteLLMProviderContract(
        provider="ollama",
        api_flavor=ProviderApiFlavor.OLLAMA_NATIVE,
        base_url="http://10.128.0.3:11434",
        model="qwen3:4b-instruct-2507-q4_K_M",
        expected_digest="sha256:" + "a" * 64,
        expected_quantization="Q4_K_M",
        timeouts=timeout_policy(),
        connection_retries=1,
    )

    public = contract.to_safe_dict()
    assert public["contract_version"] == LLM_PROVIDER_CONTRACT_VERSION
    assert public["private_network_required"] is True
    assert public["correlation_header"] == PROVIDER_CORRELATION_HEADER
    assert public["retry_scope"] == "connection_establishment_only"
    assert "base_url" not in public
    assert "10.128.0.3" not in str(public)


@pytest.mark.parametrize(
    "code",
    [
        ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE,
        ProviderFailureCode.LLM_PROVIDER_CONNECT_TIMEOUT,
        ProviderFailureCode.LLM_PROVIDER_READ_TIMEOUT,
        ProviderFailureCode.LLM_PROVIDER_OVERLOADED,
    ],
)
def test_transient_provider_failures_are_retryable_and_have_public_mapping(
    code: ProviderFailureCode,
) -> None:
    assert is_retryable_provider_failure(code) is True
    assert code.value in _RUNTIME_ERRORS


def test_model_identity_mismatch_is_not_blindly_retryable() -> None:
    assert (
        is_retryable_provider_failure(
            ProviderFailureCode.LLM_PROVIDER_DIGEST_MISMATCH
        )
        is False
    )


def test_gpu_off_maps_to_structured_retryable_503() -> None:
    http_status, recovery_action, retry_after_ms, category = _RUNTIME_ERRORS[
        ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value
    ]

    assert http_status == 503
    assert recovery_action == "retry_same_turn"
    assert retry_after_ms == 2000
    assert category == "provider"


@pytest.mark.parametrize(
    ("internal", "public"),
    [
        ("ollama_unavailable", "LLM_PROVIDER_UNAVAILABLE"),
        ("ollama_connect_timeout", "LLM_PROVIDER_CONNECT_TIMEOUT"),
        ("ollama_read_timeout", "LLM_PROVIDER_READ_TIMEOUT"),
        ("ollama_model_digest_mismatch", "LLM_PROVIDER_DIGEST_MISMATCH"),
        ("provider_invalid_response", "LLM_PROVIDER_INVALID_RESPONSE"),
    ],
)
def test_provider_specific_codes_are_normalized_before_the_public_boundary(
    internal: str,
    public: str,
) -> None:
    normalized = normalize_provider_failure_code(internal)

    assert normalized is not None
    assert normalized.value == public
    assert not public.casefold().startswith("ollama")


def test_provider_contract_rejects_mutable_model_and_credentialed_url() -> None:
    with pytest.raises(ValueError, match="non-latest"):
        RemoteLLMProviderContract(
            provider="ollama",
            api_flavor=ProviderApiFlavor.OLLAMA_NATIVE,
            base_url="http://ollama:11434",
            model="qwen3:latest",
            timeouts=timeout_policy(),
            connection_retries=1,
        )

    with pytest.raises(ValueError, match="credentials"):
        RemoteLLMProviderContract(
            provider="ollama",
            api_flavor=ProviderApiFlavor.OLLAMA_NATIVE,
            base_url="http://user:secret@ollama:11434",
            model="qwen3:4b",
            timeouts=timeout_policy(),
            connection_retries=1,
        )


def test_provider_contract_bounds_retry_scope_and_stream_deadline() -> None:
    with pytest.raises(ValueError, match="zero or one"):
        RemoteLLMProviderContract(
            provider="ollama",
            api_flavor=ProviderApiFlavor.OLLAMA_NATIVE,
            base_url="http://ollama:11434",
            model="qwen3:4b",
            timeouts=timeout_policy(),
            connection_retries=2,
        )

    with pytest.raises(ValueError, match="stream deadline"):
        ProviderTimeoutPolicy(
            connect_seconds=3,
            read_seconds=151,
            write_seconds=15,
            pool_seconds=5,
            stream_deadline_seconds=150,
            heartbeat_seconds=15,
        )


def test_provider_contract_cannot_disable_private_network_requirement() -> None:
    with pytest.raises(ValueError, match="private network"):
        RemoteLLMProviderContract(
            provider="ollama",
            api_flavor=ProviderApiFlavor.OLLAMA_NATIVE,
            base_url="http://ollama:11434",
            model="qwen3:4b",
            timeouts=timeout_policy(),
            connection_retries=1,
            private_network_required=False,
        )
