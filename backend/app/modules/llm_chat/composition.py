from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.availability import ChatAvailability, ProviderAvailability
from app.core.config import Settings
from app.db.session import SessionLocal
from app.modules.llm_chat.application.services.blocking_work import (
    BoundedBlockingExecutor,
)
from app.modules.llm_chat.application.services.conversation_memory import (
    ConversationMemoryService,
)
from app.modules.llm_chat.application.services.chat_profile_policy import (
    ChatProfilePolicy,
)
from app.modules.llm_chat.application.services.output_validator import OutputValidator
from app.modules.llm_chat.application.services.output_sanitizer import OutputSanitizer
from app.modules.llm_chat.application.services.prompt_builder import PromptBuilder
from app.modules.llm_chat.application.services.retrieval_service import (
    RetrievalOutcome,
    RetrievalService,
)
from app.modules.llm_chat.application.services.safety_policy import SafetyPolicy
from app.modules.llm_chat.application.services.structured_response import (
    StructuredResponseService,
)
from app.modules.llm_chat.application.services.token_budget import TokenCounter
from app.modules.llm_chat.application.use_cases.send_chat_message import (
    SendChatMessageUseCase,
)
from app.modules.llm_chat.api.schemas import chat_response_from_result
from app.modules.llm_chat.domain.rag_index import (
    RAGIndexFingerprint,
    build_rag_index_fingerprint,
)
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings
from app.modules.llm_chat.domain.ports import LLMProvider
from app.modules.llm_chat.domain.provider_contract import (
    ProviderApiFlavor,
    ProviderFailureCode,
    ProviderTimeoutPolicy,
    RemoteLLMProviderContract,
    is_retryable_provider_failure,
    normalize_provider_failure_code,
)
from app.modules.llm_chat.infrastructure.documents.markdown_chunker import (
    MarkdownChunker,
)
from app.modules.llm_chat.infrastructure.documents.source_catalog import SourceCatalog
from app.modules.llm_chat.infrastructure.embeddings.fastembed_client import (
    FastEmbedEmbeddingClient,
)
from app.modules.llm_chat.infrastructure.entailment import (
    OnnxClaimEntailmentVerifier,
)
from app.modules.llm_chat.infrastructure.llm.openai_compatible_client import (
    OpenAICompatibleLLMClient,
    OllamaNativeLLMClient,
)
from app.modules.llm_chat.application.services.rerankers import (
    HeuristicMultilingualReranker,
    NoopReranker,
)
from app.modules.llm_chat.infrastructure.observability import ChatTelemetry
from app.modules.llm_chat.infrastructure.retrieval.bm25_store import ChromaBM25Store
from app.modules.llm_chat.infrastructure.repositories.sqlalchemy_repositories import (
    NonBlockingSqlAlchemyRepository,
    SqlAlchemyAnalysisContextRepository,
    SqlAlchemyConversationRepository,
)
from app.modules.llm_chat.infrastructure.vectorstores.chroma_store import (
    ChromaNeighborStore,
    ChromaRetrievalStore,
)

logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")
PROVIDER_HEALTH_PROBE_BUDGET_SECONDS = 2.0
# Etapa 8, Block B: how long a chat_ready snapshot stays valid before a new
# turn triggers a fresh probe. Short enough that a genuinely broken provider
# is caught within one interval; long enough that a normal turn almost never
# pays a live provider round-trip on top of generation itself.
CHAT_AVAILABILITY_CACHE_SECONDS = 5.0


def resolve_telemetry_hmac_secret(settings: Settings) -> str | None:
    """Use the dedicated telemetry key only when it contains a real value."""

    configured = (
        settings.OTEL_IDENTIFIER_HMAC_SECRET.get_secret_value()
        if settings.OTEL_IDENTIFIER_HMAC_SECRET is not None
        else ""
    )
    if configured:
        return configured
    return settings.SECRET_KEY if len(settings.SECRET_KEY) >= 16 else None


