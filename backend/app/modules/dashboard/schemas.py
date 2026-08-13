"""Dashboard and model-quality response contracts."""

from typing import Literal

from pydantic import BaseModel


class LabelMetrics(BaseModel):
    name: str
    pr_auc: float
    roc_auc: float
    f1: float
    ece: float
    threshold: float | None = None
    status: str


class DomainShiftEntry(BaseModel):
    feature: str
    d: float
    severity: str


class ExternalValidation(BaseModel):
    dataset: str
    n: int
    coherence_check: str
    domain_shifts: list[DomainShiftEntry]


class ModelQualityResponse(BaseModel):
    version: str
    prauc_macro: float
    labels: list[LabelMetrics]
    external_validation: ExternalValidation
    gates: dict[str, str]


class LabelActivationEntry(BaseModel):
    name: str
    rate_idexx: float
    rate_dap: float
    threshold: float | None = None
    diagnosis: str | None = None


class LabelActivationResponse(BaseModel):
    labels: list[LabelActivationEntry]


class TemporalPoint(BaseModel):
    period: str
    n_analyses: int
    mean_confidence: float
    qc_flag_pct: float
    top_finding: str


class TemporalAnalyticsResponse(BaseModel):
    timeline: list[TemporalPoint]
    granularity: Literal["week", "month"]
    period_days: int


class BreedEntry(BaseModel):
    name: str
    count: int
    pct: float


class BreedDistributionResponse(BaseModel):
    breeds: list[BreedEntry]
    period_days: int
    total: int
