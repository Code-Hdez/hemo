from __future__ import annotations

import asyncio
from time import perf_counter
import inspect

from app import application
from app.modules.llm_chat.composition import ChatContainer


class FakeChromaClient:
    async def heartbeat(self) -> int:
        return 1


class FakeCollection:
    def __init__(self, count: int) -> None:
        self._count = count

    async def count(self) -> int:
        return self._count


class FakeLlm:
    model_name = "qwen3:4b"

    async def identity_status(self) -> dict[str, object]:
        return {
            "provider": "ollama",
            "model": self.model_name,
            "installed": True,
        }

    async def health(self) -> bool:
        return True

    async def runtime_status(self) -> dict[str, object]:
        return {
            "provider": "ollama",
            "model": self.model_name,
            "loaded": True,
            "gpu_active": None,
            "gpu_memory_bytes": None,
            "inference_device": "unknown",
        }


class FakePinnedLlm(FakeLlm):
    async def runtime_status(self) -> dict[str, object]:
        return {
            "provider": "ollama",
            "model": "qwen3:4b",
            "loaded": True,
            "digest": "f" * 64,
            "quantization": "Q4_K_M",
        }


def container_with_chunks(count: int) -> ChatContainer:
    return ChatContainer(
        send_chat=None,  # type: ignore[arg-type]
        conversations=None,  # type: ignore[arg-type]
        llm=FakeLlm(),  # type: ignore[arg-type]
        chroma_client=FakeChromaClient(),
        collection=FakeCollection(count),
        http_client=None,  # type: ignore[arg-type]
        embedding_model="fake-embedding",
    )


def test_chat_health_is_degraded_when_collection_has_no_chunks() -> None:
    health = asyncio.run(container_with_chunks(0).health())

    assert health["status"] == "degraded"
    assert health["contract_version"] == "hemovet.availability/v1"
    # An empty RAG collection no longer takes chat_ready down with it: the
    # provider is fine, so chat can still generate (just without retrieval).
    assert health["chat_ready"] is True
    assert health["provider_ready"] is True
    assert health["rag_ready"] is False
    assert health["chunk_count"] == 0


def test_chat_health_is_ok_when_runtime_chroma_and_rag_are_ready() -> None:
    health = asyncio.run(container_with_chunks(3).health())

    assert health["status"] == "ok"
    assert health["chat_ready"] is True
    assert health["provider_ready"] is True
    assert health["rag_ready"] is True
    assert health["runtime"]["loaded"] is True
    assert health["gpu_active"] is None
    assert health["inference_device"] == "unknown"


def test_chat_health_recovers_when_the_provider_returns_without_rebuilding_core() -> (
    None
):
    class RecoveringLlm(FakeLlm):
        checks = 0

        async def identity_status(self) -> dict[str, object]:
            self.checks += 1
            return {
                "provider": "ollama",
                "model": self.model_name,
                "installed": self.checks >= 2,
            }

        async def runtime_status(self) -> dict[str, object]:
            return {
                "provider": "ollama",
                "model": self.model_name,
                "loaded": False,
                "gpu_active": False,
                "gpu_memory_bytes": 0,
                "inference_device": "not_loaded",
            }

    container = container_with_chunks(3)
    provider = RecoveringLlm()
    container.llm = provider

    first = asyncio.run(container.health())
    second = asyncio.run(container.health())

    # The provider itself is not installed yet on the first probe: that is a
    # chat_ready=False condition (fails closed), not a RAG-only degradation.
    assert first["status"] == "fail"
    assert first["provider"]["code"] == "LLM_PROVIDER_UNAVAILABLE"  # type: ignore[index]
    assert second["status"] == "ok"
    assert second["chat_ready"] is True
    assert provider.checks == 2


