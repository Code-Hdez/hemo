from __future__ import annotations

import json
import logging

import pytest

from app.modules.llm_chat.application.use_cases.send_chat_message import (
    _safe_operational_log_payload,
)
from app.modules.llm_chat.infrastructure import observability
from app.modules.llm_chat.infrastructure.observability import (
    ChatTelemetry,
    IdentifierAnonymizer,
    OtelLifecycleErrorCode,
    OtelSdkErrorCode,
    OtelSdkRuntime,
    OtelSdkSettings,
    StructuredChatLogger,
)

_SECRET = "unit-test-telemetry-secret-32-bytes"


def test_legacy_operational_logs_drop_text_and_hash_identifiers() -> None:
    payload = _safe_operational_log_payload(
        {
            "client_message_id": "client-sensitive",
            "conversation_id": "conversation-sensitive",
            "message": "texto clínico privado",
            "system_prompt": "instrucciones privadas",
            "prompt_tokens": 42,
            "provider_metrics": {
                "eval_count": 7,
                "raw_response": "no registrar",
            },
        }
    )

    serialized = json.dumps(payload)
    assert payload["prompt_tokens"] == 42
    assert payload["provider_metrics"] == {"eval_count": 7}
    assert payload["client_message_hash"]
    assert payload["conversation_hash"]
    for forbidden in (
        "client-sensitive",
        "conversation-sensitive",
        "texto clínico privado",
        "instrucciones privadas",
        "no registrar",
    ):
        assert forbidden not in serialized


def test_identifier_anonymization_is_stable_and_namespace_separated() -> None:
    anonymizer = IdentifierAnonymizer(_SECRET)

    first = anonymizer.anonymize("pet_id", "pet-123")
    repeated = anonymizer.anonymize("pet_id", "pet-123")
    another_namespace = anonymizer.anonymize("analysis_id", "pet-123")

    assert first == repeated
    assert first.startswith("hmac_")
    assert first != another_namespace
    assert "pet-123" not in first


def test_identifier_anonymizer_rejects_short_configured_secrets() -> None:
    with pytest.raises(ValueError, match="telemetry_hmac_secret_too_short"):
        IdentifierAnonymizer("too-short")


