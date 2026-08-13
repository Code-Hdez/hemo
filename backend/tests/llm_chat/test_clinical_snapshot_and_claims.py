from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.llm_chat.application.services.clinical_context_selector import (
    ClinicalContextMaterializer,
    ClinicalContextSelector,
)
from app.modules.llm_chat.application.services.clinical_facts import (
    enrich_case_facts,
    lab_fact_from_mapping,
    normalize_clinical_unit,
    temporal_fact_index,
)
from app.modules.llm_chat.application.services.output_claim_validator import (
    OutputClaimValidator,
)
from app.modules.llm_chat.application.services.output_validator import OutputValidator
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    ClinicalContextSnapshot,
    ClinicalStudy,
    HemogramParameter,
    HemogramStudy,
    PatientContext,
    ResolvedQuestion,
    VerifiedFact,
    clinical_fact_id,
)


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
    status = "low" if number < minimum else "high" if number > maximum else "normal"
    return HemogramParameter(
        canonical_name=code,
        display_name={"WBC": "Leucocitos", "RBC": "Eritrocitos"}.get(code, code),
        original_name=code,
        value=number,
        value_text=value,
        unit=unit,
        reference_min=minimum,
        reference_max=maximum,
        flag=status,
    )


def _study(key: str, date: str, wbc: str, *, plt: str = "250") -> HemogramStudy:
    return HemogramStudy(
        analysis_id=f"analysis-{key}",
        study_key=key,
        date=date,
        label="Hemograma",
        laboratory=None,
        parameters=(
            _parameter("WBC", wbc, "6", "17"),
            _parameter("PLT", plt, "150", "500", unit="K/µL"),
        ),
        source_revision=f"revision-{key}",
    )


def _patient() -> PatientContext:
    return PatientContext(pet_id="pet-1", name="Luna")


def _snapshot(clinical: ClinicalContext) -> ClinicalContextSnapshot:
    return ClinicalContextSnapshot.from_context(
        clinical,
        owner_id="owner-1",
        conversation_id="conversation-1",
        context_revision=2,
        generated_at=datetime(2026, 7, 18, tzinfo=UTC),
    )


def test_classifier_outcome_is_retained_in_prompt_snapshot_and_public_context() -> None:
    study = HemogramStudy(
        analysis_id="analysis-H2",
        study_key="H2",
        date="2026-07-18",
        label="Hemograma",
        laboratory=None,
        parameters=(_parameter("WBC", "20", "6", "17"),),
        classifier_outcome={
            "classification_status": "NO_TARGET_PATTERN_DETECTED",
            "active_labels": [],
            "uploaded_at": "2026-07-18T12:00:00Z",
        },
    )
    clinical = ClinicalContext(
        mode="selected_hemogram",
        patient=_patient(),
        selected=study,
        history=(study,),
    )

    assert (
        clinical.prompt_payload()["selected_hemogram"]["classifier_outcome"]
        ["classification_status"]
        == "NO_TARGET_PATTERN_DETECTED"
    )
    assert clinical.public_payload()["classification_facts"] == [
        {
            "analysis_id": "analysis-H2",
            "study_key": "H2",
            "sample_date": "2026-07-18",
            "classification_status": "NO_TARGET_PATTERN_DETECTED",
            "active_labels": [],
            "uploaded_at": "2026-07-18T12:00:00Z",
        }
    ]


def _question(text: str, parameter: str | None = None) -> ResolvedQuestion:
    return ResolvedQuestion(
        original=text,
        standalone=text,
        is_follow_up=False,
        referenced_parameter=parameter,
    )


def _facts() -> list[dict[str, object]]:
    return [
        {
            "fact_type": "lab_value",
            "analysis_id": "analysis-H1",
            "study_key": "H1",
            "analysis_date": "2026-01-10",
            "code": "WBC",
            "parameter": "WBC",
            "label": "Leucocitos",
            "value": 3.0,
            "unit": "×10⁹/L",
            "ref_min": 6.0,
            "ref_max": 17.0,
            "status": "low",
        },
        {
            "fact_type": "lab_value",
            "analysis_id": "analysis-H2",
            "study_key": "H2",
            "analysis_date": "2026-07-18",
            "code": "WBC",
            "parameter": "WBC",
            "label": "Leucocitos",
            "value": 20.0,
            "unit": "×10⁹/L",
            "ref_min": 6.0,
            "ref_max": 17.0,
            "status": "high",
        },
    ]


