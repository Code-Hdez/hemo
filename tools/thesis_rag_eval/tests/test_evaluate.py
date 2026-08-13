from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.thesis_rag_eval.src import evaluate as cli


def _write_answers(path: Path) -> None:
    records = [
        {
            "run_id": "eval-20260710T151552Z",
            "question_id": "SEL-06",
            "modo": "hemograma_seleccionado",
            "pregunta": "¿Cuál es el valor de los leucocitos de Lucas?",
            "answer": "Los leucocitos de Lucas son 9,9 x10³/µL, dentro del rango.",
            "case_facts": [{"code": "WBC", "label": "Leucocitos", "value": "9.9"}],
            "safety_action": "allow",
            "status": "PASS",
        },
        {
            "run_id": "eval-20260709T030704Z",
            "question_id": "SEL-12",
            "modo": "hemograma_seleccionado",
            "pregunta": "¿Cuál es el valor de reticulocitos de Lucas?",
            "answer": "Los reticulocitos son 78,4 fL.",
            "case_facts": [{"code": "WBC", "label": "Leucocitos", "value": "9.9"}],
            "safety_action": "allow",
            "status": "PASS",
        },
    ]
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )


def test_cli_writes_the_report_for_the_requested_run(tmp_path: Path, monkeypatch) -> None:
    answers = tmp_path / "respuestas.jsonl"
    output = tmp_path / "informe.md"
    _write_answers(answers)
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate.py", "--answers", str(answers), "--output", str(output), "--run", "last"],
    )
    assert cli.main() == 0
    content = output.read_text(encoding="utf-8")
    assert "eval-20260710T151552Z" in content
    assert "| Fidelidad numérica | n/d | 100,0 % (1/1) | n/d | 100,0 % (1/1) |" in content


def test_cli_rejects_a_missing_answers_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["evaluate.py", "--answers", str(tmp_path / "no_existe.jsonl"), "--output", "x.md"],
    )
    with pytest.raises(SystemExit):
        cli.main()