def build_claim_entailment_verifier(
    settings: Settings,
) -> OnnxClaimEntailmentVerifier | None:
    """The entailment verifier for documentary support, or nothing.

    Nothing is the default. Returning ``None`` leaves StructuredResponseService
    exactly as it behaves without this feature — lexical support decision plus
    the numeric and polarity vetoes — and nothing is downloaded or loaded into
    memory. Construction cannot fail the startup either: the model is fetched
    and initialized in the verifier's own worker thread, and a failure there
    only costs the entailment opinion.
    """

    if not settings.CHAT_CLAIM_ENTAILMENT_ENABLED:
        return None
    cache_dir = settings.CHAT_CLAIM_ENTAILMENT_CACHE_DIR
    if not cache_dir.is_absolute():
        cache_dir = (settings.HEMOVET_PROJECT_ROOT / cache_dir).resolve()
    verifier = OnnxClaimEntailmentVerifier(
        model_repo=settings.CHAT_CLAIM_ENTAILMENT_MODEL,
        threshold=settings.CHAT_CLAIM_ENTAILMENT_THRESHOLD,
        timeout_seconds=settings.CHAT_CLAIM_ENTAILMENT_TIMEOUT_SECONDS,
        cache_dir=cache_dir,
        intra_op_threads=settings.CHAT_CLAIM_ENTAILMENT_THREADS,
    )
    # Loading 1.1 GB of weights takes far longer than one claim's deadline, so
    # it starts here instead of inside the first turn that needs it. Turns
    # arriving meanwhile get no verdict and fall back to the lexical rule.
    verifier.warmup()
    logger.info(
        "llm_chat.claim_entailment_enabled model=%s threshold=%s timeout=%s",
        settings.CHAT_CLAIM_ENTAILMENT_MODEL,
        settings.CHAT_CLAIM_ENTAILMENT_THRESHOLD,
        settings.CHAT_CLAIM_ENTAILMENT_TIMEOUT_SECONDS,
    )
    return verifier


def validate_ollama_runtime_identity(
    runtime_status: dict[str, object],
    *,
    expected_model: str | None,
    expected_digest: str | None,
    expected_quantization: str | None,
) -> str | None:
    """Return a stable readiness error when a pinned Ollama artifact differs."""

    if not expected_digest and not expected_quantization:
        return None
    if runtime_status.get("installed") is False:
        return ProviderFailureCode.LLM_PROVIDER_IDENTITY_UNVERIFIED.value
    actual_model = str(runtime_status.get("model") or "").removesuffix(":latest")
    configured_model = str(expected_model or "").removesuffix(":latest")
    if configured_model and not actual_model:
        return ProviderFailureCode.LLM_PROVIDER_IDENTITY_UNVERIFIED.value
    if configured_model and actual_model != configured_model:
        return ProviderFailureCode.LLM_PROVIDER_MODEL_MISMATCH.value
    if expected_digest:
        configured_digest = expected_digest.strip().casefold().removeprefix("sha256:")
        actual_digest = (
            str(runtime_status.get("digest") or "")
            .strip()
            .casefold()
            .removeprefix("sha256:")
        )
        if not actual_digest:
            return ProviderFailureCode.LLM_PROVIDER_IDENTITY_UNVERIFIED.value
        if actual_digest != configured_digest:
            return ProviderFailureCode.LLM_PROVIDER_DIGEST_MISMATCH.value
    if expected_quantization:
        actual_quantization = (
            str(runtime_status.get("quantization") or "").strip().casefold()
        )
        if not actual_quantization:
            return ProviderFailureCode.LLM_PROVIDER_IDENTITY_UNVERIFIED.value
        if actual_quantization != expected_quantization.strip().casefold():
            return ProviderFailureCode.LLM_PROVIDER_QUANTIZATION_MISMATCH.value
    return None


class UnavailableRetriever:
    """Safe fallback that keeps non-RAG chat routes available.

    Identity, social and out-of-domain turns must not depend on Chroma. Clinical
    routes receive no evidence and therefore follow the insufficient-evidence
    policy instead of silently using a stale or incompatible collection.
    """

    available = False

    async def retrieve(self, _query: str, **_kwargs: object) -> RetrievalOutcome:
        return RetrievalOutcome(chunks=(), available=False)