def test_selected_snapshot_authorizes_only_the_selected_study() -> None:
    previous = _study("H1", "2026-01-10", "3")
    selected = _study("H2", "2026-07-18", "20")
    clinical = ClinicalContext(
        mode="selected_hemogram",
        patient=_patient(),
        selected=selected,
        history=(previous, selected),
    )

    snapshot = _snapshot(clinical)

    assert [study.analysis_id for study in snapshot.authorized_studies] == [
        "analysis-H2"
    ]
    assert {fact.analysis_id for fact in snapshot.authorized_parameters} == {
        "analysis-H2"
    }
    assert len(snapshot.context_fingerprint) == 64


def test_snapshot_keeps_absolute_and_percentage_differential_as_distinct_facts() -> None:
    study = HemogramStudy(
        analysis_id="analysis-differential",
        study_key="H1",
        date="2026-07-18",
        label="Hemograma",
        laboratory=None,
        parameters=(
            _parameter("NEU", "5", "3", "11", unit="K/µL"),
            _parameter("NEU_PCT", "80", "40", "75", unit="%"),
        ),
    )
    snapshot = _snapshot(
        ClinicalContext(
            mode="selected_hemogram",
            patient=_patient(),
            selected=study,
            history=(study,),
        )
    )

    assert {
        parameter.key.parameter_code
        for parameter in snapshot.authorized_parameters
    } == {"NEU", "NEU_PCT"}
    assert len(snapshot.authorized_parameters) == 2


def test_history_materialization_keeps_all_studies_in_authorized_universe() -> None:
    studies = (
        _study("H1", "2026-01-10", "3"),
        _study("H2", "2026-04-10", "20"),
        _study("H3", "2026-07-18", "21"),
    )
    clinical = ClinicalContext(
        mode="hemogram_history",
        patient=_patient(),
        history=studies,
    )
    snapshot = _snapshot(clinical)
    selection = ClinicalContextSelector().select(
        question=_question("¿Cómo cambiaron los leucocitos?", "WBC"),
        clinical=clinical,
    )

    materialized = ClinicalContextMaterializer().materialize(
        snapshot=snapshot,
        selection=selection,
    )

    assert len(materialized.authorized_studies) == 3
    assert len(materialized.authorized_parameters) == 6
    assert [key.analysis_id for key in materialized.materialized_fact_keys] == [
        "analysis-H1",
        "analysis-H2",
        "analysis-H3",
    ]
    assert all(
        key.parameter_code == "WBC" for key in materialized.materialized_fact_keys
    )


def test_history_prompt_materialization_prioritizes_recent_studies_round_robin() -> None:
    studies = (
        _study("H1", "2026-01-10", "3"),
        _study("H2", "2026-04-10", "20"),
        _study("H3", "2026-07-18", "21"),
    )
    clinical = ClinicalContext(
        mode="hemogram_history",
        patient=_patient(),
        history=studies,
    )
    snapshot = _snapshot(clinical)
    selection = ClinicalContextSelector().select(
        question=_question("Dame un resumen completo del hemograma"),
        clinical=clinical,
    )

    materialized = ClinicalContextMaterializer().materialize(
        snapshot=snapshot,
        selection=selection,
        maximum_fact_count=4,
        maximum_tokens=4096,
    )

    assert [
        (key.analysis_id, key.parameter_code)
        for key in materialized.materialized_fact_keys
    ] == [
        ("analysis-H3", "WBC"),
        ("analysis-H2", "WBC"),
        ("analysis-H1", "WBC"),
        ("analysis-H3", "PLT"),
    ]
    assert materialized.token_budget_metadata.omitted_fact_count == 2
    assert len(materialized.authorized_parameters) == 6

    payload = clinical.prompt_payload(
        materialized_fact_keys=frozenset(materialized.materialized_fact_keys),
        include_history=True,
    )
    rows_by_study = {
        study["study_key"]: [row[0] for row in study["parameters"]]
        for study in payload["hemogram_history"]
    }
    assert rows_by_study == {
        "H1": ["WBC"],
        "H2": ["WBC"],
        "H3": ["WBC", "PLT"],
    }


def test_compact_history_prompt_keeps_direction_without_duplicate_observations() -> None:
    studies = (
        _study("H1", "2026-01-10", "3"),
        _study("H2", "2026-04-10", "20"),
    )
    full_trend = {
        "fact_type": "history_parameter",
        "code": "WBC",
        "display_name": "Leucocitos",
        "occurrences": 2,
        "comparison_valid": True,
        "comparison_reasons": [],
        "direction_from_previous": "increased",
        "trend": "increasing",
        "unit": "×10³/µL",
        "observations": [{"value": "3"}, {"value": "20"}],
        "previous": {"value": "3"},
        "latest": {"value": "20"},
        "highest": {"value": "20"},
        "delta_from_previous": "17",
        "latest_change_percent": "566.7",
    }
    clinical = ClinicalContext(
        mode="hemogram_history",
        patient=_patient(),
        history=studies,
        computed_facts=(full_trend,),
    )

    compact = clinical.prompt_payload(compact_history=True)
    trend = compact["historical_trends"][0]

    assert trend["code"] == "WBC"
    assert trend["comparison_valid"] is True
    assert trend["direction_from_previous"] == "increased"
    assert trend["trend"] == "increasing"
    assert "observations" not in trend
    assert "previous" not in trend
    assert "latest" not in trend
    assert "highest" not in trend
    assert "delta_from_previous" not in trend
    assert "latest_change_percent" not in trend
    assert compact["hemogram_history_parameter_columns"][0] == "canonical_name"
    assert all(
        "parameter_columns" not in study
        for study in compact["hemogram_history"]
    )

    # The authoritative in-memory context is untouched and still carries the
    # complete backend-computed series for validation and persistence.
    assert clinical.computed_facts[0] == full_trend


