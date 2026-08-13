from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from fastapi import FastAPI
import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-32-characters")
os.environ.setdefault("HEMOVET_ENABLE_LOCAL_ML", "0")

from app import application  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.modules.llm_chat.infrastructure.observability import (  # noqa: E402
    OtelLifecycleResult,
    OtelSdkErrorCode,
    OtelSdkSetupResult,
    TelemetryAvailability,
)

_SECRET_HEADER = "Bearer super-private-observability-token"


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "test",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "SECRET_KEY": "test-secret-key-with-at-least-32-characters",
        "OTEL_ENABLED": False,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


class _FakeSdkRuntime:
    def __init__(self, events: list[str] | None = None) -> None:
        self.tracer_provider = object()
        self.meter_provider = object()
        self.shutdown_calls = 0
        self.events = events

    def shutdown(self) -> OtelLifecycleResult:
        self.shutdown_calls += 1
        if self.events is not None:
            self.events.append("sdk.shutdown")
        return OtelLifecycleResult(completed=True)


def _ready_setup(runtime: _FakeSdkRuntime) -> OtelSdkSetupResult:
    return OtelSdkSetupResult(
        availability=TelemetryAvailability(True, True, "ready"),
        runtime=runtime,  # type: ignore[arg-type]
    )


def test_settings_load_typed_otel_values_from_dotenv_and_mask_headers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keys = (
        "OTEL_ENABLED",
        "OTEL_SERVICE_NAME",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_TRACES_SAMPLER",
        "OTEL_TRACES_SAMPLER_ARG",
        "OTEL_FASTAPI_INSTRUMENTATION_ENABLED",
    )
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "DATABASE_URL=sqlite+pysqlite:///:memory:\n"
        "SECRET_KEY=test-secret-key-with-at-least-32-characters\n"
        "APP_ENV=test\n"
        "OTEL_ENABLED=true\n"
        "OTEL_SERVICE_NAME=hemovet-test\n"
        "OTEL_EXPORTER_OTLP_ENDPOINT=https://collector.test/otel\n"
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://traces.test/v1/traces\n"
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=https://metrics.test/v1/metrics\n"
        f"OTEL_EXPORTER_OTLP_HEADERS=authorization={_SECRET_HEADER}\n"
        "OTEL_TRACES_SAMPLER=traceidratio\n"
        "OTEL_TRACES_SAMPLER_ARG=0.2\n"
        "OTEL_FASTAPI_INSTRUMENTATION_ENABLED=false\n",
        encoding="utf-8",
    )

    runtime_settings = Settings(_env_file=dotenv)

    assert runtime_settings.OTEL_ENABLED is True
    assert runtime_settings.OTEL_SERVICE_NAME == "hemovet-test"
    assert runtime_settings.OTEL_EXPORTER_OTLP_ENDPOINT == (
        "https://collector.test/otel"
    )
    assert runtime_settings.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT == (
        "https://traces.test/v1/traces"
    )
    assert runtime_settings.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT == (
        "https://metrics.test/v1/metrics"
    )
    assert runtime_settings.OTEL_EXPORTER_OTLP_HEADERS is not None
    assert (
        runtime_settings.OTEL_EXPORTER_OTLP_HEADERS.get_secret_value()
        == f"authorization={_SECRET_HEADER}"
    )
    assert runtime_settings.OTEL_TRACES_SAMPLER == "traceidratio"
    assert runtime_settings.OTEL_TRACES_SAMPLER_ARG == 0.2
    assert runtime_settings.OTEL_FASTAPI_INSTRUMENTATION_ENABLED is False
    assert _SECRET_HEADER not in repr(runtime_settings)


def test_sdk_settings_decode_standard_headers_and_map_sampler_without_leaking() -> None:
    runtime_settings = _settings(
        OTEL_ENABLED=True,
        OTEL_SERVICE_NAME="hemovet-api",
        HEMOVET_API_VERSION="9.2.0",
        OTEL_EXPORTER_OTLP_ENDPOINT="https://collector.test/root",
        OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://traces.test/v1/traces",
        OTEL_EXPORTER_OTLP_METRICS_ENDPOINT="https://metrics.test/v1/metrics",
        OTEL_EXPORTER_OTLP_HEADERS=(
            "authorization=Bearer%20super-private-observability-token,"
            "x-api-key=abc%3D123"
        ),
        OTEL_TRACES_SAMPLER="parentbased_traceidratio",
        OTEL_TRACES_SAMPLER_ARG=0.15,
    )

    sdk_settings = application._build_otel_sdk_settings(runtime_settings)

    assert sdk_settings.enabled is True
    assert sdk_settings.service_name == "hemovet-api"
    assert sdk_settings.service_version == "9.2.0"
    assert sdk_settings.environment == "test"
    assert sdk_settings.otlp_endpoint == "https://collector.test/root"
    assert sdk_settings.traces_endpoint == "https://traces.test/v1/traces"
    assert sdk_settings.metrics_endpoint == "https://metrics.test/v1/metrics"
    assert sdk_settings.sampler == "parent_based_trace_id_ratio"
    assert sdk_settings.sample_ratio == 0.15
    assert sdk_settings.headers == {
        "authorization": _SECRET_HEADER,
        "x-api-key": "abc=123",
    }
    assert _SECRET_HEADER not in repr(sdk_settings)


