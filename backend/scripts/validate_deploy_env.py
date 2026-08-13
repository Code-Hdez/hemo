#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class DeployEnvironmentError(ValueError):
    """Production environment is incomplete or unsafe to deploy."""


@dataclass(frozen=True, slots=True)
class DeployEnvironmentResult:
    variable_count: int
    app_env: str


REQUIRED_VARIABLES = {
    "APP_ENV",
    "API_V1_PREFIX",
    "SECRET_KEY",
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "HEMOVET_DOG_ID_SALT",
    "ADMIN_EMAILS",
    "OTEL_ENABLED",
    "OTEL_SERVICE_NAME",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_IDENTIFIER_HMAC_SECRET",
    "OTEL_TRACES_SAMPLER",
    "OTEL_TRACES_SAMPLER_ARG",
    "OTEL_FASTAPI_INSTRUMENTATION_ENABLED",
    "CORS_ORIGINS",
    "PUBLIC_BASE_URL",
    "CADDY_SITE_ADDRESS",
    "CADDY_WWW_ADDRESS",
    "HEMOVET_BACKEND_IMAGE",
    "HEMOVET_FRONTEND_IMAGE",
    "INSTALL_LOCAL_ML",
    "HEMOVET_ENABLE_LOCAL_ML",
    "INSTALL_LOCAL_EXTRACTION",
    "HEMOVET_ENABLE_LOCAL_EXTRACTION",
    "OPENROUTER_API_KEY",
    "GEMINI_API_KEY",
    "OLLAMA_CONNECT_TIMEOUT_SECONDS",
    "OLLAMA_TIMEOUT_SECONDS",
    "OLLAMA_WRITE_TIMEOUT_SECONDS",
    "OLLAMA_POOL_TIMEOUT_SECONDS",
    "OLLAMA_HTTP_MAX_CONNECTIONS",
    "OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS",
    "OLLAMA_HTTP_KEEPALIVE_EXPIRY_SECONDS",
    "OLLAMA_THINK",
    "OLLAMA_NUM_PREDICT",
    "OLLAMA_TEMPERATURE",
    "OLLAMA_TOP_P",
    "OLLAMA_TOP_K",
    "OLLAMA_REPEAT_PENALTY",
    "OLLAMA_MAX_RETRIES",
    "OLLAMA_KEEP_ALIVE",
    "OLLAMA_CONTEXT_LENGTH",
    "OLLAMA_WARMUP_ENABLED",
    "OLLAMA_WARMUP_TIMEOUT_SECONDS",
    "CHAT_LLM_PROVIDER",
    "CHAT_MESSAGE_MAX_CHARS",
    "CHAT_HISTORY_LIMIT",
    "CHAT_SUMMARY_MAX_CHARS",
    "CHAT_SUMMARY_MAX_TOKENS",
    "CHAT_MAX_INPUT_TOKENS",
    "CHAT_CONTEXT_RESERVE_TOKENS",
    "CHAT_REPAIR_NUM_PREDICT",
    "CHAT_REPAIR_TEMPERATURE",
    "CHAT_REPAIR_TOP_P",
    "CHAT_REPAIR_TOP_K",
    "CHAT_REPAIR_REPEAT_PENALTY",
    "CHAT_REPAIR_THINK",
    "CHAT_MAX_GENERATION_ATTEMPTS",
    "CHAT_REPAIR_MIN_REMAINING_SECONDS",
    "CHAT_CLINICAL_FACT_MIN_COUNT",
    "CHAT_CLINICAL_FACT_MAX_COUNT",
    "CHAT_CLINICAL_FACT_TOKENS_PER_ITEM",
    "CHAT_MEMORY_TOPIC_LIMIT",
    "CHAT_MEMORY_RECENT_QUESTION_LIMIT",
    "CHAT_MEMORY_CLINICAL_FACT_LIMIT",
    "CHAT_MEMORY_SUMMARIZED_MESSAGE_ID_LIMIT",
    "CHAT_MEMORY_ANSWER_EXCERPT_CHARS",
    "CHAT_MEMORY_QUESTION_EXCERPT_CHARS",
    "CHAT_MEMORY_SUMMARY_ENTRY_CHARS",
    "CHAT_SESSION_TTL_SECONDS",
    "CHAT_TURN_LEASE_GRACE_SECONDS",
    "CHAT_QUEUE_TIMEOUT_SECONDS",
    "CHROMA_HOST",
    "CHROMA_PORT",
    "CHROMA_PERSIST_DIRECTORY",
    "RAG_ENABLED",
    "RAG_SOURCE_DIR",
    "RAG_COLLECTION_NAME",
    "RAG_SCHEMA_VERSION",
    "RAG_SOURCE_MANIFEST",
    "RAG_EMBEDDING_MODEL",
    "RAG_EMBEDDING_MODEL_REVISION",
    "RAG_EMBEDDING_POOLING_STRATEGY",
    "RAG_EMBEDDING_NORMALIZATION",
    "RAG_EMBEDDING_DIMENSION",
    "RAG_EMBEDDING_CACHE_DIR",
    "RAG_CHUNK_SIZE_WORDS",
    "RAG_CHUNK_OVERLAP_WORDS",
    "RAG_INGEST_BATCH_SIZE",
    "RAG_FETCH_K",
    "RAG_TOP_K",
    "RAG_MIN_RELEVANCE_SCORE",
    "RAG_BLOCKING_MAX_CONCURRENCY",
    "RAG_MAX_CONTEXT_CHARS",
    "RAG_MAX_PER_SOURCE",
    "RAG_RRF_K",
    "RAG_ALLOW_TEST_DOCUMENTS",
    "RAG_ALLOW_AI_PROVISIONAL",
    "CHAT_STRUCTURED_OUTPUT_ENABLED",
    "CHAT_REQUIRE_BROWSER_SESSION_ID",
    "CHAT_TOTAL_TIMEOUT_SECONDS",
    "CHAT_MAX_CONCURRENT_GENERATIONS",
    "CHAT_DB_BLOCKING_MAX_CONCURRENCY",
    "CHAT_STREAM_HEARTBEAT_SECONDS",
    "VETERINARY_PLACES_OVERPASS_URL",
    "VETERINARY_PLACES_TIMEOUT_SECONDS",
}