def test_history_materialization_reserves_latest_and_previous_under_tight_limit() -> None:
    studies = (
        _study("H1", "2026-01-10", "3"),
        _study("H2", "2026-04-10", "20"),
        _study("H3", "2026-07-18", "21"),
    )
    clinical = ClinicalContext(
        mode="hemogram_history",
        patient=_patient(),
        history=studies,
    )
    snapshot = _snapshot(clinical)
    selection = ClinicalContextSelector().select(
        question=_question("Dame un resumen completo del hemograma"),
        clinical=clinical,
    )

    latest_only = ClinicalContextMaterializer().materialize(
        snapshot=snapshot,
        selection=selection,
        maximum_fact_count=1,
    )
    latest_and_previous = ClinicalContextMaterializer().materialize(
        snapshot=snapshot,
        selection=selection,
        maximum_fact_count=2,
    )

    assert [
        (key.analysis_id, key.parameter_code)
        for key in latest_only.materialized_fact_keys
    ] == [("analysis-H3", "WBC")]
    assert [
        (key.analysis_id, key.parameter_code)
        for key in latest_and_previous.materialized_fact_keys
    ] == [
        ("analysis-H3", "WBC"),
        ("analysis-H2", "WBC"),
    ]


def test_history_selector_detects_a_transition_before_the_latest_pair() -> None:
    studies = (
        _study("H1", "2026-01-10", "3"),
        _study("H2", "2026-04-10", "20"),
        _study("H3", "2026-07-18", "20"),
    )
    clinical = ClinicalContext(
        mode="hemogram_history",
        patient=_patient(),
        history=studies,
    )

    selection = ClinicalContextSelector().select(
        question=_question("¿Qué cambió en los estudios?"),
        clinical=clinical,
    )

    assert "WBC" in (selection.parameter_codes or ())


def test_temporal_fact_index_preserves_every_wbc_measurement() -> None:
    index = temporal_fact_index(_facts())

    assert [fact.value for fact in index.series("WBC")] == [3.0, 20.0]
    assert index.previous("WBC").analysis_id == "analysis-H1"  # type: ignore[union-attr]
    assert index.latest("WBC").analysis_id == "analysis-H2"  # type: ignore[union-attr]
    assert len(index.by_key) == 2


def test_verified_fact_has_a_stable_id_and_complete_provenance() -> None:
    study = HemogramStudy(
        analysis_id="analysis-provenance",
        study_key="H1",
        date="2026-07-18",
        label="Hemograma",
        laboratory="Laboratorio Central",
        analyzer="Sysmex XN-V",
        pet_id="pet-1",
        date_origin="laboratory_result",
        parameters=(_parameter("WBC", "10.4", "6", "17"),),
        source_revision="revision-42",
    )
    clinical_study = ClinicalStudy.from_hemogram(study, pet_id="pet-1")

    first = VerifiedFact.from_parameter(clinical_study.parameters[0])
    second = VerifiedFact.from_parameter(clinical_study.parameters[0])
    payload = first.validation_dict()

    assert first.fact_id == second.fact_id
    assert first.fact_id == clinical_fact_id("analysis-provenance", "WBC")
    assert payload["provenance"] == {
        "pet_id": "pet-1",
        "analysis_id": "analysis-provenance",
        "field": "WBC",
        "study_date": "2026-07-18",
        "date_origin": "laboratory_result",
        "laboratory": "Laboratorio Central",
        "analyzer": "Sysmex XN-V",
        "data_origin": "analysis_database",
        "source_revision": "revision-42",
    }


def test_partial_reference_interval_never_implies_normality() -> None:
    below_known_upper = lab_fact_from_mapping(
        {
            "analysis_id": "analysis-1",
            "code": "WBC",
            "value": 10.4,
            "unit": "10^9/L",
            "reference_high": 17,
            "status": "normal",
        }
    )
    above_known_upper = lab_fact_from_mapping(
        {
            "analysis_id": "analysis-1",
            "code": "WBC",
            "value": 20,
            "unit": "10^9/L",
            "reference_high": 17,
        }
    )

    assert below_known_upper is not None
    assert below_known_upper.status == "unknown"
    assert above_known_upper is not None
    assert above_known_upper.status == "high"


