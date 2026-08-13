import pytest
from pydantic import ValidationError

from app.core.config import Settings


BASE = {
    "APP_ENV": "test",
    "DATABASE_URL": "sqlite:///:memory:",
    "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
}


def test_llm_rag_settings_have_safe_low_latency_defaults() -> None:
    settings = Settings(**BASE, _env_file=None)

    assert settings.RAG_COLLECTION_NAME == "hemovet_canine_hematology_v2"
    assert settings.RAG_SCHEMA_VERSION == "hemovet-rag-v2"
    assert settings.RAG_TOP_K == 3
    assert settings.RAG_FETCH_K == 10
    assert settings.RAG_CHUNK_SIZE_WORDS == 90
    assert settings.RAG_CHUNK_OVERLAP_WORDS == 15
    assert settings.RAG_EMBEDDING_MODEL_REVISION == "fastembed-registry-0.8.0"
    assert settings.RAG_EMBEDDING_POOLING_STRATEGY == "mean"
    assert settings.RAG_EMBEDDING_NORMALIZATION is True
    assert settings.RAG_BLOCKING_MAX_CONCURRENCY == 2
    assert settings.RAG_MAX_CONTEXT_CHARS == 3000
    assert settings.OLLAMA_MODEL == "qwen3:4b-instruct-2507-q4_K_M"
    assert settings.OLLAMA_NUM_PREDICT == 384
    assert settings.OLLAMA_TEMPERATURE == 0.1
    assert settings.OLLAMA_TOP_P == 0.9
    assert settings.OLLAMA_TOP_K == 40
    assert settings.OLLAMA_REPEAT_PENALTY == 1.1
    assert settings.OLLAMA_MAX_RETRIES == 1
    assert settings.OLLAMA_HTTP_MAX_CONNECTIONS == 8
    assert settings.OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS == 4
    assert settings.OLLAMA_POOL_TIMEOUT_SECONDS == 5
    assert settings.OLLAMA_KEEP_ALIVE == "30m"
    assert settings.OLLAMA_CONTEXT_LENGTH == 4096
    assert settings.OLLAMA_WARMUP_ENABLED is True
    assert settings.OLLAMA_WARMUP_TIMEOUT_SECONDS == 120
    assert settings.CHAT_TOTAL_TIMEOUT_SECONDS == 150
    assert settings.CHAT_QUEUE_TIMEOUT_SECONDS == 20
    assert settings.CHAT_SESSION_TTL_SECONDS == 3600
    assert settings.CHAT_STRUCTURED_OUTPUT_ENABLED is True
    assert settings.CHAT_REQUIRE_BROWSER_SESSION_ID is False
    assert settings.CHAT_HISTORY_LIMIT == 12
    assert settings.CHAT_SUMMARY_MAX_TOKENS == 800
    assert settings.CHAT_MAX_INPUT_TOKENS == 3200
    assert settings.CHAT_MAX_CONCURRENT_GENERATIONS == 1
    assert settings.RAG_ALLOW_AI_PROVISIONAL is False


def test_structured_output_can_be_disabled_explicitly() -> None:
    settings = Settings(
        **BASE,
        CHAT_STRUCTURED_OUTPUT_ENABLED=False,
        _env_file=None,
    )

    assert settings.CHAT_STRUCTURED_OUTPUT_ENABLED is False


def test_warmup_timeout_can_cover_a_measured_cold_load() -> None:
    """The warmup ceiling must clear the load it is meant to wait for.

    Measured on the production L4 on 2026-08-06: 126 s to load
    qwen3.6:27b-q4_K_M from cold, 77-94 s with a warm page cache. While this
    field was capped at 120 the warmup could not be configured to outlast a
    cold load, and giving up is not passive — it closes the connection, and
    Ollama aborts the load it had already started. The model then never
    became resident, so the provider reported itself unavailable and the
    chat stayed down until someone loaded the model by hand.
    """

    settings = Settings(**BASE, OLLAMA_WARMUP_TIMEOUT_SECONDS=180, _env_file=None)

    assert settings.OLLAMA_WARMUP_TIMEOUT_SECONDS == 180


def test_queue_timeout_can_cover_a_full_generation() -> None:
    """Waiting in the queue means waiting for one whole generation.

    Real generations run 20-123 s, so a ceiling of 60 could not be raised to
    cover even the median: the second person to write was rejected while the
    first was still being answered.
    """

    settings = Settings(
        **BASE,
        CHAT_QUEUE_TIMEOUT_SECONDS=150,
        CHAT_TOTAL_TIMEOUT_SECONDS=240,
        _env_file=None,
    )

    assert settings.CHAT_QUEUE_TIMEOUT_SECONDS == 150


@pytest.mark.parametrize(
    "overrides",
    [
        {"RAG_CHUNK_SIZE_WORDS": 10, "RAG_CHUNK_OVERLAP_WORDS": 10},
        {"RAG_FETCH_K": 3, "RAG_TOP_K": 4},
        {"CHAT_MAX_INPUT_TOKENS": 3500},
        # The wider queue range does not weaken the ordering check: 150 is a
        # legal value on its own and still rejected against the default
        # total timeout of 150.
        {"CHAT_QUEUE_TIMEOUT_SECONDS": 150},
        {
            "OLLAMA_HTTP_MAX_CONNECTIONS": 2,
            "OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS": 3,
        },
    ],
)
def test_llm_rag_settings_reject_incoherent_limits(overrides: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE, **overrides)
