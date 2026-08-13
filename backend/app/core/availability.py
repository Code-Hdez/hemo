from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


AVAILABILITY_CONTRACT_VERSION = "hemovet.availability/v1"


class OperationalStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    FAIL = "fail"


class ProbeKind(StrEnum):
    LIVENESS = "liveness"
    READINESS = "readiness"
    CHAT_AVAILABILITY = "chat_availability"
    RAG_AVAILABILITY = "rag_availability"
    PROVIDER_AVAILABILITY = "provider_availability"


def _unique_codes(codes: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(code for code in codes if code))


@dataclass(frozen=True, slots=True)
class ProviderAvailability:
    """Sanitized availability of the external inference boundary.

    The object deliberately excludes the provider URL, host and credentials.
    Those values belong to private runtime configuration, not public health
    payloads.
    """

    provider: str
    model: str | None
    ready: bool
    code: str | None = None
    retryable: bool = False
    identity_verified: bool | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider is required")
        if self.ready and self.code is not None:
            raise ValueError("a ready provider cannot expose an error code")
        if self.ready and self.identity_verified is False:
            raise ValueError("a provider with invalid identity cannot be ready")
        if not self.ready and not self.code:
            raise ValueError("an unavailable provider requires a stable error code")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "contract_version": AVAILABILITY_CONTRACT_VERSION,
            "probe": ProbeKind.PROVIDER_AVAILABILITY.value,
            "status": "ready" if self.ready else "unavailable",
            "provider": self.provider,
            "model": self.model,
            "ready": self.ready,
            "code": self.code,
            "retryable": self.retryable,
            "identity_verified": self.identity_verified,
        }


@dataclass(frozen=True, slots=True)
class RagAvailability:
    """Availability of the local retrieval capability."""

    required: bool
    chroma_ready: bool
    collection_ready: bool
    index_ready: bool

    def __post_init__(self) -> None:
        if self.index_ready and (not self.chroma_ready or not self.collection_ready):
            raise ValueError("a ready RAG index requires Chroma and its collection")

    @property
    def ready(self) -> bool:
        if not self.required:
            return True
        return self.chroma_ready and self.collection_ready and self.index_ready

    @property
    def codes(self) -> tuple[str, ...]:
        if not self.required:
            return ()
        codes: list[str] = []
        if not self.chroma_ready:
            codes.append("chroma_not_ready")
        if not self.collection_ready:
            codes.append("rag_collection_not_ready")
        if not self.index_ready:
            codes.append("rag_not_ready")
        return _unique_codes(codes)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "contract_version": AVAILABILITY_CONTRACT_VERSION,
            "probe": ProbeKind.RAG_AVAILABILITY.value,
            "status": "ready" if self.ready else "unavailable",
            "required": self.required,
            "ready": self.ready,
            "chroma_ready": self.chroma_ready,
            "collection_ready": self.collection_ready,
            "index_ready": self.index_ready,
            "codes": list(self.codes),
        }


@dataclass(frozen=True, slots=True)
class ChatAvailability:
    """Availability of chat without conflating it with process readiness."""

    provider: ProviderAvailability
    module_ready: bool
    rag_required: bool
    chroma_ready: bool
    collection_ready: bool
    rag_index_ready: bool

    def __post_init__(self) -> None:
        _ = self.rag

    @property
    def rag(self) -> RagAvailability:
        return RagAvailability(
            required=self.rag_required,
            chroma_ready=self.chroma_ready,
            collection_ready=self.collection_ready,
            index_ready=self.rag_index_ready,
        )

    @property
    def rag_ready(self) -> bool:
        return self.rag.ready

    @property
    def chat_ready(self) -> bool:
        # RAG is an optional, independently degradable capability: its module
        # or provider must be up to answer at all, but a Chroma/index outage
        # must not take down general, database-grounded, or safety answers.
        return self.module_ready and self.provider.ready

    @property
    def degraded(self) -> bool:
        return self.chat_ready and not self.rag_ready

    @property
    def status(self) -> OperationalStatus:
        if not self.chat_ready:
            return OperationalStatus.FAIL
        if self.degraded:
            return OperationalStatus.DEGRADED
        return OperationalStatus.OK

    @property
    def codes(self) -> tuple[str, ...]:
        codes: list[str] = []
        if not self.module_ready:
            codes.append("chat_module_not_ready")
        if not self.provider.ready and self.provider.code:
            codes.append(self.provider.code)
        codes.extend(self.rag.codes)
        return _unique_codes(codes)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "contract_version": AVAILABILITY_CONTRACT_VERSION,
            "probe": ProbeKind.CHAT_AVAILABILITY.value,
            "status": self.status.value,
            "chat_ready": self.chat_ready,
            "degraded": self.degraded,
            "module_ready": self.module_ready,
            "provider_ready": self.provider.ready,
            # Compatibility alias retained until all callers consume
            # ``provider_ready``.
            "llm_ready": self.provider.ready,
            "rag_required": self.rag_required,
            "rag_ready": self.rag_ready,
            "chroma_ready": self.chroma_ready,
            "collection_ready": self.collection_ready,
            "codes": list(self.codes),
            "provider": self.provider.to_public_dict(),
            "rag": self.rag.to_public_dict(),
        }


