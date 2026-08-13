from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import math
from typing import Any, Protocol


class VerifiedContextKind(StrEnum):
    LABORATORY_FACT = "laboratory_fact"
    DETERMINISTIC_RULE = "deterministic_rule"
    ML_PREDICTION = "ml_prediction"
    DOCUMENT_EVIDENCE = "document_evidence"
    LIMITATION = "limitation"


@dataclass(frozen=True, slots=True)
class MLPrediction:
    label: str
    probability: float
    display_status: str = "possible"
    validated_for_explanation: bool = False

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("ml_prediction_label_required")
        if not math.isfinite(self.probability) or not 0 <= self.probability <= 1:
            raise ValueError("ml_prediction_probability_out_of_range")

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "probability": self.probability,
            "display_status": self.display_status,
            "validated_for_explanation": self.validated_for_explanation,
        }


@dataclass(frozen=True, slots=True)
class MLAnalysisContext:
    """Versioned, read-only boundary between the ML and conversational modules."""

    analysis_id: str
    model_name: str
    model_version: str
    prediction_timestamp: datetime
    predictions: tuple[MLPrediction, ...]
    quality_flags: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    contract_version: str = "hemovet-ml-analysis-context-v1"

    def __post_init__(self) -> None:
        if not self.analysis_id.strip():
            raise ValueError("ml_analysis_id_required")
        if not self.model_name.strip() or not self.model_version.strip():
            raise ValueError("ml_model_identity_required")
        if self.prediction_timestamp.tzinfo is None:
            raise ValueError("ml_prediction_timestamp_must_be_timezone_aware")
        labels = [prediction.label for prediction in self.predictions]
        if len(labels) != len(set(labels)):
            raise ValueError("ml_prediction_labels_must_be_unique")

    @property
    def explainable_predictions(self) -> tuple[MLPrediction, ...]:
        return tuple(
            prediction
            for prediction in self.predictions
            if prediction.validated_for_explanation
        )

    def prompt_payload(self) -> dict[str, object]:
        """Expose only predictions explicitly approved for explanation."""

        return {
            "contract_version": self.contract_version,
            "analysis_id": self.analysis_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
            "predictions": [
                prediction.as_dict() for prediction in self.explainable_predictions
            ],
            "quality_flags": list(self.quality_flags),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class VerifiedContextBundle:
    analysis_id: str | None = None
    clinical_facts: tuple[dict[str, Any], ...] = ()
    historical_trends: tuple[dict[str, Any], ...] = ()
    ml_analysis: MLAnalysisContext | None = None
    document_evidence: tuple[dict[str, Any], ...] = ()
    provenance_kinds: frozenset[VerifiedContextKind] = field(default_factory=frozenset)
    contract_version: str = "hemovet-verified-context-v1"

    def __post_init__(self) -> None:
        if (
            self.ml_analysis is not None
            and self.analysis_id != self.ml_analysis.analysis_id
        ):
            raise ValueError("ml_context_analysis_mismatch")


class ClinicalFactsProvider(Protocol):
    async def clinical_facts(
        self,
        *,
        user_id: str,
        analysis_id: str,
    ) -> tuple[dict[str, Any], ...]: ...


class HistoricalTrendProvider(Protocol):
    async def historical_trends(
        self,
        *,
        user_id: str,
        patient_id: str,
    ) -> tuple[dict[str, Any], ...]: ...


class MLPredictionContextProvider(Protocol):
    async def ml_analysis_context(
        self,
        *,
        user_id: str,
        analysis_id: str,
    ) -> MLAnalysisContext | None: ...


class DocumentEvidenceProvider(Protocol):
    async def document_evidence(
        self,
        *,
        query: str,
    ) -> tuple[dict[str, Any], ...]: ...


class VerifiedContextProvider(Protocol):
    async def verified_context(
        self,
        *,
        user_id: str,
        mode: str,
        patient_id: str | None,
        analysis_id: str | None,
        query: str,
    ) -> VerifiedContextBundle: ...
