from __future__ import annotations

from app.modules.llm_chat.claim_validation import contains_english_passage


def test_contains_english_passage_detects_consecutive_english_words() -> None:
    assert contains_english_passage(
        "Thrombocytopenia is a reduction in platelet count below the reference interval."
    )


def test_contains_english_passage_ignores_short_spanish_text() -> None:
    assert not contains_english_passage(
        "La trombocitopenia es un recuento de plaquetas por debajo del rango esperado."
    )


def test_contains_english_passage_ignores_acronyms_in_spanish() -> None:
    assert not contains_english_passage(
        "El hallazgo PATRON_HEMOLISIS_MCHC sugiere revisar la calidad del frotis."
    )
