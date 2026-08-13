"""Ejecuta los 4 casos de prueba de la sección 2.6.2 y guarda evidencia.

Salida: outputs/e2e_demo_run.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.modules.ml.predictor import load_resources, predict  # noqa: E402


CASES = [
    {
        "id": "A",
        "titulo": "Trombocitopenia inflamatoria",
        "esperado": ["QC_REQUIERE_FROTIS", "PATRON_INFLAMATORIO"],
        "cbc": {
            "RBC": 6.0, "WBC": 19.0, "Platelets": 55.0,
            "HGB": 14.5, "HCT": 42.0, "MCV": 68.0, "MCH": 23.9, "MCHC": 35.2,
            "RDW": 22.0,
            "Neutrophils": 13.0, "Neutrophils_pct": 68.4,
            "Lymphocytes": 3.0, "Lymphocytes_pct": 15.8,
            "Monocytes": 1.5, "Monocytes_pct": 7.9,
            "Eosinophils": 0.8, "Basophils": 0.02,
            "MPV": 14.2, "PDW": 17.5, "age_years": 5.0,
        },
        "comentarios_idexx": "Platelet count decreased. Review smear. Band cells present.",
    },
    {
        "id": "B",
        "titulo": "Leucograma de estres",
        "esperado": ["PATRON_LEUCOGRAMA_ESTRES"],
        "cbc": {
            "RBC": 7.0, "WBC": 15.0, "Platelets": 320.0,
            "HGB": 17.0, "HCT": 49.0, "MCV": 71.0, "MCH": 25.0, "MCHC": 35.0,
            "RDW": 16.8,
            "Neutrophils": 12.0, "Neutrophils_pct": 80.0,
            "Lymphocytes": 0.6, "Lymphocytes_pct": 4.0,
            "Monocytes": 2.2, "Monocytes_pct": 14.7,
            "Eosinophils": 0.08, "Basophils": 0.01,
            "MPV": 10.5, "PDW": 13.2, "age_years": 6.0,
        },
        "comentarios_idexx": "",
    },
    {
        "id": "C",
        "titulo": "Anemia no regenerativa (HCT 28%, HGB 9.2, normocitica normocromica)",
        "esperado": ["PATRON_ANEMIA_NO_REGENERATIVA"],
        "cbc": {
            "RBC": 4.2, "WBC": 9.5, "Platelets": 280.0,
            "HGB": 9.2, "HCT": 28.0, "MCV": 68.5, "MCH": 22.5, "MCHC": 34.5,
            "RDW": 15.8,
            "Neutrophils": 6.2, "Neutrophils_pct": 65.3,
            "Lymphocytes": 2.2, "Lymphocytes_pct": 23.1,
            "Monocytes": 0.8, "Monocytes_pct": 8.4,
            "Eosinophils": 0.25, "Basophils": 0.01,
            "MPV": 11.2, "PDW": 14.1, "age_years": 9.0,
        },
        "comentarios_idexx": "",
    },
    {
        "id": "D",
        "titulo": "Artefacto MCHC (53 g/dL) + agregados plaquetarios (regla Modulo 2)",
        "esperado": [
            "QC_AGREGADOS_PLAQUETARIOS (regla Modulo 2)",
            "PATRON_HEMOLISIS_MCHC suprimido por politica de artefacto",
        ],
        "cbc": {
            "RBC": 6.8, "WBC": 10.2, "Platelets": 120.0,
            "HGB": 16.9, "HCT": 32.0, "MCV": 70.0, "MCH": 24.8, "MCHC": 53.0,
            "RDW": 17.9,
            "Neutrophils": 7.1, "Neutrophils_pct": 69.6,
            "Lymphocytes": 1.9, "Lymphocytes_pct": 18.6,
            "Monocytes": 0.9, "Monocytes_pct": 8.8,
            "Eosinophils": 0.3, "Basophils": 0.02,
            "MPV": 11.9, "PDW": 14.8, "age_years": 4.0,
        },
        "comentarios_idexx": "Platelet aggregates detected. Recuento plaquetas mayor al reportado.",
    },
]


def _active_labels(result) -> list[dict]:
    active = []
    for label, prob in result.probabilities.items():
        if result.predictions.get(label):
            active.append({"label": label, "prob": round(prob, 4), "source": "model"})
    for rule_label in ("QC_AGREGADOS_PLAQUETARIOS", "QC_INTERFERENCIA_GR"):
        if result.predictions.get(rule_label):
            active.append({"label": rule_label, "prob": None, "source": "rule_module2"})
    return active


def run() -> dict:
    resources = load_resources(PROJECT_ROOT)
    runs = []
    for case in CASES:
        started = time.perf_counter()
        result = predict(
            cbc=case["cbc"],
            comments=case["comentarios_idexx"] or None,
            resources=resources,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        runs.append({
            "id": case["id"],
            "titulo": case["titulo"],
            "esperado": case["esperado"],
            "activas": _active_labels(result),
            "probabilidades_modelo": {k: round(v, 4) for k, v in result.probabilities.items()},
            "umbral_por_etiqueta_activa": {
                label: round(resources.thresholds.get(label, 0.5), 4)
                for label in result.probabilities
                if result.predictions.get(label)
            },
            "status": result.status,
            "latency_ms": round(latency_ms, 2),
            "mchc_input": case["cbc"]["MCHC"],
            "mchc_hemolysis_suppressed": case["cbc"]["MCHC"] > 50.0,
        })
    payload = {
        "model_version": resources.model_metadata.get("version", "unknown"),
        "policy_version": resources.label_policy.get("version", "unknown"),
        "n_cases": len(runs),
        "cases": runs,
    }
    out = PROJECT_ROOT / "outputs" / "e2e_demo_run.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evidencia E2E guardada en {out}")
    return payload


if __name__ == "__main__":
    run()