def test_structured_logger_drops_prompts_and_hashes_clinical_ids(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = StructuredChatLogger(
        logging.getLogger("test.llm.telemetry"),
        hmac_secret=_SECRET,
    )

    with caplog.at_level(logging.INFO, logger="test.llm.telemetry"):
        with logger.bind(
            request_id="request-123",
            session_id="session-sensitive",
            patient_id="patient-sensitive",
        ):
            payload = logger.emit(
                "request.result",
                {
                    "message": "contenido clínico privado",
                    "system_prompt": "instrucciones privadas",
                    "answer": "respuesta privada",
                    "analysis_id": "analysis-sensitive",
                    "intent": "selected_cbc",
                    "result_status": "valid",
                    "unknown_free_text": "no debe registrarse",
                },
            )

    serialized = caplog.records[-1].getMessage()
    decoded = json.loads(serialized)
    assert decoded == payload
    assert decoded["request_id"] == "request-123"
    assert decoded["intent"] == "selected_cbc"
    assert decoded["result_status"] == "valid"
    assert decoded["session_hash"].startswith("hmac_")
    assert decoded["patient_hash"].startswith("hmac_")
    assert decoded["analysis_hash"].startswith("hmac_")
    for forbidden in (
        "contenido clínico privado",
        "instrucciones privadas",
        "respuesta privada",
        "session-sensitive",
        "patient-sensitive",
        "analysis-sensitive",
        "no debe registrarse",
    ):
        assert forbidden not in serialized


def test_optional_telemetry_is_a_safe_noop_without_otel(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(observability, "_load_optional_otel", lambda: None)
    structured = StructuredChatLogger(
        logging.getLogger("test.llm.noop"),
        hmac_secret=_SECRET,
    )
    telemetry = ChatTelemetry(enabled=True, logger=structured)

    with caplog.at_level(logging.INFO, logger="test.llm.noop"):
        with telemetry.bind(request_id="request-456", pet_id="pet-private"):
            with telemetry.span("retrieval", {"intent": "selected_cbc"}):
                pass
            telemetry.record_result("valid", attributes={"mode": "selected_hemogram"})

    assert telemetry.availability.enabled is True
    assert telemetry.availability.available is False
    assert telemetry.availability.reason == "opentelemetry_api_unavailable"
    assert telemetry.current_trace_id() is None
    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "stage.started" in output
    assert "stage.completed" in output
    assert "request.result" in output
    assert "pet-private" not in output


def test_span_failure_logs_only_exception_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    structured = StructuredChatLogger(
        logging.getLogger("test.llm.failure"),
        hmac_secret=_SECRET,
    )
    telemetry = ChatTelemetry(enabled=False, logger=structured)

    with caplog.at_level(logging.INFO, logger="test.llm.failure"):
        with pytest.raises(RuntimeError, match="private patient text"):
            with telemetry.span("validation"):
                raise RuntimeError("private patient text")

    output = "\n".join(record.getMessage() for record in caplog.records)
    assert "RuntimeError" in output
    assert "private patient text" not in output


class _FakeInstrument:
    def __init__(self) -> None:
        self.records: list[tuple[float, dict[str, object]]] = []

    def record(self, value: float, attributes: dict[str, object]) -> None:
        self.records.append((value, attributes))

    def add(self, value: int, attributes: dict[str, object]) -> None:
        self.records.append((value, attributes))


class _FakeMeter:
    def __init__(self) -> None:
        self.duration = _FakeInstrument()
        self.results = _FakeInstrument()

    def create_histogram(self, *args: object, **kwargs: object) -> _FakeInstrument:
        return self.duration

    def create_counter(self, *args: object, **kwargs: object) -> _FakeInstrument:
        return self.results


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


class _FakeSpanContextManager:
    def __init__(self) -> None:
        self.span = _FakeSpan()

    def __enter__(self) -> _FakeSpan:
        return self.span

    def __exit__(self, *args: object) -> None:
        return None


class _FakeTracer:
    def __init__(self) -> None:
        self.started: list[tuple[str, dict[str, object]]] = []

    def start_as_current_span(
        self,
        name: str,
        *,
        attributes: dict[str, object],
    ) -> _FakeSpanContextManager:
        self.started.append((name, attributes))
        return _FakeSpanContextManager()


class _FakeTraceApi:
    def __init__(self) -> None:
        self.tracer = _FakeTracer()

    def get_tracer(self, name: str) -> _FakeTracer:
        return self.tracer

    @staticmethod
    def get_current_span():
        raise RuntimeError("no active span")


class _FakeMetricsApi:
    def __init__(self) -> None:
        self.meter = _FakeMeter()

    def get_meter(self, name: str) -> _FakeMeter:
        return self.meter


def test_otel_metrics_use_only_low_cardinality_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace_api = _FakeTraceApi()
    metrics_api = _FakeMetricsApi()
    monkeypatch.setattr(
        observability,
        "_load_optional_otel",
        lambda: observability._OtelApi(trace=trace_api, metrics=metrics_api),
    )
    telemetry = ChatTelemetry(enabled=True, hmac_secret=_SECRET)

    with telemetry.span(
        "validation",
        {
            "intent": "selected_cbc",
            "mode": "selected_hemogram",
            "request_id": "high-cardinality-request",
            "patient_id": "patient-private",
        },
    ):
        pass
    telemetry.record_result(
        "valid",
        attributes={
            "intent": "selected_cbc",
            "request_id": "another-request",
            "analysis_id": "analysis-private",
        },
    )

    assert telemetry.availability.available is True
    assert trace_api.tracer.started[0][0] == "llm_chat.validation"
    assert "patient_hash" in trace_api.tracer.started[0][1]
    assert metrics_api.meter.duration.records[0][1] == {
        "stage": "validation",
        "intent": "selected_cbc",
        "mode": "selected_hemogram",
    }
    assert metrics_api.meter.results.records[0][1] == {
        "result_status": "valid",
        "intent": "selected_cbc",
    }


def _make_fake_sdk() -> tuple[observability._OtelSdkLoadResult, dict[str, object]]:
    state: dict[str, object] = {}

    class Resource:
        @staticmethod
        def create(attributes: dict[str, str]) -> dict[str, str]:
            state["resource_attributes"] = attributes
            return attributes

    class SpanExporter:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            state["span_exporter"] = self

    class MetricExporter:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            state["metric_exporter"] = self

    class BatchSpanProcessor:
        def __init__(self, exporter: object, **kwargs: object) -> None:
            self.exporter = exporter
            self.kwargs = kwargs
            state["span_processor"] = self

    class PeriodicMetricReader:
        def __init__(self, exporter: object, **kwargs: object) -> None:
            self.exporter = exporter
            self.kwargs = kwargs
            state["metric_reader"] = self

    class TracerProvider:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.processors: list[object] = []
            self.force_flush_calls = 0
            self.shutdown_calls = 0
            state["tracer_provider"] = self

        def add_span_processor(self, processor: object) -> None:
            self.processors.append(processor)

        def force_flush(self, *, timeout_millis: int) -> bool:
            self.force_flush_calls += 1
            state["trace_flush_timeout"] = timeout_millis
            return True

        def shutdown(self) -> None:
            self.shutdown_calls += 1

    class MeterProvider:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.force_flush_calls = 0
            self.shutdown_calls = 0
            state["meter_provider"] = self

        def force_flush(self, *, timeout_millis: int) -> bool:
            self.force_flush_calls += 1
            state["metric_flush_timeout"] = timeout_millis
            return True

        def shutdown(self, *, timeout_millis: int) -> None:
            self.shutdown_calls += 1
            state["metric_shutdown_timeout"] = timeout_millis

    class TraceApi:
        def __init__(self) -> None:
            self.providers: list[object] = []

        def set_tracer_provider(self, provider: object) -> None:
            self.providers.append(provider)

        def get_tracer_provider(self) -> object | None:
            return self.providers[-1] if self.providers else None

    class MetricsApi:
        def __init__(self) -> None:
            self.providers: list[object] = []

        def set_meter_provider(self, provider: object) -> None:
            self.providers.append(provider)

        def get_meter_provider(self) -> object | None:
            return self.providers[-1] if self.providers else None

    def trace_id_ratio_based(ratio: float) -> tuple[str, float]:
        return ("ratio", ratio)

    def parent_based(root: object) -> tuple[str, object]:
        return ("parent", root)

    trace_api = TraceApi()
    metrics_api = MetricsApi()
    state["trace_api"] = trace_api
    state["metrics_api"] = metrics_api
    return (
        observability._OtelSdkLoadResult(
            sdk=observability._OtelSdk(
                trace_api=trace_api,
                metrics_api=metrics_api,
                resource=Resource,
                tracer_provider=TracerProvider,
                meter_provider=MeterProvider,
                batch_span_processor=BatchSpanProcessor,
                periodic_metric_reader=PeriodicMetricReader,
                span_exporter=SpanExporter,
                metric_exporter=MetricExporter,
                always_on="always-on",
                always_off="always-off",
                trace_id_ratio_based=trace_id_ratio_based,
                parent_based=parent_based,
            )
        ),
        state,
    )


def test_otel_sdk_disabled_does_not_load_optional_packages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_load() -> observability._OtelSdkLoadResult:
        raise AssertionError("SDK imports must remain lazy when disabled")

    monkeypatch.setattr(observability, "_load_optional_otel_sdk", unexpected_load)

    result = observability.configure_otel_sdk(OtelSdkSettings(enabled=False))

    assert result.availability.enabled is False
    assert result.availability.available is False
    assert result.availability.reason == "disabled"
    assert result.runtime is None
    assert result.error_code is None


@pytest.mark.parametrize(
    ("load_error", "expected"),
    [
        (
            OtelSdkErrorCode.SDK_UNAVAILABLE,
            OtelSdkErrorCode.SDK_UNAVAILABLE,
        ),
        (
            OtelSdkErrorCode.OTLP_HTTP_EXPORTER_UNAVAILABLE,
            OtelSdkErrorCode.OTLP_HTTP_EXPORTER_UNAVAILABLE,
        ),
    ],
)
def test_otel_sdk_missing_packages_degrade_to_typed_result(
    monkeypatch: pytest.MonkeyPatch,
    load_error: OtelSdkErrorCode,
    expected: OtelSdkErrorCode,
) -> None:
    monkeypatch.setattr(
        observability,
        "_load_optional_otel_sdk",
        lambda: observability._OtelSdkLoadResult(
            sdk=None,
            error_code=load_error,
        ),
    )

    result = observability.configure_otel_sdk(OtelSdkSettings(enabled=True))

    assert result.availability.enabled is True
    assert result.availability.available is False
    assert result.availability.reason == expected.value
    assert result.error_code is expected
    assert result.runtime is None


def test_optional_otel_sdk_loader_classifies_core_and_exporter_import_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_core(name: str) -> object:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(observability.importlib, "import_module", missing_core)
    core_result = observability._load_optional_otel_sdk()

    assert core_result.sdk is None
    assert core_result.error_code is OtelSdkErrorCode.SDK_UNAVAILABLE

    def missing_exporter(name: str) -> object:
        if name.startswith("opentelemetry.exporter.otlp"):
            raise ModuleNotFoundError(name)
        return object()

    monkeypatch.setattr(observability.importlib, "import_module", missing_exporter)
    exporter_result = observability._load_optional_otel_sdk()

    assert exporter_result.sdk is None
    assert exporter_result.error_code is OtelSdkErrorCode.OTLP_HTTP_EXPORTER_UNAVAILABLE


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"otlp_endpoint": "https://user:secret@collector.test"},
            OtelSdkErrorCode.INVALID_OTLP_ENDPOINT,
        ),
        (
            {"headers": {"authorization": "secret\r\ninjected"}},
            OtelSdkErrorCode.INVALID_OTLP_HEADERS,
        ),
        (
            {"service_name": "bad\nservice"},
            OtelSdkErrorCode.INVALID_RESOURCE_ATTRIBUTE,
        ),
        ({"sampler": "unknown"}, OtelSdkErrorCode.INVALID_SAMPLER),
        ({"sample_ratio": float("nan")}, OtelSdkErrorCode.INVALID_SAMPLE_RATIO),
        ({"export_timeout_ms": 0}, OtelSdkErrorCode.INVALID_EXPORT_TIMEOUT),
        (
            {"max_queue_size": 4, "max_export_batch_size": 5},
            OtelSdkErrorCode.INVALID_BATCH_CONFIGURATION,
        ),
        (
            {"metric_export_interval_ms": 0},
            OtelSdkErrorCode.INVALID_METRIC_INTERVAL,
        ),
        ({"shutdown_timeout_ms": 0}, OtelSdkErrorCode.INVALID_SHUTDOWN_TIMEOUT),
    ],
)
def test_invalid_otel_sdk_configuration_is_typed_and_checked_before_imports(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, object],
    expected: OtelSdkErrorCode,
) -> None:
    def unexpected_load() -> observability._OtelSdkLoadResult:
        raise AssertionError("invalid configuration must fail before SDK imports")

    monkeypatch.setattr(observability, "_load_optional_otel_sdk", unexpected_load)
    settings = OtelSdkSettings(enabled=True, **overrides)

    result = observability.configure_otel_sdk(settings)

    assert result.availability.available is False
    assert result.error_code is expected
    assert result.availability.reason == expected.value


