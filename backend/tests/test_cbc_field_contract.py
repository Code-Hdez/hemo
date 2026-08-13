from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.hematology.cbc_fields import (  # noqa: E402
    CBC_FIELD_DEFINITIONS,
    canonical_cbc_clinical_code,
    cbc_clinical_display_label,
    complete_cbc_fields,
)
from app.modules.hematology.schemas import ExtractionDebugResponse  # noqa: E402


def test_cbc_field_definitions_expose_exactly_24_visible_fields() -> None:
    keys = [field.key for field in CBC_FIELD_DEFINITIONS]

    assert len(keys) == 24
    assert "age_years" not in keys
    assert keys == [
        "WBC",
        "RBC",
        "HGB",
        "HCT",
        "MCV",
        "MCH",
        "MCHC",
        "RDW",
        "Reticulocytes_pct",
        "Reticulocytes",
        "Platelets",
        "MPV",
        "PDW",
        "PCT",
        "Neutrophils",
        "Neutrophils_pct",
        "Lymphocytes",
        "Lymphocytes_pct",
        "Monocytes",
        "Monocytes_pct",
        "Eosinophils",
        "Eosinophils_pct",
        "Basophils",
        "Basophils_pct",
    ]


def test_complete_cbc_fields_keeps_all_fields_and_marks_missing_values_empty() -> None:
    fields = complete_cbc_fields({"WBC": 12.4, "PLT": 230, "NEU": 8.2})

    assert len(fields) == 24
    by_key = {field.key: field for field in fields}
    assert by_key["WBC"].value == "12.4"
    assert by_key["WBC"].detected is True
    assert by_key["Platelets"].value == "230"
    assert by_key["Platelets"].detected is True
    assert by_key["Neutrophils"].value == "8.2"
    assert by_key["Neutrophils"].detected is True
    assert by_key["RBC"].value == ""
    assert by_key["RBC"].detected is False


def test_clinical_codes_keep_absolute_and_percentage_differential_distinct() -> None:
    assert canonical_cbc_clinical_code("Neutrophils") == "NEU"
    assert canonical_cbc_clinical_code("NEU#") == "NEU"
    assert canonical_cbc_clinical_code("Neutrophils_pct") == "NEU_PCT"
    assert canonical_cbc_clinical_code("NEU %") == "NEU_PCT"
    assert canonical_cbc_clinical_code("Platelets") == "PLT"
    assert cbc_clinical_display_label("NEU") == "NEU absoluto / Neutrófilos"
    assert cbc_clinical_display_label("NEU_PCT") == "NEU % / Neutrófilos %"


def test_extraction_response_includes_completed_field_list() -> None:
    response = ExtractionDebugResponse(
        cbc={"WBC": 12.4, "Platelets": 230.0},
        metadata={"species": "Canino"},
        comments=None,
        extraction_provider="gemini",
        extraction_mode="auto",
        fallback_used=False,
        warnings=[],
    )

    payload = response.model_dump()
    assert len(payload["fields"]) == 24
    assert payload["fields"][0]["key"] == "WBC"
    assert payload["fields"][1]["value"] == ""
