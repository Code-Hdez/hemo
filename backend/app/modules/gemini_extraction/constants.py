"""Constants for hemogram extraction providers and canonical CBC fields."""

from __future__ import annotations

OPENROUTER_GEMMA_DEFAULT_MODEL = "google/gemma-4-31b-it:free"
OPENROUTER_NEMOTRON_DEFAULT_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"
OPENROUTER_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

# These are the raw CBC inputs consumed by the current runtime model artifacts.
MODEL_CBC_FIELDS: tuple[str, ...] = (
    "RBC",
    "WBC",
    "Platelets",
    "HGB",
    "HCT",
    "MCV",
    "MCH",
    "MCHC",
    "RDW",
    "Reticulocytes",
    "Reticulocytes_pct",
    "Neutrophils",
    "Neutrophils_pct",
    "Lymphocytes",
    "Lymphocytes_pct",
    "Monocytes",
    "Monocytes_pct",
    "Eosinophils",
    "Basophils",
    "MPV",
    "PDW",
)

MODEL_CBC_FIELD_SET = frozenset(MODEL_CBC_FIELDS)

EXTRACTION_PROMPT_FIELDS: tuple[str, ...] = (
    "RBC",
    "Hematocrit",
    "Hemoglobin",
    "MCV",
    "MCHC",
    "MCH",
    "RDW",
    "% Reticulocytes",
    "Reticulocytes",
    "WBC",
    "% Neutrophils",
    "% Lymphocytes",
    "% Monocytes",
    "Neutrophils",
    "Lymphocytes",
    "Monocytes",
    "Eosinophils",
    "Basophils",
    "Platelets",
    "PDW",
    "MPV",
)

PROMPT_TO_MODEL_KEY: dict[str, str] = {
    "Hemoglobin": "HGB",
    "Hematocrit": "HCT",
    "% Reticulocytes": "Reticulocytes_pct",
    "% Neutrophils": "Neutrophils_pct",
    "% Lymphocytes": "Lymphocytes_pct",
    "% Monocytes": "Monocytes_pct",
}

BASIC_NUMERIC_RANGES: dict[str, tuple[float, float]] = {
    "WBC": (0.1, 300.0),
    "RBC": (0.1, 15.0),
    "HGB": (1.0, 30.0),
    "HCT": (1.0, 80.0),
    "MCV": (30.0, 150.0),
    "MCH": (5.0, 60.0),
    "MCHC": (10.0, 50.0),
    "RDW": (1.0, 80.0),
    "Platelets": (1.0, 3000.0),
    "MPV": (1.0, 30.0),
    "PDW": (1.0, 80.0),
    "Reticulocytes": (0.0, 2000.0),
    "Reticulocytes_pct": (0.0, 100.0),
    "Neutrophils": (0.0, 250.0),
    "Neutrophils_pct": (0.0, 100.0),
    "Lymphocytes": (0.0, 250.0),
    "Lymphocytes_pct": (0.0, 100.0),
    "Monocytes": (0.0, 250.0),
    "Monocytes_pct": (0.0, 100.0),
    "Eosinophils": (0.0, 250.0),
    "Basophils": (0.0, 250.0),
}

IGNORED_LINE_MARKERS: tuple[str, ...] = (
    "curve",
    "threshold",
    "thresholds",
    "alarm",
    "alarms",
    "interpretive",
)
