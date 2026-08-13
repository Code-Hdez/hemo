from __future__ import annotations

import sys
import asyncio
import threading
import time
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.hematology import service  # noqa: E402
from app.modules.hematology.extraction_service import (  # noqa: E402
    ExtractionServiceResult,
)
from app.modules.hematology.extraction_types import ExtractionResult  # noqa: E402
from app.modules.hematology.schemas import (  # noqa: E402
    AnalysisResult,
    ConfirmedAnalysisRequest,
)


def test_extract_returns_partial_cbc_for_human_review(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_extract_uploaded_file(**_: Any) -> ExtractionServiceResult:
        return ExtractionServiceResult(
            extraction=ExtractionResult(
                cbc={"WBC": 12.4, "RBC": 6.2},
                metadata={"species": "Canino"},
                comments=None,
            ),
            provider="gemini",
            mode="auto",
            warnings=[],
        )

    monkeypatch.setattr(service.extraction_service, "extract_uploaded_file", fake_extract_uploaded_file)

    response = service.extract(
        contents=b"%PDF",
        content_type="application/pdf",
        filename="parcial.pdf",
        mode="auto",
        user_id=None,
    )

    assert response.cbc == {"WBC": 12.4, "RBC": 6.2}
    assert len(response.fields) == 24
    assert response.fields[0].value == "12.4"
    assert response.fields[10].value == ""


def test_authenticated_user_can_analyze_confirmed_values_without_pet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run_prediction(**kwargs: Any) -> AnalysisResult:
        captured.update(kwargs)
        return AnalysisResult(
            id="tmp-123",
            prediction_id="pred-123",
            model_version="test-model",
            policy_version="test-policy",
            schema_version="3.0.0",
            status="partial_imputation",
            imputed_fields=[],
            extraction_provider="gemini",
            extraction_mode="auto",
            extraction_warnings=[],
            filename="confirmado.pdf",
            file_size=100,
            created_at="2026-06-25T12:00:00Z",
            confidence=0.7,
            quality_score=0.8,
            species="Canina",
            summary="Resultado temporal.",
            diagnoses=["Resultado temporal"],
            findings=[],
            qc_flags=[],
            lab_values=[],
            pet_id=None,
            pet_name=None,
            persisted=False,
        )

    monkeypatch.setattr(service, "_run_prediction", fake_run_prediction)

    result = service.analyze_confirmed(
        ConfirmedAnalysisRequest(
            cbc={"WBC": 12.4, "RBC": 6.2, "HGB": 14.1},
            filename="confirmado.pdf",
            file_size=100,
            pet_id=None,
        ),
        user_id="user-1",
    )

    assert result.persisted is False
    assert captured["pet"] is None
    assert captured["pet_id"] is None
    assert captured["extraction"].parameter_details == {}


def test_blocking_analysis_tasks_are_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.settings, "HEMOVET_ANALYSIS_CONCURRENCY", 1)
    monkeypatch.setattr(service, "_analysis_limiter", None)
    monkeypatch.setattr(service, "_analysis_limiter_loop", None)
    monkeypatch.setattr(service, "_analysis_limiter_size", None)

    active = 0
    max_active = 0
    lock = threading.Lock()

    def slow_task(value: int) -> int:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return value

    async def run_tasks() -> list[int]:
        return await asyncio.gather(
            service.run_limited_blocking(slow_task, 1),
            service.run_limited_blocking(slow_task, 2),
        )

    assert asyncio.run(run_tasks()) == [1, 2]
    assert max_active == 1