# Prefixes form part of the embedding fingerprint. An empty prefix is a valid,
# meaningful value, so these keys must be present but are not required to be
# non-empty like REQUIRED_VARIABLES.
PRESENT_VARIABLES = {
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "RAG_EMBEDDING_DOCUMENT_PREFIX",
    "RAG_EMBEDDING_QUERY_PREFIX",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_EXPECTED_MODEL_DIGEST",
    "OLLAMA_EXPECTED_QUANTIZATION",
    "OPENAI_COMPATIBLE_BASE_URL",
    "OPENAI_COMPATIBLE_MODEL",
    "OPENAI_COMPATIBLE_API_KEY",
    "CHAT_PROFILE_GENERAL_CONTEXT_LENGTH",
    "CHAT_PROFILE_SELECTED_CONTEXT_LENGTH",
    "CHAT_PROFILE_HISTORY_CONTEXT_LENGTH",
    "CHAT_REPAIR_CONTEXT_LENGTH",
    "CHAT_REPAIR_MAX_INPUT_TOKENS",
    "CHAT_TOKENIZER_JSON",
}

ENABLED_VARIABLES = {
    "INSTALL_LOCAL_ML",
    "HEMOVET_ENABLE_LOCAL_ML",
    "INSTALL_LOCAL_EXTRACTION",
    "HEMOVET_ENABLE_LOCAL_EXTRACTION",
    "RAG_ENABLED",
    "RAG_EMBEDDING_NORMALIZATION",
    "CHAT_STRUCTURED_OUTPUT_ENABLED",
    "CHAT_REQUIRE_BROWSER_SESSION_ID",
    "OTEL_ENABLED",
    "OTEL_FASTAPI_INSTRUMENTATION_ENABLED",
}
DISABLED_VARIABLES = {
    "RAG_ALLOW_TEST_DOCUMENTS",
    "RAG_ALLOW_AI_PROVISIONAL",
    # Thinking is a server-side decision (Block F, etapa 7): no deployed
    # profile may enable the model's private reasoning channel, and no
    # client-supplied option can override this — see api/schemas.py.
    "OLLAMA_THINK",
    "CHAT_REPAIR_THINK",
}
CONFIGURABLE_BOOLEAN_VARIABLES = {
    "OLLAMA_WARMUP_ENABLED",
}
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
DEPRECATED_VARIABLES = {"OLLAMA_TOTAL_TIMEOUT_SECONDS"}

# Corpus and telemetry invariants remain pinned independently from the selected
# generation profile. Model identity and generation values are validated below
# from the declared environment instead of being compared with historical values.
CANONICAL_VALUES = {
    "RAG_SCHEMA_VERSION": "hemovet-rag-v2",
    "RAG_EMBEDDING_MODEL": (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ),
    "RAG_EMBEDDING_DIMENSION": "384",
    "OTEL_SERVICE_NAME": "hemovet-backend",
    "OTEL_TRACES_SAMPLER": "parentbased_traceidratio",
}

