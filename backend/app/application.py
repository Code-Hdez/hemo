"""
Backend FastAPI para HemoVet

Endpoints:
  Auth (publicos):
    POST /api/v1/auth/register  -- Registro de nuevo usuario
    POST /api/v1/auth/login     -- Login con email/contrasena -> JWT
    GET  /api/v1/auth/me        -- Datos del usuario autenticado

  Mascotas (protegidos):
    GET    /api/v1/pets            -- Lista de mascotas del usuario
    POST   /api/v1/pets            -- Registrar nueva mascota
    GET    /api/v1/pets/{pet_id}   -- Obtener mascota por ID
    PUT    /api/v1/pets/{pet_id}   -- Actualizar mascota
    DELETE /api/v1/pets/{pet_id}   -- Eliminar mascota

  Hemogramas:
    POST /api/v1/analyze        -- Sube PDF/CSV/Excel/imagen, retorna analisis
    POST /api/v1/extract        -- Extrae valores CBC sin inferencia ni persistencia
    GET  /api/v1/history        -- Historial (filtrado por usuario si autenticado)
    GET  /api/v1/analysis/{id}  -- Analisis individual por ID
    GET  /api/v1/epidemiology/points -- Datos agregados para mapa
    POST /api/v1/chat           -- Asistente de preguntas clinicas
    GET  /health             -- Estado del sistema
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import importlib
import json
import logging
import random
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.v1.api import api_router
from app.core.availability import (
    ChatAvailability,
    ProviderAvailability,
    ReadinessSnapshot,
    liveness_payload,
)
from app.modules.auth import compat as auth
from app.modules.dashboard import service as dashboard_service
from app.db import queries as db
from app.modules.hematology import extraction_service, formatter
from app.modules.hematology import service as hematology_service
from app.modules.hematology.anonymizer import censor
from app.modules.hematology.extraction_types import ExtractionError
from app.modules.hematology.schemas import (
    AnalysisResult,
    Finding,
    LabValue,
)
from app.modules.gemini_extraction.client import inspect_gemini_runtime
from app.modules.ml.input_contract import InputContractError, validate_cbc_contract
from app.modules.ml.schemas import (
    BatchPredictItemOut,
    BatchPredictRequest,
    BatchPredictResponse,
)
from app.modules.maps.geocoder import resolve_location
from app.modules.population_surveillance.service import (
    sync_events_for_analysis,
)
from app.db.session import engine as database_engine
from app.modules.llm_chat.application.availability import (
    unavailable_chat_health,
)
from app.modules.llm_chat.composition import build_chat_container
from app.modules.llm_chat.domain.provider_contract import (
    ProviderFailureCode,
    is_retryable_provider_failure,
    normalize_provider_failure_code,
)
from app.modules.llm_chat.infrastructure.observability import (
    OtelSdkErrorCode,
    OtelSdkSettings,
    OtelSdkSetupResult,
    TelemetryAvailability,
    configure_otel_sdk,
)
from app.modules.llm_chat.snapshots import (
    build_case_snapshot,
    rebuild_case_snapshot_from_analysis,
)
from app.modules.pets.service import photo_store
from app.core.config import Settings, settings

logger = logging.getLogger("hemovet")

# ---------------------------------------------------------------------------
# Configuracion de la aplicacion
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = settings.HEMOVET_PROJECT_ROOT.resolve()
_API_VERSION = settings.HEMOVET_API_VERSION
_SCHEMA_VERSION = settings.HEMOVET_SCHEMA_VERSION
_BUILD_REVISION = settings.HEMOVET_BUILD_REVISION
_CHAT_POLICY_REVISION = "clinical-claims-v4"
_LOCAL_ML_ENABLED = settings.HEMOVET_ENABLE_LOCAL_ML

_OTEL_SAMPLERS = {
    "always_on": "always_on",
    "always_off": "always_off",
    "traceidratio": "trace_id_ratio",
    "parentbased_traceidratio": "parent_based_trace_id_ratio",
}
_REDACTED_HTTP_ATTRIBUTE = "[REDACTED]"
_SENSITIVE_HTTP_SPAN_ATTRIBUTES = (
    "client.address",
    "http.client_ip",
    "http.target",
    "http.url",
    "net.peer.ip",
    "network.peer.address",
    "url.full",
    "url.path",
    "url.query",
    "user_agent.original",
)


@dataclass(slots=True)
class _ApplicationObservability:
    sdk_setup: OtelSdkSetupResult = field(repr=False)
    fastapi_instrumentor: Any | None = field(default=None, repr=False)
    fastapi_instrumented: bool = False
    fastapi_reason: str = "not_started"

    def public_status(self) -> dict[str, bool | str]:
        availability = self.sdk_setup.availability
        return {
            "enabled": availability.enabled,
            "available": availability.available,
            "reason": availability.reason,
            "fastapi_instrumented": self.fastapi_instrumented,
            "fastapi_reason": self.fastapi_reason,
        }


def _decode_otel_headers(runtime_settings: Settings) -> dict[str, str]:
    secret = runtime_settings.OTEL_EXPORTER_OTLP_HEADERS
    if secret is None:
        return {}
    raw_headers = secret.get_secret_value().strip()
    if not raw_headers:
        return {}

    decoded: dict[str, str] = {}
    normalized_names: set[str] = set()
    try:
        items = raw_headers.split(",")
        for item in items:
            encoded_name, separator, encoded_value = item.strip().partition("=")
            if not separator:
                raise ValueError("invalid_otel_exporter_headers")
            name = unquote(encoded_name.strip(), errors="strict")
            value = unquote(encoded_value.strip(), errors="strict")
            normalized_name = name.casefold()
            if not name or not value or normalized_name in normalized_names:
                raise ValueError("invalid_otel_exporter_headers")
            normalized_names.add(normalized_name)
            decoded[name] = value
    except (UnicodeError, ValueError) as exc:
        raise ValueError("invalid_otel_exporter_headers") from exc
    return decoded


def _build_otel_sdk_settings(runtime_settings: Settings) -> OtelSdkSettings:
    headers = (
        _decode_otel_headers(runtime_settings) if runtime_settings.OTEL_ENABLED else {}
    )
    return OtelSdkSettings(
        enabled=runtime_settings.OTEL_ENABLED,
        otlp_endpoint=runtime_settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        traces_endpoint=runtime_settings.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT,
        metrics_endpoint=runtime_settings.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT,
        headers=headers,
        service_name=runtime_settings.OTEL_SERVICE_NAME,
        service_version=runtime_settings.HEMOVET_API_VERSION,
        environment=runtime_settings.APP_ENV,
        sampler=_OTEL_SAMPLERS[runtime_settings.OTEL_TRACES_SAMPLER],
        sample_ratio=runtime_settings.OTEL_TRACES_SAMPLER_ARG,
    )


def _otel_setup_failure(error_code: OtelSdkErrorCode) -> OtelSdkSetupResult:
    return OtelSdkSetupResult(
        availability=TelemetryAvailability(True, False, error_code.value),
        error_code=error_code,
    )


def _load_fastapi_instrumentor() -> Any | None:
    try:
        module = importlib.import_module("opentelemetry.instrumentation.fastapi")
        return getattr(module, "FastAPIInstrumentor")
    except Exception:
        return None


def _redact_fastapi_request_span(span: Any, _scope: object) -> None:
    if span is None:
        return
    try:
        is_recording = getattr(span, "is_recording", None)
        if callable(is_recording) and not is_recording():
            return
        for attribute in _SENSITIVE_HTTP_SPAN_ATTRIBUTES:
            span.set_attribute(attribute, _REDACTED_HTTP_ATTRIBUTE)
    except Exception:
        return


def _start_application_observability(
    fastapi_app: FastAPI,
    runtime_settings: Settings,
) -> _ApplicationObservability:
    try:
        sdk_settings = _build_otel_sdk_settings(runtime_settings)
        sdk_setup = configure_otel_sdk(sdk_settings)
    except ValueError:
        sdk_setup = _otel_setup_failure(OtelSdkErrorCode.INVALID_OTLP_HEADERS)
    except Exception:
        sdk_setup = _otel_setup_failure(OtelSdkErrorCode.SDK_INITIALIZATION_FAILED)

    lifecycle = _ApplicationObservability(sdk_setup=sdk_setup)
    runtime = sdk_setup.runtime
    if not sdk_setup.availability.enabled:
        lifecycle.fastapi_reason = "disabled"
    elif not sdk_setup.availability.available or runtime is None:
        lifecycle.fastapi_reason = "sdk_unavailable"
    elif not runtime_settings.OTEL_FASTAPI_INSTRUMENTATION_ENABLED:
        lifecycle.fastapi_reason = "disabled"
    else:
        instrumentor = _load_fastapi_instrumentor()
        if instrumentor is None:
            lifecycle.fastapi_reason = "fastapi_instrumentation_unavailable"
        else:
            lifecycle.fastapi_instrumentor = instrumentor
            try:
                instrumentor.instrument_app(
                    fastapi_app,
                    tracer_provider=runtime.tracer_provider,
                    meter_provider=runtime.meter_provider,
                    server_request_hook=_redact_fastapi_request_span,
                    http_capture_headers_server_request=[],
                    http_capture_headers_server_response=[],
                    http_capture_headers_sanitize_fields=[".*"],
                    exclude_spans=["receive", "send"],
                )
                # Instrumentation 0.65b0 replaces the stack builder. Lifespan is
                # entered through the already-built stack, so rebuild it once for
                # subsequent HTTP requests.
                fastapi_app.middleware_stack = fastapi_app.build_middleware_stack()
                lifecycle.fastapi_instrumented = True
                lifecycle.fastapi_reason = "ready"
            except Exception as exc:
                lifecycle.fastapi_reason = "fastapi_instrumentation_failed"
                try:
                    instrumentor.uninstrument_app(fastapi_app)
                except Exception:
                    pass
                logger.warning(
                    "OpenTelemetry FastAPI instrumentation failed (error_type=%s)",
                    type(exc).__name__,
                )

    fastapi_app.state.otel = lifecycle.public_status()
    availability = sdk_setup.availability
    log_method = (
        logger.warning
        if availability.enabled and not availability.available
        else logger.info
    )
    log_method(
        "OpenTelemetry lifecycle (sdk_status=%s, fastapi_status=%s)",
        availability.reason,
        lifecycle.fastapi_reason,
    )
    return lifecycle


async def _stop_application_observability(
    fastapi_app: FastAPI,
    lifecycle: _ApplicationObservability,
) -> None:
    if lifecycle.fastapi_instrumented and lifecycle.fastapi_instrumentor is not None:
        try:
            lifecycle.fastapi_instrumentor.uninstrument_app(fastapi_app)
        except Exception as exc:
            logger.warning(
                "OpenTelemetry FastAPI shutdown failed (error_type=%s)",
                type(exc).__name__,
            )
        lifecycle.fastapi_instrumented = False

    shutdown_status = "not_started"
    runtime = lifecycle.sdk_setup.runtime
    if runtime is not None:
        executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="hemovet-otel-shutdown",
        )
        try:
            shutdown_result = await asyncio.get_running_loop().run_in_executor(
                executor,
                runtime.shutdown,
            )
            shutdown_status = "completed" if shutdown_result.completed else "failed"
            if not shutdown_result.completed:
                error_codes = ",".join(
                    code.value for code in shutdown_result.error_codes
                )
                logger.warning(
                    "OpenTelemetry shutdown failed (error_codes=%s)",
                    error_codes,
                )
        except Exception as exc:
            shutdown_status = "failed"
            logger.warning(
                "OpenTelemetry SDK shutdown failed (error_type=%s)",
                type(exc).__name__,
            )
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

    status = lifecycle.public_status()
    status["shutdown_status"] = shutdown_status
    fastapi_app.state.otel = status


@asynccontextmanager
async def _lifespan(fastapi_app: FastAPI):
    observability = _start_application_observability(fastapi_app, settings)
    container = None
    try:
        if settings.APP_ENV != "test":
            _startup()
            try:
                # The conversational runtime is useful even when RAG is disabled or
                # temporarily degraded (identity, social and redirection routes).
                container = await build_chat_container(settings)
                fastapi_app.state.llm_chat = container
            except Exception:
                fastapi_app.state.llm_chat = None
                logger.exception("No se pudo inicializar el módulo conversacional")
        yield
    finally:
        try:
            if container is not None:
                await container.close()
        finally:
            await _stop_application_observability(fastapi_app, observability)


app = FastAPI(
    title="VetCDSS API",
    version=_API_VERSION,
    description="API para interpretacion hematologica canina",
    lifespan=_lifespan,
)


def _parse_cors_origins(raw_value: str | None) -> list[str]:
    origins = [item.strip() for item in str(raw_value or "").split(",") if item.strip()]
    return origins or ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials="*" not in settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount(
    "/api/v1/media/pets",
    StaticFiles(directory=str(photo_store.directory), check_dir=True),
    name="pet-media",
)
app.include_router(api_router)

# ---------------------------------------------------------------------------
# Recursos del modelo
# ---------------------------------------------------------------------------

_resources: Any | None = None
_predictor_runtime: Any | None = None


def _load_predictor_runtime() -> Any:
    global _predictor_runtime
    if _predictor_runtime is None:
        from app.modules.ml import predictor as _predictor

        _predictor_runtime = _predictor
    return _predictor_runtime


def _log_analyze_event(
    *,
    stage: str,
    status: str,
    prediction_id: str,
    **extra,
) -> None:
    """Registra eventos estructurados del pipeline de analisis."""
    payload = {
        "event": "analyze_pipeline",
        "stage": stage,
        "status": status,
        "prediction_id": prediction_id,
        # Alias legacy para consumidores existentes de logs v2.
        "trace_id": prediction_id,
        "timestamp": datetime.now().isoformat(),
    }
    payload.update(extra)
    logger.info(
        "analyze.pipeline %s", json.dumps(payload, ensure_ascii=False, sort_keys=True)
    )


hematology_service.configure_runtime(
    resources_getter=lambda: _resources,
    predictor_loader=_load_predictor_runtime,
    local_ml_enabled=_LOCAL_ML_ENABLED,
    event_logger=_log_analyze_event,
)


def _startup() -> None:
    """Carga el modelo, la base de datos y el cache de analytics al arrancar."""
    global _resources

    logger.info(
        "Runtime HemoVet (build_revision=%s, chat_policy_revision=%s)",
        _BUILD_REVISION,
        _CHAT_POLICY_REVISION,
    )

    if _LOCAL_ML_ENABLED:
        try:
            predictor_runtime = _load_predictor_runtime()
            _resources = predictor_runtime.load_resources(_PROJECT_ROOT)
            manifest = _resources.artifact_manifest or {}
            logger.info(
                "Modelo cargado correctamente (version api=%s, manifest=%s, generado=%s)",
                _API_VERSION,
                manifest.get("version", "desconocida"),
                manifest.get("generated_at", "desconocida"),
            )
        except Exception as exc:
            logger.error("No se pudo cargar el modelo local: %s", exc)
            _resources = None
    else:
        _resources = None
        logger.info(
            "HEMOVET_ENABLE_LOCAL_ML=0; se omite carga de dependencias y artefactos ML locales."
        )

    hematology_service.refresh_resources(_resources)

    db.seed_breeds()

    # Cargar metricas del modelo desde archivos de outputs/
    dashboard_service.refresh(_PROJECT_ROOT)
    analytics_cache = dashboard_service.analytics_cache()
    logger.info(
        "analytics.cache.loaded entradas=%d cv_labels=%d",
        len(analytics_cache),
        len(analytics_cache.get("cv_results", [])),
    )
    if db.count_analyses() == 0 and settings.HEMOVET_SEED_DEMO_HISTORY:
        _seed_history()
        logger.info(
            "Historial de demostracion insertado (%d registros)", db.count_analyses()
        )


# ---------------------------------------------------------------------------
# Datos opcionales para seed de demostracion del historial.
# ---------------------------------------------------------------------------

DEMO_LOCATIONS = [
    ("Santo Domingo", 18.4861, -69.9312),
    ("Santiago", 19.4517, -70.6970),
    ("La Romana", 18.4272, -68.9728),
    ("San Pedro de Macorís", 18.4539, -69.3086),
    ("Puerto Plata", 19.7934, -70.6884),
    ("Higüey", 18.6152, -68.7080),
    ("San Cristóbal", 18.4167, -70.1000),
    ("La Vega", 19.2220, -70.5296),
    ("Moca", 19.3948, -70.5237),
    ("Bonao", 18.9400, -70.4089),
]


def _generate_demo_analysis(filename: str, file_size: int) -> AnalysisResult:
    """Genera un resultado de demostracion realista para entornos sin datos."""
    analysis_id = str(uuid.uuid4())[:8]
    loc = random.choice(DEMO_LOCATIONS)
    confidence = round(random.uniform(0.78, 0.96), 2)

    lab_values = [
        LabValue(
            name="WBC",
            value="17.8",
            unit="x10³/µL",
            status="high",
            ref_min=5.5,
            ref_max=16.9,
        ),
        LabValue(
            name="RBC",
            value="6.1",
            unit="x10⁶/µL",
            status="normal",
            ref_min=5.5,
            ref_max=8.5,
        ),
        LabValue(
            name="HGB",
            value="13.9",
            unit="g/dL",
            status="normal",
            ref_min=12.0,
            ref_max=18.0,
        ),
        LabValue(
            name="HCT",
            value="39.8",
            unit="%",
            status="normal",
            ref_min=37.0,
            ref_max=55.0,
        ),
        LabValue(
            name="PLT",
            value="92",
            unit="x10³/µL",
            status="low",
            ref_min=175.0,
            ref_max=500.0,
        ),
        LabValue(
            name="NEU",
            value="13.2",
            unit="x10³/µL",
            status="high",
            ref_min=2.0,
            ref_max=12.0,
        ),
        LabValue(
            name="LYM",
            value="2.1",
            unit="x10³/µL",
            status="normal",
            ref_min=1.0,
            ref_max=4.8,
        ),
        LabValue(
            name="MONO",
            value="0.8",
            unit="x10³/µL",
            status="normal",
            ref_min=0.3,
            ref_max=2.0,
        ),
        LabValue(
            name="EOS",
            value="0.4",
            unit="x10³/µL",
            status="normal",
            ref_min=0.1,
            ref_max=1.4,
        ),
        LabValue(
            name="TP",
            value="6.6",
            unit="g/dL",
            status="normal",
            ref_min=5.2,
            ref_max=8.2,
        ),
    ]

    for lv in lab_values:
        base = float(lv.value)
        variation = base * random.uniform(-0.15, 0.15)
        new_val = round(base + variation, 1)
        lv.value = str(new_val)
        if new_val < lv.ref_min:
            lv.status = "low"
        elif new_val > lv.ref_max:
            lv.status = "high"
        else:
            lv.status = "normal"

    findings = [
        Finding(
            label="PLT bajo",
            detail="Revisar agregación plaquetaria, repetir muestra si hay dudas.",
            severity="danger",
        ),
        Finding(
            label="NEU alto",
            detail="Compatible con inflamación/estrés; evaluar desviación a la izquierda.",
            severity="warn",
        ),
        Finding(
            label="HCT límite",
            detail="Monitorizar hidratación; correlacionar con mucosas/TP.",
            severity="info",
        ),
    ]

    diagnoses = [
        "Probable trombocitopenia leve a moderada (confirmar con frotis y recuento manual).",
        "Leucograma compatible con respuesta inflamatoria (correlacionar con signos clínicos).",
        "Considerar estrés / uso de corticosteroides si hay neutrofilia con linfopenia.",
    ]

    return AnalysisResult(
        id=analysis_id,
        filename=filename,
        file_size=file_size,
        created_at=datetime.now().isoformat(),
        confidence=confidence,
        quality_score=round(random.uniform(0.70, 0.98), 2),
        species="Canino",
        summary="Resumen automático basado en el hemograma cargado. Requiere validación clínica.",
        diagnoses=diagnoses,
        findings=findings,
        lab_values=lab_values,
        location=loc[0],
        latitude=loc[1] + random.uniform(-0.05, 0.05),
        longitude=loc[2] + random.uniform(-0.05, 0.05),
    )


def _seed_history() -> None:
    """Crea registros historicos de demostracion y los persiste censurados."""
    filenames = [
        "hemograma_luna_2025.csv",
        "reporte_max_lab.pdf",
        "analisis_rocky_idexx.xlsx",
        "hemograma_bella_032025.csv",
        "reporte_thor_clinica.pdf",
        "hemograma_canela_feb.csv",
        "lab_results_rex.pdf",
        "hemograma_simba_ene.csv",
    ]
    for i, fn in enumerate(filenames):
        result = _generate_demo_analysis(fn, random.randint(15000, 250000))
        days_ago = (len(filenames) - i) * random.randint(3, 12)
        result.created_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
        stored = censor(result.model_dump())
        stored["_case_snapshot"] = rebuild_case_snapshot_from_analysis(stored)
        db.save_analysis(stored)


# ---------------------------------------------------------------------------
# Endpoints de salud
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    manifest = (_resources.artifact_manifest if _resources is not None else None) or {}
    gates = dashboard_service.load_gate_statuses(_PROJECT_ROOT)
    payload = liveness_payload()
    payload.update(
        {
            "local_ml_enabled": _LOCAL_ML_ENABLED,
            "model_ready": _resources is not None and _resources.ready,
            "version": _API_VERSION,
            "schema_version": _SCHEMA_VERSION,
            "artifact_manifest_version": manifest.get("version"),
            "artifact_manifest_generated_at": manifest.get("generated_at"),
            "artifact_manifest_runtime_count": len(
                manifest.get("runtime_artifacts", [])
            ),
            "gates": gates,
        }
    )
    return payload


@app.get("/health/llm")
async def health_llm() -> dict[str, Any]:
    """Estado agregado y sanitizado del runtime generativo y vectorial."""
    container = getattr(app.state, "llm_chat", None)
    if container is None:
        return unavailable_chat_health(
            rag_required=settings.RAG_ENABLED,
            provider_name=settings.CHAT_LLM_PROVIDER,
            model=(
                settings.OLLAMA_MODEL
                if settings.CHAT_LLM_PROVIDER == "ollama"
                else settings.OPENAI_COMPATIBLE_MODEL
            ),
            embedding_model=settings.RAG_EMBEDDING_MODEL,
        )
    return await container.health()


@app.get("/health/gemini")
def health_gemini() -> dict[str, Any]:
    """Diagnostico de configuracion Gemini sin exponer secretos."""
    return inspect_gemini_runtime()


@app.get("/health/operational")
async def health_operational() -> dict[str, Any]:
    """Readiness of the core, with chat reported as an optional capability."""
    gate_statuses = dashboard_service.load_gate_statuses(_PROJECT_ROOT)
    model_ready = _resources is not None and _resources.ready
    llm_status = await health_llm()
    database_ready = await asyncio.to_thread(_database_is_ready)

    blocking_codes: list[str] = []
    advisory_codes: list[str] = []
    for gate_name, gate_status in gate_statuses.items():
        if gate_status == "fail":
            blocking_codes.append(f"GATE_{gate_name.upper()}_FAIL")
        elif gate_status == "warn":
            advisory_codes.append(f"GATE_{gate_name.upper()}_WARN")
        elif gate_status == "unknown":
            advisory_codes.append(f"GATE_{gate_name.upper()}_UNKNOWN")

    chat = _chat_availability_from_health(llm_status)
    readiness = ReadinessSnapshot(
        database_ready=database_ready,
        local_model_required=_LOCAL_ML_ENABLED,
        local_model_ready=model_ready,
        chat=chat,
        blocking_codes=tuple(blocking_codes),
        advisory_codes=tuple(advisory_codes),
    )
    payload = readiness.to_public_dict()
    payload.update(
        {
            "api_version": _API_VERSION,
            "schema_version": _SCHEMA_VERSION,
            "build_revision": _BUILD_REVISION,
            "chat_policy_revision": _CHAT_POLICY_REVISION,
            "local_ml_enabled": _LOCAL_ML_ENABLED,
            "chunk_count": int(llm_status.get("chunk_count") or 0),
            "gates": gate_statuses,
        }
    )
    return payload


def _database_is_ready() -> bool:
    try:
        with database_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(
            "database readiness probe failed (error_type=%s)",
            type(exc).__name__,
        )
        return False


def _chat_availability_from_health(
    llm_status: dict[str, Any],
) -> ChatAvailability:
    runtime = llm_status.get("runtime")
    runtime_payload = runtime if isinstance(runtime, dict) else {}
    provider_payload = llm_status.get("provider")
    provider_data = provider_payload if isinstance(provider_payload, dict) else {}
    provider_name = str(
        provider_data.get("provider")
        or runtime_payload.get("provider")
        or settings.CHAT_LLM_PROVIDER
    )
    provider_ready = bool(
        provider_data.get(
            "ready",
            llm_status.get("provider_ready", llm_status.get("llm_ready")),
        )
    )
    provider_code = str(
        provider_data.get("code")
        or llm_status.get("runtime_identity_error")
        or ""
    ) or None
    if not provider_ready and provider_code is None:
        provider_code = ProviderFailureCode.LLM_PROVIDER_UNAVAILABLE.value
    normalized_provider_code = (
        normalize_provider_failure_code(provider_code)
        if provider_code is not None
        else None
    )
    if normalized_provider_code is not None:
        provider_code = normalized_provider_code.value
    identity_value = provider_data.get(
        "identity_verified",
        runtime_payload.get("identity_verified"),
    )
    identity_verified = (
        bool(identity_value) if identity_value is not None else None
    )
    provider = ProviderAvailability(
        provider=provider_name,
        model=str(
            provider_data.get("model") or runtime_payload.get("model") or ""
        )
        or None,
        ready=provider_ready,
        code=provider_code,
        retryable=bool(
            provider_data.get(
                "retryable",
                is_retryable_provider_failure(provider_code or ""),
            )
        ),
        identity_verified=identity_verified,
    )
    return ChatAvailability(
        provider=provider,
        module_ready=bool(llm_status.get("module_ready", False)),
        rag_required=bool(llm_status.get("rag_required", settings.RAG_ENABLED)),
        chroma_ready=bool(llm_status.get("chroma_ready")),
        collection_ready=bool(
            llm_status.get("collection_ready", llm_status.get("chroma_ready"))
        ),
        rag_index_ready=bool(llm_status.get("rag_ready")),
    )


# ---------------------------------------------------------------------------
# Endpoint de analisis
# ---------------------------------------------------------------------------


def _require_predictor_runtime() -> Any:
    if _resources is None or not _resources.ready:
        raise HTTPException(
            status_code=503,
            detail=(
                "El modelo local no esta habilitado en este contenedor."
                if not _LOCAL_ML_ENABLED
                else "El modelo no esta disponible. Reinicia el servidor."
            ),
        )
    return _load_predictor_runtime()


def _resolve_analysis_pet(
    *,
    pet_id: str | None,
    user_id: str | None,
    prediction_id: str,
    require_for_authenticated: bool,
) -> tuple[dict[str, Any] | None, str | None]:
    """Valida la mascota que se usara para persistencia y vigilancia."""
    if user_id is not None and require_for_authenticated and not pet_id:
        _log_analyze_event(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="pet_required",
            error_code="PET_REQUIRED",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecciona una mascota registrada antes de analizar un hemograma con tu cuenta.",
        )

    if pet_id is None:
        return None, None

    if user_id is None:
        return None, None

    pet = db.get_pet(pet_id)
    if pet is None or pet["owner_id"] != user_id:
        _log_analyze_event(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="pet_ownership",
            error_code="FORBIDDEN_PET",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La mascota indicada no pertenece a tu cuenta.",
        )
    return pet, pet_id


def _apply_pet_context_to_result(
    result_dict: dict[str, Any], pet: dict[str, Any] | None
) -> None:
    if not pet:
        return
    result_dict["pet_id"] = pet.get("id")
    result_dict["pet_name"] = pet.get("name")
    result_dict["residence_zone_code"] = pet.get("residence_zone_code")
    result_dict["residence_label"] = pet.get("residence_label")


def _run_confirmed_analysis_pipeline(
    *,
    extraction: Any,
    prediction_id: str,
    filename: str,
    file_size: int,
    extraction_provider: Literal["gemini", "local", "local_fallback"] | None,
    extraction_mode: Literal["auto", "gemini", "local"] | None,
    extraction_warnings: list[str],
    linked_pet: dict[str, Any] | None,
    user_id: str | None,
    pet_id: str | None,
    t0: float,
) -> AnalysisResult:
    predictor_runtime = _require_predictor_runtime()

    try:
        extraction.cbc = validate_cbc_contract(extraction.cbc)
    except InputContractError as exc:
        _log_analyze_event(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="input_contract",
            error_code=exc.error_code,
            fields=exc.fields,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        detail = exc.to_api_detail()
        detail["trace_id"] = prediction_id
        detail["prediction_id"] = prediction_id
        raise HTTPException(status_code=422, detail=detail)

    _log_analyze_event(
        stage="validacion",
        status="ok",
        prediction_id=prediction_id,
        step="input_contract",
        normalized_fields=len(extraction.cbc),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    try:
        prediction = predictor_runtime.predict(
            extraction.cbc, extraction.comments, _resources
        )
    except InputContractError as exc:
        _log_analyze_event(
            stage="prediccion",
            status="fail",
            prediction_id=prediction_id,
            error_code=exc.error_code,
            fields=exc.fields,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        detail = exc.to_api_detail()
        detail["trace_id"] = prediction_id
        detail["prediction_id"] = prediction_id
        raise HTTPException(status_code=422, detail=detail)
    except Exception:
        logger.exception("Error durante la inferencia del modelo")
        _log_analyze_event(
            stage="prediccion",
            status="fail",
            prediction_id=prediction_id,
            error_code="MODEL_INFERENCE_ERROR",
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(
            status_code=500, detail="Error durante el analisis del modelo."
        )

    _log_analyze_event(
        stage="prediccion",
        status="ok",
        prediction_id=prediction_id,
        confidence=prediction.confidence,
        prediction_status=getattr(prediction, "status", "success"),
        n_imputed_fields=len(getattr(prediction, "imputed_fields", [])),
        n_warnings=len(getattr(prediction, "warnings", [])),
        warnings=getattr(prediction, "warnings", []),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    result_dict = formatter.format_analysis(
        extraction=extraction,
        prediction=prediction,
        filename=filename or "desconocido",
        file_size=file_size,
    )
    envelope = predictor_runtime.build_prediction_envelope(
        prediction_id=prediction_id,
        resources=_resources,
        prediction=prediction,
    )

    result_dict["id"] = prediction_id[:8]
    result_dict.update(envelope)
    result_dict["extraction_provider"] = extraction_provider
    result_dict["extraction_mode"] = extraction_mode
    result_dict["extraction_warnings"] = extraction_warnings
    _apply_pet_context_to_result(result_dict, linked_pet)

    if result_dict.get("location") and result_dict.get("latitude") is None:
        coords = resolve_location(result_dict["location"])
        if coords:
            result_dict["latitude"], result_dict["longitude"] = coords

    should_persist = (
        user_id is not None and linked_pet is not None and pet_id is not None
    )
    result_dict["persisted"] = should_persist
    result = AnalysisResult(**result_dict)

    stored_result = censor(result.model_dump())
    stored_result["_case_snapshot"] = build_case_snapshot(
        result_dict=result.model_dump(),
        extraction=extraction,
        prediction=prediction,
        pet=linked_pet,
    )

    if should_persist:
        db.save_analysis(stored_result, user_id=user_id, pet_id=pet_id)
        try:
            event_count = sync_events_for_analysis(stored_result, linked_pet)
            _log_analyze_event(
                stage="epidemiologia",
                status="ok",
                prediction_id=prediction_id,
                events_synced=event_count,
                residence_zone=linked_pet.get("residence_zone_code"),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
        except Exception:
            logger.exception(
                "No se pudieron crear eventos epidemiologicos para analysis_id=%s",
                stored_result.get("id"),
            )
            _log_analyze_event(
                stage="epidemiologia",
                status="fail",
                prediction_id=prediction_id,
                error_code="EPIDEMIOLOGY_EVENT_ERROR",
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

    _log_analyze_event(
        stage="respuesta",
        status="ok",
        prediction_id=prediction_id,
        analysis_id=result_dict.get("id"),
        model_version=envelope["model_version"],
        policy_version=envelope["policy_version"],
        schema_version=result_dict.get("schema_version"),
        prediction_status=envelope["status"],
        quality_score=result_dict.get("quality_score"),
        confidence=result_dict.get("confidence"),
        persisted=should_persist,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )
    return result


async def analyze_hemogram(
    file: UploadFile = File(...),
    pet_id: str | None = Query(default=None),
    extraction_mode: Literal["auto", "gemini", "local"] = Query(default="auto"),
    user_id: str | None = Depends(auth.get_optional_user_id),
):
    """
    Sube un hemograma (PDF, CSV, Excel o imagen) y retorna el analisis.

    Si se proporciona pet_id, valida que la mascota pertenezca al usuario.
    Retorna 503 si el modelo no pudo cargarse al iniciar.
    """
    if _resources is None or not _resources.ready:
        raise HTTPException(
            status_code=503,
            detail=(
                "El modelo local no esta habilitado en este contenedor."
                if not _LOCAL_ML_ENABLED
                else "El modelo no esta disponible. Reinicia el servidor."
            ),
        )
    predictor_runtime = _load_predictor_runtime()

    prediction_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    _log_analyze_event(
        stage="ingesta",
        status="ok",
        prediction_id=prediction_id,
        step="upload_received",
        filename=file.filename or "desconocido",
        content_type=file.content_type or "desconocido",
        extraction_mode=extraction_mode,
        user_authenticated=user_id is not None,
        pet_requested=pet_id is not None,
    )

    linked_pet: dict | None = None

    if user_id is not None and pet_id is None:
        _log_analyze_event(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="pet_required",
            error_code="PET_REQUIRED",
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selecciona una mascota registrada antes de analizar un hemograma con tu cuenta.",
        )

    # Validar que la mascota pertenece al usuario si ambos estan presentes
    if pet_id is not None and user_id is not None:
        pet = db.get_pet(pet_id)
        if pet is None or pet["owner_id"] != user_id:
            _log_analyze_event(
                stage="validacion",
                status="fail",
                prediction_id=prediction_id,
                step="pet_ownership",
                error_code="FORBIDDEN_PET",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La mascota indicada no pertenece a tu cuenta.",
            )
        linked_pet = pet
    elif pet_id is not None and user_id is None:
        # No se puede vincular mascota sin usuario autenticado
        pet_id = None

    contents = await file.read()

    try:
        extraction_result = extraction_service.extract_uploaded_file(
            contents=contents,
            content_type=file.content_type or "",
            filename=file.filename,
            mode=extraction_mode,
        )
        extraction = extraction_result.extraction
    except ExtractionError as exc:
        _log_analyze_event(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="extraction",
            error_code="EXTRACTION_ERROR",
            detail=str(exc),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        logger.exception("Error inesperado durante la extraccion del archivo")
        _log_analyze_event(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="extraction",
            error_code="EXTRACTION_INTERNAL_ERROR",
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(status_code=500, detail="Error al procesar el archivo.")

    _log_analyze_event(
        stage="validacion",
        status="ok",
        prediction_id=prediction_id,
        step="extraction",
        cbc_fields=len(extraction.cbc),
        has_comments=bool(extraction.comments),
        extraction_provider=extraction_result.provider,
        extraction_mode=extraction_result.mode,
        fallback_used=extraction_result.fallback_used,
        extraction_warnings=extraction_result.warnings,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    try:
        extraction.cbc = validate_cbc_contract(extraction.cbc)
    except InputContractError as exc:
        _log_analyze_event(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="input_contract",
            error_code=exc.error_code,
            fields=exc.fields,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        detail = exc.to_api_detail()
        detail["trace_id"] = prediction_id
        detail["prediction_id"] = prediction_id
        raise HTTPException(status_code=422, detail=detail)

    _log_analyze_event(
        stage="validacion",
        status="ok",
        prediction_id=prediction_id,
        step="input_contract",
        normalized_fields=len(extraction.cbc),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    _log_analyze_event(
        stage="features",
        status="ok",
        prediction_id=prediction_id,
        expected_features=len(getattr(_resources, "feature_columns", [])),
        normalized_cbc_fields=len(extraction.cbc),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    try:
        prediction = predictor_runtime.predict(
            extraction.cbc, extraction.comments, _resources
        )
    except InputContractError as exc:
        _log_analyze_event(
            stage="prediccion",
            status="fail",
            prediction_id=prediction_id,
            error_code=exc.error_code,
            fields=exc.fields,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        detail = exc.to_api_detail()
        detail["trace_id"] = prediction_id
        detail["prediction_id"] = prediction_id
        raise HTTPException(status_code=422, detail=detail)
    except Exception:
        logger.exception("Error durante la inferencia del modelo")
        _log_analyze_event(
            stage="prediccion",
            status="fail",
            prediction_id=prediction_id,
            error_code="MODEL_INFERENCE_ERROR",
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )
        raise HTTPException(
            status_code=500, detail="Error durante el analisis del modelo."
        )

    _log_analyze_event(
        stage="prediccion",
        status="ok",
        prediction_id=prediction_id,
        confidence=prediction.confidence,
        prediction_status=getattr(prediction, "status", "success"),
        n_imputed_fields=len(getattr(prediction, "imputed_fields", [])),
        n_warnings=len(getattr(prediction, "warnings", [])),
        warnings=getattr(prediction, "warnings", []),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    result_dict = formatter.format_analysis(
        extraction=extraction,
        prediction=prediction,
        filename=file.filename or "desconocido",
        file_size=len(contents),
    )

    envelope = predictor_runtime.build_prediction_envelope(
        prediction_id=prediction_id,
        resources=_resources,
        prediction=prediction,
    )
    model_version = envelope["model_version"]
    policy_version = envelope["policy_version"]
    status_envelope = envelope["status"]

    result_dict["id"] = prediction_id[:8]
    result_dict.update(envelope)
    result_dict["extraction_provider"] = extraction_result.provider
    result_dict["extraction_mode"] = extraction_result.mode
    result_dict["extraction_warnings"] = extraction_result.warnings
    _apply_pet_context_to_result(result_dict, linked_pet)
    result_dict["persisted"] = (
        user_id is not None and linked_pet is not None and pet_id is not None
    )

    _log_analyze_event(
        stage="postproceso",
        status="ok",
        prediction_id=prediction_id,
        summary=result_dict.get("summary"),
        findings=len(result_dict.get("findings", [])),
        qc_flags=len(result_dict.get("qc_flags", [])),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    # Resolver coordenadas a partir del location extraído del PDF
    if result_dict.get("location") and result_dict.get("latitude") is None:
        coords = resolve_location(result_dict["location"])
        if coords:
            result_dict["latitude"], result_dict["longitude"] = coords

    result = AnalysisResult(**result_dict)
    stored_result = censor(result.model_dump())
    stored_result["_case_snapshot"] = build_case_snapshot(
        result_dict=result.model_dump(),
        extraction=extraction,
        prediction=prediction,
        pet=linked_pet,
    )

    if result.persisted:
        db.save_analysis(stored_result, user_id=user_id, pet_id=pet_id)
        try:
            event_count = sync_events_for_analysis(stored_result, linked_pet)
            _log_analyze_event(
                stage="epidemiologia",
                status="ok",
                prediction_id=prediction_id,
                events_synced=event_count,
                residence_zone=linked_pet.get("residence_zone_code"),
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )
        except Exception:
            logger.exception(
                "No se pudieron crear eventos epidemiologicos para analysis_id=%s",
                stored_result.get("id"),
            )
            _log_analyze_event(
                stage="epidemiologia",
                status="fail",
                prediction_id=prediction_id,
                error_code="EPIDEMIOLOGY_EVENT_ERROR",
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            )

    _log_analyze_event(
        stage="respuesta",
        status="ok",
        prediction_id=prediction_id,
        analysis_id=result_dict.get("id"),
        model_version=model_version,
        policy_version=policy_version,
        schema_version=result_dict.get("schema_version"),
        prediction_status=status_envelope,
        quality_score=result_dict.get("quality_score"),
        confidence=result_dict.get("confidence"),
        persisted=result.persisted,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
    )

    return result


@app.post("/api/v1/predict/batch", response_model=BatchPredictResponse)
def predict_batch_runtime(
    request: BatchPredictRequest,
    user_id: str | None = Depends(auth.get_optional_user_id),
) -> BatchPredictResponse:
    """Ejecuta inferencia batch con contrato estricto y no_prediction explicito por item."""
    if _resources is None or not _resources.ready:
        raise HTTPException(
            status_code=503,
            detail=(
                "El modelo local no esta habilitado en este contenedor."
                if not _LOCAL_ML_ENABLED
                else "El modelo no esta disponible. Reinicia el servidor."
            ),
        )
    predictor_runtime = _load_predictor_runtime()

    batch_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    _log_analyze_event(
        stage="ingesta",
        status="ok",
        prediction_id=batch_id,
        step="batch_received",
        batch_size=len(request.items),
        user_authenticated=user_id is not None,
    )

    cbc_items = [item.cbc for item in request.items]
    comments_items = [item.comments for item in request.items]
    predictions = predictor_runtime.predict_batch(cbc_items, comments_items, _resources)

    items_out: list[BatchPredictItemOut] = []
    status_counts: Counter[str] = Counter()
    model_version = "unknown"
    policy_version = "unknown"

    for idx, (item_in, prediction) in enumerate(zip(request.items, predictions)):
        prediction_id = f"{batch_id}-{idx:04d}"
        envelope = predictor_runtime.build_prediction_envelope(
            prediction_id=prediction_id,
            resources=_resources,
            prediction=prediction,
        )

        model_version = envelope["model_version"]
        policy_version = envelope["policy_version"]
        status_counts[envelope["status"]] += 1

        items_out.append(
            BatchPredictItemOut(
                index=idx,
                external_id=item_in.external_id,
                prediction_id=envelope["prediction_id"],
                model_version=envelope["model_version"],
                policy_version=envelope["policy_version"],
                schema_version=envelope["schema_version"],
                status=envelope["status"],
                confidence=prediction.confidence,
                probabilities=prediction.probabilities,
                predictions=prediction.predictions,
                imputed_fields=envelope["imputed_fields"],
                error_code=prediction.error_code,
                error_message=prediction.error_message,
                warnings=prediction.warnings,
            )
        )

        _log_analyze_event(
            stage="respuesta",
            status=envelope["status"],
            prediction_id=prediction_id,
            step="batch_item_completed",
            batch_id=batch_id,
            item_index=idx,
            error_code=prediction.error_code,
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
        )

    return BatchPredictResponse(
        batch_id=batch_id,
        model_version=model_version,
        policy_version=policy_version,
        schema_version=_SCHEMA_VERSION,
        total_items=len(items_out),
        status_counts={
            "success": int(status_counts.get("success", 0)),
            "partial_imputation": int(status_counts.get("partial_imputation", 0)),
            "no_prediction": int(status_counts.get("no_prediction", 0)),
        },
        created_at=datetime.now().isoformat(),
        items=items_out,
    )
