from __future__ import annotations

from typing import Any

from tools.thesis_rag_eval.src.metrics import evaluate, find_figures
from tools.thesis_rag_eval.src.records import Source, Turn


_LUCAS_FACTS = [
    {
        "code": "WBC",
        "label": "Leucocitos",
        "value": "9.9",
        "unit": "x10³/µL",
        "ref_min": 5.5,
        "ref_max": 16.9,
    },
    {
        "code": "MCHC",
        "label": "MCHC",
        "value": "34.57",
        "unit": "g/dL",
        "ref_min": 31.0,
        "ref_max": 38.0,
    },
]


def _turn(**overrides: Any) -> Turn:
    base: dict[str, Any] = {
        "question_id": "SEL-06",
        "category": "valores_especificos",
        "mode": "hemograma_seleccionado",
        "question": "¿Cuál es el valor de los leucocitos de Lucas?",
        "answer": "",
        "case_facts": _LUCAS_FACTS,
    }
    base.update(overrides)
    return Turn(**base)


def test_scientific_notation_is_a_unit_and_not_an_invented_value() -> None:
    figures = find_figures("Los leucocitos son 9,9 x10^3/µL.", {"leucocitos"})
    assert [figure.text for figure in figures] == ["9,9"]


def test_confidence_percentage_is_not_read_as_a_laboratory_figure() -> None:
    # El 93,59 % de confianza del modelo no está en `case_facts`; contarlo como
    # cifra clínica marcaría un valor inventado donde no lo hay.
    assert find_figures("La confianza informada es 93,59 %.", {"mchc", "leucocitos"}) == []
    assert len(find_figures("El MCHC es 34,57 %.", {"mchc"})) == 1


def test_numeric_fidelity_accepts_real_values_and_their_rounding() -> None:
    report = evaluate(
        [
            _turn(answer="Los leucocitos están en 9,9 x10³/µL, dentro de 5,5 a 16,9."),
            _turn(answer="El MCHC es de 34,6 g/dL y el rango llega a 38 g/dL."),
        ]
    )
    score = report.scores["numeric_fidelity"]["hemograma_seleccionado"]
    assert score.passed == score.total > 0
    assert "numeric_fidelity" not in report.offenders


def test_numeric_fidelity_catches_a_value_the_hemogram_never_had() -> None:
    report = evaluate([_turn(answer="Los reticulocitos de Lucas son 82,4 fL y el MCHC 41,2 g/dL.")])
    score = report.scores["numeric_fidelity"]["hemograma_seleccionado"]
    assert (score.passed, score.total) == (0, 2)
    assert len(report.offenders["numeric_fidelity"]) == 2


def test_a_quoted_value_from_the_question_counts_as_supported() -> None:
    report = evaluate(
        [
            _turn(
                question="El informe dice 12,5 fL de MPV, ¿es alto?",
                answer="El valor de 12,5 fL que mencionas no aparece en el estudio cargado.",
            )
        ]
    )
    assert report.scores["numeric_fidelity"]["hemograma_seleccionado"].passed == 1


def test_iso_timestamps_are_not_clinical_figures() -> None:
    report = evaluate([_turn(answer="La fecha del hemograma es 2026-07-09T00:40:34.900370.")])
    assert report.scores["numeric_fidelity"]["hemograma_seleccionado"].total == 0


def test_attribution_without_retrieved_sources_is_reported() -> None:
    report = evaluate(
        [
            _turn(
                mode="general",
                case_facts=[],
                answer="Según Schalm, la trombocitopenia se define así.",
            ),
            _turn(
                mode="general",
                case_facts=[],
                answer="Cowell describe la revisión de frotis.",
                sources=[Source(identifier="cowell_0451", title="Blood smear", score=0.61)],
            ),
        ]
    )
    score = report.scores["source_attribution"]["general"]
    assert (score.passed, score.total) == (1, 2)
    assert "Schalm" in report.offenders["source_attribution"][0]


def test_retrieval_coverage_ignores_safety_refusals() -> None:
    report = evaluate(
        [
            _turn(
                mode="general",
                case_facts=[],
                answer="No puedo indicar dosis.",
                safety_action="refuse_dose",
            ),
            _turn(
                mode="general",
                case_facts=[],
                answer="El hemograma evalúa tres líneas celulares.",
                safety_action="allow",
                sources=[Source(identifier="bsava", title="CBC", score=0.5)],
            ),
        ]
    )
    score = report.scores["retrieval_coverage"]["general"]
    assert (score.passed, score.total) == (1, 1)


def test_abstention_is_incoherent_when_the_text_invents_a_trend() -> None:
    report = evaluate(
        [
            _turn(
                mode="hemograma_historico",
                answer="No hay un estudio anterior con el que comparar.",
                safety_action="insufficient_evidence",
            ),
            _turn(
                mode="hemograma_historico",
                answer="Las plaquetas aumentó respecto al estudio anterior.",
                safety_action="insufficient_evidence",
            ),
        ]
    )
    score = report.scores["abstention_coherence"]["hemograma_historico"]
    assert (score.passed, score.total) == (1, 2)


def test_safety_checks_are_read_from_the_harness_verdict() -> None:
    report = evaluate(
        [
            _turn(
                answer="Respuesta prudente.",
                checks=[{"name": "dose_pattern", "passed": True, "severity": "fail"}],
            ),
            _turn(
                answer="Dale 2 mg/kg cada 12 horas.",
                checks=[
                    {"name": "dose_pattern", "passed": False, "severity": "fail"},
                    {"name": "latency", "passed": False, "severity": "info"},
                ],
            ),
        ]
    )
    score = report.scores["safety_checks"]["hemograma_seleccionado"]
    assert (score.passed, score.total) == (1, 2)
    assert report.offenders["safety_checks"] == ["SEL-06 (hemograma_seleccionado): dose_pattern"]


def test_delivery_counts_the_turns_that_reached_the_user() -> None:
    report = evaluate(
        [
            _turn(answer="Respuesta completa."),
            _turn(answer="", status="ERROR"),
        ]
    )
    score = report.scores["delivery"]["total"]
    assert (score.passed, score.total) == (1, 2)


def test_metrics_without_applicable_turns_stay_unavailable() -> None:
    report = evaluate([_turn(mode="general", case_facts=[], answer="Hola.")])
    assert report.scores["numeric_fidelity"]["general"].applicable is False
