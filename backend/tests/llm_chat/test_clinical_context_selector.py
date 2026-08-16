from __future__ import annotations

from decimal import Decimal

from app.modules.llm_chat.application.services.clinical_context_selector import (
    ClinicalContextSelector,
)
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    HemogramParameter,
    HemogramStudy,
    ResolvedQuestion,
)
from app.modules.llm_chat.domain.value_objects import FunctionalIntent


def _parameter(
    code: str,
    value: str,
    low: str,
    high: str,
    *,
    unit: str = "×10⁹/L",
) -> HemogramParameter:
    number = Decimal(value)
    minimum = Decimal(low)
    maximum = Decimal(high)
    flag = "high" if number > maximum else "low" if number < minimum else "normal"
    return HemogramParameter(
        canonical_name=code,
        display_name=code,
        original_name=code,
        value=number,
        value_text=value,
        unit=unit,
        reference_min=minimum,
        reference_max=maximum,
        flag=flag,
    )


def _study(key: str, date: str, *, wbc: str = "10.4") -> HemogramStudy:
    return HemogramStudy(
        analysis_id=f"analysis-{key}",
        study_key=key,
        date=date,
        label="Hemograma",
        laboratory=None,
        parameters=(
            _parameter("WBC", wbc, "6", "17"),
            _parameter("NEU", "12", "3", "11"),
            _parameter("LYM", "2.5", "1", "5"),
            _parameter("RBC", "7", "5", "8"),
            _parameter("HGB", "14", "12", "18", unit="g/dL"),
            _parameter("HCT", "42", "37", "55", unit="%"),
            _parameter("PLT", "90", "150", "500", unit="K/µL"),
            _parameter("MPV", "10", "7", "13", unit="fL"),
        ),
    )


def _question(text: str, parameter: str | None = None) -> ResolvedQuestion:
    return ResolvedQuestion(
        original=text,
        standalone=text,
        is_follow_up=False,
        referenced_parameter=parameter,
    )


def test_point_question_selects_only_the_requested_parameter() -> None:
    study = _study("H1", "2026-07-15")
    selection = ClinicalContextSelector().select(
        question=_question("¿Acaso los leucocitos están altos?", "WBC"),
        clinical=ClinicalContext(
            mode="selected_hemogram", selected=study, history=(study,)
        ),
    )

    assert selection.parameter_codes == frozenset({"WBC"})
    assert selection.detection.intent is FunctionalIntent.VALUE_CLASSIFICATION


_PANEL = frozenset({"WBC", "NEU", "LYM", "RBC", "HGB", "HCT", "PLT", "MPV"})
_ABNORMAL = frozenset({"NEU", "PLT"})


def test_vet_questions_see_the_whole_authorized_panel_not_only_the_abnormal_head() -> (
    None
):
    """A broad clinical question receives every authorized parameter.

    This used to assert ``frozenset({"NEU", "PLT"})``: the abnormal head only,
    four codes at most, chosen when the deployed model was a 4B with a 4096
    token context. That is the behavior the thesis review found unacceptable —
    the assistant discussed a study it had been shown a fraction of, and could
    not say which values came back normal because it had never seen them.
    Breadth is now bounded by the token budget (CHAT_CONTEXT_PARAMETER_LIMIT
    plus ClinicalContextSelector.limit_for_budget), not by a literal.
    """

    study = _study("H1", "2026-07-15")
    selection = ClinicalContextSelector().select(
        question=_question("¿Qué preguntas puedo hacerle a mi veterinario?"),
        clinical=ClinicalContext(
            mode="selected_hemogram", selected=study, history=(study,)
        ),
    )

    assert selection.detection.intent is FunctionalIntent.VET_QUESTIONS
    assert selection.parameter_codes == _PANEL
    # Still not the same thing as an explicit whole-study request: that one
    # alone materializes every study, not just every parameter of this turn.
    assert selection.is_complete_summary is False


def test_narrow_budget_falls_back_to_the_salient_head_instead_of_failing() -> None:
    """A deployment too small for the full panel degrades, never errors.

    The clinical block cannot be shrunk by PromptBuilder's reduction loop, so
    proposing more parameters than the budget holds fails the turn with
    context_budget_exceeded. Below the fit threshold the selector returns the
    previous narrow selection instead.
    """

    study = _study("H1", "2026-07-15")
    selector = ClinicalContextSelector()
    narrow = selector.limit_for_budget(input_budget=2000, tokens_per_parameter=96)
    wide = selector.limit_for_budget(input_budget=60000, tokens_per_parameter=96)

    assert narrow == 4
    assert wide == selector.parameter_limit

    selection = selector.select(
        question=_question("¿Qué preguntas puedo hacerle a mi veterinario?"),
        clinical=ClinicalContext(
            mode="selected_hemogram", selected=study, history=(study,)
        ),
        parameter_limit=narrow,
    )

    assert len(selection.parameter_codes) == 4
    # The abnormal values are what a truncated prompt must never lose.
    assert _ABNORMAL <= selection.parameter_codes


