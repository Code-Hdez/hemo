from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Literal
from urllib.parse import urlsplit


LLM_PROVIDER_CONTRACT_VERSION = "hemovet.llm-provider/v1"
PROVIDER_CORRELATION_HEADER = "X-HemoVet-Correlation-ID"

_DIGEST_PATTERN = re.compile(r"^(?:sha256:)?[a-fA-F0-9]{64}$")
_QUANTIZATION_PATTERN = re.compile(r"^[A-Za-z0-9_]{2,32}$")


class ProviderApiFlavor(StrEnum):
    OLLAMA_NATIVE = "ollama-native/v1"
    OPENAI_COMPATIBLE = "openai-compatible/v1"


class ProviderFailureCode(StrEnum):
    """Provider-neutral codes that are safe to expose outside infrastructure."""

    LLM_PROVIDER_CONNECT_TIMEOUT = "LLM_PROVIDER_CONNECT_TIMEOUT"
    LLM_PROVIDER_READ_TIMEOUT = "LLM_PROVIDER_READ_TIMEOUT"
    LLM_PROVIDER_OVERLOADED = "LLM_PROVIDER_OVERLOADED"
    LLM_PROVIDER_UNAVAILABLE = "LLM_PROVIDER_UNAVAILABLE"
    LLM_PROVIDER_INVALID_RESPONSE = "LLM_PROVIDER_INVALID_RESPONSE"
    LLM_PROVIDER_IDENTITY_UNVERIFIED = "LLM_PROVIDER_IDENTITY_UNVERIFIED"
    LLM_PROVIDER_MODEL_MISMATCH = "LLM_PROVIDER_MODEL_MISMATCH"
    LLM_PROVIDER_DIGEST_MISMATCH = "LLM_PROVIDER_DIGEST_MISMATCH"
    LLM_PROVIDER_QUANTIZATION_MISMATCH = "LLM_PROVIDER_QUANTIZATION_MISMATCH"
    LLM_PROVIDER_REVISION_MISMATCH = "LLM_PROVIDER_REVISION_MISMATCH"


_INTERNAL_FAILURE_CODES: dict[str, ProviderFailureCode] = {
    "provider_timeout": ProviderFailureCode.LLM_PROVIDER_READ_TIMEOUT,
    "provider_connect_timeout": ProviderFailureCode.LLM_PROVIDER_CONNECT_TIMEOUT,
    "provider_read_timeout": ProviderFailureCode.LLM_PROVIDER_READ_TIMEOUT,
    "provider_overloaded": ProviderFailureCode.LLM_PROVIDER_OVERLOADED,
    "provider_unavailable": ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE,
    "provider_invalid_response": ProviderFailureCode.LLM_PROVIDER_INVALID_RESPONSE,
    # Ollama remains an infrastructure concern. These legacy/internal codes are
    # normalized before crossing an HTTP or health boundary.
    "ollama_connect_timeout": ProviderFailureCode.LLM_PROVIDER_CONNECT_TIMEOUT,
    "ollama_read_timeout": ProviderFailureCode.LLM_PROVIDER_READ_TIMEOUT,
    "ollama_overloaded": ProviderFailureCode.LLM_PROVIDER_OVERLOADED,
    "ollama_unavailable": ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE,
    "ollama_invalid_response": ProviderFailureCode.LLM_PROVIDER_INVALID_RESPONSE,
    "ollama_model_identity_unverified": (
        ProviderFailureCode.LLM_PROVIDER_IDENTITY_UNVERIFIED
    ),
    "ollama_model_tag_mismatch": ProviderFailureCode.LLM_PROVIDER_MODEL_MISMATCH,
    "ollama_model_digest_mismatch": ProviderFailureCode.LLM_PROVIDER_DIGEST_MISMATCH,
    "ollama_model_quantization_mismatch": (
        ProviderFailureCode.LLM_PROVIDER_QUANTIZATION_MISMATCH
    ),
    "runtime_revision_mismatch": ProviderFailureCode.LLM_PROVIDER_REVISION_MISMATCH,
}


_RETRYABLE_FAILURES = frozenset(
    {
        ProviderFailureCode.LLM_PROVIDER_CONNECT_TIMEOUT,
        ProviderFailureCode.LLM_PROVIDER_READ_TIMEOUT,
        ProviderFailureCode.LLM_PROVIDER_OVERLOADED,
        ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE,
    }
)


