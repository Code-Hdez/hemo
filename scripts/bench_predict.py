"""Benchmark de latencia de inferencia ML (sin HTTP).

Mide p50, p95 y p99 sobre N llamadas a predictor.predict() con un CBC canonico.

Salida: outputs/api_bench_predict.json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.modules.ml.predictor import load_resources, predict  # noqa: E402


BASELINE_CBC = {
    "RBC": 6.91, "WBC": 12.64, "Platelets": 338.0,
    "HGB": 17.3, "HCT": 49.2, "MCV": 71.7, "MCH": 25.2, "MCHC": 35.1,
    "RDW": 17.5,
    "Neutrophils": 8.45, "Neutrophils_pct": 69.3,
    "Lymphocytes": 1.9, "Lymphocytes_pct": 16.2,
    "Monocytes": 1.06, "Monocytes_pct": 8.6,
    "Eosinophils": 0.27, "Basophils": 0.01,
    "MPV": 11.3, "PDW": 14.2, "age_years": 5.0,
}


def percentile(data: list[float], pct: float) -> float:
    ordered = sorted(data)
    k = (len(ordered) - 1) * pct
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def run(n: int = 1000, warmup: int = 50) -> dict:
    resources = load_resources(PROJECT_ROOT)
    for _ in range(warmup):
        predict(cbc=dict(BASELINE_CBC), comments=None, resources=resources)

    latencies_ms: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        predict(cbc=dict(BASELINE_CBC), comments=None, resources=resources)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)

    payload = {
        "component": "inference.predictor.predict",
        "note": "Latencia in-process del motor ML. Excluye HTTP, auth, DB y RAG.",
        "model_version": resources.model_metadata.get("version", "unknown"),
        "n_requests": n,
        "warmup": warmup,
        "latency_ms": {
            "min": round(min(latencies_ms), 2),
            "p50": round(percentile(latencies_ms, 0.50), 2),
            "p95": round(percentile(latencies_ms, 0.95), 2),
            "p99": round(percentile(latencies_ms, 0.99), 2),
            "max": round(max(latencies_ms), 2),
            "mean": round(statistics.fmean(latencies_ms), 2),
            "stdev": round(statistics.pstdev(latencies_ms), 2),
        },
    }
    out = PROJECT_ROOT / "outputs" / "api_bench_predict.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Bench guardado en {out}")
    return payload


if __name__ == "__main__":
    run()