def test_chat_health_does_not_confuse_residency_telemetry_with_provider_readiness() -> (
    None
):
    class BrokenRuntimeStatusLlm(FakeLlm):
        async def runtime_status(self) -> dict[str, object]:
            raise RuntimeError("provider details must remain private")

    container = container_with_chunks(3)
    container.llm = BrokenRuntimeStatusLlm()

    health = asyncio.run(container.health())

    assert health["status"] == "ok"
    assert health["provider_ready"] is True
    assert health["runtime"]["loaded"] is False  # type: ignore[index]
    assert health["runtime"]["residency_observed"] is False  # type: ignore[index]
    assert health["provider"]["identity_verified"] is None  # type: ignore[index]
    assert health["provider"]["code"] is None  # type: ignore[index]


def test_pinned_ollama_is_ready_only_after_full_gpu_residency() -> None:
    class ResidencyLlm(FakeLlm):
        def __init__(self, *, loaded: bool) -> None:
            self.loaded = loaded

        async def identity_status(self) -> dict[str, object]:
            return {
                "provider": "ollama",
                "model": self.model_name,
                "installed": True,
                "digest": "f" * 64,
                "quantization": "Q4_K_M",
            }

        async def runtime_status(self) -> dict[str, object]:
            return {
                "provider": "ollama",
                "model": self.model_name,
                "loaded": self.loaded,
                "gpu_active": self.loaded,
                "gpu_memory_bytes": 18_000_000_000 if self.loaded else 0,
                "inference_device": "full_gpu" if self.loaded else "not_loaded",
            }

    cold = container_with_chunks(3)
    cold.llm = ResidencyLlm(loaded=False)
    cold.expected_model = "qwen3:4b"
    cold.expected_model_digest = "f" * 64
    cold.expected_quantization = "Q4_K_M"

    warm = container_with_chunks(3)
    warm.llm = ResidencyLlm(loaded=True)
    warm.expected_model = "qwen3:4b"
    warm.expected_model_digest = "f" * 64
    warm.expected_quantization = "Q4_K_M"

    cold_health = asyncio.run(cold.health())
    warm_health = asyncio.run(warm.health())

    assert cold_health["chat_ready"] is False
    assert cold_health["provider_ready"] is False
    assert cold_health["provider"]["code"] == "LLM_PROVIDER_UNAVAILABLE"  # type: ignore[index]
    assert cold_health["runtime"]["residency_ready"] is False  # type: ignore[index]
    assert cold_health["runtime"]["identity_verified"] is True  # type: ignore[index]
    assert warm_health["chat_ready"] is True
    assert warm_health["provider_ready"] is True
    assert warm_health["runtime"]["residency_ready"] is True  # type: ignore[index]


def test_chat_health_fails_closed_on_pinned_model_digest_mismatch() -> None:
    container = container_with_chunks(3)
    container.llm = FakePinnedLlm()
    container.expected_model = "qwen3:4b"
    container.expected_model_digest = "0" * 64
    container.expected_quantization = "Q4_K_M"

    health = asyncio.run(container.health())

    # An unverified/mismatched identity cannot be a ready provider (see
    # ProviderAvailability.__post_init__), so this fails closed rather than
    # degrading.
    assert health["status"] == "fail"
    assert health["llm_ready"] is False
    assert health["runtime_identity_error"] == "LLM_PROVIDER_DIGEST_MISMATCH"
    assert health["runtime"]["identity_verified"] is False


def test_provider_probe_timeout_is_retryable_and_not_an_identity_mismatch() -> None:
    class TimedOutLlm(FakeLlm):
        async def identity_status(self) -> dict[str, object]:
            raise TimeoutError("private provider did not answer")

    container = container_with_chunks(3)
    container.llm = TimedOutLlm()
    container.expected_model = "qwen3:4b"
    container.expected_model_digest = "0" * 64
    container.expected_quantization = "Q4_K_M"

    health = asyncio.run(container.health())

    assert health["status"] == "fail"
    assert health["provider_ready"] is False
    assert health["provider"]["code"] == "LLM_PROVIDER_UNAVAILABLE"
    assert health["provider"]["retryable"] is True
    assert health["provider"]["identity_verified"] is None
    assert health["runtime_identity_error"] is None


