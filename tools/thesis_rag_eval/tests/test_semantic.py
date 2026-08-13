from __future__ import annotations

from pathlib import Path

import pytest

from tools.thesis_rag_eval.src import semantic
from tools.thesis_rag_eval.src.records import Source, Turn


def _fake_embedder(_model: str, _cache: Path):
    """Embebedor determinista: la respuesta se parece a su propia pregunta."""
    numpy = pytest.importorskip("numpy")

    def embed(texts):
        vectors = []
        for text in texts:
            marker = text.strip()[-1]
            vector = numpy.zeros(4, dtype="float32")
            vector[ord(marker) % 4] = 1.0
            vectors.append(vector)
        return numpy.asarray(vectors)

    return embed


def _turn(question: str, answer: str, **overrides) -> Turn:
    base = {
        "question_id": "GEN-01",
        "category": "identidad",
        "mode": "general",
        "question": question,
        "answer": answer,
        "safety_action": "allow",
    }
    base.update(overrides)
    return Turn(**base)


def test_relevance_leaves_the_mismatched_baseline_below_the_pair(monkeypatch) -> None:
    monkeypatch.setattr(semantic, "_load_embedder", _fake_embedder)
    turns = [
        _turn("¿Qué mide el hematocrito?A", "El hematocrito mide el volumen.A"),
        _turn("¿Qué son las plaquetas?B", "Las plaquetas participan en la coagulación.B"),
        _turn("¿Qué es la hemólisis?C", "La hemólisis es la ruptura de eritrocitos.C"),
    ]
    scores = semantic.measure_relevance(turns)
    assert scores["general"].own_mean == pytest.approx(1.0)
    assert scores["general"].mismatched_mean == pytest.approx(0.0)
    assert scores["general"].win_rate == pytest.approx(1.0)


def test_relevance_ignores_safety_refusals(monkeypatch) -> None:
    monkeypatch.setattr(semantic, "_load_embedder", _fake_embedder)
    turns = [
        _turn("¿Qué mide el hematocrito?A", "El hematocrito mide el volumen.A"),
        _turn("¿Qué mide el hematocrito?A", "El hematocrito mide el volumen.A"),
        _turn(
            "Dame una dosis de prednisona.A",
            "No puedo indicar dosis.B",
            safety_action="refuse_dose",
        ),
    ]
    assert semantic.measure_relevance(turns)["general"].turns == 2


def test_passage_windows_drop_the_front_matter(tmp_path: Path) -> None:
    document = tmp_path / "cowell_0451__hematology__smear.md"
    document.write_text(
        "---\ntitle: Blood smear\nlanguage: en\n---\n\n" + "palabra " * 200,
        encoding="utf-8",
    )
    windows = semantic._read_windows(
        tmp_path, Source(identifier="cowell_0451", title="", score=None)
    )
    assert windows and "title: Blood smear" not in windows[0]
    assert len(windows[0].split()) == 90


def test_grounding_calibration_needs_resolvable_passages(tmp_path: Path) -> None:
    turns = [
        _turn(
            "¿Cómo se evalúa un frotis?",
            "Se revisa el monocapa con objetivo de 10x y luego con 40x. " * 4,
            sources=[Source(identifier="inexistente", title="", score=0.5)],
        )
    ]
    with pytest.raises(semantic.EmbeddingUnavailableError, match="--knowledge-dir"):
        semantic.calibrate_grounding(turns, tmp_path)
