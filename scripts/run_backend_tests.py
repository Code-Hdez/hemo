"""Ejecuta la suite de backend y guarda resumen en outputs/backend_test_report.json."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run() -> dict:
    cmd = [
        sys.executable, "-m", "pytest", "backend/tests", "-q", "--tb=no",
    ]
    result = subprocess.run(
        cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""

    summary_line = ""
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if " passed" in stripped or " failed" in stripped or " error" in stripped:
            summary_line = stripped
            break

    passed = failed = errors = 0
    for token in summary_line.replace(",", " ").split():
        prev = summary_line.split(token, 1)[0].strip().split()
        if token == "passed" and prev:
            try: passed = int(prev[-1])
            except ValueError: pass
        if token == "failed" and prev:
            try: failed = int(prev[-1])
            except ValueError: pass
        if token in ("error", "errors") and prev:
            try: errors = int(prev[-1])
            except ValueError: pass

    payload = {
        "command": " ".join(cmd),
        "returncode": result.returncode,
        "summary_line": summary_line,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "stdout_tail": "\n".join(stdout.splitlines()[-40:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-20:]),
    }
    out = PROJECT_ROOT / "outputs" / "backend_test_report.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Reporte de pruebas guardado en {out}")
    print(summary_line)
    return payload


if __name__ == "__main__":
    run()
