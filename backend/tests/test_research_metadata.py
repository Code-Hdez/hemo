from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.hematology.extraction_types import ExtractionResult  # noqa: E402
from app.modules.hematology.formatter import format_analysis  # noqa: E402
from app.modules.ml.gates import (  # noqa: E402
    run_dog_leakage_gate,
    run_metadata_retention_gate,
)  # noqa: E402
from app.modules.ml.metadata import make_dog_id, parse_hemogram_date  # noqa: E402
from app.modules.ml.input_contract import validate_cbc_contract  # noqa: E402
from app.modules.ml.predictor import (  # noqa: E402
    PredictionResult,
    _calibrate_probability,
)


class ResearchMetadataTests(unittest.TestCase):
    def test_sigmoid_logit_calibrator_is_supported(self) -> None:
        calibrator = {"type": "sigmoid_logit", "coefficient": 1.0, "intercept": 0.0}

        self.assertAlmostEqual(_calibrate_probability(calibrator, 0.25), 0.25)

    def test_unknown_calibrator_format_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            _calibrate_probability({"type": "unknown"}, 0.5)

    def test_high_mchc_passes_input_contract(self) -> None:
        cbc = validate_cbc_contract(
            {
                "WBC": 6.47,
                "RBC": 3.64,
                "HGB": 16.6,
                "HCT": 26.4,
                "MCHC": 62.8,
                "RDW": 4.1,
            }
        )

        self.assertEqual(cbc["MCHC"], 62.8)
        self.assertEqual(cbc["RDW"], 4.1)

    def test_parse_hemogram_date_accepts_two_and_four_digit_years(self) -> None:
        self.assertEqual(
            parse_hemogram_date("12/31/25").date().isoformat(), "2025-12-31"
        )
        self.assertEqual(
            parse_hemogram_date("12/31/2025").date().isoformat(), "2025-12-31"
        )

    def test_make_dog_id_is_stable_and_does_not_expose_names(self) -> None:
        first = make_dog_id(
            patient_name="Luna",
            pet_owner="Maria Perez",
            clinic="BOCA SERVICIOS VETERINARIOS",
        )
        second = make_dog_id(
            patient_name=" luna ",
            pet_owner="MARÍA  PÉREZ",
            clinic="boca servicios veterinarios",
        )

        self.assertEqual(first, second)
        self.assertNotIn("luna", first.lower())
        self.assertEqual(len(first), 20)

    def test_format_analysis_uses_pdf_date_with_two_digit_year(self) -> None:
        extraction = ExtractionResult(
            cbc={"WBC": 10.0, "RBC": 7.0, "HGB": 14.0, "HCT": 42.0, "Platelets": 250.0},
            metadata={"species": "Canine", "date_result": "05/01/26"},
            comments=None,
        )
        prediction = PredictionResult(
            probabilities={},
            predictions={},
            confidence=0.9,
            feature_row=pd.DataFrame([{}]),
            status="success",
            imputed_fields=[],
        )

        result = format_analysis(
            extraction, prediction, filename="batch_1.pdf", file_size=100
        )

        self.assertTrue(result["created_at"].startswith("2026-05-01"))
        self.assertIn("_uploaded_at", result)

    def test_metadata_retention_gate_passes_and_dog_leakage_gate_detects_cross_split(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "data" / "processed"
            processed.mkdir(parents=True)
            (processed / "feature_columns.json").write_text(
                json.dumps({"feature_columns": ["WBC"], "n_features": 1}),
                encoding="utf-8",
            )
            metadata = pd.DataFrame(
                [
                    {
                        "record_id": "r1",
                        "record_uuid": "r1",
                        "dog_id": "dog-a",
                        "source_dataset": "IDEXX",
                        "ingestion_cohort": "baseline_historico",
                        "sample_date": "2025-01-01",
                        "raw_location_text": "Boca Chica",
                        "location_source": "manual_override",
                        "location_confidence": 0.95,
                    },
                    {
                        "record_id": "r2",
                        "record_uuid": "r2",
                        "dog_id": "dog-a",
                        "source_dataset": "IDEXX",
                        "ingestion_cohort": "baseline_historico",
                        "sample_date": "2025-06-01",
                        "raw_location_text": "Boca Chica",
                        "location_source": "manual_override",
                        "location_confidence": 0.95,
                    },
                    {
                        "record_id": "r3",
                        "record_uuid": "r3",
                        "dog_id": "dog-b",
                        "source_dataset": "IDEXX",
                        "ingestion_cohort": "baseline_historico",
                        "sample_date": "2025-10-01",
                        "raw_location_text": "Boca Chica",
                        "location_source": "manual_override",
                        "location_confidence": 0.95,
                    },
                ]
            )
            metadata.to_csv(processed / "analysis_metadata.csv", index=False)
            pd.DataFrame([{"record_uuid": "r1", "WBC": 10.0}]).to_csv(
                processed / "train.csv", index=False
            )
            pd.DataFrame([{"record_uuid": "r2", "WBC": 11.0}]).to_csv(
                processed / "val.csv", index=False
            )
            pd.DataFrame([{"record_uuid": "r3", "WBC": 12.0}]).to_csv(
                processed / "test.csv", index=False
            )

            metadata_report = run_metadata_retention_gate(root)
            leakage_report = run_dog_leakage_gate(root)

        self.assertEqual(metadata_report["status"], "pass")
        self.assertEqual(leakage_report["status"], "fail")
        self.assertEqual(leakage_report["dogs_crossing_splits"], 1)


if __name__ == "__main__":
    unittest.main()
