from __future__ import annotations

from app.core.availability import ChatAvailability, ProviderAvailability
from app.modules.llm_chat.domain.provider_contract import ProviderFailureCode


def unavailable_chat_health(
    *,
    rag_required: bool,
    provider_name: str = "ollama",
    model: str | None = None,
    embedding_model: str | None = None,
) -> dict[str, object]:
    """Project a safe degraded state when the chat container is unavailable."""

    availability = ChatAvailability(
        provider=ProviderAvailability(
            provider=provider_name,
            model=model,
            ready=False,
            code=ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value,
            retryable=True,
            identity_verified=None,
        ),
        module_ready=False,
        rag_required=rag_required,
        chroma_ready=False,
        collection_ready=False,
        rag_index_ready=False,
    )
    public = availability.to_public_dict()
    public.update(
        {
            "rag_enabled": rag_required,
            "rag_issue": "chat_module_not_ready",
            "chunk_count": 0,
            "embedding_model": embedding_model,
            "index_fingerprint": None,
            "runtime": {
                "provider": provider_name,
                "model": model,
                "loaded": False,
                "identity_verified": None,
                "identity_error_code": None,
                "gpu_active": None,
                "gpu_memory_bytes": None,
                "inference_device": "unknown",
            },
            "runtime_identity_error": None,
            "gpu_active": None,
            "gpu_memory_bytes": None,
            "inference_device": "unknown",
            "provider_contract": None,
        }
    )
    return public
