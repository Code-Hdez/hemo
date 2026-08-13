"""Dashboard and model-observability endpoints."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from app.modules.auth.dependencies import require_admin
from app.modules.dashboard import service
from app.modules.dashboard.schemas import (
    BreedDistributionResponse,
    LabelActivationResponse,
    ModelQualityResponse,
    TemporalAnalyticsResponse,
)

router = APIRouter(tags=["Dashboard"])


@router.get("/model/quality", response_model=ModelQualityResponse)
def get_model_quality(
    _admin_user: dict[str, Any] = Depends(require_admin),
) -> ModelQualityResponse:
    return service.model_quality()


@router.get("/analytics/label-activation", response_model=LabelActivationResponse)
def get_label_activation(
    _admin_user: dict[str, Any] = Depends(require_admin),
) -> LabelActivationResponse:
    return service.label_activation()


@router.get("/analytics/temporal", response_model=TemporalAnalyticsResponse)
def get_temporal_analytics(
    granularity: Literal["week", "month"] = Query(default="week"),
    period_days: int = Query(default=90, ge=7, le=365),
) -> TemporalAnalyticsResponse:
    return service.temporal(granularity, period_days)


@router.get("/analytics/breed-distribution", response_model=BreedDistributionResponse)
def get_breed_distribution(
    period_days: int = Query(default=30, ge=7, le=365),
    _admin_user: dict[str, Any] = Depends(require_admin),
) -> BreedDistributionResponse:
    return service.breed_distribution(period_days)
