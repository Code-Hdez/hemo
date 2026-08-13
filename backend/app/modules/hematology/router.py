"""Hematology extraction and analysis HTTP endpoints."""

from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.modules.auth.compat import get_optional_user_id
from app.modules.hematology import service
from app.modules.hematology.schemas import (
    AnalysisResult,
    ConfirmedAnalysisRequest,
    ExtractionDebugResponse,
)

router = APIRouter(tags=["Hematology"])


@router.post("/extract", response_model=ExtractionDebugResponse)
async def extract_hemogram(
    file: UploadFile = File(...),
    extraction_mode: Literal["auto", "gemini", "local"] = Query(default="auto"),
    user_id: str | None = Depends(get_optional_user_id),
) -> ExtractionDebugResponse:
    return await service.run_limited_blocking(
        service.extract,
        contents=await file.read(),
        content_type=file.content_type or "",
        filename=file.filename,
        mode=extraction_mode,
        user_id=user_id,
    )


@router.post("/analyze/confirmed", response_model=AnalysisResult)
async def analyze_confirmed_hemogram(
    request: ConfirmedAnalysisRequest,
    user_id: str | None = Depends(get_optional_user_id),
) -> AnalysisResult:
    return await service.run_limited_blocking(
        service.analyze_confirmed, request, user_id
    )


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_hemogram(
    file: UploadFile = File(...),
    pet_id: str | None = Query(default=None),
    extraction_mode: Literal["auto", "gemini", "local"] = Query(default="auto"),
    user_id: str | None = Depends(get_optional_user_id),
) -> AnalysisResult:
    return await service.run_limited_blocking(
        service.analyze_upload,
        contents=await file.read(),
        content_type=file.content_type or "",
        filename=file.filename,
        pet_id=pet_id,
        mode=extraction_mode,
        user_id=user_id,
    )