def test_invalid_secret_headers_degrade_without_startup_failure_or_leak(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def unexpected_configure(settings: object) -> OtelSdkSetupResult:
        raise AssertionError("invalid headers must fail before SDK configuration")

    monkeypatch.setattr(application, "configure_otel_sdk", unexpected_configure)
    runtime_settings = _settings(
        OTEL_ENABLED=True,
        OTEL_EXPORTER_OTLP_HEADERS="authorization-without-value-separator",
    )
    fastapi_app = FastAPI()

    with caplog.at_level(logging.INFO, logger="hemovet"):
        lifecycle = application._start_application_observability(
            fastapi_app,
            runtime_settings,
        )

    assert lifecycle.sdk_setup.error_code is OtelSdkErrorCode.INVALID_OTLP_HEADERS
    assert fastapi_app.state.otel == {
        "enabled": True,
        "available": False,
        "reason": OtelSdkErrorCode.INVALID_OTLP_HEADERS.value,
        "fastapi_instrumented": False,
        "fastapi_reason": "sdk_unavailable",
    }
    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "authorization-without-value-separator" not in logs


def test_missing_sdk_is_typed_and_fastapi_instrumentation_is_not_imported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unavailable = OtelSdkSetupResult(
        availability=TelemetryAvailability(
            True,
            False,
            OtelSdkErrorCode.SDK_UNAVAILABLE.value,
        ),
        error_code=OtelSdkErrorCode.SDK_UNAVAILABLE,
    )
    monkeypatch.setattr(application, "configure_otel_sdk", lambda settings: unavailable)

    def unexpected_instrumentor_load() -> object:
        raise AssertionError("FastAPI instrumentation requires a ready SDK")

    monkeypatch.setattr(
        application,
        "_load_fastapi_instrumentor",
        unexpected_instrumentor_load,
    )
    fastapi_app = FastAPI()

    lifecycle = application._start_application_observability(
        fastapi_app,
        _settings(OTEL_ENABLED=True),
    )

    assert lifecycle.sdk_setup.error_code is OtelSdkErrorCode.SDK_UNAVAILABLE
    assert lifecycle.fastapi_instrumented is False
    assert lifecycle.fastapi_reason == "sdk_unavailable"


def test_fastapi_instrumentation_disables_header_capture_redacts_pii_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    runtime = _FakeSdkRuntime(events)
    captured: dict[str, object] = {}

    class FakeInstrumentor:
        @staticmethod
        def instrument_app(fastapi_app: FastAPI, **kwargs: object) -> None:
            events.append("fastapi.instrument")
            captured["app"] = fastapi_app
            captured.update(kwargs)

        @staticmethod
        def uninstrument_app(fastapi_app: FastAPI) -> None:
            events.append("fastapi.uninstrument")
            captured["uninstrumented_app"] = fastapi_app

    monkeypatch.setattr(
        application,
        "configure_otel_sdk",
        lambda settings: _ready_setup(runtime),
    )
    monkeypatch.setattr(
        application,
        "_load_fastapi_instrumentor",
        lambda: FakeInstrumentor,
    )
    fastapi_app = FastAPI()

    lifecycle = application._start_application_observability(
        fastapi_app,
        _settings(OTEL_ENABLED=True),
    )

    assert lifecycle.fastapi_instrumented is True
    assert lifecycle.fastapi_reason == "ready"
    assert captured["app"] is fastapi_app
    assert captured["tracer_provider"] is runtime.tracer_provider
    assert captured["meter_provider"] is runtime.meter_provider
    assert captured["http_capture_headers_server_request"] == []
    assert captured["http_capture_headers_server_response"] == []
    assert captured["http_capture_headers_sanitize_fields"] == [".*"]
    assert captured["exclude_spans"] == ["receive", "send"]

    class FakeSpan:
        def __init__(self) -> None:
            self.attributes = {
                "url.path": "/api/v1/pets/private-patient-id",
                "client.address": "192.0.2.42",
            }

        @staticmethod
        def is_recording() -> bool:
            return True

        def set_attribute(self, key: str, value: object) -> None:
            self.attributes[key] = value

    span = FakeSpan()
    hook = captured["server_request_hook"]
    hook(
        span,
        {
            "headers": [(b"authorization", b"private-token")],
            "body": b"private clinical prompt",
        },
    )

    assert set(span.attributes.values()) == {"[REDACTED]"}
    serialized_attributes = repr(span.attributes)
    assert "private-patient-id" not in serialized_attributes
    assert "192.0.2.42" not in serialized_attributes
    assert "private-token" not in serialized_attributes
    assert "private clinical prompt" not in serialized_attributes

    asyncio.run(application._stop_application_observability(fastapi_app, lifecycle))

    assert events == [
        "fastapi.instrument",
        "fastapi.uninstrument",
        "sdk.shutdown",
    ]
    assert runtime.shutdown_calls == 1
    assert fastapi_app.state.otel["shutdown_status"] == "completed"
    assert _SECRET_HEADER not in repr(fastapi_app.state.otel)


def test_application_lifespan_initializes_and_closes_disabled_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(application, "settings", _settings(OTEL_ENABLED=False))
    fastapi_app = FastAPI()

    async def run() -> None:
        async with application._lifespan(fastapi_app):
            assert fastapi_app.state.otel["enabled"] is False
            assert fastapi_app.state.otel["reason"] == "disabled"
        assert fastapi_app.state.otel["shutdown_status"] == "not_started"

    asyncio.run(run())


def test_requirements_pin_compatible_opentelemetry_packages() -> None:
    requirements = (Path(__file__).resolve().parents[2] / "requirements.txt").read_text(
        encoding="utf-8"
    )

    assert "opentelemetry-api==1.44.0" in requirements
    assert "opentelemetry-sdk==1.44.0" in requirements
    assert "opentelemetry-exporter-otlp-proto-http==1.44.0" in requirements
    assert "opentelemetry-instrumentation-fastapi==0.65b0" in requirements