def test_explicit_critical_status_is_preserved() -> None:
    fact = lab_fact_from_mapping(
        {
            "analysis_id": "analysis-critical",
            "code": "PLT",
            "value": 20,
            "unit": "K/µL",
            "reference_low": 150,
            "reference_high": 500,
            "status": "critical",
        }
    )

    assert fact is not None
    assert fact.status == "critical"


def test_red_cell_derived_facts_require_rbc_hgb_and_hct() -> None:
    partial = enrich_case_facts(
        [
            {
                "fact_type": "lab_value",
                "analysis_id": "analysis-partial",
                "code": "RBC",
                "value": 7.0,
                "unit": "10^12/L",
                "reference_low": 5.5,
                "reference_high": 8.5,
                "status": "normal",
            }
        ]
    )
    complete = enrich_case_facts(
        [
            {
                "fact_type": "lab_value",
                "analysis_id": "analysis-complete",
                "code": code,
                "value": value,
                "unit": unit,
                "reference_low": low,
                "reference_high": high,
                "status": "normal",
            }
            for code, value, unit, low, high in (
                ("RBC", 7.0, "10^12/L", 5.5, 8.5),
                ("HGB", 14.0, "g/dL", 12.0, 18.0),
                ("HCT", 45.0, "%", 37.0, 55.0),
            )
        ]
    )

    partial_all_normal = next(
        fact
        for fact in partial
        if fact.get("code") == "DERIVED:all_red_cell_values_normal"
    )
    complete_all_normal = next(
        fact
        for fact in complete
        if fact.get("code") == "DERIVED:all_red_cell_values_normal"
    )

    assert partial_all_normal["truth_state"] == "insufficient_data"
    assert partial_all_normal["value"] is None
    assert partial_all_normal["missing_codes"] == ["HCT", "HGB"]
    assert complete_all_normal["truth_state"] == "true"
    assert complete_all_normal["value"] is True


def test_temporal_fact_index_rejects_cross_patient_facts() -> None:
    mixed = [
        {
            **fact,
            "pet_id": "pet-1" if index == 0 else "pet-2",
        }
        for index, fact in enumerate(_facts())
    ]

    with pytest.raises(ValueError, match="clinical_facts_cannot_mix_patients"):
        temporal_fact_index(mixed)


def test_clinical_fact_indexes_reject_duplicate_analysis_parameters() -> None:
    duplicated = [_facts()[0], dict(_facts()[0])]

    with pytest.raises(
        ValueError,
        match="clinical_facts_duplicate_analysis_parameter",
    ):
        enrich_case_facts(duplicated)
    with pytest.raises(
        ValueError,
        match="clinical_facts_duplicate_analysis_parameter",
    ):
        temporal_fact_index(duplicated)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("10^9/L", "× 10⁹/L"),
        ("K/µL", "10^9/L"),
        ("10^3/µL", "×10^9/L"),
        ("M/µL", "10^12/L"),
        ("10^6/µL", "×10^12/L"),
    ],
)
def test_equivalent_cbc_units_share_a_canonical_form(left: str, right: str) -> None:
    assert normalize_clinical_unit(left) == normalize_clinical_unit(right)


@pytest.mark.parametrize(
    "answer",
    [
        "Los eritrocitos participan en el transporte de oxígeno.",
        "Conviene preguntar al veterinario si también debe revisar los eritrocitos.",
        "¿Sería útil revisar los eritrocitos con el veterinario?",
    ],
)
def test_parameter_concepts_and_questions_are_not_patient_claims(answer: str) -> None:
    validation = OutputValidator().validate(
        answer,
        case_facts=[
            {
                "code": "NEU",
                "value": 12,
                "unit": "×10⁹/L",
                "ref_min": 3,
                "ref_max": 11,
                "status": "high",
            },
            {
                "code": "PLT",
                "value": 90,
                "unit": "K/µL",
                "ref_min": 150,
                "ref_max": 500,
                "status": "low",
            },
        ],
    )

    assert validation.is_safe is True
    assert validation.reason == "ok"


def test_patient_status_for_an_absent_parameter_is_rejected() -> None:
    validation = OutputClaimValidator().validate(
        "Los eritrocitos están bajos.",
        case_facts=_facts(),
    )

    assert validation.is_valid is False
    assert validation.first_issue is not None
    assert validation.first_issue.code == "unsupported_status_claim"
    assert validation.first_issue.detail.startswith("parameter_not_available:RBC")


