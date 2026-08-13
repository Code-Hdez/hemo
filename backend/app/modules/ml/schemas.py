"""Machine-learning prediction contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class BatchPredictItemIn(BaseModel):
    external_id: str | None = None
    cbc: dict[str, float | int | str | None]
    comments: str | None = None


class BatchPredictRequest(BaseModel):
    items: list[BatchPredictItemIn] = Field(min_length=1, max_length=200)


class BatchPredictItemOut(BaseModel):
    index: int
    external_id: str | None = None
    prediction_id: str
    model_version: str
    policy_version: str
    schema_version: str
    status: Literal["success", "partial_imputation", "no_prediction"]
    confidence: float
    probabilities: dict[str, float]
    predictions: dict[str, bool]
    imputed_fields: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BatchPredictResponse(BaseModel):
    batch_id: str
    model_version: str
    policy_version: str
    schema_version: str
    total_items: int
    status_counts: dict[str, int]
    created_at: str
    items: list[BatchPredictItemOut]