def test_pattern_selects_related_series_and_full_summary_is_explicit_only() -> None:
    study = _study("H1", "2026-07-15")
    clinical = ClinicalContext(
        mode="selected_hemogram", selected=study, history=(study,)
    )

    pattern = ClinicalContextSelector().select(
        question=_question("¿Hay un patrón hematológico en este hemograma?"),
        clinical=clinical,
    )
    complete = ClinicalContextSelector().select(
        question=_question("Dame un resumen completo del hemograma"),
        clinical=clinical,
    )

    assert pattern.detection.intent is FunctionalIntent.HEMATOLOGIC_PATTERN
    # A pattern is read against the values that stayed normal too, so the
    # panel travels; the abnormal components still lead the ordering so a
    # truncating budget keeps them.
    assert pattern.parameter_codes == _PANEL
    assert complete.detection.intent is FunctionalIntent.FULL_HEMOGRAM_SUMMARY
    assert complete.parameter_codes is None


def test_history_question_without_a_detected_change_still_carries_values() -> None:
    """Regression: "¿qué cambió entre los estudios?" materialized zero facts.

    ``_changed_codes`` returns nothing for a single study, for studies whose
    units were reported differently, and for a history where no value moved.
    That empty list used to pass straight through, so production logged
    ``materialized_fact_count: 0`` and the model was asked to compare studies
    while holding no value at all — which is why that turn could only answer
    with a limitation.
    """

    only = _study("H1", "2026-07-15")
    selection = ClinicalContextSelector().select(
        question=_question("¿Qué cambió entre los estudios?"),
        clinical=ClinicalContext(mode="hemogram_history", history=(only,)),
    )

    assert selection.parameter_codes
    assert _ABNORMAL <= selection.parameter_codes


def test_history_comparison_requires_two_compatible_studies() -> None:
    only = _study("H1", "2026-07-15")
    insufficient = ClinicalContextSelector().select(
        question=_question("¿Qué cambió en los leucocitos?", "WBC"),
        clinical=ClinicalContext(mode="hemogram_history", history=(only,)),
    )
    enough = ClinicalContextSelector().select(
        question=_question("¿Qué cambió en los leucocitos?", "WBC"),
        clinical=ClinicalContext(
            mode="hemogram_history",
            history=(only, _study("H2", "2026-07-17", wbc="12.1")),
        ),
    )

    assert insufficient.history_sufficient is False
    assert enough.history_sufficient is True


def test_bare_differential_reference_uses_percentage_when_absolute_is_absent() -> None:
    study = HemogramStudy(
        analysis_id="analysis-H1",
        study_key="H1",
        date="2026-07-15",
        label="Hemograma",
        laboratory=None,
        parameters=(_parameter("NEU_PCT", "80", "40", "75", unit="%"),),
    )

    selection = ClinicalContextSelector().select(
        question=_question("¿Los neutrófilos están altos?"),
        clinical=ClinicalContext(
            mode="selected_hemogram",
            selected=study,
            history=(study,),
        ),
    )

    assert selection.parameter_codes == frozenset({"NEU_PCT"})


# ── La metrica que el Bloque G.2 exige y no existia ─────────────────────────


def _selector_para_prueba():
    from app.modules.llm_chat.application.services.clinical_context_selector import (
        ClinicalContextSelector,
    )

    return ClinicalContextSelector()


def test_el_selector_declara_cuando_la_pregunta_pide_un_parametro_ausente() -> None:
    """`_resolve_available_parameter` devuelve el codigo AUNQUE no este presente.

    Su ultima linea es `return code`, asi que el turno sigue con un parametro
    «seleccionado» y `filter_facts` devuelve lista vacia. La regla de decision
    del Bloque G.2 revierte el cambio si eso pasa en mas del 2 % de los turnos,
    y hasta ahora no dejaba ningun rastro que contar.
    """
    from app.modules.llm_chat.application.services.clinical_context_selector import (
        ClinicalContextSelection,
    )

    # El campo es aditivo y con valor por defecto: los constructores que ya
    # existian siguen siendo validos.
    sin_ausencia = ClinicalContextSelection(None, frozenset({"HCT"}), True)
    assert sin_ausencia.parametro_pedido_ausente is None

    con_ausencia = ClinicalContextSelection(None, frozenset({"EOS"}), True, "EOS")
    assert con_ausencia.parametro_pedido_ausente == "EOS"


def test_el_parametro_ausente_deja_la_seleccion_sin_hechos() -> None:
    """La consecuencia que hace util la metrica: cero hechos para el modelo."""
    from app.modules.llm_chat.application.services.clinical_context_selector import (
        ClinicalContextSelection,
    )

    seleccion = ClinicalContextSelection(None, frozenset({"EOS"}), True, "EOS")
    hechos = [{"code": "HCT", "value": 63.6}, {"code": "HGB", "value": 21.0}]
    assert seleccion.filter_facts(hechos) == []
    # Y por eso importa saberlo: sin la marca, este turno es indistinguible de
    # uno en el que el selector acerto y el paciente simplemente no tenia datos.
    assert seleccion.parametro_pedido_ausente == "EOS"