def normalize_provider_failure_code(
    code: str | ProviderFailureCode,
) -> ProviderFailureCode | None:
    """Translate provider-specific implementation errors to the public taxonomy."""

    if isinstance(code, ProviderFailureCode):
        return code
    candidate = str(code).strip()
    if not candidate:
        return None
    try:
        return ProviderFailureCode(candidate)
    except ValueError:
        return _INTERNAL_FAILURE_CODES.get(candidate.casefold())


def is_retryable_provider_failure(code: str | ProviderFailureCode) -> bool:
    normalized = normalize_provider_failure_code(code)
    if normalized is None:
        return False
    return normalized in _RETRYABLE_FAILURES


@dataclass(frozen=True, slots=True)
class ProviderTimeoutPolicy:
    connect_seconds: float
    read_seconds: float
    write_seconds: float
    pool_seconds: float
    stream_deadline_seconds: float
    heartbeat_seconds: float

    def __post_init__(self) -> None:
        values = {
            "connect_seconds": self.connect_seconds,
            "read_seconds": self.read_seconds,
            "write_seconds": self.write_seconds,
            "pool_seconds": self.pool_seconds,
            "stream_deadline_seconds": self.stream_deadline_seconds,
            "heartbeat_seconds": self.heartbeat_seconds,
        }
        for name, value in values.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.connect_seconds > self.stream_deadline_seconds:
            raise ValueError("connect timeout cannot exceed the stream deadline")
        if self.read_seconds > self.stream_deadline_seconds:
            raise ValueError("read timeout cannot exceed the stream deadline")
        if self.heartbeat_seconds >= self.stream_deadline_seconds:
            raise ValueError("heartbeat must be lower than the stream deadline")


@dataclass(frozen=True, slots=True)
class RemoteLLMProviderContract:
    """Versioned contract between the modular backend and remote inference."""

    provider: str
    api_flavor: ProviderApiFlavor
    base_url: str
    model: str
    timeouts: ProviderTimeoutPolicy
    connection_retries: int
    expected_digest: str | None = None
    expected_quantization: str | None = None
    private_network_required: bool = True
    correlation_header: str = PROVIDER_CORRELATION_HEADER
    cancellation_policy: Literal[
        "propagate_client_cancellation"
    ] = "propagate_client_cancellation"
    retry_scope: Literal[
        "connection_establishment_only"
    ] = "connection_establishment_only"

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider is required")
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("provider base_url must be an absolute HTTP URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("provider base_url cannot contain credentials or query data")
        normalized_model = self.model.strip()
        if not normalized_model or normalized_model.casefold().endswith(":latest"):
            raise ValueError("provider model must be an explicit non-latest tag")
        if self.connection_retries not in {0, 1}:
            raise ValueError("connection retries must be zero or one")
        if self.expected_digest and not _DIGEST_PATTERN.fullmatch(
            self.expected_digest
        ):
            raise ValueError("expected model digest must be SHA-256")
        if self.expected_quantization and not _QUANTIZATION_PATTERN.fullmatch(
            self.expected_quantization
        ):
            raise ValueError("expected quantization is invalid")
        if not self.private_network_required:
            raise ValueError("the production inference contract requires private network")
        if self.correlation_header != PROVIDER_CORRELATION_HEADER:
            raise ValueError("the provider correlation header is versioned")
        if self.cancellation_policy != "propagate_client_cancellation":
            raise ValueError("the provider cancellation policy is versioned")
        if self.retry_scope != "connection_establishment_only":
            raise ValueError("the provider retry scope is versioned")

    def to_safe_dict(self) -> dict[str, object]:
        """Describe the contract without revealing its private host or secrets."""

        return {
            "contract_version": LLM_PROVIDER_CONTRACT_VERSION,
            "provider": self.provider,
            "api_flavor": self.api_flavor.value,
            "model": self.model,
            "expected_digest_configured": bool(self.expected_digest),
            "expected_quantization": self.expected_quantization,
            "private_network_required": self.private_network_required,
            "correlation_header": self.correlation_header,
            "connection_retries": self.connection_retries,
            "retry_scope": self.retry_scope,
            "cancellation_policy": self.cancellation_policy,
            "timeouts": {
                "connect_seconds": self.timeouts.connect_seconds,
                "read_seconds": self.timeouts.read_seconds,
                "write_seconds": self.timeouts.write_seconds,
                "pool_seconds": self.timeouts.pool_seconds,
                "stream_deadline_seconds": self.timeouts.stream_deadline_seconds,
                "heartbeat_seconds": self.timeouts.heartbeat_seconds,
            },
        }
