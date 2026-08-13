"""Orquesta la generacion de todos los artefactos de evidencia para 4.3 en adelante.

Ejecuta en orden:
  1. e2e_demo_run.py            -> outputs/e2e_demo_run.json
  2. bench_predict.py           -> outputs/api_bench_predict.json
  3. llm_guardrails_eval.py     -> outputs/llm_guardrails_eval.json
  4. run_backend_tests.py       -> outputs/backend_test_report.json
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "scripts/e2e_demo_run.py",
    "scripts/bench_predict.py",
    "scripts/llm_guardrails_eval.py",
    "scripts/run_backend_tests.py",
]


def main() -> int:
    for rel in SCRIPTS:
        print(f"--- {rel}")
        result = subprocess.run(
            [sys.executable, rel], cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            print(f"FALLO {rel}", file=sys.stderr)
            return result.returncode
    print("Artefactos generados en outputs/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
