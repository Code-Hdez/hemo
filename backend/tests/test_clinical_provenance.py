from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import queries
from app.db.base import Base
from app.modules.gemini_extraction.normalizer import normalize_extracted_payload
from app.modules.hematology.extraction_types import ExtractedParameter, ExtractionResult
from app.modules.hematology.formatter import format_analysis
from app.modules.hematology.models import Analysis, AnalysisParameter


def _prediction() -> SimpleNamespace:
    return SimpleNamespace(predictions={}, confidence=0.94)


def test_normalizer_preserves_original_label_unit_range_flag_and_confidence() -> None:
    normalized = normalize_extracted_payload(
        {
            "Leucocitos": {
                "value": 22.4,
                "unit": "10^9/L",
                "raw_label": "Leucocitos (WBC)",
                "reference_min": 6.0,
                "reference_max": 17.0,
                "flag": "H",
                "confidence": 97,
            }
        }
    )

    detail = normalized.parameter_details["WBC"]
    assert detail.value == 22.4
    assert detail.original_name == "Leucocitos (WBC)"
    assert detail.unit == "10^9/L"
    assert detail.reference_min == 6.0
    assert detail.reference_max == 17.0
    assert detail.recorded_flag == "h"
    assert detail.confidence == 0.97


def test_formatter_prioritizes_laboratory_range_and_preserves_recorded_flag() -> None:
    extraction = ExtractionResult(
        cbc={"WBC": 22.4},
        metadata={"species": "Canino"},
        parameter_details={
            "WBC": ExtractedParameter(
                canonical_name="WBC",
                value=22.4,
                original_value="22.40",
                original_name="Leucocitos",
                unit="10^9/L",
                reference_min=6.0,
                reference_max=17.0,
                recorded_flag="H",
                confidence=0.97,
                data_origin="gemini",
            )
        },
    )

    result = format_analysis(extraction, _prediction(), "luna.pdf", 100)
    wbc = result["lab_values"][0]

    assert wbc["value"] == "22.4"
    assert wbc["unit"] == "10^9/L"
    assert wbc["ref_min"] == 6.0
    assert wbc["ref_max"] == 17.0
    assert wbc["reference_origin"] == "laboratory"
    assert wbc["status"] == "high"
    assert wbc["status_origin"] == "recorded"
    # Preserve the laboratory flag even if HemoVet's separate derived policy is
    # more conservative; the chat can disclose the distinction without
    # overwriting either value.
    assert wbc["derived_status"] == "critical"
    assert wbc["extraction_confidence"] == 0.97


def test_formatter_labels_catalog_ranges_instead_of_claiming_they_are_laboratory_data() -> None:
    extraction = ExtractionResult(
        cbc={"WBC": 10.0},
        metadata={"species": "Canino"},
    )

    result = format_analysis(extraction, _prediction(), "luna.pdf", 100)
    wbc = result["lab_values"][0]

    assert wbc["reference_origin"] == "validated_catalog"
    assert wbc["status_origin"] == "derived"
    assert wbc["status"] == "normal"


def test_formatter_does_not_compare_an_incompatible_unit_with_catalog_ranges() -> None:
    extraction = ExtractionResult(
        cbc={"WBC": 22.4},
        metadata={"species": "Canino"},
        parameter_details={
            "WBC": ExtractedParameter(
                canonical_name="WBC",
                value=22.4,
                unit="cells/mL",
                data_origin="local",
            )
        },
    )

    result = format_analysis(extraction, _prediction(), "luna.txt", 100)
    wbc = result["lab_values"][0]

    assert wbc["reference_origin"] == "unknown"
    assert wbc["ref_min"] is None
    assert wbc["ref_max"] is None
    assert wbc["status"] == "not_evaluable"


def test_save_analysis_persists_normalized_parameter_rows(
    tmp_path, monkeypatch
) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'clinical.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(queries, "engine", engine)
    monkeypatch.setattr(queries, "_use_db", True)

    queries.save_analysis(
        {
            "id": "a1",
            "created_at": "2026-03-14T10:00:00",
            "confidence": 0.97,
            "extraction_provider": "gemini",
            "lab_values": [
                {
                    "name": "WBC",
                    "canonical_name": "WBC",
                    "original_name": "Leucocitos",
                    "value": "22.40",
                    "unit": "10^9/L",
                    "normalized_unit": "10^9/L",
                    "ref_min": 6.0,
                    "ref_max": 17.0,
                    "reference_origin": "laboratory",
                    "status": "high",
                    "status_origin": "recorded",
                    "derived_status": "critical",
                    "extraction_confidence": 0.97,
                    "data_origin": "gemini",
                }
            ],
        }
    )

    with Session(engine) as session:
        row = session.scalar(select(AnalysisParameter))

    assert row is not None
    assert row.canonical_name == "WBC"
    assert str(row.numeric_value).startswith("22.4")
    assert row.reference_origin == "laboratory"
    assert row.recorded_flag == "high"
    assert row.derived_flag == "critical"
    assert row.extraction_confidence == 0.97


def test_save_analysis_leaves_extraction_confidence_null_for_the_classifier_score(
    tmp_path, monkeypatch
) -> None:
    """``confidence`` is the ML classifier's, and the chat reads this column as
    the document's digitisation quality. With no extraction confidence
    reported, the column stays NULL instead of borrowing another metric."""
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'confidence.db'}")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(queries, "engine", engine)
    monkeypatch.setattr(queries, "_use_db", True)

    queries.save_analysis(
        {
            "id": "a1",
            "created_at": "2026-03-14T10:00:00",
            "confidence": 0.97,
            "extraction_provider": "gemini",
            "lab_values": [],
        }
    )
    queries.save_analysis(
        {
            "id": "a2",
            "created_at": "2026-03-14T10:00:00",
            "confidence": 0.97,
            "extraction_confidence": 0.55,
            "extraction_provider": "gemini",
            "lab_values": [],
        }
    )

    with Session(engine) as session:
        assert session.get(Analysis, "a1").extraction_confidence is None
        assert session.get(Analysis, "a2").extraction_confidence == 0.55