def test_absolute_and_percentage_statuses_require_unambiguous_wording() -> None:
    facts = [
        {
            "fact_type": "lab_value",
            "analysis_id": "analysis-H1",
            "analysis_date": "2026-07-18",
            "code": "NEU",
            "value": 5.0,
            "unit": "K/µL",
            "ref_min": 3.0,
            "ref_max": 11.0,
            "status": "normal",
        },
        {
            "fact_type": "lab_value",
            "analysis_id": "analysis-H1",
            "analysis_date": "2026-07-18",
            "code": "NEU_PCT",
            "value": 80.0,
            "unit": "%",
            "ref_min": 40.0,
            "ref_max": 75.0,
            "status": "high",
        },
    ]

    ambiguous = OutputClaimValidator().validate(
        "Los neutrófilos están altos.",
        case_facts=facts,
    )
    explicit = OutputClaimValidator().validate(
        "NEU % está alto.",
        case_facts=facts,
    )
    percentage_only = OutputClaimValidator().validate(
        "Los neutrófilos están altos.",
        case_facts=[facts[1]],
    )

    assert ambiguous.is_valid is False
    assert ambiguous.first_issue is not None
    assert ambiguous.first_issue.code == "ambiguous_parameter_claim"
    assert explicit.is_valid is True
    assert percentage_only.is_valid is True


def test_suggested_question_cannot_smuggle_an_invented_patient_value() -> None:
    validation = OutputClaimValidator().validate(
        "Pregunte al veterinario si los eritrocitos son 999 ×10⁹/L.",
        case_facts=_facts(),
    )

    assert validation.is_valid is False
    assert validation.first_issue is not None
    assert validation.first_issue.code == "unsupported_numeric_claim"


def test_absent_reticulocytes_can_be_explained_but_not_invented() -> None:
    conceptual = OutputClaimValidator().validate(
        "Los reticulocitos no están disponibles en este análisis.",
        case_facts=_facts(),
    )
    invented = OutputClaimValidator().validate(
        "Los reticulocitos son 4.8 ×10⁹/L.",
        case_facts=_facts(),
    )

    assert conceptual.is_valid is True
    assert invented.is_valid is False
    assert invented.first_issue is not None
    assert invented.first_issue.code == "unsupported_numeric_claim"
    assert invented.first_issue.detail == "parameter_not_available:RETIC"


def test_general_conceptual_status_is_not_a_patient_claim() -> None:
    validation = OutputValidator().validate(
        "En general, los leucocitos pueden estar altos en procesos muy diferentes.",
        case_facts=[],
    )

    assert validation.is_safe is True


@pytest.mark.parametrize(
    "answer",
    [
        "La leucocitosis ocurre cuando los leucocitos están altos.",
        (
            "Los leucocitos están altos cuando su número supera el intervalo "
            "de referencia."
        ),
    ],
)
def test_general_conditional_definition_is_not_a_patient_status_claim(
    answer: str,
) -> None:
    validation = OutputValidator().validate(answer, case_facts=[])

    assert validation.is_safe is True
    assert validation.reason == "ok"


def test_bare_status_without_authorized_facts_remains_rejected() -> None:
    validation = OutputValidator().validate(
        "Los eritrocitos están bajos.",
        case_facts=[],
    )

    assert validation.is_safe is False
    assert validation.reason == "unsupported_status_claim"
    assert validation.detail == "parameter_not_available:RBC:low"


@pytest.mark.parametrize(
    ("answer", "value", "status"),
    [
        (
            "Los leucocitos están altos y requieren seguimiento bajo supervisión "
            "veterinaria.",
            20.0,
            "high",
        ),
        (
            "Los leucocitos están altos y, bajo este contexto, requieren seguimiento.",
            20.0,
            "high",
        ),
        (
            "Los leucocitos están bajos y ameritan una consulta de alta prioridad "
            "clínica.",
            3.0,
            "low",
        ),
    ],
)
def test_follow_up_language_is_not_misclassified_as_a_clinical_status(
    answer: str,
    value: float,
    status: str,
) -> None:
    fact = {**_facts()[-1], "value": value, "status": status}

    validation = OutputClaimValidator().validate(answer, case_facts=[fact])

    assert validation.is_valid is True


@pytest.mark.parametrize(
    ("answer", "value", "status", "claimed_status"),
    [
        (
            "Los leucocitos están bajos y requieren seguimiento bajo supervisión "
            "veterinaria.",
            20.0,
            "high",
            "claimed_low",
        ),
        (
            "Los leucocitos están altos y ameritan una consulta de alta prioridad "
            "clínica.",
            3.0,
            "low",
            "claimed_high",
        ),
    ],
)
def test_follow_up_language_does_not_hide_an_explicit_false_clinical_status(
    answer: str,
    value: float,
    status: str,
    claimed_status: str,
) -> None:
    fact = {**_facts()[-1], "value": value, "status": status}

    validation = OutputClaimValidator().validate(answer, case_facts=[fact])

    assert validation.is_valid is False
    assert validation.first_issue is not None
    assert validation.first_issue.code == "unsupported_status_claim"
    assert claimed_status in validation.first_issue.detail


