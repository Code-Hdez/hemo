"""What a claim may call the analyte it cites.

Two checks gate every claim that carries fact_ids: it must *anchor* the fact
(name it, or reproduce its value or date) and — for the strict claim types — it
must be a *materialized projection* of that fact's own vocabulary. Both read
their vocabulary from the fact dict, whose names are whatever the laboratory
report happened to print: `original_name`, `display_name`, and the stable code.

That is not the vocabulary a Spanish speaker uses. Measured against production
on 2026-08-06, on Nala's hemogram whose WBC row is labelled "WBC":

    "Explícame el valor de los leucocitos."
      → structured_fact_claim_mismatch, repair failed the same way,
        HTTP 502 after 73 s

The word "leucocitos" is the ordinary name of that analyte and the project
already knows it — `PARAMETER_ALIASES` in clinical_code_registry.py, the same
list the *question* side uses to work out which parameter the user asked about.
Only the answer side did not consult it, so the two halves of the pipeline
disagreed about what the analyte is called.
"""

from __future__ import annotations

import pytest

from app.modules.llm_chat.application.use_cases.send_chat_message import (
    _patient_claim_links_cited_facts,
    _patient_fact_is_materialized_projection,
)


def _wbc_fact(display_name: str = "WBC") -> dict[str, object]:
    """A WBC row as PostgreSQL hands it over.

    ``display_name`` is the knob that matters: a report that printed "WBC"
    leaves the fact with no Spanish name at all, which is the production case.
    """

    return {
        "fact_id": "fact_wbc",
        "fact_type": "lab_value",
        "code": "WBC",
        "canonical_name": "WBC",
        "display_name": display_name,
        "label": display_name,
        "aliases": [display_name],
        "value": "10.4",
        "value_text": "10.4",
        "unit": "×10³/µL",
        "reference_min": "5.5",
        "reference_max": "16.9",
        "reference_low": "5.5",
        "reference_high": "16.9",
        "status": "normal",
        "flag": "normal",
        "analysis_date": "2026-08-06",
    }


# Every one of these states exactly the recorded value, in the words a Spanish
# speaker uses for it.
NATURAL_WBC_CLAIMS = (
    "Los leucocitos son normales.",
    "Los glóbulos blancos se encuentran dentro del rango de referencia.",
    "El recuento de glóbulos blancos es normal, en 10.4 ×10³/µL.",
    "El recuento de leucocitos es de 10.4 ×10³/µL y está dentro del rango.",
    "Los leucocitos están en 10.4, un valor normal.",
    # The flat register the contract used to force. It must keep working.
    "WBC: 10.4 ×10³/µL, rango 5.5 a 16.9, estado normal.",
)


@pytest.mark.parametrize("text", NATURAL_WBC_CLAIMS)
@pytest.mark.parametrize("display_name", ["WBC", "Leucocitos"])
def test_a_claim_may_name_the_analyte_the_way_people_do(
    text: str, display_name: str
) -> None:
    """And the verdict must not depend on what the lab report printed.

    Parametrizing over ``display_name`` is the point: before this, the same
    sentence passed or failed depending on whether the laboratory happened to
    label the row in Spanish. That made the failure look intermittent.
    """

    fact = _wbc_fact(display_name)

    assert _patient_claim_links_cited_facts(text, [fact]), text
    assert _patient_fact_is_materialized_projection(
        text, [fact], authorized_facts=[fact]
    ), text


def test_naming_a_different_analyte_still_fails_to_anchor() -> None:
    """The check exists so a model cannot attach the WBC id to another row."""

    assert not _patient_claim_links_cited_facts(
        "Las plaquetas están dentro del rango.", [_wbc_fact()]
    )


def test_saying_nothing_about_the_analyte_still_fails_to_anchor() -> None:
    assert not _patient_claim_links_cited_facts(
        "El hemograma se ve bien en general.", [_wbc_fact()]
    )


@pytest.mark.parametrize(
    "text",
    [
        # A figure the fact does not carry.
        "Los leucocitos están en 12.7 ×10³/µL.",
        # A range the fact does not carry.
        "Los leucocitos están en 10.4, con rango de 4.0 a 12.0.",
        # Interpretation attached to a measurement.
        "Los leucocitos indican una infección.",
    ],
)
def test_widening_the_names_does_not_widen_the_numbers(text: str) -> None:
    """The relaxation is about what the analyte is called, nothing else.

    Every measurement a claim states must still come from the fact it cites —
    which is the property the whole structured contract exists to hold, and the
    reason the output validation is not removed the way socratic-tutor removed
    theirs (analysis §4.4).
    """

    fact = _wbc_fact()

    assert not _patient_fact_is_materialized_projection(
        text, [fact], authorized_facts=[fact]
    ), text


def test_the_two_checks_agree_with_the_question_side_registry() -> None:
    """Answer and question must resolve the same words to the same analyte.

    They disagreed: `mentioned_parameter_codes` recognized "glóbulos blancos"
    as WBC while the claim validators did not, so the pipeline could select a
    fact for a question it then refused to let the answer name.
    """

    from app.modules.llm_chat.application.services.clinical_code_registry import (
        mentioned_parameter_codes,
    )

    fact = _wbc_fact()
    for phrase in ("leucocitos", "glóbulos blancos"):
        question = f"¿Cómo están los {phrase}?"
        assert "WBC" in mentioned_parameter_codes(question), phrase
        assert _patient_claim_links_cited_facts(
            f"Los {phrase} están dentro del rango.", [fact]
        ), phrase


# --------------------------------------------------------------------------
# El estado registrado, en el idioma que lo escribiera el laboratorio
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stored_status", "claim"),
    [
        ("normal", "Los leucocitos son normales."),
        ("NORMAL", "Los leucocitos son normales."),
        ("high", "Los leucocitos están altos."),
        ("high", "Los leucocitos están elevados."),
        ("alto", "Los leucocitos están altos."),
        ("Alto", "Los leucocitos están altos."),
        ("ELEVADO", "Los leucocitos están elevados."),
        ("low", "Los leucocitos están bajos."),
        ("low", "Los leucocitos están disminuidos."),
        ("bajo", "Los leucocitos están bajos."),
    ],
)
def test_the_status_is_readable_however_the_laboratory_wrote_it(
    stored_status: str, claim: str
) -> None:
    """Same defect as the parameter names, one field over.

    The status keys are internal English names. A report writes "alto" or
    "Alto" and the extraction stores what it read, so a Spanish-stored status
    mapped to no tokens at all and the claim could not state the very status it
    was reporting — "los leucocitos están altos" rejected as unmaterialized on
    a row whose recorded status *is* alto.
    """

    fact = {**_wbc_fact(), "status": stored_status, "flag": stored_status}

    assert _patient_fact_is_materialized_projection(
        claim, [fact], authorized_facts=[fact]
    ), f"{stored_status}: {claim}"


def test_a_status_the_fact_does_not_record_is_still_refused() -> None:
    """Reading the label in any language is not the same as inventing one."""

    fact = {**_wbc_fact(), "status": "normal", "flag": "normal"}

    assert not _patient_fact_is_materialized_projection(
        "Los leucocitos están muy elevados.", [fact], authorized_facts=[fact]
    )
