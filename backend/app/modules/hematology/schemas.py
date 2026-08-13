"""Hematology extraction and analysis HTTP contracts."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.hematology.cbc_fields import complete_cbc_fields


class LabValue(BaseModel):
    name: str
    value: str
    unit: str
    status: str
    ref_min: float | None = None
    ref_max: float | None = None
    canonical_name: str | None = None
    original_name: str | None = None
    original_value: str | None = None
    normalized_unit: str | None = None
    reference_origin: Literal[
        "laboratory", "validated_catalog", "system_default_legacy", "unknown"
    ] = "unknown"
    status_origin: Literal["recorded", "derived", "unknown"] = "unknown"
    derived_status: str | None = None
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    notes: str | None = None
    data_origin: str = "unknown"


class Finding(BaseModel):
    label: str
    detail: str
    severity: str


class ExtractedCbcField(BaseModel):
    key: str
    label: str
    unit: str
    value: str = ""
    detected: bool = False
    required: bool = False
    group: str
    order: int


class AnalysisResult(BaseModel):
    id: str
    prediction_id: str | None = None
    model_version: str | None = None
    policy_version: str | None = None
    schema_version: str | None = None
    status: Literal["success", "partial_imputation", "no_prediction"] = "success"
    imputed_fields: list[str] = Field(default_factory=list)
    extraction_provider: Literal["gemini", "local", "local_fallback"] | None = None
    extraction_mode: Literal["auto", "gemini", "local"] | None = None
    extraction_warnings: list[str] = Field(default_factory=list)
    filename: str
    file_size: int
    created_at: str
    confidence: float
    quality_score: float
    species: str
    summary: str
    diagnoses: list[str]
    findings: list[Finding]
    qc_flags: list[str] = Field(default_factory=list)
    lab_values: list[LabValue]
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    pet_id: str | None = None
    pet_name: str | None = None
    residence_zone_code: str | None = None
    residence_label: str | None = None
    persisted: bool = False


class ExtractionDebugResponse(BaseModel):
    cbc: dict[str, float]
    fields: list[ExtractedCbcField] = Field(default_factory=list)
    metadata: dict[str, str | None]
    comments: str | None = None
    extraction_provider: Literal["gemini", "local", "local_fallback"]
    extraction_mode: Literal["auto", "gemini", "local"]
    fallback_used: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def complete_visible_fields(self) -> "ExtractionDebugResponse":
        if not self.fields:
            self.fields = [
                ExtractedCbcField(**field.__dict__)
                for field in complete_cbc_fields(self.cbc)
            ]
        return self


class ConfirmedAnalysisRequest(BaseModel):
    cbc: dict[str, float]
    metadata: dict[str, Any | None] = Field(default_factory=dict)
    comments: str | None = None
    extraction_provider: Literal["gemini", "local", "local_fallback"] | None = None
    extraction_mode: Literal["auto", "gemini", "local"] | None = None
    extraction_warnings: list[str] = Field(default_factory=list)
    filename: str = "valores-confirmados"
    file_size: int = 0
    pet_id: str | None = None
