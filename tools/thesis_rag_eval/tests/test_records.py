from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.thesis_rag_eval.src.records import (
    build_turn,
    latest_run_id,
    load_turns,
    normalize_mode,
    parse_number,
)


def test_normalize_mode_maps_harness_backend_and_manual_names() -> None:
    assert normalize_mode("informacion_general") == "general"
    assert normalize_mode("uploaded_analysis") == "hemograma_seleccionado"
    assert normalize_mode("hemogram_history") == "hemograma_historico"
    assert normalize_mode("otra_cosa") is None


def test_build_turn_accepts_a_minimal_manual_capture() -> None:
    turn = build_turn(
        {
            "id": "SEL-06",
            "mode": "selected_hemogram",
            "pregunta": "¿Cuál es el valor de los leucocitos?",
            "respuesta": "WBC 9,9 ×10³/µL, dentro del rango.",
            "fuentes": ["schalm"],
        }
    )
    assert turn is not None
    assert turn.mode == "hemograma_seleccionado"
    assert turn.question_id == "SEL-06"
    assert turn.sources[0].identifier == "schalm"
    assert turn.delivered is True


def test_build_turn_discards_records_without_a_known_mode() -> None:
    assert build_turn({"modo": "modo_inventado", "answer": "hola"}) is None


def test_load_turns_filters_by_run_and_reports_the_broken_line(tmp_path: Path) -> None:
    path = tmp_path / "respuestas.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"run_id": "eval-A", "modo": "general", "answer": "a"}),
                "",
                json.dumps({"run_id": "eval-B", "modo": "general", "answer": "b"}),
            ]
        ),
        encoding="utf-8",
    )
    assert [turn.answer for turn in load_turns([path], run_id="eval-B")] == ["b"]
    assert latest_run_id([path]) == "eval-B"

    path.write_text("{no es json}", encoding="utf-8")
    with pytest.raises(ValueError, match="línea 1"):
        load_turns([path])


def test_parse_number_reads_the_clinical_comma() -> None:
    assert parse_number("34,57") == pytest.approx(34.57)
    assert parse_number(None) is None
    assert parse_number("normal") is None
