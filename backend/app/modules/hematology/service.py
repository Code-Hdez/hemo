"""Hematology extraction and prediction orchestration."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from functools import partial
from types import SimpleNamespace
from typing import Any, Callable, Literal

from fastapi import HTTPException, status
from app.core.config import settings
from app.db import queries as db
from app.modules.hematology import extraction_service, formatter
from app.modules.hematology.anonymizer import censor
from app.modules.hematology.cbc_fields import normalize_visible_cbc_values
from app.modules.hematology.extraction_types import ExtractionError
from app.modules.hematology.schemas import (
    AnalysisResult,
    ConfirmedAnalysisRequest,
    ExtractionDebugResponse,
)
from app.modules.maps.geocoder import resolve_location
from app.modules.ml.input_contract import InputContractError, validate_cbc_contract
from app.modules.population_surveillance.service import sync_events_for_analysis
from app.modules.llm_chat.snapshots import build_case_snapshot

logger = logging.getLogger("hemovet.hematology")

_resources: Any | None = None
_predictor_loader: Callable[[], Any] | None = None
_local_ml_enabled = True
_event_logger: Callable[..., None] | None = None
_analysis_limiter: asyncio.Semaphore | None = None
_analysis_limiter_loop: asyncio.AbstractEventLoop | None = None
_analysis_limiter_size: int | None = None
_analysis_executor = ThreadPoolExecutor(
    max_workers=16,
    thread_name_prefix="hemovet-analysis",
)


def configure_runtime(
    *,
    resources_getter: Callable[[], Any | None],
    predictor_loader: Callable[[], Any],
    local_ml_enabled: bool,
    event_logger: Callable[..., None],
) -> None:
    global _resources, _predictor_loader, _local_ml_enabled, _event_logger
    _resources = resources_getter()
    _predictor_loader = predictor_loader
    _local_ml_enabled = local_ml_enabled
    _event_logger = event_logger


def refresh_resources(resources: Any | None) -> None:
    global _resources
    _resources = resources


def _log(**payload: Any) -> None:
    if _event_logger is not None:
        _event_logger(**payload)


def _get_analysis_limiter() -> asyncio.Semaphore:
    global _analysis_limiter, _analysis_limiter_loop, _analysis_limiter_size
    loop = asyncio.get_running_loop()
    limit = settings.HEMOVET_ANALYSIS_CONCURRENCY
    if (
        _analysis_limiter is None
        or _analysis_limiter_loop is not loop
        or _analysis_limiter_size != limit
    ):
        _analysis_limiter = asyncio.Semaphore(limit)
        _analysis_limiter_loop = loop
        _analysis_limiter_size = limit
    return _analysis_limiter


async def run_limited_blocking(
    func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    limiter = _get_analysis_limiter()
    async with limiter:
        # Keep this workload out of Starlette's shared AnyIO worker pool: a busy
        # upload/extraction path must not consume the same worker tokens used by
        # unrelated request handlers.  The semaphore remains the effective
        # (and configurable) concurrency boundary; the executor only supplies
        # enough isolated workers for the largest allowed setting.
        context = copy_context()
        call = partial(func, *args, **kwargs)
        future = _analysis_executor.submit(context.run, call)
        try:
            # Polling the concurrent future keeps cancellation and completion
            # independent from the event loop's cross-thread wakeup mechanism.
            # This is important on constrained runtimes where that wakeup may
            # be delayed, while still yielding the loop on every iteration.
            while not future.done():
                await asyncio.sleep(0.01)
            return future.result()
        except asyncio.CancelledError:
            future.cancel()
            raise


def _predictor() -> Any:
    if _resources is None or not _resources.ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El modelo local no esta habilitado en este contenedor."
                if not _local_ml_enabled
                else "El modelo no esta disponible. Reinicia el servidor."
            ),
        )
    if _predictor_loader is None:
        raise HTTPException(status_code=503, detail="El modelo no esta disponible.")
    return _predictor_loader()


def _contract_error(exc: InputContractError, prediction_id: str) -> HTTPException:
    detail = exc.to_api_detail()
    detail.update(trace_id=prediction_id, prediction_id=prediction_id)
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
    )


def extract(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
    mode: Literal["auto", "gemini", "local"],
    user_id: str | None,
) -> ExtractionDebugResponse:
    prediction_id = str(uuid.uuid4())
    started = time.perf_counter()
    _log(
        stage="ingesta",
        status="ok",
        prediction_id=prediction_id,
        step="extract_upload_received",
        filename=filename or "desconocido",
        content_type=content_type or "desconocido",
        extraction_mode=mode,
        user_authenticated=user_id is not None,
    )
    try:
        result = extraction_service.extract_uploaded_file(
            contents=contents, content_type=content_type, filename=filename, mode=mode
        )
        result.extraction.cbc = normalize_visible_cbc_values(result.extraction.cbc)
    except ExtractionError as exc:
        _log(
            stage="validacion",
            status="fail",
            prediction_id=prediction_id,
            step="extract_extraction",
            error_code="EXTRACTION_ERROR",
            detail=str(exc),
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
        raise HTTPException(status_code=422, detail=str(exc))
    except InputContractError as exc:
        raise _contract_error(exc, prediction_id)
    except Exception as exc:
        logger.exception("Unexpected error extracting hematology file")
        raise HTTPException(
            status_code=500, detail="Error al extraer el archivo."
        ) from exc
    _log(
        stage="respuesta",
        status="ok",
        prediction_id=prediction_id,
        step="extract_completed",
        extraction_provider=result.provider,
        extraction_mode=result.mode,
        fallback_used=result.fallback_used,
        cbc_fields=len(result.extraction.cbc),
        warnings=result.warnings,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return ExtractionDebugResponse(
        cbc=result.extraction.cbc,
        metadata=result.extraction.metadata,
        comments=result.extraction.comments,
        extraction_provider=result.provider,
        extraction_mode=result.mode,
        fallback_used=result.fallback_used,
        warnings=result.warnings,
    )


def _owned_pet(
    *, pet_id: str | None, user_id: str | None, prediction_id: str, required: bool
) -> tuple[dict[str, Any] | None, str | None]:
    if user_id is not None and required and not pet_id:
        _log(
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
    if pet_id is None or user_id is None:
        return None, None
    pet = db.get_pet(pet_id)
    if pet is None or pet["owner_id"] != user_id:
        _log(
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


def _result_with_context(result: dict[str, Any], pet: dict[str, Any] | None) -> None:
    if pet is not None:
        result.update(
            pet_id=pet.get("id"),
            pet_name=pet.get("name"),
            residence_zone_code=pet.get("residence_zone_code"),
            residence_label=pet.get("residence_label"),
        )
    if result.get("location") and result.get("latitude") is None:
        coords = resolve_location(result["location"])
        if coords:
            result["latitude"], result["longitude"] = coords


def _run_prediction(
    *,
    extraction: Any,
    prediction_id: str,
    filename: str,
    file_size: int,
    extraction_provider: Literal["gemini", "local", "local_fallback"] | None,
    extraction_mode: Literal["auto", "gemini", "local"] | None,
    extraction_warnings: list[str],
    pet: dict[str, Any] | None,
    user_id: str | None,
    pet_id: str | None,
    started: float,
) -> AnalysisResult:
    predictor = _predictor()
    try:
        extraction.cbc = validate_cbc_contract(extraction.cbc)
        prediction = predictor.predict(extraction.cbc, extraction.comments, _resources)
    except InputContractError as exc:
        raise _contract_error(exc, prediction_id)
    except Exception as exc:
        logger.exception("Model inference failed")
        raise HTTPException(
            status_code=500, detail="Error durante el analisis del modelo."
        ) from exc
    for detail in getattr(extraction, "parameter_details", {}).values():
        detail.data_origin = extraction_provider or "unknown"
    result = formatter.format_analysis(
        extraction=extraction,
        prediction=prediction,
        filename=filename or "desconocido",
        file_size=file_size,
    )
    envelope = predictor.build_prediction_envelope(
        prediction_id=prediction_id, resources=_resources, prediction=prediction
    )
    result.update(
        id=prediction_id[:8],
        **envelope,
        extraction_provider=extraction_provider,
        extraction_mode=extraction_mode,
        extraction_warnings=extraction_warnings,
    )
    _result_with_context(result, pet)
    result["persisted"] = user_id is not None and pet is not None and pet_id is not None
    response = AnalysisResult(**result)
    stored = censor(response.model_dump())
    stored["_case_snapshot"] = build_case_snapshot(
        result_dict=response.model_dump(),
        extraction=extraction,
        prediction=prediction,
        pet=pet,
    )
    if response.persisted:
        db.save_analysis(stored, user_id=user_id, pet_id=pet_id)
        try:
            sync_events_for_analysis(stored, pet)
        except Exception:
            logger.exception(
                "Unable to sync epidemiology events for analysis %s", response.id
            )
    _log(
        stage="respuesta",
        status="ok",
        prediction_id=prediction_id,
        analysis_id=response.id,
        model_version=envelope["model_version"],
        policy_version=envelope["policy_version"],
        schema_version=response.schema_version,
        prediction_status=envelope["status"],
        quality_score=response.quality_score,
        confidence=response.confidence,
        persisted=response.persisted,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return response


def analyze_confirmed(
    request: ConfirmedAnalysisRequest, user_id: str | None
) -> AnalysisResult:
    prediction_id = str(uuid.uuid4())
    started = time.perf_counter()
    pet, effective_pet_id = _owned_pet(
        pet_id=request.pet_id,
        user_id=user_id,
        prediction_id=prediction_id,
        required=False,
    )
    extraction = SimpleNamespace(
        cbc=dict(request.cbc),
        metadata=dict(request.metadata),
        comments=request.comments,
        # Confirmed values bypass the document extractor, but downstream
        # formatting still consumes the extractor's structured provenance map.
        # Keep the same contract with an empty map so catalog units/ranges can
        # be applied without crashing the authenticated persistence flow.
        parameter_details={},
    )
    return _run_prediction(
        extraction=extraction,
        prediction_id=prediction_id,
        filename=request.filename,
        file_size=max(0, int(request.file_size or 0)),
        extraction_provider=request.extraction_provider,
        extraction_mode=request.extraction_mode,
        extraction_warnings=request.extraction_warnings,
        pet=pet,
        user_id=user_id,
        pet_id=effective_pet_id,
        started=started,
    )


def analyze_upload(
    *,
    contents: bytes,
    content_type: str,
    filename: str | None,
    pet_id: str | None,
    mode: Literal["auto", "gemini", "local"],
    user_id: str | None,
) -> AnalysisResult:
    prediction_id = str(uuid.uuid4())
    started = time.perf_counter()
    pet, effective_pet_id = _owned_pet(
        pet_id=pet_id, user_id=user_id, prediction_id=prediction_id, required=False
    )
    try:
        extraction_result = extraction_service.extract_uploaded_file(
            contents=contents, content_type=content_type, filename=filename, mode=mode
        )
    except ExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected extraction failure")
        raise HTTPException(
            status_code=500, detail="Error al procesar el archivo."
        ) from exc
    return _run_prediction(
        extraction=extraction_result.extraction,
        prediction_id=prediction_id,
        filename=filename or "desconocido",
        file_size=len(contents),
        extraction_provider=extraction_result.provider,
        extraction_mode=extraction_result.mode,
        extraction_warnings=extraction_result.warnings,
        pet=pet,
        user_id=user_id,
        pet_id=effective_pet_id,
        started=started,
    )