def test_patient_number_without_any_authorized_context_is_rejected() -> None:
    validation = OutputValidator().validate(
        "Los leucocitos son 18.77 ×10⁹/L.",
        case_facts=[],
    )

    assert validation.is_safe is False
    assert validation.reason == "unsupported_numeric_claim"
    assert validation.detail == "parameter_not_available:WBC"


@pytest.mark.parametrize(
    ("answer", "expected_code"),
    [
        ("Los leucocitos son 19 ×10⁹/L.", "unsupported_numeric_claim"),
        ("Los leucocitos son 20 g/dL.", "unsupported_unit_claim"),
        (
            "Los leucocitos tienen un rango de referencia 5–15 ×10⁹/L.",
            "unsupported_range_claim",
        ),
        (
            "El 2026-06-01 los leucocitos estaban altos.",
            "unsupported_date_claim",
        ),
        (
            "El 2026-01-10 los leucocitos son 20 ×10⁹/L.",
            "unsupported_numeric_claim",
        ),
    ],
)
def test_unsupported_patient_measurements_are_rejected(
    answer: str,
    expected_code: str,
) -> None:
    validation = OutputClaimValidator().validate(answer, case_facts=_facts())

    assert validation.is_valid is False
    assert validation.first_issue is not None
    assert validation.first_issue.code == expected_code


def test_correct_low_to_high_transition_is_accepted() -> None:
    answer = (
        "En el estudio anterior los leucocitos estaban bajos y en el más reciente "
        "aparecen altos."
    )
    validation = OutputClaimValidator().validate(
        answer,
        case_facts=_facts(),
    )
    facade = OutputValidator().validate(answer, case_facts=_facts())

    assert validation.is_valid is True
    assert facade.is_safe is True


@pytest.mark.parametrize(
    "answer",
    [
        (
            "En enero de 2026, los leucocitos eran 3 ×10⁹/L; "
            "en julio de 2026 son 20 ×10⁹/L."
        ),
        (
            "Los leucocitos aumentaron de 3 ×10⁹/L en enero de 2026 "
            "a 20 ×10⁹/L en julio de 2026."
        ),
    ],
)
def test_natural_spanish_dates_bind_each_measurement_to_its_study(
    answer: str,
) -> None:
    validation = OutputClaimValidator().validate(answer, case_facts=_facts())

    assert validation.is_valid is True


def test_natural_spanish_dates_reject_values_assigned_to_the_wrong_study() -> None:
    validation = OutputClaimValidator().validate(
        "En enero de 2026, los leucocitos eran 20 ×10⁹/L; "
        "en julio de 2026 son 3 ×10⁹/L.",
        case_facts=_facts(),
    )

    assert validation.is_valid is False
    assert validation.first_issue is not None
    assert validation.first_issue.code == "unsupported_numeric_claim"


def test_natural_date_year_is_not_misread_as_a_patient_value() -> None:
    validation = OutputClaimValidator().validate(
        "Los leucocitos del estudio de enero de 2026 eran 3 ×10⁹/L.",
        case_facts=_facts(),
    )

    assert validation.is_valid is True


def test_long_transition_with_parenthetical_statuses_binds_the_latest_value() -> None:
    validation = OutputClaimValidator().validate(
        "Los leucocitos aumentaron de 3.0 ×10⁹/L (valor bajo) en el estudio "
        "del 2026-01-10 al 20.0 ×10⁹/L (valor alto) en el estudio del 2026-07-18.",
        case_facts=_facts(),
    )

    assert validation.is_valid is True


def test_status_transition_wording_uses_previous_and_latest_facts() -> None:
    valid = OutputClaimValidator().validate(
        "Los leucocitos aumentaron de un valor bajo a uno alto entre ambos estudios.",
        case_facts=_facts(),
    )
    inverted = OutputClaimValidator().validate(
        "Los leucocitos cambiaron de un valor alto a uno bajo entre ambos estudios.",
        case_facts=_facts(),
    )

    assert valid.is_valid is True
    assert inverted.is_valid is False
    assert inverted.first_issue is not None
    assert inverted.first_issue.code == "unsupported_temporal_claim"


def test_supported_value_unit_range_date_and_status_are_accepted() -> None:
    validation = OutputClaimValidator().validate(
        "El 2026-07-18 los leucocitos son 20 ×10⁹/L, están altos y su rango de "
        "referencia es 6–17 ×10⁹/L.",
        case_facts=_facts(),
    )

    assert validation.is_valid is True


