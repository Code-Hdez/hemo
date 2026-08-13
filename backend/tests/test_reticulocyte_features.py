import unittest
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.ml.features import RAW_CBC_FIELDS, build_features  # noqa: E402


class ReticulocyteFeatureTests(unittest.TestCase):
    def test_runtime_contract_includes_reticulocytes(self):
        self.assertIn("Reticulocytes", RAW_CBC_FIELDS)
        self.assertIn("Reticulocytes_pct", RAW_CBC_FIELDS)

    def test_build_features_derives_reticulocyte_flags(self):
        feature_columns = [
            "Reticulocytes",
            "Reticulocytes_pct",
            "flag_reticulocytosis_pct_gt2",
            "flag_reticulocytopenia_abs_lt10",
            "flag_regen_anemia_proxy",
        ]
        row = build_features(
            {"HCT": 30, "Reticulocytes": 85, "Reticulocytes_pct": 5.3},
            feature_columns,
            {},
        )

        self.assertEqual(float(row["Reticulocytes"].iloc[0]), 85.0)
        self.assertEqual(float(row["Reticulocytes_pct"].iloc[0]), 5.3)
        self.assertEqual(float(row["flag_reticulocytosis_pct_gt2"].iloc[0]), 1.0)
        self.assertEqual(float(row["flag_reticulocytopenia_abs_lt10"].iloc[0]), 0.0)
        self.assertEqual(float(row["flag_regen_anemia_proxy"].iloc[0]), 1.0)

    def test_build_features_imputes_missing_reticulocytes(self):
        feature_columns = [
            "Reticulocytes",
            "Reticulocytes_pct",
            "flag_reticulocytosis_pct_gt2",
            "flag_regen_anemia_proxy",
        ]
        row = build_features(
            {"HCT": 42},
            feature_columns,
            {"Reticulocytes": 40.0, "Reticulocytes_pct": 0.8},
        )

        self.assertEqual(float(row["Reticulocytes"].iloc[0]), 40.0)
        self.assertEqual(float(row["Reticulocytes_pct"].iloc[0]), 0.8)
        self.assertEqual(float(row["flag_reticulocytosis_pct_gt2"].iloc[0]), 0.0)
        self.assertEqual(float(row["flag_regen_anemia_proxy"].iloc[0]), 0.0)


if __name__ == "__main__":
    unittest.main()
