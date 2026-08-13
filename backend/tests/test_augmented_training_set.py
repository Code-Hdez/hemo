from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_augmented_training_set import (  # noqa: E402
    build_engineered_features,
    label_record,
    split_by_dog_id,
)


class AugmentedTrainingSetTests(unittest.TestCase):
    def test_label_record_extracts_known_idexx_patterns(self) -> None:
        labels = [
            "QC_REQUIERE_FROTIS",
            "PATRON_INFLAMATORIO",
            "PATRON_LEUCOGRAMA_ESTRES",
        ]

        result = label_record(
            "Confirmar con revision de frotis. Considere la inflamacion.",
            labels,
        )

        self.assertEqual(result["QC_REQUIERE_FROTIS"], 1)
        self.assertEqual(result["PATRON_INFLAMATORIO"], 1)
        self.assertEqual(result["PATRON_LEUCOGRAMA_ESTRES"], 0)

    def test_build_engineered_features_matches_notebook_feature_contract(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "RBC": 5.0,
                    "WBC": 18.0,
                    "Platelets": 80.0,
                    "HGB": 10.0,
                    "HCT": 30.0,
                    "MCV": 60.0,
                    "MCH": 20.0,
                    "MCHC": 30.0,
                    "RDW": 15.0,
                    "Neutrophils": 12.0,
                    "Neutrophils_pct": 80.0,
                    "Lymphocytes": 0.5,
                    "Lymphocytes_pct": 3.0,
                    "Monocytes": 1.0,
                    "Monocytes_pct": 6.0,
                    "Eosinophils": 0.1,
                    "Basophils": 0.0,
                    "MPV": 13.0,
                    "PDW": 12.0,
                    "age_years": 4.0,
                }
            ]
        )

        out = build_engineered_features(df)

        self.assertEqual(int(out.loc[0, "flag_thrombocytopenia_severe"]), 1)
        self.assertEqual(int(out.loc[0, "flag_anemia"]), 1)
        self.assertEqual(int(out.loc[0, "pattern_stress_leukogram"]), 1)
        self.assertGreater(float(out.loc[0, "ratio_NLR"]), 20.0)

    def test_split_by_dog_id_keeps_groups_exclusive(self) -> None:
        rows = []
        for i in range(40):
            rows.append(
                {
                    "record_uuid": f"r{i}",
                    "dog_id": f"dog-{i // 2}",
                    "L1": 1 if i % 5 == 0 else 0,
                    "L2": 1 if i % 7 == 0 else 0,
                }
            )
        df = pd.DataFrame(rows)

        split = split_by_dog_id(
            df, ["L1", "L2"], train_frac=0.70, val_frac=0.15, seed=7
        )

        dog_split_counts = split.groupby("dog_id")["split"].nunique()
        self.assertEqual(int((dog_split_counts > 1).sum()), 0)
        self.assertEqual(set(split["split"]), {"train", "val", "test"})
        self.assertLess(abs((split["split"].eq("train").mean()) - 0.70), 0.15)


if __name__ == "__main__":
    unittest.main()