RAG_COLLECTION_BASE = "hemovet_canine_hematology_v2"
PROMOTED_RAG_COLLECTION_PATTERN = re.compile(
    rf"^{re.escape(RAG_COLLECTION_BASE)}__[0-9a-f]{{12}}$"
)
HEMOVET_IMAGE_PATTERN = re.compile(
    r"^us-central1-docker\.pkg\.dev/"
    r"project-5b36701c-f44f-4c03-a12/hemovet-images/"
    r"(?P<package>backend|frontend)@sha256:[0-9a-f]{64}$"
)


def _valid_http_endpoint(value: str) -> bool:
    try:
        parsed = urlparse(value)
        _ = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
    )


def _valid_private_ollama_endpoint(value: str) -> bool:
    if not _valid_http_endpoint(value):
        return False
    hostname = urlparse(value).hostname or ""
    if hostname.endswith((".internal", ".local")):
        return True
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return address.is_private or address.is_link_local


def _valid_hemovet_image(value: str, *, package: str) -> bool:
    match = HEMOVET_IMAGE_PATTERN.fullmatch(value)
    return match is not None and match.group("package") == package


def _parse_env(path: Path) -> tuple[dict[str, str], set[str]]:
    values: dict[str, str] = {}
    duplicates: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in values:
            duplicates.add(key)
        values[key] = value.strip().strip('"').strip("'")
    return values, duplicates