def test_stalled_provider_probe_is_bounded_without_losing_rag_readiness() -> None:
    class StalledLlm(FakeLlm):
        async def identity_status(self) -> dict[str, object]:
            await asyncio.sleep(30)
            raise AssertionError("unreachable")

        async def runtime_status(self) -> dict[str, object]:
            await asyncio.sleep(30)
            raise AssertionError("unreachable")

    container = container_with_chunks(3)
    container.llm = StalledLlm()
    started = perf_counter()

    health = asyncio.run(container.health())

    assert perf_counter() - started < 2.5
    assert health["status"] == "fail"
    assert health["provider_ready"] is False
    assert health["provider"]["code"] == "LLM_PROVIDER_UNAVAILABLE"
    assert health["provider"]["retryable"] is True
    assert health["rag_ready"] is True


class DegradedChatContainer:
    async def health(self) -> dict[str, object]:
        return {
            "status": "degraded",
            "module_ready": True,
            "provider_ready": False,
            "llm_ready": False,
            "chroma_ready": True,
            "collection_ready": True,
            "rag_required": True,
            "rag_ready": False,
            "chunk_count": 0,
            "provider": {
                "provider": "ollama",
                "model": "qwen3:4b-instruct-2507-q4_K_M",
                "ready": False,
                "code": "LLM_PROVIDER_UNAVAILABLE",
                "retryable": True,
                "identity_verified": None,
            },
        }


def test_operational_health_fails_when_chat_provider_is_not_ready(
    monkeypatch,
) -> None:
    monkeypatch.setattr(application.settings, "RAG_ENABLED", True)
    monkeypatch.setattr(application, "_LOCAL_ML_ENABLED", False)
    monkeypatch.setattr(
        application.dashboard_service, "load_gate_statuses", lambda _: {}
    )
    monkeypatch.setattr(application, "_database_is_ready", lambda: True)
    monkeypatch.setattr(
        application.app.state,
        "llm_chat",
        DegradedChatContainer(),
        raising=False,
    )

    result = application.health_operational()
    if inspect.isawaitable(result):
        result = asyncio.run(result)

    # The core (database/model) is fine, but chat's own provider is down —
    # that is chat_ready=False, which fails closed at the aggregate level
    # too (see ReadinessSnapshot.status), not merely "degraded". Only a
    # RAG-only shortfall with a healthy provider degrades without failing.
    assert result["status"] == "fail"
    assert result["core_ready"] is True
    assert result["chat_ready"] is False
    assert {"LLM_PROVIDER_NOT_READY", "RAG_NOT_READY"} <= set(result["codes"])
    assert result["database_ready"] is True
    assert result["llm_ready"] is False
    assert result["chroma_ready"] is True
    assert result["rag_ready"] is False
    assert result["build_revision"] == application._BUILD_REVISION
    assert result["chat_policy_revision"] == "clinical-claims-v4"


def test_operational_health_fails_only_when_core_database_is_down(
    monkeypatch,
) -> None:
    monkeypatch.setattr(application.settings, "RAG_ENABLED", False)
    monkeypatch.setattr(application, "_LOCAL_ML_ENABLED", False)
    monkeypatch.setattr(
        application.dashboard_service, "load_gate_statuses", lambda _: {}
    )
    monkeypatch.setattr(application, "_database_is_ready", lambda: False)
    monkeypatch.setattr(
        application.app.state,
        "llm_chat",
        container_with_chunks(0),
        raising=False,
    )

    result = asyncio.run(application.health_operational())

    assert result["status"] == "fail"
    assert result["core_ready"] is False
    assert result["chat_ready"] is False
    assert result["database_ready"] is False
    assert "DATABASE_NOT_READY" in result["codes"]


def test_chat_health_contract_includes_rag_readiness_without_container(
    monkeypatch,
) -> None:
    monkeypatch.delattr(application.app.state, "llm_chat", raising=False)

    health = asyncio.run(application.health_llm())

    assert health["status"] == "fail"
    assert health["contract_version"] == "hemovet.availability/v1"
    assert health["module_ready"] is False
    assert health["provider_ready"] is False
    assert health["rag_ready"] is False
    assert health["chunk_count"] == 0
