from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        enable_decoding=False,
    )

    APP_ENV: Literal["development", "test", "staging", "production"] = "development"
    PROJECT_NAME: str = "VetCDSS API"
    HEMOVET_API_VERSION: str = "2.1.0"
    HEMOVET_SCHEMA_VERSION: str = "3.0.0"
    HEMOVET_BUILD_REVISION: str = Field(
        default="dev",
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$",
    )
    API_V1_PREFIX: str = "/api/v1"
    HEMOVET_PROJECT_ROOT: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3]
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_EMAILS: str = ""

    # OpenTelemetry is opt-in. OTLP credentials remain SecretStr values and are
    # decoded only while constructing the exporter during the application
    # lifespan; they are never included in settings repr/logs.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = Field(
        default="hemovet-backend",
        min_length=1,
        max_length=255,
    )
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4318"
    OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_METRICS_ENDPOINT: str | None = None
    OTEL_EXPORTER_OTLP_HEADERS: SecretStr | None = None
    OTEL_IDENTIFIER_HMAC_SECRET: SecretStr | None = None
    OTEL_TRACES_SAMPLER: Literal[
        "always_on",
        "always_off",
        "traceidratio",
        "parentbased_traceidratio",
    ] = "parentbased_traceidratio"
    OTEL_TRACES_SAMPLER_ARG: float = Field(default=1.0, ge=0, le=1)
    OTEL_FASTAPI_INSTRUMENTATION_ENABLED: bool = True

    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])
    HEMOVET_ENABLE_LOCAL_ML: bool = True
    HEMOVET_ENABLE_LOCAL_EXTRACTION: bool = True
    HEMOVET_SEED_DEMO_HISTORY: bool = False
    HEMOVET_ANALYSIS_CONCURRENCY: int = Field(default=2, ge=1, le=16)

    PET_MEDIA_DIR: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2] / "media"
    )
    PET_PHOTO_MAX_BYTES: int = 5 * 1024 * 1024
    HEMOGRAM_FILE_MAX_BYTES: int = 10 * 1024 * 1024

    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_TIMEOUT_SECONDS: float = 90
    GEMINI_FILE_POLL_SECONDS: float = 2
    GEMINI_FILE_POLL_MAX_ATTEMPTS: int = 30
    GEMINI_INLINE_TEXT_MAX_BYTES: int = Field(default=200_000, ge=0)
    OPENROUTER_EXTRACTION_ENABLED: bool = False
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_GEMMA_MODEL: str = "google/gemma-4-31b-it:free"
    OPENROUTER_NEMOTRON_MODEL: str = "nvidia/nemotron-nano-12b-v2-vl:free"
    OPENROUTER_HTTP_REFERER: str | None = None
    OPENROUTER_X_TITLE: str = "hemogramas-proyectoICC"
    OPENROUTER_GEMMA_TIMEOUT_SECONDS: float = 20
    OPENROUTER_NEMOTRON_TIMEOUT_SECONDS: float = 20
    GEMINI_EXTRACTION_TIMEOUT_SECONDS: float = 30
    LOCAL_EXTRACTION_TIMEOUT_SECONDS: float = 20
    HEMOGRAM_EXTRACTION_TOTAL_TIMEOUT_SECONDS: float = 60
    HEMOGRAM_MIN_VALID_FIELDS: int = Field(default=8, ge=1, le=24)

    OLLAMA_BASE_URL: str | None = None
    # Qwen3 is the qualified local conversational runtime.  The model remains
    # external to FastAPI and can be replaced by an OpenAI-compatible vLLM
    # endpoint without changing the chat use case.
    OLLAMA_MODEL: str | None = "qwen3:4b-instruct-2507-q4_K_M"
    OLLAMA_EXPECTED_MODEL_DIGEST: str | None = Field(
        default=None,
        pattern=r"^(?:sha256:)?[A-Fa-f0-9]{64}$",
    )
    OLLAMA_EXPECTED_QUANTIZATION: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_]{2,32}$",
    )
    OLLAMA_CONNECT_TIMEOUT_SECONDS: float = Field(default=3, gt=0, le=120)
    # Canonical deadline for one provider generation request.
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=90, gt=0, le=600)
    OLLAMA_WRITE_TIMEOUT_SECONDS: float = Field(default=15, ge=1, le=120)
    OLLAMA_POOL_TIMEOUT_SECONDS: float = Field(default=5, ge=0.1, le=60)
    OLLAMA_HTTP_MAX_CONNECTIONS: int = Field(default=8, ge=1, le=128)
    OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS: int = Field(default=4, ge=0, le=128)
    OLLAMA_HTTP_KEEPALIVE_EXPIRY_SECONDS: float = Field(
        default=30,
        ge=1,
        le=300,
    )
    OLLAMA_API_KEY: SecretStr | None = None
    # The default Instruct model is intentionally non-thinking. Reasoning-model
    # deployments may opt in; the adapter never forwards the private field.
    OLLAMA_THINK: bool = False
    OLLAMA_NUM_PREDICT: int = Field(default=384, ge=64, le=8192)
    OLLAMA_TEMPERATURE: float = Field(default=0.1, ge=0, le=1)
    OLLAMA_TOP_P: float = Field(default=0.9, gt=0, le=1)
    OLLAMA_TOP_K: int = Field(default=40, ge=1, le=500)
    OLLAMA_REPEAT_PENALTY: float = Field(default=1.1, ge=0.1, le=3)
    # HTTPX only retries connection-establishment failures here. HemoVet never
    # retries a read timeout or an HTTP error after generation may have begun.
    OLLAMA_MAX_RETRIES: int = Field(default=1, ge=0, le=1)
    OLLAMA_KEEP_ALIVE: str = Field(default="30m", min_length=1, max_length=32)
    OLLAMA_CONTEXT_LENGTH: int = Field(default=4096, ge=512, le=262144)
    OLLAMA_WARMUP_ENABLED: bool = True
    # The ceiling has to clear a cold load, or the warmup cannot succeed at
    # all: when it gives up it closes the connection, and Ollama then aborts
    # the load it had started ("client connection closed before llama-server
    # finished loading"). The model never becomes resident, /api/ps stays
    # empty, and the provider reports itself unavailable — measured in
    # production on 2026-08-06 with this field at its old ceiling of 120,
    # against loads of 126 s cold and 77-94 s with a warm page cache.
    # Cada cuánto se comprueba que el runner residente sigue siendo el del
    # perfil. La VM de la GPU lo puede recargar con otro contexto al reiniciarse,
    # y sin esta vigilancia el desajuste lo paga el primer turno real: 101 s de
    # mediana (n=5). El intervalo es la ventana de exposición, no un coste: la
    # comprobación es un GET a /api/ps de milisegundos.
    OLLAMA_RUNNER_REALIGN_SECONDS: float = Field(default=0.0, ge=0)
    OLLAMA_WARMUP_TIMEOUT_SECONDS: float = Field(default=120, ge=1, le=300)

    CHAT_LLM_PROVIDER: Literal["ollama", "openai_compatible"] = "ollama"
    OPENAI_COMPATIBLE_BASE_URL: str | None = None
    OPENAI_COMPATIBLE_MODEL: str | None = None
    OPENAI_COMPATIBLE_API_KEY: SecretStr | None = None

    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = Field(default=8000, ge=1, le=65535)
    CHROMA_SSL: bool = False
    CHROMA_TENANT: str = "default_tenant"
    CHROMA_DATABASE: str = "default_database"

    RAG_ENABLED: bool = True
    RAG_SOURCE_DIR: Path = Path("knowledge_base/expert_review/approved")
    RAG_COLLECTION_NAME: str = "hemovet_canine_hematology_v2"
    RAG_SCHEMA_VERSION: str = "hemovet-rag-v2"
    RAG_SOURCE_MANIFEST: Path = Path("knowledge_base/manifests/sources_manifest.json")
    RAG_EMBEDDING_MODEL: str = (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    RAG_EMBEDDING_MODEL_REVISION: str = "fastembed-registry-0.8.0"
    RAG_EMBEDDING_POOLING_STRATEGY: str = "mean"
    RAG_EMBEDDING_NORMALIZATION: bool = True
    RAG_EMBEDDING_DOCUMENT_PREFIX: str = ""
    RAG_EMBEDDING_QUERY_PREFIX: str = ""
    RAG_EMBEDDING_DIMENSION: int = Field(default=384, ge=1)
    RAG_EMBEDDING_CACHE_DIR: Path = Path(".cache/fastembed")
    RAG_CHUNK_SIZE_WORDS: int = Field(default=90, ge=20, le=600)
    RAG_CHUNK_OVERLAP_WORDS: int = Field(default=15, ge=0, le=120)
    RAG_INGEST_BATCH_SIZE: int = Field(default=64, ge=1, le=512)
    RAG_FETCH_K: int = Field(default=10, ge=1, le=100)
    RAG_TOP_K: int = Field(default=3, ge=1, le=20)
    RAG_MIN_RELEVANCE_SCORE: float = Field(default=0.38, ge=0, le=1)
    RAG_BLOCKING_MAX_CONCURRENCY: int = Field(default=2, ge=1, le=8)
    RAG_MAX_CONTEXT_CHARS: int = Field(default=3000, ge=1000, le=50000)
    RAG_MAX_PER_SOURCE: int = Field(default=2, ge=1, le=20)
    RAG_RRF_K: int = Field(default=60, ge=1, le=1000)
    RAG_ALLOW_TEST_DOCUMENTS: bool = False
    RAG_ALLOW_AI_PROVISIONAL: bool = False
    # Etapa 5: species/domain eligibility was previously hardcoded identically
    # in three call sites (BM25Index, ChromaBM25Store, ChromaRetrievalStore).
    # This is now the single configurable source of truth for both stores.
    RAG_ALLOWED_SPECIES: tuple[str, ...] = ("canine", "canine_feline")
    RAG_ALLOWED_DOMAINS: tuple[str, ...] = (
        "hematology",
        "clinical_pathology",
        "coagulation",
        "sample_collection",
        "laboratory_methods",
        "cytology",
    )
    RAG_QUERY_MAX_VARIANTS: int = Field(default=4, ge=1, le=12)
    # A real reranker stays honest about its degraded state: disabling it (or
    # a runtime failure) falls back to fusion order via NoopReranker, never a
    # silent, unconfigured no-op passed off as production reranking.
    RAG_RERANKER_ENABLED: bool = True
    RAG_RERANKER_TOP_N: int = Field(default=20, ge=1, le=200)
    # Neighbor expansion defaults to off: it is an optional continuity aid
    # (Block F), not required for the core RAG-optional invariant.
    RAG_NEIGHBOR_EXPANSION_ENABLED: bool = False
    RAG_NEIGHBOR_EXPANSION_MAX_CHUNKS: int = Field(default=1, ge=0, le=4)

    CHAT_MESSAGE_MAX_CHARS: int = Field(default=2000, ge=100, le=10000)
    CHAT_STRUCTURED_OUTPUT_ENABLED: bool = True
    # M.2/M.3 — «que escriba el servidor». Apagado por defecto: se enciende
    # para la ventana de medicion y su regla sellada decide si se conserva.
    # Con el apagado, la ruta de generacion es EXACTAMENTE la de hoy.
    CHAT_SERVER_WRITES_ENABLED: bool = False
    # Let the model choose which authorized values it needs, by calling a
    # tool, instead of receiving the whole materialized panel in the prompt.
    # Off by default: it changes the shape of a clinical turn, and the only
    # way to know whether it pays for itself on this hardware is to measure
    # both with the battery. See ClinicalToolbox.
    CHAT_TOOLS_ENABLED: bool = False
    # How many times one turn may call tools before it must answer. Three is
    # room to list the studies, read a panel and correct one mistaken call;
    # beyond that the turn is looping, not working.
    CHAT_TOOL_MAX_ROUNDS: int = Field(default=3, ge=1, le=5)
    # Development keeps legacy API clients usable. Production enables this
    # boundary so a conversation can only be resumed by the browser tab that
    # owns its ephemeral sessionStorage identifier.
    CHAT_REQUIRE_BROWSER_SESSION_ID: bool = False
    CHAT_HISTORY_LIMIT: int = Field(default=12, ge=0, le=30)
    CHAT_SUMMARY_MAX_CHARS: int = Field(default=3200, ge=500, le=12000)
    CHAT_SUMMARY_MAX_TOKENS: int = Field(default=800, ge=128, le=4096)
    CHAT_MAX_INPUT_TOKENS: int = Field(default=3200, ge=256, le=262144)
    CHAT_CONTEXT_RESERVE_TOKENS: int = Field(default=256, ge=64, le=8192)
    # Optional, explicit per-scope overrides.  When unset the global context
    # length remains effective; no profile may silently lower it.
    CHAT_PROFILE_GENERAL_CONTEXT_LENGTH: int | None = Field(
        default=None, ge=512, le=262144
    )
    CHAT_PROFILE_SELECTED_CONTEXT_LENGTH: int | None = Field(
        default=None, ge=512, le=262144
    )
    CHAT_PROFILE_HISTORY_CONTEXT_LENGTH: int | None = Field(
        default=None, ge=512, le=262144
    )
    # Temperatura por ámbito, misma forma que los overrides de contexto. La
    # lotería del validador (38/70 reparaciones en la batería rigurosa del
    # 9-ago) vive en los caminos clínicos: la redacción cambia entre corridas
    # y una redacción rechazada cuesta una regeneración entera. El chat
    # general conserva OLLAMA_TEMPERATURE: su tono conversacional no paga esa
    # factura.
    CHAT_PROFILE_GENERAL_TEMPERATURE: float | None = Field(
        default=None, ge=0, le=1
    )
    CHAT_PROFILE_SELECTED_TEMPERATURE: float | None = Field(
        default=None, ge=0, le=1
    )
    CHAT_PROFILE_HISTORY_TEMPERATURE: float | None = Field(
        default=None, ge=0, le=1
    )
    CHAT_REPAIR_CONTEXT_LENGTH: int | None = Field(default=None, ge=512, le=262144)
    CHAT_REPAIR_MAX_INPUT_TOKENS: int | None = Field(default=None, ge=256, le=262144)
    CHAT_REPAIR_NUM_PREDICT: int = Field(default=512, ge=64, le=8192)
    # Strictly positive: a repair temperature of exactly 0 makes the model
    # reproduce its own rejected draft near-verbatim instead of correcting it.
    CHAT_REPAIR_TEMPERATURE: float = Field(default=0.1, gt=0, le=1)
    CHAT_REPAIR_TOP_P: float = Field(default=0.9, gt=0, le=1)
    CHAT_REPAIR_TOP_K: int = Field(default=40, ge=1, le=500)
    CHAT_REPAIR_REPEAT_PENALTY: float = Field(default=1.1, ge=0.1, le=3)
    CHAT_REPAIR_THINK: bool = False
    CHAT_MAX_GENERATION_ATTEMPTS: int = Field(default=2, ge=1, le=2)
    CHAT_REPAIR_MIN_REMAINING_SECONDS: float = Field(default=30, gt=0, le=300)
    CHAT_CLINICAL_FACT_MIN_COUNT: int = Field(default=12, ge=1, le=1024)
    CHAT_CLINICAL_FACT_MAX_COUNT: int = Field(default=64, ge=1, le=4096)
    CHAT_CLINICAL_FACT_TOKENS_PER_ITEM: int = Field(default=96, ge=1, le=4096)
    # How many parameters a non-explicit clinical question may put in front of
    # the model before the token budget above takes over. This was hardcoded
    # as 4 (and 6 for pattern questions) inside ClinicalContextSelector, which
    # is why a 12-parameter study reached generation with 4 values and
    # `omitted_fact_count: 0` — nothing had been dropped for space. The
    # default covers a full canonical CBC panel.
    CHAT_CONTEXT_PARAMETER_LIMIT: int = Field(default=24, ge=1, le=256)
    CHAT_MEMORY_TOPIC_LIMIT: int = Field(default=12, ge=1, le=100)
    CHAT_MEMORY_RECENT_QUESTION_LIMIT: int = Field(default=40, ge=1, le=500)
    CHAT_MEMORY_CLINICAL_FACT_LIMIT: int = Field(default=24, ge=1, le=500)
    CHAT_MEMORY_SUMMARIZED_MESSAGE_ID_LIMIT: int = Field(default=200, ge=1, le=5000)
    CHAT_MEMORY_ANSWER_EXCERPT_CHARS: int = Field(default=420, ge=32, le=4000)
    CHAT_MEMORY_QUESTION_EXCERPT_CHARS: int = Field(default=240, ge=32, le=4000)
    CHAT_MEMORY_SUMMARY_ENTRY_CHARS: int = Field(default=260, ge=32, le=4000)
    CHAT_SESSION_TTL_SECONDS: int = Field(default=3600, ge=300, le=86400)
    CHAT_TURN_LEASE_GRACE_SECONDS: float = Field(default=5, ge=0, le=120)
    # Whoever waits in the queue is waiting for one whole generation to end,
    # and measured generations run 20-123 s. A ceiling of 60 could not even
    # be raised to cover the median, so the second person to write was
    # rejected while the first was still being answered. The cross-field
    # check below still keeps it under the turn's total budget.
    CHAT_QUEUE_TIMEOUT_SECONDS: float = Field(default=20, ge=0.1, le=180)
    CHAT_TOTAL_TIMEOUT_SECONDS: float = Field(default=150, ge=5, le=600)
    CHAT_MAX_CONCURRENT_GENERATIONS: int = Field(default=1, ge=1, le=32)
    CHAT_DB_BLOCKING_MAX_CONCURRENCY: int = Field(default=4, ge=1, le=16)
    CHAT_STREAM_HEARTBEAT_SECONDS: float = Field(default=15, ge=5, le=60)
    CHAT_TOKENIZER_JSON: str | None = None
    # Optional integrity check: when set, TokenCounter hashes the loaded
    # tokenizer file and refuses to start if it does not match — identity
    # verified by content, not just by trusting CHAT_TOKENIZER_JSON's path.
    CHAT_TOKENIZER_SHA256: str | None = Field(
        default=None,
        pattern=r"^[A-Fa-f0-9]{64}$",
    )
    # When true, composition must resolve a real, loadable tokenizer at
    # CHAT_TOKENIZER_JSON or fail explicitly at startup — never fall back to
    # the heuristic estimator silently for a profile that declared it needs
    # exact counts.
    CHAT_TOKENIZER_REQUIRED: bool = False

    # Cross-lingual entailment check for documentary support. Off by default:
    # with it disabled the claim validator behaves exactly as it does today
    # (lexical overlap plus the numeric/polarity vetoes), and nothing is
    # downloaded or loaded. Measured on the 70-case bilingual bench
    # (backend/tests/data/bilingual_support_bench.jsonl,
    # scripts/evaluate_support_bench.py): the lexical rule scores 46/70 with
    # 11 unsafe accepts, this verifier 66/70 with 1 — the negation category
    # goes from 10/14 to 14/14, which is the polarity blindness embedding
    # similarity cannot see.
    CHAT_CLAIM_ENTAILMENT_ENABLED: bool = False
    # mDeBERTa-v3-base-XNLI is trained on premise/hypothesis pairs written in
    # different languages, which is literally HemoVet's case: English corpus,
    # Spanish claim. Its ONNX export runs on onnxruntime + tokenizers, both
    # already in the image as fastembed dependencies, so enabling this adds no
    # new inference stack — only 1.1 GB of model weights downloaded from the
    # Hugging Face Hub into CHAT_CLAIM_ENTAILMENT_CACHE_DIR on first use.
    CHAT_CLAIM_ENTAILMENT_MODEL: str = (
        "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
    )
    CHAT_CLAIM_ENTAILMENT_CACHE_DIR: Path = Path(".cache/entailment")
    # Calibrated on the bench, where the separation is wide: the weakest
    # faithful claim entails at 0.916 and every unsafe one but a single
    # subject-swap stays at or below 0.685. Any cut between 0.69 and 0.91
    # scores the same, so the default sits at the centre of that plateau
    # instead of at its edge. The bound refuses a cut so low that the model's
    # own argmax would no longer be entailment.
    CHAT_CLAIM_ENTAILMENT_THRESHOLD: float = Field(default=0.80, ge=0.5, le=0.99)
    # One inference measured 123 ms on an idle 8-core CPU and 180-300 ms while
    # the machine was contended, so 2 s is roughly seven times the worst
    # measurement. Exceeding it does not fail the turn: the claim falls back
    # to the lexical rule.
    CHAT_CLAIM_ENTAILMENT_TIMEOUT_SECONDS: float = Field(default=2, gt=0, le=30)
    # The production backend runs under a 4-CPU cgroup (docker-compose.prod.yml
    # `deploy.resources.limits.cpus`) shared with the API itself, so the
    # session is not allowed to claim every core it can see. Inference is
    # pinned to the CPU provider in any case — the L4 belongs to the LLM.
    CHAT_CLAIM_ENTAILMENT_THREADS: int = Field(default=2, ge=1, le=16)

    MAP_MIN_ZONE_COUNT: int = 3
    MAP_MIN_DISTINCT_PETS: int = 3
    MAP_PUBLIC_GRID_DEGREES: float = 0.03
    MAP_AGGREGATION_GRID_DEGREES: float = 0.02
    RESIDENCE_GEOCODER_ENABLED: bool = True
    RESIDENCE_GEOCODER_TIMEOUT_SECONDS: float = 8
    RESIDENCE_GEOCODER_URL: str = "https://nominatim.openstreetmap.org/search"
    RESIDENCE_GEOCODER_USER_AGENT: str = "HemoVet/2.1 community-surveillance"
    VETERINARY_PLACES_OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    VETERINARY_PLACES_TIMEOUT_SECONDS: float = Field(default=8, ge=1, le=30)

    @field_validator(
        "CHAT_PROFILE_GENERAL_CONTEXT_LENGTH",
        "CHAT_PROFILE_SELECTED_CONTEXT_LENGTH",
        "CHAT_PROFILE_HISTORY_CONTEXT_LENGTH",
        "CHAT_REPAIR_CONTEXT_LENGTH",
        "CHAT_REPAIR_MAX_INPUT_TOKENS",
        mode="before",
    )
    @classmethod
    def parse_optional_chat_integer(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()] or ["*"]
        return list(value) if isinstance(value, (list, tuple)) else ["*"]

    @field_validator("RAG_ALLOWED_SPECIES", "RAG_ALLOWED_DOMAINS", mode="before")
    @classmethod
    def parse_rag_allowlist(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        if isinstance(value, (list, tuple)):
            return tuple(str(item) for item in value)
        return value

    @model_validator(mode="after")
    def validate_runtime_secrets(self) -> "Settings":
        if not self.DATABASE_URL.strip():
            raise ValueError("DATABASE_URL is required")
        if self.APP_ENV != "test" and len(self.SECRET_KEY.strip()) < 32:
            raise ValueError(
                "SECRET_KEY must contain at least 32 characters outside tests"
            )
        if self.RAG_CHUNK_OVERLAP_WORDS >= self.RAG_CHUNK_SIZE_WORDS:
            raise ValueError("RAG_CHUNK_OVERLAP_WORDS must be lower than chunk size")
        if self.RAG_TOP_K > self.RAG_FETCH_K:
            raise ValueError("RAG_TOP_K cannot exceed RAG_FETCH_K")
        if not self.RAG_ALLOWED_SPECIES:
            raise ValueError("RAG_ALLOWED_SPECIES must not be empty")
        if not self.RAG_ALLOWED_DOMAINS:
            raise ValueError("RAG_ALLOWED_DOMAINS must not be empty")
        if self.CHAT_QUEUE_TIMEOUT_SECONDS >= self.CHAT_TOTAL_TIMEOUT_SECONDS:
            raise ValueError(
                "CHAT_QUEUE_TIMEOUT_SECONDS must be lower than chat total timeout"
            )
        if self.OLLAMA_TIMEOUT_SECONDS >= self.CHAT_TOTAL_TIMEOUT_SECONDS:
            raise ValueError(
                "OLLAMA_TIMEOUT_SECONDS must be lower than chat total timeout"
            )
        if any(
            timeout > self.OLLAMA_TIMEOUT_SECONDS
            for timeout in (
                self.OLLAMA_CONNECT_TIMEOUT_SECONDS,
                self.OLLAMA_WRITE_TIMEOUT_SECONDS,
                self.OLLAMA_POOL_TIMEOUT_SECONDS,
            )
        ):
            raise ValueError(
                "Ollama connect, write, and pool timeouts must not exceed "
                "OLLAMA_TIMEOUT_SECONDS"
            )
        if self.CHAT_REPAIR_MIN_REMAINING_SECONDS >= self.CHAT_TOTAL_TIMEOUT_SECONDS:
            raise ValueError(
                "CHAT_REPAIR_MIN_REMAINING_SECONDS must be lower than chat total timeout"
            )
        if self.CHAT_STREAM_HEARTBEAT_SECONDS >= self.CHAT_TOTAL_TIMEOUT_SECONDS:
            raise ValueError(
                "CHAT_STREAM_HEARTBEAT_SECONDS must be lower than chat total timeout"
            )
        if (
            self.OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS
            > self.OLLAMA_HTTP_MAX_CONNECTIONS
        ):
            raise ValueError(
                "OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS cannot exceed max connections"
            )
        if (
            self.OLLAMA_NUM_PREDICT + self.CHAT_CONTEXT_RESERVE_TOKENS
            >= self.OLLAMA_CONTEXT_LENGTH
        ):
            raise ValueError(
                "OLLAMA context must leave room for prompt and output tokens"
            )
        if (
            self.CHAT_MAX_INPUT_TOKENS
            + self.OLLAMA_NUM_PREDICT
            + self.CHAT_CONTEXT_RESERVE_TOKENS
            > self.OLLAMA_CONTEXT_LENGTH
        ):
            raise ValueError(
                "CHAT_MAX_INPUT_TOKENS plus output and reserve must fit model context"
            )
        if self.CHAT_SUMMARY_MAX_TOKENS >= self.CHAT_MAX_INPUT_TOKENS:
            raise ValueError("CHAT_SUMMARY_MAX_TOKENS must be lower than input budget")
        if self.CHAT_CLINICAL_FACT_MIN_COUNT > self.CHAT_CLINICAL_FACT_MAX_COUNT:
            raise ValueError("CHAT_CLINICAL_FACT_MIN_COUNT cannot exceed its maximum")
        if self.CHAT_TOKENIZER_REQUIRED and not (self.CHAT_TOKENIZER_JSON or "").strip():
            raise ValueError(
                "CHAT_TOKENIZER_REQUIRED needs CHAT_TOKENIZER_JSON to point at a "
                "loadable tokenizer"
            )
        if self.CHAT_CLAIM_ENTAILMENT_ENABLED and not (
            self.CHAT_CLAIM_ENTAILMENT_MODEL.strip()
        ):
            raise ValueError(
                "CHAT_CLAIM_ENTAILMENT_ENABLED needs CHAT_CLAIM_ENTAILMENT_MODEL "
                "to name a model repository"
            )
        scope_contexts = (
            self.CHAT_PROFILE_GENERAL_CONTEXT_LENGTH,
            self.CHAT_PROFILE_SELECTED_CONTEXT_LENGTH,
            self.CHAT_PROFILE_HISTORY_CONTEXT_LENGTH,
        )
        for configured_context in scope_contexts:
            effective_context = configured_context or self.OLLAMA_CONTEXT_LENGTH
            if (
                self.CHAT_MAX_INPUT_TOKENS
                + self.OLLAMA_NUM_PREDICT
                + self.CHAT_CONTEXT_RESERVE_TOKENS
                > effective_context
            ):
                raise ValueError(
                    "each chat profile context must fit its input, output, and reserve"
                )
        repair_contexts = (
            (self.CHAT_REPAIR_CONTEXT_LENGTH,)
            if self.CHAT_REPAIR_CONTEXT_LENGTH is not None
            else scope_contexts
        )
        for configured_context in repair_contexts:
            effective_context = configured_context or self.OLLAMA_CONTEXT_LENGTH
            if (
                (self.CHAT_REPAIR_MAX_INPUT_TOKENS or self.CHAT_MAX_INPUT_TOKENS)
                + self.CHAT_REPAIR_NUM_PREDICT
                + self.CHAT_CONTEXT_RESERVE_TOKENS
                > effective_context
            ):
                raise ValueError(
                    "the repair profile must fit its input, output, and reserve"
                )
        return self

    @property
    def admin_emails(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.ADMIN_EMAILS.split(",")
            if item.strip()
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
