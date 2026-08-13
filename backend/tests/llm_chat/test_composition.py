from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from app.core.config import Settings
from app.modules.llm_chat import composition
from app.modules.llm_chat.composition import (
    build_chat_container,
    resolve_telemetry_hmac_secret,
    validate_ollama_runtime_identity,
    validate_runtime_rag_index,
)
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.rag_index import build_rag_index_fingerprint
from app.modules.llm_chat.infrastructure.documents.markdown_chunker import (
    MarkdownChunker,
)
from app.modules.llm_chat.infrastructure.embeddings.fastembed_client import (
    FastEmbedEmbeddingClient,
)
from app.modules.llm_chat.infrastructure.llm.openai_compatible_client import (
    OllamaNativeLLMClient,
    OpenAICompatibleLLMClient,
)
from app.modules.llm_chat.infrastructure.repositories.sqlalchemy_repositories import (
    NonBlockingSqlAlchemyRepository,
)
from app.modules.llm_chat.infrastructure.observability import ChatTelemetry


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "test",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "SECRET_KEY": "test-secret",
        "RAG_ENABLED": False,
        "OLLAMA_WARMUP_ENABLED": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_composition_builds_external_ollama_runtime_without_rag() -> None:
    async def run() -> None:
        container = await build_chat_container(
            _settings(
                CHAT_LLM_PROVIDER="ollama",
                OLLAMA_BASE_URL="http://ollama.test:11434",
                OLLAMA_MODEL="qwen3:4b",
            )
        )
        try:
            assert isinstance(container.llm, OllamaNativeLLMClient)
            assert container.collection is None
            assert container.rag_enabled is False
            assert container.analysis_context is not None
            assert isinstance(container.conversations, NonBlockingSqlAlchemyRepository)
            assert isinstance(
                container.analysis_context,
                NonBlockingSqlAlchemyRepository,
            )
            assert container.send_chat.structured_output_enabled is True
            assert isinstance(container.send_chat.telemetry, ChatTelemetry)
        finally:
            await container.close()

    asyncio.run(run())


def test_composition_builds_openai_compatible_runtime_without_rag() -> None:
    async def run() -> None:
        container = await build_chat_container(
            _settings(
                CHAT_LLM_PROVIDER="openai_compatible",
                OPENAI_COMPATIBLE_BASE_URL="http://vllm.test/v1",
                OPENAI_COMPATIBLE_MODEL="Qwen/Qwen3-8B",
                CHAT_STRUCTURED_OUTPUT_ENABLED=False,
            )
        )
        try:
            assert isinstance(container.llm, OpenAICompatibleLLMClient)
            assert container.llm.model_name == "Qwen/Qwen3-8B"
            assert container.collection is None
            assert container.send_chat.structured_output_enabled is False
        finally:
            await container.close()

    asyncio.run(run())


def test_provider_warmup_never_blocks_persistence_or_container_startup(
    monkeypatch,
) -> None:
    warmup_started = asyncio.Event()

    async def blocked_warmup(
        _client: OllamaNativeLLMClient,
        *,
        timeout_seconds: float,
    ) -> bool:
        assert timeout_seconds > 0
        warmup_started.set()
        await asyncio.Event().wait()
        return False

    monkeypatch.setattr(OllamaNativeLLMClient, "warmup", blocked_warmup)

    async def run() -> None:
        container = await asyncio.wait_for(
            build_chat_container(
                _settings(
                    CHAT_LLM_PROVIDER="ollama",
                    OLLAMA_BASE_URL="http://provider-unavailable.test:11434",
                    OLLAMA_MODEL="qwen3:4b",
                    OLLAMA_WARMUP_ENABLED=True,
                )
            ),
            timeout=0.5,
        )
        try:
            await asyncio.wait_for(warmup_started.wait(), timeout=0.5)
            assert isinstance(
                container.conversations,
                NonBlockingSqlAlchemyRepository,
            )
            assert container.send_chat is not None
        finally:
            await container.close()

    asyncio.run(run())


