from __future__ import annotations

from pathlib import Path

from tools.thesis_rag_eval.src.metrics import evaluate
from tools.thesis_rag_eval.src.records import Source, Turn
from tools.thesis_rag_eval.src.report import render_markdown
from tools.thesis_rag_eval.src.semantic import GroundingCalibration, RelevanceScore


def _turns() -> list[Turn]:
    return [
        Turn(
            question_id="GEN-06",
            category="interpretacion_general",
            mode="general",
            question="¿Qué información aporta un hemograma canino?",
            answer="Evalúa eritrograma, leucograma y plaquetas.",
            sources=[Source(identifier="bsava_0120", title="CBC", score=0.62)],
            safety_action="allow",
        ),
        Turn(
            question_id="HIS-02",
            category="seguimiento_comparacion",
            mode="hemograma_historico",
            question="Compara este hemograma con el anterior.",
            answer="No hay un estudio anterior con el que comparar.",
            safety_action="insufficient_evidence",
        ),
    ]


def test_markdown_has_one_column_per_context_mode_and_spanish_decimals() -> None:
    turns = _turns()
    content = render_markdown(turns, evaluate(turns), sources=[Path("respuestas.jsonl")])
    assert "| Métrica | General | Hemograma seleccionado | Historial | Total |" in content
    assert "| Cobertura de recuperación | 100,0 % (1/1) |" in content
    # El modo sin turnos aplicables no puede quedar como 0 %: eso se leería como
    # un fallo del asistente y no como una métrica que ahí no aplica.
    assert "| Fidelidad numérica | n/d | n/d | n/d | n/d |" in content
    assert "## Métricas que quedan fuera y por qué" in content


def test_markdown_publishes_the_grounding_calibration_verdict() -> None:
    turns = _turns()
    content = render_markdown(
        turns,
        evaluate(turns),
        sources=[Path("respuestas.jsonl")],
        relevance={
            "total": RelevanceScore(turns=2, own_mean=0.66, mismatched_mean=0.38, win_rate=0.95)
        },
        grounding=GroundingCalibration(turns=60, own_mean=0.466, rival_mean=0.412, win_rate=0.53),
    )
    assert "| Total | 2 | 0,660 | 0,380 | 95,0 % |" in content
    assert "no es utilizable como métrica" in content