@dataclass(frozen=True, slots=True)
class ReadinessSnapshot:
    """Aggregate deployment readiness with an independently degradable chat."""

    database_ready: bool
    local_model_required: bool
    local_model_ready: bool
    chat: ChatAvailability
    blocking_codes: tuple[str, ...] = ()
    advisory_codes: tuple[str, ...] = ()

    @property
    def core_ready(self) -> bool:
        model_ready = not self.local_model_required or self.local_model_ready
        return self.database_ready and model_ready and not self.blocking_codes

    @property
    def chat_ready(self) -> bool:
        return self.core_ready and self.chat.chat_ready

    @property
    def status(self) -> OperationalStatus:
        if not self.core_ready:
            return OperationalStatus.FAIL
        if not self.chat_ready:
            return OperationalStatus.FAIL
        if self.chat.degraded or self.advisory_codes:
            return OperationalStatus.DEGRADED
        return OperationalStatus.OK

    @property
    def codes(self) -> tuple[str, ...]:
        codes: list[str] = []
        if not self.database_ready:
            codes.append("DATABASE_NOT_READY")
        if self.local_model_required and not self.local_model_ready:
            codes.append("MODEL_NOT_READY")
        codes.extend(self.blocking_codes)
        if not self.chat.module_ready:
            codes.append("CHAT_MODULE_NOT_READY")
        if not self.chat.provider.ready:
            if self.chat.provider.identity_verified is False:
                codes.append("LLM_PROVIDER_IDENTITY_INVALID")
            else:
                codes.append("LLM_PROVIDER_NOT_READY")
        if self.chat.rag_required:
            if not self.chat.chroma_ready:
                codes.append("CHROMA_NOT_READY")
            if not self.chat.collection_ready:
                codes.append("RAG_COLLECTION_NOT_READY")
            if not self.chat.rag_index_ready:
                codes.append("RAG_NOT_READY")
        codes.extend(self.advisory_codes)
        return _unique_codes(codes)

    def to_public_dict(self) -> dict[str, object]:
        return {
            "contract_version": AVAILABILITY_CONTRACT_VERSION,
            "probe": ProbeKind.READINESS.value,
            "status": self.status.value,
            "core_ready": self.core_ready,
            "chat_ready": self.chat_ready,
            "database_ready": self.database_ready,
            "model_required": self.local_model_required,
            "model_ready": self.local_model_ready,
            "provider_ready": self.chat.provider.ready,
            # Compatibility alias retained for existing observability clients.
            "llm_ready": self.chat.provider.ready,
            "rag_required": self.chat.rag_required,
            "rag_ready": self.chat.rag_ready,
            "chroma_ready": self.chat.chroma_ready,
            "collection_ready": self.chat.collection_ready,
            "codes": list(self.codes),
            "provider": self.chat.provider.to_public_dict(),
            "rag": self.chat.rag.to_public_dict(),
        }


def liveness_payload() -> dict[str, object]:
    """Return process liveness without probing external dependencies."""

    return {
        "contract_version": AVAILABILITY_CONTRACT_VERSION,
        "probe": ProbeKind.LIVENESS.value,
        "status": OperationalStatus.OK.value,
        "alive": True,
    }
