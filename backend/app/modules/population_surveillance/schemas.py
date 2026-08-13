from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EpidemiologyPoint(BaseModel):
    zone_code: str
    zone_label: str
    lat: float
    lng: float
    finding: str
    count: int = Field(ge=1)
    report_count: int = Field(ge=1)
    pet_count: int = Field(ge=1)
    intensity_level: str
    intensity_score: float
    severity: str
    location_name: str


class EpidemiologyStreamEvent(BaseModel):
    type: str
    revision: str
    updated_at: str


class EpidemiologyPointResponse(BaseModel):
    zone_code: str | None = None
    zone_label: str | None = None
    lat: float
    lng: float
    finding: str
    count: int
    report_count: int | None = None
    pet_count: int | None = None
    intensity_level: str | None = None
    intensity_score: float | None = None
    severity: str
    location_name: str


class SurveillanceSignal(BaseModel):
    metric: str
    value: float
    baseline: float | None = None
    status: Literal["pass", "warn", "fail"]
    action: str


class SurveillanceGeoPoint(BaseModel):
    location: str
    count: int
    pct: float


class SurveillanceReport(BaseModel):
    generated_at: str
    period_days: int
    cohort_size: int
    status: Literal["pass", "warn", "fail"]
    status_counts: dict[str, int]
    temporal_signals: list[SurveillanceSignal]
    geographic_hotspots: list[SurveillanceGeoPoint]
    gate_status: dict[str, str]