def test_empty_telemetry_secret_falls_back_to_application_secret() -> None:
    application_secret = "application-secret-long-enough"

    settings = _settings(
        SECRET_KEY=application_secret,
        OTEL_IDENTIFIER_HMAC_SECRET="",
    )

    assert resolve_telemetry_hmac_secret(settings) == application_secret


def test_active_composition_is_isolated_from_the_legacy_parallel_stack() -> None:
    tree = ast.parse(Path(composition.__file__).read_text(encoding="utf-8"))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert (
        not {
            "app.modules.llm_chat.service",
            "app.modules.llm_chat.local_model",
            "app.modules.llm_chat.context",
            "app.modules.llm_chat.knowledge_base",
        }
        & imported_modules
    )


def test_runtime_rag_fingerprint_failure_has_a_typed_code() -> None:
    settings = _settings()
    incompatible = build_rag_index_fingerprint(
        embedding=FastEmbedEmbeddingClient.fingerprint_spec(
            model_name=settings.RAG_EMBEDDING_MODEL,
            dimension=settings.RAG_EMBEDDING_DIMENSION,
            model_revision=settings.RAG_EMBEDDING_MODEL_REVISION,
            pooling_strategy="cls",
            normalization=settings.RAG_EMBEDDING_NORMALIZATION,
            document_prefix=settings.RAG_EMBEDDING_DOCUMENT_PREFIX,
            query_prefix=settings.RAG_EMBEDDING_QUERY_PREFIX,
        ),
        chunking_version=MarkdownChunker.SCHEMA_VERSION,
        chunk_size=settings.RAG_CHUNK_SIZE_WORDS,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP_WORDS,
        metadata_schema_version=settings.RAG_SCHEMA_VERSION,
        content_version="corpus-content-a",
    )

    try:
        validate_runtime_rag_index(settings, incompatible.collection_metadata())
    except ChatRuntimeUnavailable as exc:
        assert exc.code == "rag_index_fingerprint_runtime_mismatch"
    else:
        raise AssertionError("An incompatible RAG index must fail closed")

    try:
        validate_runtime_rag_index(settings, {})
    except ChatRuntimeUnavailable as exc:
        assert exc.code == "rag_index_fingerprint_invalid"
    else:
        raise AssertionError("A legacy collection without fingerprint must fail closed")


def test_ollama_runtime_identity_requires_the_pinned_artifact() -> None:
    digest = "0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0"
    runtime = {
        "model": "qwen3:4b-instruct-2507-q4_K_M",
        "installed": True,
        "loaded": True,
        "digest": digest,
        "quantization": "Q4_K_M",
    }

    assert (
        validate_ollama_runtime_identity(
            runtime,
            expected_model="qwen3:4b-instruct-2507-q4_K_M",
            expected_digest=digest,
            expected_quantization="Q4_K_M",
        )
        is None
    )
    assert validate_ollama_runtime_identity(
        {**runtime, "digest": "f" * 64},
        expected_model="qwen3:4b-instruct-2507-q4_K_M",
        expected_digest=digest,
        expected_quantization="Q4_K_M",
    ) == "LLM_PROVIDER_DIGEST_MISMATCH"
    assert validate_ollama_runtime_identity(
        {**runtime, "quantization": "Q8_0"},
        expected_model="qwen3:4b-instruct-2507-q4_K_M",
        expected_digest=digest,
        expected_quantization="Q4_K_M",
    ) == "LLM_PROVIDER_QUANTIZATION_MISMATCH"
    assert (
        validate_ollama_runtime_identity(
            {**runtime, "loaded": False},
            expected_model="qwen3:4b-instruct-2507-q4_K_M",
            expected_digest=digest,
            expected_quantization="Q4_K_M",
        )
        is None
    )
    assert validate_ollama_runtime_identity(
        {**runtime, "installed": False, "loaded": False},
        expected_model="qwen3:4b-instruct-2507-q4_K_M",
        expected_digest=digest,
        expected_quantization="Q4_K_M",
    ) == "LLM_PROVIDER_IDENTITY_UNVERIFIED"
