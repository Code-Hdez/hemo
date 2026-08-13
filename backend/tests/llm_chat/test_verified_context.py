from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.llm_chat.domain.verified_context import (
    MLAnalysisContext,
    MLPrediction,
    VerifiedContextBundle,
)


def test_ml_context_exposes_only_predictions_approved_for_explanation() -> None:
    context = MLAnalysisContext(
        analysis_id="analysis-1",
        model_name="hemovet_classifier",
        model_version="1.4.0",
        prediction_timestamp=datetime(2026, 7, 19, 20, tzinfo=UTC),
        predictions=(
            MLPrediction(
                label="possible_anemia_pattern",
                probability=0.82,
                validated_for_explanation=True,
            ),
            MLPrediction(
                label="internal_unvalidated_label",
                probability=0.51,
                validated_for_explanation=False,
            ),
        ),
        limitations=("La salida es orientativa y no constituye un diagnóstico.",),
    )

    payload = context.prompt_payload()

    assert payload["contract_version"] == "hemovet-ml-analysis-context-v1"
    assert payload["model_version"] == "1.4.0"
    assert [item["label"] for item in payload["predictions"]] == [
        "possible_anemia_pattern"
    ]
    assert payload["predictions"][0]["probability"] == 0.82


@pytest.mark.parametrize("probability", [-0.01, 1.01, float("nan")])
def test_ml_prediction_rejects_invalid_probability(probability: float) -> None:
    with pytest.raises(ValueError, match="ml_prediction_probability_out_of_range"):
        MLPrediction(label="possible_pattern", probability=probability)


def test_verified_bundle_rejects_cross_analysis_ml_context() -> None:
    ml_context = MLAnalysisContext(
        analysis_id="analysis-other",
        model_name="hemovet_classifier",
        model_version="1.4.0",
        prediction_timestamp=datetime.now(UTC),
        predictions=(),
    )

    with pytest.raises(ValueError, match="ml_context_analysis_mismatch"):
        VerifiedContextBundle(analysis_id="analysis-active", ml_analysis=ml_context)