def test_otel_sdk_configures_otlp_http_resource_sampler_and_processors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded, state = _make_fake_sdk()
    monkeypatch.setattr(observability, "_load_optional_otel_sdk", lambda: loaded)
    token = "collector-token-must-not-appear"
    settings = OtelSdkSettings(
        enabled=True,
        otlp_endpoint="https://collector.example.test/otel/",
        headers={"authorization": token},
        service_name="hemovet-api",
        service_version="2.4.1",
        environment="production",
        sampler="parent_based_trace_id_ratio",
        sample_ratio=0.25,
        export_timeout_ms=3_500,
        batch_schedule_delay_ms=750,
        max_queue_size=128,
        max_export_batch_size=32,
        metric_export_interval_ms=15_000,
        shutdown_timeout_ms=4_000,
    )

    result = observability.configure_otel_sdk(settings)

    assert result.availability.available is True
    assert result.error_code is None
    assert result.runtime is not None
    assert state["resource_attributes"] == {
        "service.name": "hemovet-api",
        "service.version": "2.4.1",
        "deployment.environment.name": "production",
    }
    span_exporter = state["span_exporter"]
    metric_exporter = state["metric_exporter"]
    assert span_exporter.kwargs == {
        "endpoint": "https://collector.example.test/otel/v1/traces",
        "headers": {"authorization": token},
        "timeout": 3.5,
    }
    assert metric_exporter.kwargs == {
        "endpoint": "https://collector.example.test/otel/v1/metrics",
        "headers": {"authorization": token},
        "timeout": 3.5,
    }
    span_processor = state["span_processor"]
    assert span_processor.exporter is span_exporter
    assert span_processor.kwargs == {
        "max_queue_size": 128,
        "schedule_delay_millis": 750,
        "max_export_batch_size": 32,
        "export_timeout_millis": 3_500,
    }
    metric_reader = state["metric_reader"]
    assert metric_reader.exporter is metric_exporter
    assert metric_reader.kwargs == {
        "export_interval_millis": 15_000,
        "export_timeout_millis": 3_500,
    }
    tracer_provider = state["tracer_provider"]
    meter_provider = state["meter_provider"]
    assert tracer_provider.kwargs["resource"] == state["resource_attributes"]
    assert tracer_provider.kwargs["sampler"] == ("parent", ("ratio", 0.25))
    assert tracer_provider.kwargs["shutdown_on_exit"] is False
    assert tracer_provider.processors == [span_processor]
    assert meter_provider.kwargs == {
        "resource": state["resource_attributes"],
        "metric_readers": [metric_reader],
        "shutdown_on_exit": False,
    }
    assert state["trace_api"].providers == [tracer_provider]
    assert state["metrics_api"].providers == [meter_provider]
    assert token not in repr(settings)
    assert token not in repr(result)

    flushed = result.runtime.force_flush()
    first_shutdown = result.runtime.shutdown()
    repeated_shutdown = result.runtime.shutdown()

    assert flushed.completed is True
    assert state["trace_flush_timeout"] == 4_000
    assert state["metric_flush_timeout"] == 4_000
    assert first_shutdown.completed is True
    assert first_shutdown.already_shutdown is False
    assert repeated_shutdown.completed is True
    assert repeated_shutdown.already_shutdown is True
    assert tracer_provider.shutdown_calls == 1
    assert meter_provider.shutdown_calls == 1
    assert state["metric_shutdown_timeout"] == 4_000