def validate_runtime_rag_index(
    settings: Settings,
    metadata: dict[str, Any],
) -> RAGIndexFingerprint:
    try:
        configured = RAGIndexFingerprint.from_collection_metadata(metadata)
    except ValueError as exc:
        raise ChatRuntimeUnavailable("rag_index_fingerprint_invalid") from exc
    embedding_spec = FastEmbedEmbeddingClient.fingerprint_spec(
        model_name=settings.RAG_EMBEDDING_MODEL,
        dimension=settings.RAG_EMBEDDING_DIMENSION,
        model_revision=settings.RAG_EMBEDDING_MODEL_REVISION,
        pooling_strategy=settings.RAG_EMBEDDING_POOLING_STRATEGY,
        normalization=settings.RAG_EMBEDDING_NORMALIZATION,
        document_prefix=settings.RAG_EMBEDDING_DOCUMENT_PREFIX,
        query_prefix=settings.RAG_EMBEDDING_QUERY_PREFIX,
    )
    expected = build_rag_index_fingerprint(
        embedding=embedding_spec,
        chunking_version=MarkdownChunker.SCHEMA_VERSION,
        chunk_size=settings.RAG_CHUNK_SIZE_WORDS,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP_WORDS,
        metadata_schema_version=settings.RAG_SCHEMA_VERSION,
        content_version=configured.content_version,
    )
    if expected.digest != configured.digest:
        raise ChatRuntimeUnavailable("rag_index_fingerprint_runtime_mismatch")
    return configured


# Referencias fuertes a las tareas de fondo. Ver el comentario en
# `start_runner_realignment`: el bucle de eventos solo guarda una debil.
_TAREAS_VIVAS: set[asyncio.Task[None]] = set()


