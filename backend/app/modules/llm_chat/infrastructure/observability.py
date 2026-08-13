from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import hashlib
import hmac
import importlib
import json
import logging
import math
import re
import secrets
from threading import Lock
import time
from typing import Any
from urllib.parse import urlsplit

_CORRELATION: ContextVar[Mapping[str, object]] = ContextVar(
    "hemovet_llm_chat_correlation",
    default={},
)
_IDENTIFIER_KEYS = frozenset(
    {
        "analysis_id",
        "auth_session_id",
        "browser_session_id",
        "client_message_id",
        "conversation_id",
        "owner_id",
        "patient_id",
        "pet_id",
        "session_id",
        "turn_id",
        "user_id",
    }
)
_FORBIDDEN_KEYS = frozenset(
    {
        "answer",
        "case_facts",
        "chain_of_thought",
        "clinical_facts",
        "content",
        "conversation",
        "conversation_history",
        "document_text",
        "evidence_text",
        "message",
        "messages",
        "prompt",
        "query",
        "reasoning",
        "system_prompt",
        "thinking_content",
        "user_prompt",
    }
)
_SAFE_LOG_KEYS = frozenset(
    {
        "attempt",
        "bm25_duration_ms",
        "cancelled",
        "chroma_duration_ms",
        "clinical_context_duration_ms",
        "clinical_facts_duration_ms",
        "claim_ids",
        "completion_tokens",
        "context_length",
        "context_revision",
        "contract_version",
        "cuda_version",
        "duration_ms",
        "embedding_duration_ms",
        "embedding_fingerprint",
        "embedding_model",
        "embedding_provider",
        "embedding_version",
        "error_code",
        "eval_count",
        "eval_duration_ms",
        "finish_reason",
        "first_valid_response_ms",
        "fusion_duration_ms",
        "generated_tokens",
        "generation_attempt",
        "generation_duration_ms",
        "generation_tokens_per_second",
        "guardrail_decisions",
        "inference_device",
        "input_validation_duration_ms",
        "intent",
        "intent_confidence",
        "llm_invoked",
        "load_duration_ms",
        "model_context_length",
        "mode",
        "model_digest",
        "model_name",
        "model_size_bytes",
        "nvidia_driver",
        "ollama_version",
        "operation",
        "parallelism",
        "parse_duration_ms",
        "persistence_duration_ms",
        "prompt_eval_count",
        "prompt_eval_duration_ms",
        "prompt_tokens",
        "prompt_tokens_per_second",
        "prompt_version",
        "prompt_build_duration_ms",
        "provider",
        "query_rewrite_duration_ms",
        "quantization",
        "queue_wait_ms",
        "repair_attempts",
        "request_id",
        "reranker_model",
        "reranker_scores",
        "reranking_duration_ms",
        "result_status",
        "retriever_version",
        "retrieval_duration_ms",
        "retrieval_scores",
        "retrieved_chunk_ids",
        "route",
        "seed",
        "session_resolution_duration_ms",
        "size_vram_bytes",
        "source_count",
        "span_id",
        "stage",
        "stream_mode",
        "temperature",
        "thinking_mode",
        "top_k",
        "top_p",
        "total_duration_ms",
        "trace_id",
        "ttft_ms",
        "validated",
        "validation_duration_ms",
        "validation_failures",
        "verified_fact_ids",
        "vram_ratio",
    }
)
_SAFE_METRIC_KEYS = frozenset(
    {
        "error_code",
        "intent",
        "mode",
        "provider",
        "result_status",
        "stage",
    }
)
_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+\-]{0,191}$")
_EVENT_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{0,95}$")
_HEADER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]{1,128}$")


@dataclass(frozen=True, slots=True)
class TelemetryAvailability:
    enabled: bool
    available: bool
    reason: str