def test_otel_sdk_can_build_without_installing_global_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded, state = _make_fake_sdk()
    monkeypatch.setattr(observability, "_load_optional_otel_sdk", lambda: loaded)

    result = observability.configure_otel_sdk(
        OtelSdkSettings(enabled=True, install_global_providers=False)
    )

    assert result.availability.available is True
    assert state["trace_api"].providers == []
    assert state["metrics_api"].providers == []
    assert result.runtime is not None
    assert result.runtime.shutdown().completed is True


def test_otel_sdk_reports_global_provider_rejection_and_closes_new_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded, state = _make_fake_sdk()
    trace_api = state["trace_api"]
    trace_api.get_tracer_provider = lambda: None
    monkeypatch.setattr(observability, "_load_optional_otel_sdk", lambda: loaded)

    result = observability.configure_otel_sdk(OtelSdkSettings(enabled=True))

    assert result.availability.available is False
    assert result.error_code is OtelSdkErrorCode.GLOBAL_PROVIDER_INSTALL_FAILED
    assert result.runtime is None
    assert state["tracer_provider"].shutdown_calls == 1
    assert state["meter_provider"].shutdown_calls == 1


def test_otel_runtime_shutdown_contains_failures_and_remains_idempotent() -> None:
    class BrokenMeterProvider:
        def __init__(self) -> None:
            self.calls = 0

        def shutdown(self, *, timeout_millis: int) -> None:
            self.calls += 1
            raise RuntimeError("private exporter credential")

    class BrokenTracerProvider:
        def __init__(self) -> None:
            self.calls = 0

        def shutdown(self) -> bool:
            self.calls += 1
            return False

    meter = BrokenMeterProvider()
    tracer = BrokenTracerProvider()
    runtime = OtelSdkRuntime(
        tracer_provider=tracer,
        meter_provider=meter,
        shutdown_timeout_ms=500,
    )

    first = runtime.shutdown()
    repeated = runtime.shutdown()

    assert first.completed is False
    assert first.error_codes == (
        OtelLifecycleErrorCode.METRIC_SHUTDOWN_FAILED,
        OtelLifecycleErrorCode.TRACE_SHUTDOWN_FAILED,
    )
    assert "private exporter credential" not in repr(first)
    assert repeated.completed is False
    assert repeated.already_shutdown is True
    assert repeated.error_codes == first.error_codes
    assert meter.calls == 1
    assert tracer.calls == 1
