from __future__ import annotations

from tools.llm_cbc_eval.src.select_sample import select_stratified


def _question(identifier: int, category: str, modes: list[str]) -> dict[str, object]:
    return {
        "id": identifier,
        "categoria": category,
        "pregunta": f"Pregunta {identifier}",
        "modos_aplicables": modes,
    }


def test_selection_is_stratified_reproducible_and_general_only() -> None:
    questions = [
        *[_question(index, "a", ["informacion_general"]) for index in range(1, 7)],
        *[_question(index, "b", ["informacion_general"]) for index in range(7, 11)],
        _question(11, "c", ["hemograma_seleccionado"]),
    ]

    selected_a, counts_a = select_stratified(
        questions,
        mode="informacion_general",
        sample_size=5,
        seed="release-sha",
    )
    selected_b, counts_b = select_stratified(
        questions,
        mode="informacion_general",
        sample_size=5,
        seed="release-sha",
    )

    assert [item["id"] for item in selected_a] == [item["id"] for item in selected_b]
    assert 11 not in [item["id"] for item in selected_a]
    assert counts_a == counts_b == {
        "a": {"eligible": 6, "selected": 3},
        "b": {"eligible": 4, "selected": 2},
    }


def test_selection_rejects_more_than_eligible_questions() -> None:
    questions = [_question(1, "a", ["informacion_general"])]

    try:
        select_stratified(
            questions,
            mode="informacion_general",
            sample_size=2,
            seed="seed",
        )
    except ValueError as exc:
        assert "excede" in str(exc)
    else:
        raise AssertionError("La muestra inválida debió rechazarse.")