@dataclass(slots=True)
class ChatContainer:
    send_chat: SendChatMessageUseCase
    conversations: Any
    llm: LLMProvider
    chroma_client: Any | None
    collection: Any | None
    http_client: httpx.AsyncClient | None
    embedding_model: str
    provider_contract: RemoteLLMProviderContract | None = None
    analysis_context: Any | None = None
    rag_enabled: bool = True
    rag_issue: str | None = None
    index_fingerprint: str | None = None
    expected_model: str | None = None
    expected_model_digest: str | None = None
    expected_quantization: str | None = None
    _realign_task: asyncio.Task[None] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _warmup_task: asyncio.Task[None] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    _availability_checked_at: float = field(default=0.0, init=False, repr=False)
    _availability_ready: bool = field(default=True, init=False, repr=False)
    _availability_code: str | None = field(default=None, init=False, repr=False)

    async def cached_chat_readiness(self) -> tuple[bool, str | None]:
        """Return the canonical chat_ready decision from a short-lived cache.

        Reuses ``health()`` — the same authority backing ``/chat/health`` —
        instead of a second, independent identity probe. A turn only pays a
        live provider round-trip once every ``CHAT_AVAILABILITY_CACHE_SECONDS``;
        every other turn in that window reads the cached decision.
        """
        now = time.monotonic()
        if now - self._availability_checked_at >= CHAT_AVAILABILITY_CACHE_SECONDS:
            payload = await self.health()
            ready = bool(payload.get("chat_ready"))
            code: str | None = None
            if not ready:
                provider = payload.get("provider")
                provider_code = (
                    provider.get("code") if isinstance(provider, dict) else None
                )
                code = str(
                    provider_code or ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value
                )
            self._availability_checked_at = now
            self._availability_ready = ready
            self._availability_code = code
        return self._availability_ready, self._availability_code

    async def _provider_identity(self) -> tuple[dict[str, object], bool]:
        probe = getattr(self.llm, "identity_status", None)
        if callable(probe):
            identity = await probe()
            if not isinstance(identity, dict):
                raise TypeError("provider identity status must be a mapping")
            return identity, bool(identity.get("installed"))
        ready = bool(await self.llm.health())
        return (
            {
                "provider": (
                    self.provider_contract.provider
                    if self.provider_contract is not None
                    else "unknown"
                ),
                "model": getattr(self.llm, "model_name", None),
                "installed": ready,
            },
            ready,
        )

    async def _provider_residency(self) -> dict[str, object]:
        runtime = await self.llm.runtime_status()
        if not isinstance(runtime, dict):
            raise TypeError("provider runtime status must be a mapping")
        return runtime

    async def health(self) -> dict[str, object]:
        if not self.rag_enabled:
            chunk_count = 0
            chroma_ready = False
        elif self.chroma_client is None or self.collection is None:
            chunk_count = 0
            chroma_ready = False
        else:
            try:
                await self.chroma_client.heartbeat()
                chunk_count = await self.collection.count()
                chroma_ready = True
            except Exception:
                chunk_count = 0
                chroma_ready = False
        try:
            identity_result, residency_result = await asyncio.wait_for(
                asyncio.gather(
                    self._provider_identity(),
                    self._provider_residency(),
                    return_exceptions=True,
                ),
                timeout=PROVIDER_HEALTH_PROBE_BUDGET_SECONDS,
            )
        except TimeoutError as exc:
            # Provider availability is advisory for core readiness. Bound the
            # combined identity/residency probe so a stopped GPU cannot make
            # the operational endpoint exceed the container health deadline.
            identity_result = exc
            residency_result = exc
        identity_probe_failed = isinstance(identity_result, BaseException)
        if identity_probe_failed:
            provider_ready = False
            identity_status: dict[str, object] = {
                "provider": (
                    self.provider_contract.provider
                    if self.provider_contract is not None
                    else "unknown"
                ),
                "model": getattr(self.llm, "model_name", None),
                "installed": False,
            }
        else:
            identity_status, provider_ready = identity_result

        residency_observed = not isinstance(residency_result, BaseException)
        runtime_status = (
            residency_result
            if residency_observed
            else {
                "provider": identity_status.get("provider", "unknown"),
                "model": identity_status.get(
                    "model", getattr(self.llm, "model_name", None)
                ),
                "loaded": False,
                "gpu_active": None,
                "gpu_memory_bytes": None,
                "inference_device": "unknown",
            }
        )
        runtime_status = dict(runtime_status)
        for key in ("provider", "model", "installed", "digest", "quantization"):
            value = identity_status.get(key)
            if value is not None:
                runtime_status[key] = value
        runtime_status["residency_observed"] = residency_observed
        provider_name = str(runtime_status.get("provider") or "unknown")
        residency_required = self.expected_model is not None and provider_name == "ollama"
        residency_ready: bool | None = None
        if residency_required:
            residency_ready = bool(
                residency_observed
                and runtime_status.get("loaded") is True
                and runtime_status.get("gpu_active") is True
                and runtime_status.get("inference_device") == "full_gpu"
            )
        runtime_status["residency_required"] = residency_required
        runtime_status["residency_ready"] = residency_ready
        runtime_identity_error = (
            None
            if identity_probe_failed
            else validate_ollama_runtime_identity(
                runtime_status,
                expected_model=self.expected_model,
                expected_digest=self.expected_model_digest,
                expected_quantization=self.expected_quantization,
            )
        )
        identity_verification_required = bool(
            self.expected_model_digest or self.expected_quantization
        )
        identity_verified: bool | None = None
        if identity_verification_required and not identity_probe_failed:
            identity_verified = runtime_identity_error is None
        runtime_status["identity_verified"] = identity_verified
        runtime_status["identity_error_code"] = runtime_identity_error
        if runtime_identity_error is not None:
            provider_ready = False
        if residency_required and not residency_ready:
            # An installed 27B artifact is not yet able to answer while its
            # runner is cold. Letting a turn through here makes the user's
            # request pay the multi-minute load and exceed the generation
            # timeout. The GPU bootstrap owns that warmup; chat becomes ready
            # only after /api/ps proves the pinned model is fully resident.
            provider_ready = False
        provider_code = runtime_identity_error
        if not provider_ready and provider_code is None:
            provider_code = ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value
        normalized_provider_code = (
            normalize_provider_failure_code(provider_code)
            if provider_code is not None
            else None
        )
        if normalized_provider_code is not None:
            provider_code = normalized_provider_code.value
        provider = ProviderAvailability(
            provider=provider_name,
            model=str(runtime_status.get("model") or "") or None,
            ready=provider_ready,
            code=provider_code,
            retryable=(
                is_retryable_provider_failure(provider_code)
                if provider_code is not None
                else False
            ),
            identity_verified=identity_verified,
        )
        availability = ChatAvailability(
            provider=provider,
            module_ready=True,
            rag_required=self.rag_enabled,
            chroma_ready=chroma_ready,
            collection_ready=chroma_ready,
            rag_index_ready=chroma_ready and chunk_count > 0,
        )
        public = availability.to_public_dict()
        public.update(
            {
                "rag_enabled": self.rag_enabled,
                "rag_issue": self.rag_issue,
                "chunk_count": chunk_count,
                "embedding_model": self.embedding_model,
                "index_fingerprint": self.index_fingerprint,
                "runtime": runtime_status,
                "runtime_identity_error": runtime_identity_error,
                "gpu_active": runtime_status.get("gpu_active"),
                "gpu_memory_bytes": runtime_status.get("gpu_memory_bytes"),
                "inference_device": runtime_status.get("inference_device"),
                "provider_contract": (
                    self.provider_contract.to_safe_dict()
                    if self.provider_contract is not None
                    else None
                ),
            }
        )
        return public

    def start_provider_warmup(self, *, timeout_seconds: float) -> None:
        """Schedule best-effort preparation without delaying application startup."""

        warmup = getattr(self.llm, "warmup", None)
        if not callable(warmup) or self._warmup_task is not None:
            return

        async def run() -> None:
            try:
                warmed = bool(await warmup(timeout_seconds=timeout_seconds))
                # La referencia del vigilante se toma aquí, con el modelo recién
                # cargado por nosotros: es el único instante en que sabemos que
                # el runner es el del perfil.
                baseline = getattr(self.llm, "capture_runner_baseline", None)
                referencia = None
                if warmed and callable(baseline):
                    referencia = await baseline()
                # Se registra el VALOR, no que se llamara. Si sale None, el
                # vigilante queda inerte para toda la vida del proceso —
                # `realign_runner_if_drifted` sale por `if self._warmed_vram is
                # None: return False`— y hasta ahora eso era indistinguible
                # desde fuera de un poll que mira y no encuentra deriva.
                logger.info(
                    "llm_chat.provider_warmup completed=%s baseline_vram=%s",
                    warmed,
                    referencia,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "llm_chat.provider_warmup_failed error_type=%s",
                    type(exc).__name__,
                )

        self._warmup_task = asyncio.create_task(
            run(),
            name="llm-chat-provider-warmup",
        )

    def start_runner_realignment(self, *, interval_seconds: float) -> None:
        """Vigila que el runner residente siga siendo el del perfil.

        El warmup corre una vez, al construir el contenedor. La VM de la GPU
        carga el mismo modelo con su propio contexto al validar su arranque, y
        cuando esa VM se reinicia el backend sigue vivo y no vuelve a hacer
        warmup: el runner queda desalineado y **el primer turno real paga la
        recarga** — 101 s de mediana (n=5) frente a 0,55 s cuando coinciden.

        Comprobarlo tras generar arreglaría el turno 2 y dejaría al primero
        pagando. Por eso es un poll y no un gancho de post-proceso: la ventana de
        exposición pasa a ser el intervalo, no «hasta que llegue alguien».
        """

        if interval_seconds <= 0:
            # Apagado, no revertido. El codigo y sus tres eventos siguen aqui para
            # quien retome M-15; encenderlo es cambiar un numero.
            logger.info(
                "llm_chat.runner_realign_disabled interval_seconds=%s", interval_seconds
            )
            return

        realign = getattr(self.llm, "realign_runner_if_drifted", None)
        if not callable(realign) or self._realign_task is not None:
            # Callar aqui era el fallo: un poll que nunca arranca resultaba
            # identico, desde fuera, a uno que arranca y no ve deriva.
            logger.info(
                "llm_chat.runner_realign_not_started callable=%s already_running=%s",
                callable(realign),
                self._realign_task is not None,
            )
            return

        async def run() -> None:
            vuelta = 0
            while True:
                await asyncio.sleep(interval_seconds)
                vuelta += 1
                try:
                    rearmado = await realign()
                    # La primera vuelta a nivel info: es la que demuestra que la
                    # tarea sobrevivio al primer `sleep`. `asyncio.create_task`
                    # solo deja una referencia debil en el bucle, y una tarea sin
                    # referencia fuerte puede recogerse a media ejecucion.
                    logger.log(
                        logging.INFO if vuelta == 1 else logging.DEBUG,
                        "llm_chat.runner_realign_tick vuelta=%s rearmado=%s",
                        vuelta,
                        rearmado,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Nunca debe tumbar el proceso: es mantenimiento, no camino
                    # de petición. Un fallo aquí sólo significa que el siguiente
                    # turno puede pagar la recarga, que es el estado de hoy.
                    logger.warning(
                        "llm_chat.runner_realign_failed error_type=%s",
                        type(exc).__name__,
                        exc_info=True,
                    )

        tarea = asyncio.create_task(run(), name="llm-chat-runner-realignment")
        # Dos referencias fuertes a proposito. `asyncio.create_task` solo guarda
        # una referencia debil en el bucle de eventos, y la documentacion de
        # Python avisa de que una tarea sin referencia fuerte puede recogerse
        # "en cualquier momento, incluso antes de terminar". Hoy el contenedor
        # vive en `app.state` durante todo el proceso y basta con `self`, pero
        # eso es una propiedad del llamante, no de esta funcion.
        _TAREAS_VIVAS.add(tarea)
        tarea.add_done_callback(_TAREAS_VIVAS.discard)
        self._realign_task = tarea
        logger.info(
            "llm_chat.runner_realign_started interval_seconds=%s task=%s",
            interval_seconds,
            tarea.get_name(),
        )

    async def close(self) -> None:
        if self._realign_task is not None:
            self._realign_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._realign_task
        if self._warmup_task is not None:
            self._warmup_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._warmup_task
        if self.http_client is not None:
            await self.http_client.aclose()


async def build_chat_container(settings: Settings) -> ChatContainer:
    chat_settings = GenerationProfileSettings.from_settings(settings)
    if chat_settings.provider == "ollama":
        if not settings.OLLAMA_BASE_URL:
            raise RuntimeError("OLLAMA_BASE_URL is required for Ollama chat")
        llm_base_url = settings.OLLAMA_BASE_URL
        llm_model = chat_settings.model
        api_key = settings.OLLAMA_API_KEY
    else:
        if not settings.OPENAI_COMPATIBLE_BASE_URL:
            raise RuntimeError(
                "OPENAI_COMPATIBLE_BASE_URL is required when "
                "CHAT_LLM_PROVIDER=openai_compatible"
            )
        llm_base_url = settings.OPENAI_COMPATIBLE_BASE_URL
        llm_model = chat_settings.model
        api_key = settings.OPENAI_COMPATIBLE_API_KEY

    provider_contract = RemoteLLMProviderContract(
        provider=chat_settings.provider,
        api_flavor=(
            ProviderApiFlavor.OLLAMA_NATIVE
            if chat_settings.provider == "ollama"
            else ProviderApiFlavor.OPENAI_COMPATIBLE
        ),
        base_url=llm_base_url,
        model=llm_model,
        timeouts=ProviderTimeoutPolicy(
            connect_seconds=chat_settings.runtime.connect_timeout_seconds,
            read_seconds=chat_settings.runtime.generation_timeout_seconds,
            write_seconds=chat_settings.runtime.write_timeout_seconds,
            pool_seconds=chat_settings.runtime.pool_timeout_seconds,
            stream_deadline_seconds=chat_settings.runtime.total_timeout_seconds,
            heartbeat_seconds=chat_settings.runtime.heartbeat_seconds,
        ),
        connection_retries=chat_settings.runtime.connection_retries,
        expected_digest=(
            settings.OLLAMA_EXPECTED_MODEL_DIGEST
            if chat_settings.provider == "ollama"
            else None
        ),
        expected_quantization=(
            settings.OLLAMA_EXPECTED_QUANTIZATION
            if chat_settings.provider == "ollama"
            else None
        ),
    )

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key.get_secret_value()}"
    request_timeout = httpx.Timeout(
        chat_settings.runtime.generation_timeout_seconds,
        connect=chat_settings.runtime.connect_timeout_seconds,
        read=chat_settings.runtime.generation_timeout_seconds,
        write=chat_settings.runtime.write_timeout_seconds,
        pool=chat_settings.runtime.pool_timeout_seconds,
    )
    http_client = httpx.AsyncClient(
        headers=headers,
        timeout=request_timeout,
        limits=httpx.Limits(
            max_connections=chat_settings.runtime.max_connections,
            max_keepalive_connections=(chat_settings.runtime.max_keepalive_connections),
            keepalive_expiry=chat_settings.runtime.keepalive_expiry_seconds,
        ),
        transport=httpx.AsyncHTTPTransport(
            retries=chat_settings.runtime.connection_retries
        ),
    )
    if chat_settings.provider == "ollama":
        llm = OllamaNativeLLMClient(
            http_client=http_client,
            base_url=llm_base_url,
            model_name=llm_model,
            timeout_seconds=request_timeout,
            warmup_profile=chat_settings.main_profile(
                name="warmup",
                context_scope="general",
            ),
        )
    else:
        llm = OpenAICompatibleLLMClient(
            http_client=http_client,
            base_url=llm_base_url,
            model_name=llm_model,
            timeout_seconds=request_timeout,
        )
    database_executor = BoundedBlockingExecutor(
        max_concurrency=chat_settings.runtime.database_max_concurrency
    )
    conversations = NonBlockingSqlAlchemyRepository(
        SqlAlchemyConversationRepository(
            SessionLocal,
            chat_settings=chat_settings,
        ),
        blocking_executor=database_executor,
    )
    allowed_statuses = ["approved"]
    if settings.RAG_ALLOW_TEST_DOCUMENTS:
        allowed_statuses.append("test")
    if settings.RAG_ALLOW_AI_PROVISIONAL:
        allowed_statuses.append("ai_approved_provisional")
    chroma_client: Any | None = None
    collection: Any | None = None
    rag_issue: str | None = None
    active_index_fingerprint: str | None = None
    retrieval: Any = UnavailableRetriever()
    if chat_settings.retrieval.enabled:
        try:
            import chromadb

            chroma_client = await chromadb.AsyncHttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                ssl=settings.CHROMA_SSL,
                tenant=settings.CHROMA_TENANT,
                database=settings.CHROMA_DATABASE,
            )
            # Runtime never creates an empty or ambiguously versioned collection.
            # Ingestion owns collection creation and corpus revision metadata.
            collection = await chroma_client.get_collection(
                name=settings.RAG_COLLECTION_NAME
            )
            metadata = dict(collection.metadata or {})
            if metadata.get("embedding_model") != settings.RAG_EMBEDDING_MODEL:
                raise RuntimeError("embedding_model_mismatch")
            if metadata.get("schema_version") != MarkdownChunker.SCHEMA_VERSION:
                raise RuntimeError("chunk_schema_mismatch")
            if metadata.get("corpus_schema_version") != settings.RAG_SCHEMA_VERSION:
                raise RuntimeError("corpus_schema_mismatch")
            corpus_revision = str(metadata.get("corpus_revision") or "").strip()
            if not corpus_revision:
                raise RuntimeError("missing_corpus_revision")

            configured_fingerprint = validate_runtime_rag_index(settings, metadata)
            active_index_fingerprint = configured_fingerprint.digest

            blocking_executor = BoundedBlockingExecutor(
                max_concurrency=chat_settings.retrieval.blocking_max_concurrency
            )

            embeddings = FastEmbedEmbeddingClient(
                model_name=settings.RAG_EMBEDDING_MODEL,
                dimension=settings.RAG_EMBEDDING_DIMENSION,
                cache_dir=str(settings.RAG_EMBEDDING_CACHE_DIR),
                model_revision=settings.RAG_EMBEDDING_MODEL_REVISION,
                pooling_strategy=settings.RAG_EMBEDDING_POOLING_STRATEGY,
                normalization=settings.RAG_EMBEDDING_NORMALIZATION,
                document_prefix=settings.RAG_EMBEDDING_DOCUMENT_PREFIX,
                query_prefix=settings.RAG_EMBEDDING_QUERY_PREFIX,
            )
            lexical_store = ChromaBM25Store(
                collection,
                allowed_statuses=tuple(allowed_statuses),
                allowed_species=chat_settings.retrieval.allowed_species,
                allowed_domains=chat_settings.retrieval.allowed_domains,
                expected_corpus_revision=corpus_revision,
                expected_index_fingerprint=active_index_fingerprint,
                strict_revision=True,
                blocking_executor=blocking_executor,
            )
            # Build and validate the immutable sparse snapshot before declaring
            # RAG ready. A mixed or stale collection fails closed at startup.
            await lexical_store.refresh()
            retrieval = RetrievalService(
                embeddings=embeddings,
                vector_store=ChromaRetrievalStore(
                    collection,
                    allowed_statuses=tuple(allowed_statuses),
                    allowed_species=chat_settings.retrieval.allowed_species,
                    allowed_domains=chat_settings.retrieval.allowed_domains,
                    expected_index_fingerprint=active_index_fingerprint,
                ),
                lexical_store=lexical_store,
                fetch_k=chat_settings.retrieval.fetch_k,
                top_k=chat_settings.retrieval.top_k,
                min_score=chat_settings.retrieval.min_relevance_score,
                max_per_source=chat_settings.retrieval.max_per_source,
                rrf_k=chat_settings.retrieval.rrf_k,
                blocking_executor=blocking_executor,
                query_max_variants=chat_settings.retrieval.query_max_variants,
                reranker=(
                    HeuristicMultilingualReranker(
                        top_n=chat_settings.retrieval.reranker_top_n,
                    )
                    if chat_settings.retrieval.reranker_enabled
                    else NoopReranker()
                ),
                neighbor_store=ChromaNeighborStore(collection)
                if chat_settings.retrieval.neighbor_expansion_enabled
                else None,
                neighbor_expansion_max_chunks=(
                    chat_settings.retrieval.neighbor_expansion_max_chunks
                ),
            )
        except Exception as exc:
            rag_issue = str(exc) or type(exc).__name__
            chroma_client = None
            collection = None
            active_index_fingerprint = None
            logger.warning("llm_chat.rag_unavailable code=%s", rag_issue)

    analysis_context = NonBlockingSqlAlchemyRepository(
        SqlAlchemyAnalysisContextRepository(SessionLocal),
        blocking_executor=database_executor,
    )
    manifest_path = settings.RAG_SOURCE_MANIFEST
    if not manifest_path.is_absolute():
        manifest_path = (settings.HEMOVET_PROJECT_ROOT / manifest_path).resolve()
    try:
        catalog = SourceCatalog.from_json(manifest_path)
        citable = catalog.citable_sources()
        # Etapa 5, Block G: the catalog shown to the model must represent
        # what is actually indexed and searchable right now, not merely
        # what the bibliography manifest declares. A document can be
        # quarantined during ingestion (Block G1), awaiting reindex, or
        # simply unavailable if RAG failed to initialize above — none of
        # that should still claim to be a usable, citable source.
        if collection is not None:
            try:
                indexed = await collection.get(include=["metadatas"])
                indexed_source_ids = {
                    str(
                        metadata.get("canonical_source_id")
                        or metadata.get("source_id")
                    )
                    for metadata in (indexed.get("metadatas") or [])
                    if metadata
                }
            except Exception:
                logger.warning("llm_chat.source_catalog_index_cross_check_failed")
                indexed_source_ids = set()
            citable = tuple(
                source
                for source in citable
                if source.canonical_source_id in indexed_source_ids
            )
        else:
            citable = ()
        corpus_sources = tuple(
            {
                "title": source.title,
                "authors": list(source.authors),
                "edition": source.edition,
                "source_type": source.source_type,
            }
            for source in citable
        )
    except Exception:
        logger.warning("llm_chat.source_catalog_unavailable")
        corpus_sources = ()
    token_counter = TokenCounter(
        settings.CHAT_TOKENIZER_JSON,
        model_id=chat_settings.model,
        required=settings.CHAT_TOKENIZER_REQUIRED,
        expected_sha256=settings.CHAT_TOKENIZER_SHA256,
    )
    send_chat = SendChatMessageUseCase(
        structured_response_service=StructuredResponseService(
            claim_entailment=build_claim_entailment_verifier(settings),
        ),
        conversations=conversations,
        analysis_context=analysis_context,
        retriever=retrieval,
        llm=llm,
        safety=SafetyPolicy(),
        prompts=PromptBuilder(
            corpus_sources=corpus_sources,
            token_counter=token_counter,
        ),
        output_sanitizer=OutputSanitizer(),
        output_validator=OutputValidator(),
        generation_settings=chat_settings,
        public_response_builder=chat_response_from_result,
        chat_profiles=ChatProfilePolicy(settings=chat_settings),
        memory_service=ConversationMemoryService(
            settings=chat_settings.memory,
            token_counter=token_counter,
        ),
        generation_limiter=asyncio.Semaphore(
            chat_settings.runtime.max_concurrent_generations
        ),
        telemetry=ChatTelemetry(
            enabled=settings.OTEL_ENABLED,
            service_name=f"{settings.OTEL_SERVICE_NAME}.llm_chat",
            hmac_secret=resolve_telemetry_hmac_secret(settings),
        ),
    )
    container = ChatContainer(
        send_chat=send_chat,
        conversations=conversations,
        analysis_context=analysis_context,
        llm=llm,
        chroma_client=chroma_client,
        collection=collection,
        http_client=http_client,
        embedding_model=settings.RAG_EMBEDDING_MODEL,
        provider_contract=provider_contract,
        rag_enabled=chat_settings.retrieval.enabled,
        rag_issue=rag_issue,
        index_fingerprint=active_index_fingerprint,
        expected_model=(
            chat_settings.model if chat_settings.provider == "ollama" else None
        ),
        expected_model_digest=(
            settings.OLLAMA_EXPECTED_MODEL_DIGEST
            if chat_settings.provider == "ollama"
            else None
        ),
        expected_quantization=(
            settings.OLLAMA_EXPECTED_QUANTIZATION
            if chat_settings.provider == "ollama"
            else None
        ),
    )
    if chat_settings.provider == "ollama" and settings.OLLAMA_WARMUP_ENABLED:
        container.start_provider_warmup(
            timeout_seconds=settings.OLLAMA_WARMUP_TIMEOUT_SECONDS
        )
        container.start_runner_realignment(
            interval_seconds=settings.OLLAMA_RUNNER_REALIGN_SECONDS
        )
    return container