def validate_env_file(path: Path) -> DeployEnvironmentResult:
    if not path.is_file():
        raise DeployEnvironmentError("Variables inválidas: ENV_FILE")
    values, duplicates = _parse_env(path)
    invalid = set(duplicates)
    invalid.update(DEPRECATED_VARIABLES.intersection(values))
    invalid.update(key for key in REQUIRED_VARIABLES if not values.get(key, "").strip())
    invalid.update(key for key in PRESENT_VARIABLES if key not in values)
    invalid.update(
        key for key, value in values.items() if re.search(r"<[^>]+>", value) is not None
    )

    if values.get("APP_ENV") != "production":
        invalid.add("APP_ENV")
    if values.get("API_V1_PREFIX") != "/api/v1":
        invalid.add("API_V1_PREFIX")
    if len(values.get("SECRET_KEY", "")) < 32:
        invalid.add("SECRET_KEY")
    if len(values.get("POSTGRES_PASSWORD", "")) < 20:
        invalid.add("POSTGRES_PASSWORD")
    if not values.get("DATABASE_URL", "").startswith("postgresql://"):
        invalid.add("DATABASE_URL")
    if len(values.get("HEMOVET_DOG_ID_SALT", "")) < 32:
        invalid.add("HEMOVET_DOG_ID_SALT")
    if len(values.get("OTEL_IDENTIFIER_HMAC_SECRET", "")) < 32:
        invalid.add("OTEL_IDENTIFIER_HMAC_SECRET")
    if not values.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").startswith(
        ("http://", "https://")
    ):
        invalid.add("OTEL_EXPORTER_OTLP_ENDPOINT")

    expected_origins = {"https://hemovet.app", "https://www.hemovet.app"}
    origins = {
        item.strip()
        for item in values.get("CORS_ORIGINS", "").split(",")
        if item.strip()
    }
    if origins != expected_origins:
        invalid.add("CORS_ORIGINS")
    expected_values = {
        "PUBLIC_BASE_URL": "https://hemovet.app",
        "CADDY_SITE_ADDRESS": "hemovet.app",
        "CADDY_WWW_ADDRESS": "www.hemovet.app",
        "CHROMA_HOST": "chroma",
        "CHROMA_PORT": "8000",
        "CHROMA_PERSIST_DIRECTORY": "/data",
        "RAG_SOURCE_DIR": "knowledge_base/expert_review/approved",
        "RAG_SOURCE_MANIFEST": "knowledge_base/manifests/sources_manifest.json",
        **CANONICAL_VALUES,
    }
    invalid.update(
        key for key, expected in expected_values.items() if values.get(key) != expected
    )
    selected_provider = values.get("CHAT_LLM_PROVIDER", "").strip()
    if selected_provider not in {"ollama", "openai_compatible"}:
        invalid.add("CHAT_LLM_PROVIDER")
    elif selected_provider == "ollama":
        required_provider_values = {
            "OLLAMA_BASE_URL",
            "OLLAMA_MODEL",
            "OLLAMA_EXPECTED_MODEL_DIGEST",
            "OLLAMA_EXPECTED_QUANTIZATION",
        }
        invalid.update(
            key for key in required_provider_values if not values.get(key, "").strip()
        )
        if not _valid_private_ollama_endpoint(values.get("OLLAMA_BASE_URL", "")):
            invalid.add("OLLAMA_BASE_URL")
        if (
            re.fullmatch(
                r"(?:sha256:)?[A-Fa-f0-9]{64}",
                values.get("OLLAMA_EXPECTED_MODEL_DIGEST", ""),
            )
            is None
        ):
            invalid.add("OLLAMA_EXPECTED_MODEL_DIGEST")
        if (
            re.fullmatch(
                r"[A-Za-z0-9_]{2,32}",
                values.get("OLLAMA_EXPECTED_QUANTIZATION", ""),
            )
            is None
        ):
            invalid.add("OLLAMA_EXPECTED_QUANTIZATION")
    else:
        required_provider_values = {
            "OPENAI_COMPATIBLE_BASE_URL",
            "OPENAI_COMPATIBLE_MODEL",
        }
        invalid.update(
            key for key in required_provider_values if not values.get(key, "").strip()
        )
        if not _valid_http_endpoint(values.get("OPENAI_COMPATIBLE_BASE_URL", "")):
            invalid.add("OPENAI_COMPATIBLE_BASE_URL")
    # CHAT_TOKENIZER_REQUIRED is an honest, supported, non-fail-closed-violating
    # False when no verified tokenizer.json for the exact deployed artifact is
    # available yet (Settings.validate_runtime_secrets() is the real fail-closed
    # gate: it refuses to start if CHAT_TOKENIZER_REQUIRED=true without a usable
    # CHAT_TOKENIZER_JSON). Only demand a real path/hash when the deployment
    # actually declares the tokenizer required; never fabricate one here.
    if values.get("CHAT_TOKENIZER_REQUIRED", "").lower() in TRUE_VALUES:
        tokenizer_path = values.get("CHAT_TOKENIZER_JSON", "").strip()
        if not tokenizer_path or "://" in tokenizer_path:
            invalid.add("CHAT_TOKENIZER_JSON")
        if (
            re.fullmatch(
                r"[A-Fa-f0-9]{64}", values.get("CHAT_TOKENIZER_SHA256", "")
            )
            is None
        ):
            invalid.add("CHAT_TOKENIZER_SHA256")
    if not _valid_hemovet_image(
        values.get("HEMOVET_BACKEND_IMAGE", ""), package="backend"
    ):
        invalid.add("HEMOVET_BACKEND_IMAGE")
    if not _valid_hemovet_image(
        values.get("HEMOVET_FRONTEND_IMAGE", ""), package="frontend"
    ):
        invalid.add("HEMOVET_FRONTEND_IMAGE")
    if not _valid_http_endpoint(values.get("VETERINARY_PLACES_OVERPASS_URL", "")):
        invalid.add("VETERINARY_PLACES_OVERPASS_URL")
    if (
        PROMOTED_RAG_COLLECTION_PATTERN.fullmatch(values.get("RAG_COLLECTION_NAME", ""))
        is None
    ):
        invalid.add("RAG_COLLECTION_NAME")
    invalid.update(
        key
        for key in ENABLED_VARIABLES
        if values.get(key, "").lower() not in TRUE_VALUES
    )
    invalid.update(
        key
        for key in DISABLED_VARIABLES
        if values.get(key, "").lower() not in FALSE_VALUES
    )
    invalid.update(
        key
        for key in CONFIGURABLE_BOOLEAN_VARIABLES
        if values.get(key, "").lower() not in TRUE_VALUES | FALSE_VALUES
    )

    def number(key: str) -> float | None:
        try:
            return float(values[key])
        except (KeyError, TypeError, ValueError):
            invalid.add(key)
            return None

    def integer(key: str) -> int | None:
        try:
            parsed = int(values[key])
        except (KeyError, TypeError, ValueError):
            invalid.add(key)
            return None
        if str(parsed) != values[key].strip():
            invalid.add(key)
            return None
        return parsed

    def optional_integer(key: str) -> int | None:
        raw_value = values.get(key, "").strip()
        if not raw_value:
            return None
        return integer(key)

    connect_timeout = number("OLLAMA_CONNECT_TIMEOUT_SECONDS")
    provider_timeout = number("OLLAMA_TIMEOUT_SECONDS")
    write_timeout = number("OLLAMA_WRITE_TIMEOUT_SECONDS")
    pool_timeout = number("OLLAMA_POOL_TIMEOUT_SECONDS")
    warmup_timeout = number("OLLAMA_WARMUP_TIMEOUT_SECONDS")
    queue_timeout = number("CHAT_QUEUE_TIMEOUT_SECONDS")
    total_timeout = number("CHAT_TOTAL_TIMEOUT_SECONDS")
    temperature = number("OLLAMA_TEMPERATURE")
    top_p = number("OLLAMA_TOP_P")
    sampling_top_k = integer("OLLAMA_TOP_K")
    repeat_penalty = number("OLLAMA_REPEAT_PENALTY")
    output_tokens = integer("OLLAMA_NUM_PREDICT")
    context_tokens = integer("OLLAMA_CONTEXT_LENGTH")
    input_tokens = integer("CHAT_MAX_INPUT_TOKENS")
    context_reserve = integer("CHAT_CONTEXT_RESERVE_TOKENS")
    profile_contexts = {
        key: optional_integer(key)
        for key in (
            "CHAT_PROFILE_GENERAL_CONTEXT_LENGTH",
            "CHAT_PROFILE_SELECTED_CONTEXT_LENGTH",
            "CHAT_PROFILE_HISTORY_CONTEXT_LENGTH",
        )
    }
    repair_context = optional_integer("CHAT_REPAIR_CONTEXT_LENGTH")
    repair_input_tokens = optional_integer("CHAT_REPAIR_MAX_INPUT_TOKENS")
    repair_output_tokens = integer("CHAT_REPAIR_NUM_PREDICT")
    repair_temperature = number("CHAT_REPAIR_TEMPERATURE")
    repair_top_p = number("CHAT_REPAIR_TOP_P")
    repair_top_k = integer("CHAT_REPAIR_TOP_K")
    repair_repeat_penalty = number("CHAT_REPAIR_REPEAT_PENALTY")
    max_generation_attempts = integer("CHAT_MAX_GENERATION_ATTEMPTS")
    repair_min_remaining = number("CHAT_REPAIR_MIN_REMAINING_SECONDS")
    summary_tokens = integer("CHAT_SUMMARY_MAX_TOKENS")
    summary_chars = integer("CHAT_SUMMARY_MAX_CHARS")
    retries = integer("OLLAMA_MAX_RETRIES")
    concurrency = integer("CHAT_MAX_CONCURRENT_GENERATIONS")
    database_concurrency = integer("CHAT_DB_BLOCKING_MAX_CONCURRENCY")
    history_limit = integer("CHAT_HISTORY_LIMIT")
    message_max = integer("CHAT_MESSAGE_MAX_CHARS")
    session_ttl = integer("CHAT_SESSION_TTL_SECONDS")
    turn_lease_grace = number("CHAT_TURN_LEASE_GRACE_SECONDS")
    heartbeat = number("CHAT_STREAM_HEARTBEAT_SECONDS")
    max_connections = integer("OLLAMA_HTTP_MAX_CONNECTIONS")
    max_keepalive = integer("OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS")
    keepalive_expiry = number("OLLAMA_HTTP_KEEPALIVE_EXPIRY_SECONDS")
    keep_alive = values.get("OLLAMA_KEEP_ALIVE", "")
    chunk_size = integer("RAG_CHUNK_SIZE_WORDS")
    chunk_overlap = integer("RAG_CHUNK_OVERLAP_WORDS")
    fetch_k = integer("RAG_FETCH_K")
    retrieval_top_k = integer("RAG_TOP_K")
    blocking_concurrency = integer("RAG_BLOCKING_MAX_CONCURRENCY")
    relevance_score = number("RAG_MIN_RELEVANCE_SCORE")
    rag_context_chars = integer("RAG_MAX_CONTEXT_CHARS")
    rag_max_per_source = integer("RAG_MAX_PER_SOURCE")
    rag_rrf_k = integer("RAG_RRF_K")
    clinical_fact_min = integer("CHAT_CLINICAL_FACT_MIN_COUNT")
    clinical_fact_max = integer("CHAT_CLINICAL_FACT_MAX_COUNT")
    clinical_fact_tokens = integer("CHAT_CLINICAL_FACT_TOKENS_PER_ITEM")
    memory_limits = {
        key: integer(key)
        for key in (
            "CHAT_MEMORY_TOPIC_LIMIT",
            "CHAT_MEMORY_RECENT_QUESTION_LIMIT",
            "CHAT_MEMORY_CLINICAL_FACT_LIMIT",
            "CHAT_MEMORY_SUMMARIZED_MESSAGE_ID_LIMIT",
            "CHAT_MEMORY_ANSWER_EXCERPT_CHARS",
            "CHAT_MEMORY_QUESTION_EXCERPT_CHARS",
            "CHAT_MEMORY_SUMMARY_ENTRY_CHARS",
        )
    }
    otel_sample_ratio = number("OTEL_TRACES_SAMPLER_ARG")
    veterinary_places_timeout = number("VETERINARY_PLACES_TIMEOUT_SECONDS")

    if provider_timeout is None or not 0 < provider_timeout <= 600:
        invalid.add("OLLAMA_TIMEOUT_SECONDS")
    # Keep these bounds identical to Settings (app/core/config.py): this
    # validator gates the deploy, so a range narrower than the field's would
    # reject an environment the running backend accepts.
    if queue_timeout is None or not 0.1 <= queue_timeout <= 180:
        invalid.add("CHAT_QUEUE_TIMEOUT_SECONDS")
    if total_timeout is None or not 5 <= total_timeout <= 600:
        invalid.add("CHAT_TOTAL_TIMEOUT_SECONDS")
    if (
        provider_timeout is not None
        and total_timeout is not None
        and provider_timeout >= total_timeout
    ):
        invalid.update({"OLLAMA_TIMEOUT_SECONDS", "CHAT_TOTAL_TIMEOUT_SECONDS"})
    if (
        queue_timeout is not None
        and total_timeout is not None
        and queue_timeout >= total_timeout
    ):
        invalid.update({"CHAT_QUEUE_TIMEOUT_SECONDS", "CHAT_TOTAL_TIMEOUT_SECONDS"})
    if repair_min_remaining is None or not 0 < repair_min_remaining <= 300:
        invalid.add("CHAT_REPAIR_MIN_REMAINING_SECONDS")
    if (
        repair_min_remaining is not None
        and total_timeout is not None
        and repair_min_remaining >= total_timeout
    ):
        invalid.update(
            {"CHAT_REPAIR_MIN_REMAINING_SECONDS", "CHAT_TOTAL_TIMEOUT_SECONDS"}
        )
    if temperature is None or not 0 <= temperature <= 1:
        invalid.add("OLLAMA_TEMPERATURE")
    if top_p is None or not 0 < top_p <= 1:
        invalid.add("OLLAMA_TOP_P")
    if sampling_top_k is None or not 1 <= sampling_top_k <= 500:
        invalid.add("OLLAMA_TOP_K")
    if repeat_penalty is None or not 0.1 <= repeat_penalty <= 3:
        invalid.add("OLLAMA_REPEAT_PENALTY")
    if output_tokens is None or not 64 <= output_tokens <= 8192:
        invalid.add("OLLAMA_NUM_PREDICT")
    if context_tokens is None or not 512 <= context_tokens <= 262144:
        invalid.add("OLLAMA_CONTEXT_LENGTH")
    if input_tokens is None or not 256 <= input_tokens <= 262144:
        invalid.add("CHAT_MAX_INPUT_TOKENS")
    if context_reserve is None or not 64 <= context_reserve <= 8192:
        invalid.add("CHAT_CONTEXT_RESERVE_TOKENS")
    for key, configured_context in profile_contexts.items():
        if configured_context is not None and not 512 <= configured_context <= 262144:
            invalid.add(key)
    if repair_context is not None and not 512 <= repair_context <= 262144:
        invalid.add("CHAT_REPAIR_CONTEXT_LENGTH")
    if repair_input_tokens is not None and not 256 <= repair_input_tokens <= 262144:
        invalid.add("CHAT_REPAIR_MAX_INPUT_TOKENS")
    if repair_output_tokens is None or not 64 <= repair_output_tokens <= 8192:
        invalid.add("CHAT_REPAIR_NUM_PREDICT")
    if veterinary_places_timeout is None or not 1 <= veterinary_places_timeout <= 30:
        invalid.add("VETERINARY_PLACES_TIMEOUT_SECONDS")
    if (
        output_tokens is None
        or input_tokens is None
        or context_tokens is None
        or context_reserve is None
        or input_tokens + output_tokens + context_reserve > context_tokens
    ):
        invalid.update(
            {
                "CHAT_MAX_INPUT_TOKENS",
                "CHAT_CONTEXT_RESERVE_TOKENS",
                "OLLAMA_NUM_PREDICT",
                "OLLAMA_CONTEXT_LENGTH",
            }
        )
    for key, configured_context in profile_contexts.items():
        effective_context = configured_context or context_tokens
        if (
            effective_context is None
            or input_tokens is None
            or output_tokens is None
            or context_reserve is None
            or input_tokens + output_tokens + context_reserve > effective_context
        ):
            invalid.add(key)
    effective_repair_input = repair_input_tokens or input_tokens
    repair_context_values = (
        {"CHAT_REPAIR_CONTEXT_LENGTH": repair_context}
        if repair_context is not None
        else profile_contexts
    )
    for key, configured_context in repair_context_values.items():
        effective_context = configured_context or context_tokens
        if (
            effective_context is None
            or effective_repair_input is None
            or repair_output_tokens is None
            or context_reserve is None
            or effective_repair_input + repair_output_tokens + context_reserve
            > effective_context
        ):
            invalid.add(key)
    if repair_temperature is None or not 0 < repair_temperature <= 1:
        # Strictly positive: a repair pass run at exactly 0 tends to
        # reproduce the rejected draft instead of correcting it.
        invalid.add("CHAT_REPAIR_TEMPERATURE")
    if repair_top_p is None or not 0 < repair_top_p <= 1:
        invalid.add("CHAT_REPAIR_TOP_P")
    if repair_top_k is None or not 1 <= repair_top_k <= 500:
        invalid.add("CHAT_REPAIR_TOP_K")
    if repair_repeat_penalty is None or not 0.1 <= repair_repeat_penalty <= 3:
        invalid.add("CHAT_REPAIR_REPEAT_PENALTY")
    if max_generation_attempts is None or not 1 <= max_generation_attempts <= 2:
        invalid.add("CHAT_MAX_GENERATION_ATTEMPTS")
    if (
        summary_tokens is None
        or not 128 <= summary_tokens <= 4096
        or input_tokens is None
        or summary_tokens >= input_tokens
    ):
        invalid.update({"CHAT_SUMMARY_MAX_TOKENS", "CHAT_MAX_INPUT_TOKENS"})
    if summary_chars is None or not 500 <= summary_chars <= 12000:
        invalid.add("CHAT_SUMMARY_MAX_CHARS")
    if retries is None or not 0 <= retries <= 1:
        invalid.add("OLLAMA_MAX_RETRIES")
    if connect_timeout is None or not 0 < connect_timeout <= 120:
        invalid.add("OLLAMA_CONNECT_TIMEOUT_SECONDS")
    if write_timeout is None or not 1 <= write_timeout <= 120:
        invalid.add("OLLAMA_WRITE_TIMEOUT_SECONDS")
    if pool_timeout is None or not 0.1 <= pool_timeout <= 60:
        invalid.add("OLLAMA_POOL_TIMEOUT_SECONDS")
    # The floor is 90, not 1. A cold load of the production model was measured
    # at 79 s on 2026-08-06; below that the backend declares the warmup failed
    # while the model is loading perfectly, publishes LLM_PROVIDER_UNAVAILABLE
    # and the frontend disables the chat — for over a minute, after any restart
    # of the GPU VM, with nobody having touched anything. The value shipped at
    # the time was 20. That is not a preference to record in a comment; it is a
    # release the deploy must refuse to make.
    if warmup_timeout is None or not 90 <= warmup_timeout <= 300:
        invalid.add("OLLAMA_WARMUP_TIMEOUT_SECONDS")
    if (
        not 1 <= len(keep_alive) <= 32
        or re.fullmatch(
            r"(?:-1|0|(?:\d+(?:\.\d+)?(?:ns|us|µs|ms|s|m|h))+)",
            keep_alive,
        )
        is None
    ):
        invalid.add("OLLAMA_KEEP_ALIVE")
    provider_subtimeouts = {
        "OLLAMA_CONNECT_TIMEOUT_SECONDS": connect_timeout,
        "OLLAMA_WRITE_TIMEOUT_SECONDS": write_timeout,
        "OLLAMA_POOL_TIMEOUT_SECONDS": pool_timeout,
    }
    if provider_timeout is not None:
        invalid.update(
            key
            for key, configured in provider_subtimeouts.items()
            if configured is not None and configured > provider_timeout
        )
    if max_connections is None or not 1 <= max_connections <= 128:
        invalid.add("OLLAMA_HTTP_MAX_CONNECTIONS")
    if max_keepalive is None or not 0 <= max_keepalive <= 128:
        invalid.add("OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS")
    if (
        max_connections is not None
        and max_keepalive is not None
        and max_keepalive > max_connections
    ):
        invalid.update(
            {"OLLAMA_HTTP_MAX_CONNECTIONS", "OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS"}
        )
    if keepalive_expiry is None or not 1 <= keepalive_expiry <= 300:
        invalid.add("OLLAMA_HTTP_KEEPALIVE_EXPIRY_SECONDS")
    if concurrency is None or not 1 <= concurrency <= 32:
        invalid.add("CHAT_MAX_CONCURRENT_GENERATIONS")
    if database_concurrency is None or not 1 <= database_concurrency <= 16:
        invalid.add("CHAT_DB_BLOCKING_MAX_CONCURRENCY")
    if history_limit is None or not 0 <= history_limit <= 30:
        invalid.add("CHAT_HISTORY_LIMIT")
    if message_max is None or not 100 <= message_max <= 10000:
        invalid.add("CHAT_MESSAGE_MAX_CHARS")
    if session_ttl is None or not 300 <= session_ttl <= 86400:
        invalid.add("CHAT_SESSION_TTL_SECONDS")
    if turn_lease_grace is None or not 0 <= turn_lease_grace <= 120:
        invalid.add("CHAT_TURN_LEASE_GRACE_SECONDS")
    if heartbeat is None or not 5 <= heartbeat <= 60:
        invalid.add("CHAT_STREAM_HEARTBEAT_SECONDS")
    if (
        heartbeat is not None
        and total_timeout is not None
        and heartbeat >= total_timeout
    ):
        invalid.update(
            {"CHAT_STREAM_HEARTBEAT_SECONDS", "CHAT_TOTAL_TIMEOUT_SECONDS"}
        )
    if (
        chunk_size is None
        or chunk_overlap is None
        or chunk_size < 20
        or chunk_overlap < 0
        or chunk_overlap >= chunk_size
    ):
        invalid.update({"RAG_CHUNK_SIZE_WORDS", "RAG_CHUNK_OVERLAP_WORDS"})
    if (
        fetch_k is None
        or retrieval_top_k is None
        or fetch_k < 1
        or fetch_k > 100
        or retrieval_top_k < 1
        or retrieval_top_k > 20
        or retrieval_top_k > fetch_k
    ):
        invalid.update({"RAG_FETCH_K", "RAG_TOP_K"})
    if blocking_concurrency is None or not 1 <= blocking_concurrency <= 8:
        invalid.add("RAG_BLOCKING_MAX_CONCURRENCY")
    if relevance_score is None or not 0 <= relevance_score <= 1:
        invalid.add("RAG_MIN_RELEVANCE_SCORE")
    if rag_context_chars is None or not 1000 <= rag_context_chars <= 50000:
        invalid.add("RAG_MAX_CONTEXT_CHARS")
    if rag_max_per_source is None or not 1 <= rag_max_per_source <= 20:
        invalid.add("RAG_MAX_PER_SOURCE")
    if rag_rrf_k is None or not 1 <= rag_rrf_k <= 1000:
        invalid.add("RAG_RRF_K")
    if (
        clinical_fact_min is None
        or clinical_fact_max is None
        or not 1 <= clinical_fact_min <= 1024
        or not 1 <= clinical_fact_max <= 4096
        or clinical_fact_min > clinical_fact_max
    ):
        invalid.update({"CHAT_CLINICAL_FACT_MIN_COUNT", "CHAT_CLINICAL_FACT_MAX_COUNT"})
    if clinical_fact_tokens is None or not 1 <= clinical_fact_tokens <= 4096:
        invalid.add("CHAT_CLINICAL_FACT_TOKENS_PER_ITEM")
    memory_ranges = {
        "CHAT_MEMORY_TOPIC_LIMIT": (1, 100),
        "CHAT_MEMORY_RECENT_QUESTION_LIMIT": (1, 500),
        "CHAT_MEMORY_CLINICAL_FACT_LIMIT": (1, 500),
        "CHAT_MEMORY_SUMMARIZED_MESSAGE_ID_LIMIT": (1, 5000),
        "CHAT_MEMORY_ANSWER_EXCERPT_CHARS": (32, 4000),
        "CHAT_MEMORY_QUESTION_EXCERPT_CHARS": (32, 4000),
        "CHAT_MEMORY_SUMMARY_ENTRY_CHARS": (32, 4000),
    }
    for key, (minimum, maximum) in memory_ranges.items():
        configured = memory_limits[key]
        if configured is None or not minimum <= configured <= maximum:
            invalid.add(key)
    if otel_sample_ratio is None or not 0 <= otel_sample_ratio <= 1:
        invalid.add("OTEL_TRACES_SAMPLER_ARG")

    if invalid:
        raise DeployEnvironmentError(
            "Variables inválidas: " + ", ".join(sorted(invalid))
        )
    return DeployEnvironmentResult(
        variable_count=len(values),
        app_env=values["APP_ENV"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida el entorno productivo sin imprimir valores."
    )
    parser.add_argument("path", nargs="?", type=Path, default=Path(".env"))
    args = parser.parse_args()
    try:
        result = validate_env_file(args.path)
    except DeployEnvironmentError as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Entorno productivo válido ({result.variable_count} variables).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