def test_omitted_multiplication_sign_in_stored_unit_matches_generated_unit() -> None:
    facts = [dict(fact) for fact in _facts()]
    for fact in facts:
        fact["unit"] = "10^9/L"

    validation = OutputClaimValidator().validate(
        "Los leucocitos son 20 × 10⁹/L.",
        case_facts=facts,
    )

    assert validation.is_valid is True


def test_integer_reference_bounds_keep_trailing_zeroes() -> None:
    platelets = _parameter("PLT", "90", "150", "500", unit="K/µL")

    assert platelets.prompt_dict()["reference_min"] == "150"
    assert platelets.prompt_dict()["reference_max"] == "500"
    assert platelets.prompt_row()[5:7] == ["150", "500"]
    validation = OutputClaimValidator().validate(
        "Las plaquetas están bajas.",
        case_facts=[
            {
                "analysis_id": "analysis-H1",
                "analysis_date": "2026-07-18",
                "code": "PLT",
                "value": "90",
                "unit": "K/µL",
                "reference_min": platelets.prompt_dict()["reference_min"],
                "reference_max": platelets.prompt_dict()["reference_max"],
                "status": "low",
            }
        ],
    )
    assert validation.is_valid is True


def test_inverted_low_to_high_transition_is_rejected() -> None:
    validation = OutputClaimValidator().validate(
        "En el estudio anterior los leucocitos estaban altos y en el más reciente aparecen bajos.",
        case_facts=_facts(),
    )

    assert validation.is_valid is False
    assert validation.first_issue is not None
    assert validation.first_issue.code == "unsupported_temporal_claim"
    assert "previous:expected_low:claimed_high" in validation.first_issue.detail


@pytest.mark.parametrize(
    ("answer", "expected_code"),
    [
        ("Esto confirma una infección.", "diagnostic_certainty"),
        ("Adminístrale 20 mg de medicamento.", "dosage_instruction"),
    ],
)
def test_claim_validator_blocks_diagnosis_and_dosage(
    answer: str,
    expected_code: str,
) -> None:
    validation = OutputClaimValidator().validate(answer, case_facts=_facts())

    assert validation.is_valid is False
    assert validation.first_issue is not None
    assert validation.first_issue.code == expected_code


def test_negated_diagnostic_implication_is_not_a_diagnosis() -> None:
    validation = OutputValidator().validate(
        "Los leucocitos altos no significan por sí solos que tu perro tiene una infección; "
        "conviene que lo evalúe un veterinario.",
        case_facts=_facts(),
    )

    assert validation.is_safe is True


def test_authorized_vocabulary_cannot_cross_values_between_facts() -> None:
    """Regression from the adversarial review of the projection validator.

    Widening the allowed vocabulary with every authorized fact also handed
    over every authorized *number*, so a claim needed to overlap its own fact
    by one token and could then take a value from any other one. Lab values
    stay caught by OutputClaimValidator, but profile/ML/quality facts carry no
    parameter code, so it skips them: the review confirmed "La edad de Lucas
    es 32.5 años" (32.5 is the weight) being accepted.
    """

    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _patient_fact_is_materialized_projection,
        _patient_profile_facts,
    )
    from app.modules.llm_chat.domain.clinical import PatientContext

    profile = _patient_profile_facts(
        PatientContext(
            pet_id="p1",
            name="Lucas",
            breed="labrador",
            sex="macho",
            age_years=7,
            birth_year=2019,
            weight_kg=32.5,
        )
    )
    by_id = {fact["fact_id"]: fact for fact in profile}
    lab = {
        "code": "WBC",
        "canonical_name": "WBC",
        "label": "Leucocitos",
        "value": "9.9",
        "unit": "x10³/µL",
        "reference_min": "5.5",
        "reference_max": "16.9",
        "status": "normal",
    }
    authorized = [*profile, lab]

    def projects(text: str, cited: list[dict[str, object]]) -> bool:
        return _patient_fact_is_materialized_projection(
            text, cited, authorized_facts=authorized
        )

    age = [by_id["pet:p1:age_years"]]
    assert projects("La edad de Lucas es 7 anos.", age)
    # The pet's own name stays usable; other facts' values do not.
    assert projects(
        "Los leucocitos de Lucas estan en 9.9 x10³/µL, dentro del rango 5.5 a 16.9.",
        [lab],
    )
    assert not projects("La edad de Lucas es 32.5 anos.", age)
    assert not projects("La edad de Lucas es 2019 anos.", age)
    assert not projects("El peso de Lucas es 7 kg.", [by_id["pet:p1:weight_kg"]])
    assert not projects("La raza de Lucas es macho.", [by_id["pet:p1:breed"]])