class OtelSdkErrorCode(str, Enum):
    SDK_UNAVAILABLE = "opentelemetry_sdk_unavailable"
    OTLP_HTTP_EXPORTER_UNAVAILABLE = "otlp_http_exporter_unavailable"
    INVALID_OTLP_ENDPOINT = "invalid_otlp_endpoint"
    INVALID_OTLP_HEADERS = "invalid_otlp_headers"
    INVALID_RESOURCE_ATTRIBUTE = "invalid_resource_attribute"
    INVALID_SAMPLER = "invalid_sampler"
    INVALID_SAMPLE_RATIO = "invalid_sample_ratio"
    INVALID_EXPORT_TIMEOUT = "invalid_export_timeout"
    INVALID_BATCH_CONFIGURATION = "invalid_batch_configuration"
    INVALID_METRIC_INTERVAL = "invalid_metric_interval"
    INVALID_SHUTDOWN_TIMEOUT = "invalid_shutdown_timeout"
    SDK_INITIALIZATION_FAILED = "opentelemetry_sdk_initialization_failed"
    GLOBAL_PROVIDER_INSTALL_FAILED = "opentelemetry_global_provider_install_failed"


class OtelLifecycleErrorCode(str, Enum):
    TRACE_FORCE_FLUSH_FAILED = "trace_force_flush_failed"
    METRIC_FORCE_FLUSH_FAILED = "metric_force_flush_failed"
    TRACE_SHUTDOWN_FAILED = "trace_shutdown_failed"
    METRIC_SHUTDOWN_FAILED = "metric_shutdown_failed"


@dataclass(frozen=True, slots=True)
class OtelSdkSettings:
    """Explicit OTLP/HTTP SDK settings; secrets are excluded from repr."""

    enabled: bool = False
    otlp_endpoint: str = "http://localhost:4318"
    traces_endpoint: str | None = None
    metrics_endpoint: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict, repr=False, compare=False)
    service_name: str = "hemovet-backend"
    service_version: str = "unknown"
    environment: str = "development"
    sampler: str = "parent_based_trace_id_ratio"
    sample_ratio: float = 1.0
    export_timeout_ms: int = 10_000
    batch_schedule_delay_ms: int = 5_000
    max_queue_size: int = 2_048
    max_export_batch_size: int = 512
    metric_export_interval_ms: int = 60_000
    shutdown_timeout_ms: int = 30_000
    install_global_providers: bool = True


@dataclass(frozen=True, slots=True)
class OtelLifecycleResult:
    completed: bool
    already_shutdown: bool = False
    error_codes: tuple[OtelLifecycleErrorCode, ...] = ()


@dataclass(slots=True)
class OtelSdkRuntime:
    """Own SDK providers and make flush/shutdown deterministic and idempotent."""

    tracer_provider: Any = field(repr=False)
    meter_provider: Any = field(repr=False)
    shutdown_timeout_ms: int
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _shutdown_result: OtelLifecycleResult | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def force_flush(self) -> OtelLifecycleResult:
        with self._lock:
            if self._shutdown_result is not None:
                return OtelLifecycleResult(
                    completed=self._shutdown_result.completed,
                    already_shutdown=True,
                    error_codes=self._shutdown_result.error_codes,
                )
            errors: list[OtelLifecycleErrorCode] = []
            if not _run_lifecycle_method(
                self.meter_provider,
                "force_flush",
                timeout_millis=self.shutdown_timeout_ms,
            ):
                errors.append(OtelLifecycleErrorCode.METRIC_FORCE_FLUSH_FAILED)
            if not _run_lifecycle_method(
                self.tracer_provider,
                "force_flush",
                timeout_millis=self.shutdown_timeout_ms,
            ):
                errors.append(OtelLifecycleErrorCode.TRACE_FORCE_FLUSH_FAILED)
            return OtelLifecycleResult(
                completed=not errors,
                error_codes=tuple(errors),
            )

    def shutdown(self) -> OtelLifecycleResult:
        with self._lock:
            if self._shutdown_result is not None:
                return OtelLifecycleResult(
                    completed=self._shutdown_result.completed,
                    already_shutdown=True,
                    error_codes=self._shutdown_result.error_codes,
                )
            errors: list[OtelLifecycleErrorCode] = []
            if not _run_lifecycle_method(
                self.meter_provider,
                "shutdown",
                timeout_millis=self.shutdown_timeout_ms,
            ):
                errors.append(OtelLifecycleErrorCode.METRIC_SHUTDOWN_FAILED)
            if not _run_lifecycle_method(self.tracer_provider, "shutdown"):
                errors.append(OtelLifecycleErrorCode.TRACE_SHUTDOWN_FAILED)
            self._shutdown_result = OtelLifecycleResult(
                completed=not errors,
                error_codes=tuple(errors),
            )
            return self._shutdown_result


