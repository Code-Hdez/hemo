from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import TYPE_CHECKING, Literal, TypeAlias

if TYPE_CHECKING:
    from app.core.config import Settings


ProfileKind = Literal["main", "repair"]
ProviderName = Literal["ollama", "openai_compatible"]
OllamaKeepAlive: TypeAlias = Literal[-1, 0] | str
_OLLAMA_DURATION = re.compile(
    r"^(?:\d+(?:\.\d+)?(?:ns|us|µs|ms|s|m|h))+$"
)


def normalize_ollama_keep_alive(value: str) -> OllamaKeepAlive:
    """Project the environment value into Ollama's JSON wire representation."""

    normalized = value.strip()
    if normalized == "-1":
        return -1
    if normalized == "0":
        return 0
    if not normalized:
        raise ValueError("OLLAMA_KEEP_ALIVE must not be empty")
    if _OLLAMA_DURATION.fullmatch(normalized) is None:
        raise ValueError(
            "OLLAMA_KEEP_ALIVE must be -1, 0, or a duration such as 30m"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class EffectiveGenerationProfile:
    """Immutable provider parameters resolved before a generation attempt."""

    name: str
    kind: ProfileKind
    provider: ProviderName
    model: str
    num_ctx: int
    max_input_tokens: int
    context_reserve_tokens: int
    num_predict: int
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    thinking: bool
    timeout_seconds: float
    keep_alive: OllamaKeepAlive

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("generation profile name is required")
        if self.provider not in {"ollama", "openai_compatible"}:
            raise ValueError("unsupported generation provider")
        if not self.model.strip():
            raise ValueError("generation provider and model are required")
        if self.num_ctx < 512:
            raise ValueError("num_ctx must be at least 512")
        if self.max_input_tokens < 1:
            raise ValueError("max_input_tokens must be positive")
        if self.context_reserve_tokens < 1:
            raise ValueError("context_reserve_tokens must be positive")
        if self.num_predict < 1:
            raise ValueError("num_predict must be positive")
        if (
            self.max_input_tokens + self.num_predict + self.context_reserve_tokens
            > self.num_ctx
        ):
            raise ValueError(
                "input, output, and reserve tokens must fit the effective context"
            )
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if not 0 < self.top_p <= 1:
            raise ValueError("top_p must be greater than zero and at most one")
        if self.top_k < 1:
            raise ValueError("top_k must be positive")
        if not 0.1 <= self.repeat_penalty <= 3:
            raise ValueError("repeat_penalty must be between 0.1 and 3")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if isinstance(self.keep_alive, str):
            normalized_keep_alive = self.keep_alive.strip()
            if not normalized_keep_alive:
                raise ValueError("keep_alive must not be empty")
            if normalized_keep_alive != self.keep_alive:
                raise ValueError("string keep_alive must already be normalized")
            if normalized_keep_alive in {"-1", "0"}:
                raise ValueError("numeric keep_alive sentinels must be integers")
        elif (
            isinstance(self.keep_alive, bool)
            or not isinstance(self.keep_alive, int)
            or self.keep_alive not in {-1, 0}
        ):
            raise ValueError("numeric keep_alive must be -1 or 0")

    def safe_log_fields(self) -> dict[str, object]:
        return {
            "generation_profile": self.name,
            "generation_profile_kind": self.kind,
            "model": self.model,
            "num_ctx": self.num_ctx,
            "max_input_tokens": self.max_input_tokens,
            "num_predict": self.num_predict,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "thinking": self.thinking,
            "timeout_seconds": self.timeout_seconds,
            "keep_alive": self.keep_alive,
        }


@dataclass(frozen=True, slots=True)
class RetrievalProfileSettings:
    enabled: bool
    fetch_k: int
    top_k: int
    min_relevance_score: float
    max_context_chars: int
    max_per_source: int
    rrf_k: int
    blocking_max_concurrency: int
    allowed_species: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    query_max_variants: int
    reranker_enabled: bool
    reranker_top_n: int
    neighbor_expansion_enabled: bool
    neighbor_expansion_max_chunks: int

    def __post_init__(self) -> None:
        if self.fetch_k < 1 or self.top_k < 1 or self.top_k > self.fetch_k:
            raise ValueError("RAG top_k must be positive and no greater than fetch_k")
        if not 0 <= self.min_relevance_score <= 1:
            raise ValueError("RAG relevance score must be between zero and one")
        if self.max_context_chars < 1 or self.max_per_source < 1:
            raise ValueError("RAG context and per-source limits must be positive")
        if self.rrf_k < 1 or self.blocking_max_concurrency < 1:
            raise ValueError("RAG RRF and concurrency settings must be positive")
        if not self.allowed_species or not self.allowed_domains:
            raise ValueError("RAG species and domain allowlists must not be empty")
        if self.query_max_variants < 1:
            raise ValueError("RAG query_max_variants must be positive")
        if self.reranker_top_n < 1:
            raise ValueError("RAG reranker_top_n must be positive")
        if self.neighbor_expansion_max_chunks < 0:
            raise ValueError("RAG neighbor_expansion_max_chunks cannot be negative")


@dataclass(frozen=True, slots=True)
class MemoryProfileSettings:
    history_limit: int
    summary_max_chars: int
    summary_max_tokens: int
    topic_limit: int
    recent_question_limit: int
    clinical_fact_limit: int
    summarized_message_id_limit: int
    answer_excerpt_chars: int
    question_excerpt_chars: int
    summary_entry_chars: int
    session_ttl_seconds: int
    turn_lease_grace_seconds: float

    def __post_init__(self) -> None:
        integer_values = {
            "history_limit": self.history_limit,
            "summary_max_chars": self.summary_max_chars,
            "summary_max_tokens": self.summary_max_tokens,
            "topic_limit": self.topic_limit,
            "recent_question_limit": self.recent_question_limit,
            "clinical_fact_limit": self.clinical_fact_limit,
            "summarized_message_id_limit": self.summarized_message_id_limit,
            "answer_excerpt_chars": self.answer_excerpt_chars,
            "question_excerpt_chars": self.question_excerpt_chars,
            "summary_entry_chars": self.summary_entry_chars,
            "session_ttl_seconds": self.session_ttl_seconds,
        }
        if self.history_limit < 0:
            raise ValueError("history_limit cannot be negative")
        for name, value in integer_values.items():
            if name != "history_limit" and value < 1:
                raise ValueError(f"{name} must be positive")
        if self.turn_lease_grace_seconds < 0:
            raise ValueError("turn_lease_grace_seconds cannot be negative")


@dataclass(frozen=True, slots=True)
class ProviderRuntimeSettings:
    connect_timeout_seconds: float
    generation_timeout_seconds: float
    write_timeout_seconds: float
    pool_timeout_seconds: float
    queue_timeout_seconds: float
    total_timeout_seconds: float
    repair_min_remaining_seconds: float
    heartbeat_seconds: float
    max_connections: int
    max_keepalive_connections: int
    keepalive_expiry_seconds: float
    connection_retries: int
    max_concurrent_generations: int
    database_max_concurrency: int

    def __post_init__(self) -> None:
        positive_times = {
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "generation_timeout_seconds": self.generation_timeout_seconds,
            "write_timeout_seconds": self.write_timeout_seconds,
            "pool_timeout_seconds": self.pool_timeout_seconds,
            "queue_timeout_seconds": self.queue_timeout_seconds,
            "total_timeout_seconds": self.total_timeout_seconds,
            "repair_min_remaining_seconds": self.repair_min_remaining_seconds,
            "heartbeat_seconds": self.heartbeat_seconds,
            "keepalive_expiry_seconds": self.keepalive_expiry_seconds,
        }
        for name, value in positive_times.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.generation_timeout_seconds >= self.total_timeout_seconds:
            raise ValueError("provider timeout must be lower than total chat timeout")
        provider_subtimeouts = {
            "connect_timeout_seconds": self.connect_timeout_seconds,
            "write_timeout_seconds": self.write_timeout_seconds,
            "pool_timeout_seconds": self.pool_timeout_seconds,
        }
        if any(
            value > self.generation_timeout_seconds
            for value in provider_subtimeouts.values()
        ):
            raise ValueError(
                "provider connect, write, and pool timeouts must not exceed "
                "the generation timeout"
            )
        if self.queue_timeout_seconds >= self.total_timeout_seconds:
            raise ValueError("queue timeout must be lower than total chat timeout")
        if self.repair_min_remaining_seconds >= self.total_timeout_seconds:
            raise ValueError("repair window must be lower than total chat timeout")
        if self.heartbeat_seconds >= self.total_timeout_seconds:
            raise ValueError("heartbeat must be lower than total chat timeout")
        if self.max_connections < 1:
            raise ValueError("max_connections must be positive")
        if not 0 <= self.max_keepalive_connections <= self.max_connections:
            raise ValueError("keepalive connections cannot exceed max connections")
        if self.connection_retries not in {0, 1}:
            raise ValueError("connection retries must be zero or one")
        if self.max_concurrent_generations < 1 or self.database_max_concurrency < 1:
            raise ValueError("generation and database concurrency must be positive")


@dataclass(frozen=True, slots=True)
class GenerationProfileSettings:
    """Single effective configuration source for the production chat module."""

    provider: ProviderName
    model: str
    context_length: int
    max_input_tokens: int
    context_reserve_tokens: int
    num_predict: int
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    thinking: bool
    keep_alive: OllamaKeepAlive
    general_context_length: int | None
    selected_context_length: int | None
    history_context_length: int | None
    general_temperature: float | None
    selected_temperature: float | None
    history_temperature: float | None
    repair_context_length: int | None
    repair_max_input_tokens: int | None
    repair_num_predict: int
    repair_temperature: float
    repair_top_p: float
    repair_top_k: int
    repair_repeat_penalty: float
    repair_thinking: bool
    max_generation_attempts: int
    structured_output_enabled: bool
    tools_enabled: bool
    tool_max_rounds: int
    clinical_fact_min_count: int
    clinical_fact_max_count: int
    clinical_fact_tokens_per_item: int
    context_parameter_limit: int
    retrieval: RetrievalProfileSettings
    memory: MemoryProfileSettings
    runtime: ProviderRuntimeSettings

    def __post_init__(self) -> None:
        if self.max_generation_attempts not in {1, 2}:
            raise ValueError("the current orchestrator supports one or two attempts")
        if not 1 <= self.clinical_fact_min_count <= self.clinical_fact_max_count:
            raise ValueError("clinical fact limits are inconsistent")
        if self.clinical_fact_tokens_per_item < 1:
            raise ValueError("clinical_fact_tokens_per_item must be positive")
        if self.context_parameter_limit < 1:
            raise ValueError("context_parameter_limit must be positive")
        for scope in ("general", "selected_hemogram", "hemogram_history"):
            main = self.main_profile(name=f"validation_{scope}", context_scope=scope)
            self.repair_profile(name=f"validation_{scope}_repair", base=main)

    @classmethod
    def from_settings(cls, settings: Settings) -> GenerationProfileSettings:
        provider = settings.CHAT_LLM_PROVIDER
        model = (
            settings.OLLAMA_MODEL
            if provider == "ollama"
            else settings.OPENAI_COMPATIBLE_MODEL
        )
        if not model:
            raise ValueError("the selected chat provider requires a model")
        return cls(
            provider=provider,
            model=model,
            context_length=settings.OLLAMA_CONTEXT_LENGTH,
            max_input_tokens=settings.CHAT_MAX_INPUT_TOKENS,
            context_reserve_tokens=settings.CHAT_CONTEXT_RESERVE_TOKENS,
            num_predict=settings.OLLAMA_NUM_PREDICT,
            temperature=settings.OLLAMA_TEMPERATURE,
            top_p=settings.OLLAMA_TOP_P,
            top_k=settings.OLLAMA_TOP_K,
            repeat_penalty=settings.OLLAMA_REPEAT_PENALTY,
            thinking=settings.OLLAMA_THINK,
            keep_alive=normalize_ollama_keep_alive(settings.OLLAMA_KEEP_ALIVE),
            general_context_length=settings.CHAT_PROFILE_GENERAL_CONTEXT_LENGTH,
            selected_context_length=settings.CHAT_PROFILE_SELECTED_CONTEXT_LENGTH,
            history_context_length=settings.CHAT_PROFILE_HISTORY_CONTEXT_LENGTH,
            general_temperature=settings.CHAT_PROFILE_GENERAL_TEMPERATURE,
            selected_temperature=settings.CHAT_PROFILE_SELECTED_TEMPERATURE,
            history_temperature=settings.CHAT_PROFILE_HISTORY_TEMPERATURE,
            repair_context_length=settings.CHAT_REPAIR_CONTEXT_LENGTH,
            repair_max_input_tokens=settings.CHAT_REPAIR_MAX_INPUT_TOKENS,
            repair_num_predict=settings.CHAT_REPAIR_NUM_PREDICT,
            repair_temperature=settings.CHAT_REPAIR_TEMPERATURE,
            repair_top_p=settings.CHAT_REPAIR_TOP_P,
            repair_top_k=settings.CHAT_REPAIR_TOP_K,
            repair_repeat_penalty=settings.CHAT_REPAIR_REPEAT_PENALTY,
            repair_thinking=settings.CHAT_REPAIR_THINK,
            max_generation_attempts=settings.CHAT_MAX_GENERATION_ATTEMPTS,
            structured_output_enabled=settings.CHAT_STRUCTURED_OUTPUT_ENABLED,
            tools_enabled=settings.CHAT_TOOLS_ENABLED,
            tool_max_rounds=settings.CHAT_TOOL_MAX_ROUNDS,
            clinical_fact_min_count=settings.CHAT_CLINICAL_FACT_MIN_COUNT,
            clinical_fact_max_count=settings.CHAT_CLINICAL_FACT_MAX_COUNT,
            clinical_fact_tokens_per_item=settings.CHAT_CLINICAL_FACT_TOKENS_PER_ITEM,
            context_parameter_limit=settings.CHAT_CONTEXT_PARAMETER_LIMIT,
            retrieval=RetrievalProfileSettings(
                enabled=settings.RAG_ENABLED,
                fetch_k=settings.RAG_FETCH_K,
                top_k=settings.RAG_TOP_K,
                min_relevance_score=settings.RAG_MIN_RELEVANCE_SCORE,
                max_context_chars=settings.RAG_MAX_CONTEXT_CHARS,
                max_per_source=settings.RAG_MAX_PER_SOURCE,
                rrf_k=settings.RAG_RRF_K,
                blocking_max_concurrency=settings.RAG_BLOCKING_MAX_CONCURRENCY,
                allowed_species=settings.RAG_ALLOWED_SPECIES,
                allowed_domains=settings.RAG_ALLOWED_DOMAINS,
                query_max_variants=settings.RAG_QUERY_MAX_VARIANTS,
                reranker_enabled=settings.RAG_RERANKER_ENABLED,
                reranker_top_n=settings.RAG_RERANKER_TOP_N,
                neighbor_expansion_enabled=settings.RAG_NEIGHBOR_EXPANSION_ENABLED,
                neighbor_expansion_max_chunks=(
                    settings.RAG_NEIGHBOR_EXPANSION_MAX_CHUNKS
                ),
            ),
            memory=MemoryProfileSettings(
                history_limit=settings.CHAT_HISTORY_LIMIT,
                summary_max_chars=settings.CHAT_SUMMARY_MAX_CHARS,
                summary_max_tokens=settings.CHAT_SUMMARY_MAX_TOKENS,
                topic_limit=settings.CHAT_MEMORY_TOPIC_LIMIT,
                recent_question_limit=settings.CHAT_MEMORY_RECENT_QUESTION_LIMIT,
                clinical_fact_limit=settings.CHAT_MEMORY_CLINICAL_FACT_LIMIT,
                summarized_message_id_limit=(
                    settings.CHAT_MEMORY_SUMMARIZED_MESSAGE_ID_LIMIT
                ),
                answer_excerpt_chars=settings.CHAT_MEMORY_ANSWER_EXCERPT_CHARS,
                question_excerpt_chars=settings.CHAT_MEMORY_QUESTION_EXCERPT_CHARS,
                summary_entry_chars=settings.CHAT_MEMORY_SUMMARY_ENTRY_CHARS,
                session_ttl_seconds=settings.CHAT_SESSION_TTL_SECONDS,
                turn_lease_grace_seconds=settings.CHAT_TURN_LEASE_GRACE_SECONDS,
            ),
            runtime=ProviderRuntimeSettings(
                connect_timeout_seconds=settings.OLLAMA_CONNECT_TIMEOUT_SECONDS,
                generation_timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
                write_timeout_seconds=settings.OLLAMA_WRITE_TIMEOUT_SECONDS,
                pool_timeout_seconds=settings.OLLAMA_POOL_TIMEOUT_SECONDS,
                queue_timeout_seconds=settings.CHAT_QUEUE_TIMEOUT_SECONDS,
                total_timeout_seconds=settings.CHAT_TOTAL_TIMEOUT_SECONDS,
                repair_min_remaining_seconds=(
                    settings.CHAT_REPAIR_MIN_REMAINING_SECONDS
                ),
                heartbeat_seconds=settings.CHAT_STREAM_HEARTBEAT_SECONDS,
                max_connections=settings.OLLAMA_HTTP_MAX_CONNECTIONS,
                max_keepalive_connections=(
                    settings.OLLAMA_HTTP_MAX_KEEPALIVE_CONNECTIONS
                ),
                keepalive_expiry_seconds=(
                    settings.OLLAMA_HTTP_KEEPALIVE_EXPIRY_SECONDS
                ),
                connection_retries=settings.OLLAMA_MAX_RETRIES,
                max_concurrent_generations=(settings.CHAT_MAX_CONCURRENT_GENERATIONS),
                database_max_concurrency=settings.CHAT_DB_BLOCKING_MAX_CONCURRENCY,
            ),
        )

    def main_profile(
        self,
        *,
        name: str,
        context_scope: str,
    ) -> EffectiveGenerationProfile:
        context_override = (
            self.general_context_length
            if context_scope == "general"
            else self.history_context_length
            if context_scope in {"hemogram_history", "historical_analysis"}
            else self.selected_context_length
        )
        # `is not None`, no `or`: una temperatura 0.0 configurada es una
        # decisión válida y un falsy accidental la desharía en silencio.
        temperature_override = (
            self.general_temperature
            if context_scope == "general"
            else self.history_temperature
            if context_scope in {"hemogram_history", "historical_analysis"}
            else self.selected_temperature
        )
        return EffectiveGenerationProfile(
            name=name,
            kind="main",
            provider=self.provider,
            model=self.model,
            num_ctx=context_override or self.context_length,
            max_input_tokens=self.max_input_tokens,
            context_reserve_tokens=self.context_reserve_tokens,
            num_predict=self.num_predict,
            temperature=(
                temperature_override
                if temperature_override is not None
                else self.temperature
            ),
            top_p=self.top_p,
            top_k=self.top_k,
            repeat_penalty=self.repeat_penalty,
            thinking=self.thinking,
            timeout_seconds=self.runtime.generation_timeout_seconds,
            keep_alive=self.keep_alive,
        )

    # A boundary answer is two or three sentences that name no value: "I can't
    # tell you a dose, ask your vet". Sizing it like a clinical interpretation
    # is what made a correct refusal take 41 s against production on
    # 2026-08-06 (BF-07) — the tokens were budgeted, not spent, but the
    # generation was still carried at full size behind a full clinical prompt.
    # A ceiling rather than a fixed value, so a deployment that already
    # configured a smaller num_predict keeps it.
    BOUNDARY_NUM_PREDICT_CEILING = 320

    def boundary_profile(
        self,
        *,
        name: str,
        context_scope: str,
    ) -> EffectiveGenerationProfile:
        """Return the main profile shrunk to what a policy boundary needs."""

        base = self.main_profile(name=name, context_scope=context_scope)
        return replace(
            base,
            num_predict=min(base.num_predict, self.BOUNDARY_NUM_PREDICT_CEILING),
        )

    def repair_profile(
        self,
        *,
        name: str,
        base: EffectiveGenerationProfile,
        truncated: bool = False,
    ) -> EffectiveGenerationProfile:
        # A repair that follows a truncated generation must not be born with
        # less output budget than the attempt that just ran out of room:
        # repair_num_predict below the main num_predict would guarantee a
        # second truncation and waste the whole repair call (M-5).
        num_predict = self.repair_num_predict
        if truncated:
            num_predict = max(num_predict, base.num_predict)
        return EffectiveGenerationProfile(
            name=name,
            kind="repair",
            provider=self.provider,
            model=self.model,
            num_ctx=self.repair_context_length or base.num_ctx,
            max_input_tokens=self.repair_max_input_tokens or base.max_input_tokens,
            context_reserve_tokens=self.context_reserve_tokens,
            num_predict=num_predict,
            temperature=self.repair_temperature,
            top_p=self.repair_top_p,
            top_k=self.repair_top_k,
            repeat_penalty=self.repair_repeat_penalty,
            thinking=self.repair_thinking,
            timeout_seconds=self.runtime.generation_timeout_seconds,
            keep_alive=self.keep_alive,
        )


__all__ = [
    "EffectiveGenerationProfile",
    "GenerationProfileSettings",
    "MemoryProfileSettings",
    "OllamaKeepAlive",
    "ProfileKind",
    "ProviderName",
    "ProviderRuntimeSettings",
    "RetrievalProfileSettings",
    "normalize_ollama_keep_alive",
]