def test_unlinked_clinical_assertion_is_not_disabled_by_the_referral() -> None:
    """Regression: the mandatory veterinary referral switched the guard off.

    "consulta"/"veterinario" were treated as hedges, while the same turn
    instructs the model to include a referral — so every patient-data answer
    carried the word that disabled the check. Sentence splitting was also
    inert, because the normalizer stripped ";", "!" and "?" before the split.
    """

    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _unsupported_unlinked_clinical_assertion as asserts,
    )

    for refused in (
        "la anemia causa debilidad",
        "La anemia causa debilidad, consulta a tu veterinario",
        "El hemograma indica que hay una infeccion; consulta a un veterinario",
        "Un valor asi produce enfermedad grave! Acude a un veterinario",
        "No cabe duda: el paracetamol produce insuficiencia hepatica",
        "sin excepcion el paracetamol produce insuficiencia hepatica",
    ):
        assert asserts(refused), refused

    for allowed in (
        # The assistant declining is not a mechanism claim, and "causa" as a
        # noun names a thing instead of asserting one.
        "No puedo indicarte que causa la anemia de tu perro.",
        "La anemia puede deberse a varias causas; consulta a un veterinario.",
        "No receto medicamentos. Un veterinario debe valorar la causa de la anemia.",
        "Habla con tu veterinario sobre las posibles causas de la anemia.",
        "Un valor alto no significa que haya enfermedad.",
    ):
        assert not asserts(allowed), allowed


def test_patient_fact_accepts_ordinary_prose_around_the_authorized_value() -> None:
    """Regression: this rule was the biggest single source of 502 in production.

    It required *every* token of the claim to appear in a ~90-entry whitelist,
    so any ordinary Spanish word outside the list rejected the turn — 9 of 17
    failures in the expanded battery, and the reason the selected-hemogram
    mode scored 0. What it was really protecting is enforced directly now: the
    claim must state the cited fact's value, may not carry a number that is
    not that fact's, may not introduce an unauthorized proper noun, and may
    not name a condition the authorized facts do not record.
    """

    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _patient_fact_is_materialized_projection,
        _patient_profile_facts,
    )
    from app.modules.llm_chat.domain.clinical import PatientContext

    profile = _patient_profile_facts(
        PatientContext(pet_id="p1", name="Lucas", breed="labrador", sex="macho")
    )
    lab = {
        "code": "WBC",
        "canonical_name": "WBC",
        "label": "Leucocitos",
        "value": "9.9",
        "unit": "x10³/µL",
        "reference_min": "5.5",
        "reference_max": "16.9",
        "status": "normal",
    }
    authorized = [*profile, lab]

    def projects(text: str) -> bool:
        return _patient_fact_is_materialized_projection(
            text, [lab], authorized_facts=authorized
        )

    for accepted in (
        "El valor de WBC es 9.9 x10³/µL.",
        "Los leucocitos de Lucas estan en 9.9 x10³/µL, dentro del rango 5.5 a 16.9.",
        "El WBC es 9.9 x10³/µL, lo que se considera normal para el rango informado.",
        "Los leucocitos aparecen con un recuento de 9.9 x10³/µL, cifra que queda "
        "comodamente dentro del intervalo esperado.",
    ):
        assert projects(accepted), accepted

    for refused in (
        "El WBC es 12.5 x10³/µL.",                        # valor inventado
        "El WBC de 9.9 x10³/µL indica ehrlichiosis grave.",  # diagnóstico pegado
        "El WBC de 9.9 x10³/µL confirma una anemia.",
        "El WBC es 9.9 x10³/µL en este Bulldog Frances.",    # raza inventada
        "Los leucocitos de Rocky estan en 9.9 x10³/µL.",     # otra mascota
    ):
        assert not projects(refused), refused


def test_textbook_numbers_are_legal_when_no_patient_is_in_scope() -> None:
    """GEN-12 pagó 122-125 s de reparación por decir «37 a 55 %» en una
    respuesta de libro: sin paciente en alcance no existe un valor que la
    cifra pudiera contradecir. Con paciente autorizado la puerta sigue entera
    aunque el presupuesto haya vaciado la lista de hechos."""

    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidator,
    )

    texto = "El hematocrito normal en perros suele estar entre 37 y 55 %."

    sin_paciente = OutputValidator().validate(
        texto, case_facts=[], patient_in_scope=False
    )
    assert sin_paciente.is_safe, sin_paciente.reason

    con_paciente = OutputValidator().validate(
        texto, case_facts=[], patient_in_scope=True
    )
    assert not con_paciente.is_safe
    assert con_paciente.reason == "unsupported_numeric_claim"