@dataclass(frozen=True, slots=True)
class OtelSdkSetupResult:
    availability: TelemetryAvailability
    runtime: OtelSdkRuntime | None = field(default=None, repr=False)
    error_code: OtelSdkErrorCode | None = None


@dataclass(frozen=True, slots=True)
class _OtelApi:
    trace: Any
    metrics: Any


@dataclass(frozen=True, slots=True)
class _OtelSdk:
    trace_api: Any
    metrics_api: Any
    resource: Any
    tracer_provider: Any
    meter_provider: Any
    batch_span_processor: Any
    periodic_metric_reader: Any
    span_exporter: Any
    metric_exporter: Any
    always_on: Any
    always_off: Any
    trace_id_ratio_based: Any
    parent_based: Any


@dataclass(frozen=True, slots=True)
class _OtelSdkLoadResult:
    sdk: _OtelSdk | None
    error_code: OtelSdkErrorCode | None = None


class _OtelConfigurationError(Exception):
    def __init__(self, code: OtelSdkErrorCode) -> None:
        super().__init__(code.value)
        self.code = code


class IdentifierAnonymizer:
    """Stable, namespace-separated HMAC identifiers for telemetry."""

    def __init__(self, secret: str | bytes | None = None) -> None:
        if secret is None:
            self._secret = secrets.token_bytes(32)
            self.ephemeral = True
        else:
            encoded = secret.encode("utf-8") if isinstance(secret, str) else secret
            if len(encoded) < 16:
                raise ValueError("telemetry_hmac_secret_too_short")
            self._secret = encoded
            self.ephemeral = False

    def anonymize(self, namespace: str, value: object) -> str:
        normalized = str(value).strip()
        if not normalized:
            return ""
        digest = hmac.new(
            self._secret,
            f"{namespace}\x00{normalized}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"hmac_{digest[:20]}"


class StructuredChatLogger:
    """Emit allowlisted JSON logs without prompts or raw clinical identifiers."""

    def __init__(
        self,
        logger: logging.Logger | None = None,
        *,
        hmac_secret: str | bytes | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger("hemovet.llm_chat.telemetry")
        self.anonymizer = IdentifierAnonymizer(hmac_secret)

    @contextmanager
    def bind(self, **attributes: object) -> Iterator[None]:
        safe = self.sanitize(attributes)
        token = _CORRELATION.set({**_CORRELATION.get(), **safe})
        try:
            yield
        finally:
            _CORRELATION.reset(token)

    def sanitize(
        self,
        attributes: Mapping[str, object] | None,
        *,
        metrics: bool = False,
    ) -> dict[str, object]:
        safe: dict[str, object] = {}
        allowed = _SAFE_METRIC_KEYS if metrics else _SAFE_LOG_KEYS
        for raw_key, value in (attributes or {}).items():
            key = str(raw_key).strip().casefold()
            if not key or key in _FORBIDDEN_KEYS or value is None:
                continue
            if key in _IDENTIFIER_KEYS:
                anonymous = self.anonymizer.anonymize(key, value)
                if anonymous and not metrics:
                    safe[f"{key.removesuffix('_id')}_hash"] = anonymous
                continue
            if key not in allowed:
                continue
            cleaned = _safe_value(value)
            if cleaned is not None:
                safe[key] = cleaned
        return safe

    def emit(
        self,
        event: str,
        attributes: Mapping[str, object] | None = None,
        *,
        level: int = logging.INFO,
    ) -> dict[str, object]:
        normalized_event = event.strip().casefold()
        if not _EVENT_PATTERN.fullmatch(normalized_event):
            normalized_event = "invalid_event_name"
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": normalized_event,
            **_CORRELATION.get(),
            **self.sanitize(attributes),
        }
        self.logger.log(
            level,
            json.dumps(
                payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ),
        )
        return payload


class ChatTelemetry:
    """Optional OpenTelemetry facade that remains usable without OTel packages.

    SDK/exporter setup is deliberately separate in ``configure_otel_sdk`` so the
    application lifecycle owns startup and shutdown. Importing this module is
    always safe in the minimal backend image.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        service_name: str = "hemovet.llm_chat",
        logger: StructuredChatLogger | None = None,
        hmac_secret: str | bytes | None = None,
    ) -> None:
        self.logger = logger or StructuredChatLogger(hmac_secret=hmac_secret)
        self.service_name = service_name
        self._api = _load_optional_otel() if enabled else None
        if not enabled:
            self.availability = TelemetryAvailability(False, False, "disabled")
        elif self._api is None:
            self.availability = TelemetryAvailability(
                True,
                False,
                "opentelemetry_api_unavailable",
            )
        else:
            self.availability = TelemetryAvailability(True, True, "ready")
        self._tracer = (
            self._api.trace.get_tracer(service_name) if self._api is not None else None
        )
        self._meter = (
            self._api.metrics.get_meter(service_name) if self._api is not None else None
        )
        self._duration = (
            self._meter.create_histogram(
                "hemovet.chat.stage.duration",
                unit="ms",
                description="Latency of one LLM chat processing stage.",
            )
            if self._meter is not None
            else None
        )
        self._results = (
            self._meter.create_counter(
                "hemovet.chat.results",
                unit="{request}",
                description="Terminal LLM chat request results.",
            )
            if self._meter is not None
            else None
        )

    @contextmanager
    def bind(self, **attributes: object) -> Iterator[None]:
        with self.logger.bind(**attributes):
            yield

    @contextmanager
    def span(
        self,
        stage: str,
        attributes: Mapping[str, object] | None = None,
    ) -> Iterator[Any | None]:
        normalized_stage = _safe_code(stage) or "unknown"
        started = time.perf_counter()
        log_attributes = {"stage": normalized_stage, **(attributes or {})}
        metric_attributes = self.logger.sanitize(log_attributes, metrics=True)
        span_attributes = self.logger.sanitize(log_attributes)
        self.logger.emit("stage.started", log_attributes)
        span_context = (
            self._tracer.start_as_current_span(
                f"llm_chat.{normalized_stage}",
                attributes=span_attributes,
            )
            if self._tracer is not None
            else _NullSpanContext()
        )
        span: Any | None = None
        try:
            with span_context as span:
                yield span
        except BaseException as exc:
            error_code = type(exc).__name__
            if span is not None:
                _set_span_attribute(span, "error.type", error_code)
            self.logger.emit(
                "stage.failed",
                {**log_attributes, "error_code": error_code},
                level=logging.ERROR,
            )
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            if self._duration is not None:
                self._duration.record(elapsed_ms, metric_attributes)
            self.logger.emit(
                "stage.completed",
                {**log_attributes, "duration_ms": round(elapsed_ms, 3)},
            )

    def record_result(
        self,
        result_status: str,
        *,
        attributes: Mapping[str, object] | None = None,
    ) -> None:
        values = {"result_status": result_status, **(attributes or {})}
        metric_attributes = self.logger.sanitize(values, metrics=True)
        if self._results is not None:
            self._results.add(1, metric_attributes)
        self.logger.emit("request.result", values)

    def current_trace_id(self) -> str | None:
        if self._api is None:
            return None
        try:
            context = self._api.trace.get_current_span().get_span_context()
            if not getattr(context, "is_valid", False):
                return None
            return f"{int(context.trace_id):032x}"
        except Exception:
            return None


class _NullSpanContext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *args: object) -> None:
        return None


def _load_optional_otel() -> _OtelApi | None:
    try:
        return _OtelApi(
            trace=importlib.import_module("opentelemetry.trace"),
            metrics=importlib.import_module("opentelemetry.metrics"),
        )
    except Exception:
        return None


def configure_otel_sdk(settings: OtelSdkSettings) -> OtelSdkSetupResult:
    """Build OTLP/HTTP tracing and metrics providers without eager imports.

    Configuration and import errors are intentionally reduced to stable error
    codes. Exporter headers, endpoints and exception messages are never copied
    into the returned result.
    """

    if not settings.enabled:
        return OtelSdkSetupResult(
            availability=TelemetryAvailability(False, False, "disabled")
        )

    try:
        traces_endpoint, metrics_endpoint = _validated_signal_endpoints(settings)
        headers = _validated_headers(settings.headers)
        resource_attributes = _validated_resource_attributes(settings)
        _validate_sdk_timing(settings)
    except _OtelConfigurationError as exc:
        return _sdk_setup_failure(exc.code)

    loaded = _load_optional_otel_sdk()
    if loaded is None:
        return _sdk_setup_failure(OtelSdkErrorCode.SDK_UNAVAILABLE)
    if loaded.sdk is None:
        return _sdk_setup_failure(loaded.error_code or OtelSdkErrorCode.SDK_UNAVAILABLE)
    sdk = loaded.sdk

    tracer_provider: Any | None = None
    meter_provider: Any | None = None
    span_processor: Any | None = None
    metric_reader: Any | None = None
    span_exporter: Any | None = None
    metric_exporter: Any | None = None
    span_processor_registered = False
    try:
        sampler = _build_sampler(sdk, settings)
        resource = sdk.resource.create(resource_attributes)
        span_exporter = sdk.span_exporter(
            endpoint=traces_endpoint,
            headers=headers,
            timeout=settings.export_timeout_ms / 1_000,
        )
        span_processor = sdk.batch_span_processor(
            span_exporter,
            max_queue_size=settings.max_queue_size,
            schedule_delay_millis=settings.batch_schedule_delay_ms,
            max_export_batch_size=settings.max_export_batch_size,
            export_timeout_millis=settings.export_timeout_ms,
        )
        tracer_provider = sdk.tracer_provider(
            resource=resource,
            sampler=sampler,
            shutdown_on_exit=False,
        )
        tracer_provider.add_span_processor(span_processor)
        span_processor_registered = True

        metric_exporter = sdk.metric_exporter(
            endpoint=metrics_endpoint,
            headers=headers,
            timeout=settings.export_timeout_ms / 1_000,
        )
        metric_reader = sdk.periodic_metric_reader(
            metric_exporter,
            export_interval_millis=settings.metric_export_interval_ms,
            export_timeout_millis=settings.export_timeout_ms,
        )
        meter_provider = sdk.meter_provider(
            resource=resource,
            metric_readers=[metric_reader],
            shutdown_on_exit=False,
        )
    except Exception:
        _cleanup_partial_sdk(
            tracer_provider=tracer_provider,
            meter_provider=meter_provider,
            span_processor=span_processor,
            metric_reader=metric_reader,
            span_exporter=span_exporter,
            metric_exporter=metric_exporter,
            span_processor_registered=span_processor_registered,
        )
        return _sdk_setup_failure(OtelSdkErrorCode.SDK_INITIALIZATION_FAILED)

    runtime = OtelSdkRuntime(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        shutdown_timeout_ms=settings.shutdown_timeout_ms,
    )
    if settings.install_global_providers:
        try:
            sdk.trace_api.set_tracer_provider(tracer_provider)
            sdk.metrics_api.set_meter_provider(meter_provider)
            if not _global_provider_matches(
                sdk.trace_api,
                "get_tracer_provider",
                tracer_provider,
            ) or not _global_provider_matches(
                sdk.metrics_api,
                "get_meter_provider",
                meter_provider,
            ):
                raise RuntimeError("global_provider_not_installed")
        except Exception:
            runtime.shutdown()
            return _sdk_setup_failure(OtelSdkErrorCode.GLOBAL_PROVIDER_INSTALL_FAILED)

    return OtelSdkSetupResult(
        availability=TelemetryAvailability(True, True, "ready"),
        runtime=runtime,
    )


def _load_optional_otel_sdk() -> _OtelSdkLoadResult:
    try:
        trace_api = importlib.import_module("opentelemetry.trace")
        metrics_api = importlib.import_module("opentelemetry.metrics")
        resources = importlib.import_module("opentelemetry.sdk.resources")
        sdk_trace = importlib.import_module("opentelemetry.sdk.trace")
        sampling = importlib.import_module("opentelemetry.sdk.trace.sampling")
        trace_export = importlib.import_module("opentelemetry.sdk.trace.export")
        sdk_metrics = importlib.import_module("opentelemetry.sdk.metrics")
        metrics_export = importlib.import_module("opentelemetry.sdk.metrics.export")
    except Exception:
        return _OtelSdkLoadResult(
            sdk=None,
            error_code=OtelSdkErrorCode.SDK_UNAVAILABLE,
        )

    try:
        http_trace_exporter = importlib.import_module(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter"
        )
        http_metric_exporter = importlib.import_module(
            "opentelemetry.exporter.otlp.proto.http.metric_exporter"
        )
    except Exception:
        return _OtelSdkLoadResult(
            sdk=None,
            error_code=OtelSdkErrorCode.OTLP_HTTP_EXPORTER_UNAVAILABLE,
        )

    return _OtelSdkLoadResult(
        sdk=_OtelSdk(
            trace_api=trace_api,
            metrics_api=metrics_api,
            resource=resources.Resource,
            tracer_provider=sdk_trace.TracerProvider,
            meter_provider=sdk_metrics.MeterProvider,
            batch_span_processor=trace_export.BatchSpanProcessor,
            periodic_metric_reader=metrics_export.PeriodicExportingMetricReader,
            span_exporter=http_trace_exporter.OTLPSpanExporter,
            metric_exporter=http_metric_exporter.OTLPMetricExporter,
            always_on=sampling.ALWAYS_ON,
            always_off=sampling.ALWAYS_OFF,
            trace_id_ratio_based=sampling.TraceIdRatioBased,
            parent_based=sampling.ParentBased,
        )
    )


def _sdk_setup_failure(error_code: OtelSdkErrorCode) -> OtelSdkSetupResult:
    return OtelSdkSetupResult(
        availability=TelemetryAvailability(True, False, error_code.value),
        error_code=error_code,
    )


def _validated_signal_endpoints(settings: OtelSdkSettings) -> tuple[str, str]:
    base = _validated_http_endpoint(settings.otlp_endpoint)
    traces = (
        _validated_http_endpoint(settings.traces_endpoint)
        if settings.traces_endpoint is not None
        else f"{base}/v1/traces"
    )
    metrics = (
        _validated_http_endpoint(settings.metrics_endpoint)
        if settings.metrics_endpoint is not None
        else f"{base}/v1/metrics"
    )
    return traces, metrics


def _validated_http_endpoint(value: object) -> str:
    if not isinstance(value, str):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_OTLP_ENDPOINT)
    normalized = value.strip().rstrip("/")
    try:
        parsed = urlsplit(normalized)
    except ValueError as exc:
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_OTLP_ENDPOINT) from exc
    if (
        not normalized
        or any(character.isspace() for character in normalized)
        or parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_OTLP_ENDPOINT)
    return normalized


def _validated_headers(headers: object) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_OTLP_HEADERS)
    validated: dict[str, str] = {}
    try:
        items = list(headers.items())
    except Exception as exc:
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_OTLP_HEADERS) from exc
    for key, value in items:
        if (
            not isinstance(key, str)
            or not _HEADER_NAME_PATTERN.fullmatch(key)
            or not isinstance(value, str)
            or not value
            or len(value) > 4_096
            or "\r" in value
            or "\n" in value
        ):
            raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_OTLP_HEADERS)
        validated[key] = value
    return validated


def _validated_resource_attributes(settings: OtelSdkSettings) -> dict[str, str]:
    values = {
        "service.name": settings.service_name,
        "service.version": settings.service_version,
        "deployment.environment.name": settings.environment,
    }
    for value in values.values():
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > 255
            or any(ord(character) < 32 for character in value)
        ):
            raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_RESOURCE_ATTRIBUTE)
    return {key: value.strip() for key, value in values.items()}


def _validate_sdk_timing(settings: OtelSdkSettings) -> None:
    if not isinstance(settings.sampler, str):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_SAMPLER)
    normalized_sampler = settings.sampler.strip().casefold().replace("-", "_")
    if normalized_sampler not in {
        "always_on",
        "always_off",
        "trace_id_ratio",
        "parent_based_trace_id_ratio",
    }:
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_SAMPLER)
    if (
        isinstance(settings.sample_ratio, bool)
        or not isinstance(settings.sample_ratio, int | float)
        or not math.isfinite(float(settings.sample_ratio))
        or not 0 <= float(settings.sample_ratio) <= 1
    ):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_SAMPLE_RATIO)
    if not _is_positive_int(settings.export_timeout_ms):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_EXPORT_TIMEOUT)
    if (
        not _is_positive_int(settings.batch_schedule_delay_ms)
        or not _is_positive_int(settings.max_queue_size)
        or not _is_positive_int(settings.max_export_batch_size)
        or settings.max_export_batch_size > settings.max_queue_size
    ):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_BATCH_CONFIGURATION)
    if not _is_positive_int(settings.metric_export_interval_ms):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_METRIC_INTERVAL)
    if not _is_positive_int(settings.shutdown_timeout_ms):
        raise _OtelConfigurationError(OtelSdkErrorCode.INVALID_SHUTDOWN_TIMEOUT)


def _build_sampler(sdk: _OtelSdk, settings: OtelSdkSettings) -> Any:
    normalized = settings.sampler.strip().casefold().replace("-", "_")
    if normalized == "always_on":
        return sdk.always_on
    if normalized == "always_off":
        return sdk.always_off
    ratio_sampler = sdk.trace_id_ratio_based(float(settings.sample_ratio))
    if normalized == "trace_id_ratio":
        return ratio_sampler
    return sdk.parent_based(ratio_sampler)


def _is_positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _run_lifecycle_method(
    component: object,
    method_name: str,
    *,
    timeout_millis: int | None = None,
) -> bool:
    method = getattr(component, method_name, None)
    if not callable(method):
        return False
    try:
        result = (
            method(timeout_millis=timeout_millis)
            if timeout_millis is not None
            else method()
        )
    except Exception:
        return False
    return result is not False


def _cleanup_partial_sdk(
    *,
    tracer_provider: object | None,
    meter_provider: object | None,
    span_processor: object | None,
    metric_reader: object | None,
    span_exporter: object | None,
    metric_exporter: object | None,
    span_processor_registered: bool,
) -> None:
    if meter_provider is not None:
        _run_lifecycle_method(meter_provider, "shutdown")
    elif metric_reader is not None:
        _run_lifecycle_method(metric_reader, "shutdown")
    elif metric_exporter is not None:
        _run_lifecycle_method(metric_exporter, "shutdown")

    if tracer_provider is not None:
        _run_lifecycle_method(tracer_provider, "shutdown")
    if span_processor is not None and not span_processor_registered:
        _run_lifecycle_method(span_processor, "shutdown")
    elif tracer_provider is None and span_exporter is not None:
        _run_lifecycle_method(span_exporter, "shutdown")


def _global_provider_matches(
    api: object,
    getter_name: str,
    expected_provider: object,
) -> bool:
    getter = getattr(api, getter_name, None)
    if not callable(getter):
        return True
    try:
        return getter() is expected_provider
    except Exception:
        return False


def _set_span_attribute(span: Any, key: str, value: object) -> None:
    try:
        span.set_attribute(key, value)
    except Exception:
        return


def _safe_value(value: object) -> object | None:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _safe_code(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        items = [
            safe
            for item in value[:32]
            for safe in [_safe_scalar(item)]
            if safe is not None
        ]
        return items
    return None


def _safe_scalar(value: object) -> str | int | float | bool | None:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _safe_code(value)
    return None


def _safe_code(value: object) -> str | None:
    normalized = str(value).strip()
    if not normalized or not _CODE_PATTERN.fullmatch(normalized):
        return None
    return normalized
