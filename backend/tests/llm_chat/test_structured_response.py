from __future__ import annotations

import json

import pytest

from app.modules.llm_chat.application.services.structured_response import (
    FACT_BASED_CLAIM_TYPES,
    ClaimType,
    GeneratedClaim,
    GeneratedResponseEnvelope,
    StructuredResponseError,
    StructuredResponseService,
)


def _payload() -> dict[str, object]:
    return {
        "schema_version": "hemovet-response-v2",
        "response_type": "selected_cbc_explanation",
        "intent": "SELECTED_CBC",
        "claims": [
            {
                "claim_id": "claim_001",
                "text": "El WBC está dentro del intervalo informado.",
                "claim_type": "PATIENT_FACT",
                "fact_ids": ["fact_wbc_001"],
                "source_ids": [],
                "policy_rule_ids": [],
                "evidence_spans": [],
            },
            {
                "claim_id": "claim_002",
                "text": "El hemograma aislado no confirma un diagnóstico.",
                "claim_type": "LIMITATION",
                "fact_ids": [],
                "source_ids": [],
                "policy_rule_ids": [],
                "evidence_spans": [],
            },
        ],
        "safety": {
            "contains_diagnosis_confirmation": False,
            "contains_medication_recommendation": False,
            "contains_dose": False,
            "contains_frequency": False,
            "contains_treatment_duration": False,
            "contains_personalized_treatment": False,
            "requires_urgent_referral": False,
        },
    }


def test_envelope_answer_is_derived_only_from_generated_claims() -> None:
    envelope = GeneratedResponseEnvelope.model_validate(_payload())

    assert envelope.answer == (
        "El WBC está dentro del intervalo informado.\n\n"
        "El hemograma aislado no confirma un diagnóstico."
    )
    assert envelope.used_fact_ids == ("fact_wbc_001",)


def test_envelope_rejects_an_unknown_schema_version() -> None:
    payload = _payload()
    payload["schema_version"] = "totally-wrong"

    with pytest.raises(ValueError, match="hemovet-response-v2"):
        GeneratedResponseEnvelope.model_validate(payload)


def test_documented_claim_requires_source_and_evidence_span() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_001",
            "text": "Conocimiento general.",
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [],
        }
    ]

    with pytest.raises(ValueError, match="evidence_spans"):
        GeneratedResponseEnvelope.model_validate(payload)


def test_parse_projects_schema_failure_without_exposing_rejected_text() -> None:
    payload = _payload()
    sensitive_text = "dato-clinico-que-no-debe-aparecer"
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": sensitive_text,
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": [],
            "policy_rule_ids": [],
            "evidence_spans": [],
        }
    ]

    with pytest.raises(StructuredResponseError) as captured:
        StructuredResponseService.parse(json.dumps(payload))

    assert captured.value.code == "structured_schema_invalid"
    assert captured.value.detail_code == "documented_source_ids_missing"
    assert sensitive_text not in str(captured.value)
    assert sensitive_text not in str(captured.value.detail_code)


def test_parse_projects_unknown_schema_failure_to_fixed_error_type() -> None:
    payload = _payload()
    payload["safety"] = "contenido-que-no-debe-aparecer"

    with pytest.raises(StructuredResponseError) as captured:
        StructuredResponseService.parse(json.dumps(payload))

    assert captured.value.detail_code == "schema_validation_error:model_type"
    assert "contenido-que-no-debe-aparecer" not in str(captured.value.detail_code)


def test_request_schema_rejects_unsupported_claim_types_and_identifiers() -> None:
    schema = StructuredResponseService.json_schema(
        allowed_fact_ids=(),
        allowed_source_ids=("source_safe",),
        allowed_policy_rule_ids=(),
        allowed_claim_types=(
            ClaimType.DOCUMENTED_GENERAL_KNOWLEDGE,
            ClaimType.LIMITATION,
        ),
        require_documentary_support=True,
        documentary_text_options=("Oración documental exacta y autorizada.",),
    )

    definitions = schema["$defs"]
    claim_types = definitions["ClaimType"]["enum"]
    claim_properties = definitions["GeneratedClaim"]["properties"]
    evidence_properties = definitions["EvidenceSpan"]["properties"]

    assert claim_types == ["DOCUMENTED_GENERAL_KNOWLEDGE", "LIMITATION"]
    assert "PATIENT_FACT" not in claim_types
    assert claim_properties["fact_ids"]["maxItems"] == 0
    assert claim_properties["source_ids"]["items"]["enum"] == ["source_safe"]
    assert claim_properties["source_ids"]["minItems"] == 1
    assert claim_properties["evidence_spans"]["minItems"] == 1
    assert "source_ids" in definitions["GeneratedClaim"]["required"]
    assert "evidence_spans" in definitions["GeneratedClaim"]["required"]
    assert "enum" not in claim_properties["text"]
    assert "Spanish proposition" in claim_properties["text"]["description"]
    assert definitions["EvidenceSpan"]["properties"]["text"]["enum"] == [
        "Oración documental exacta y autorizada."
    ]
    # A documentary explanation is not limited to a single claim (etapa 4,
    # Block C): the request schema allows more than 1 when documentary
    # support is required. Capped at 4 (not the original 8): each claim
    # independently requires non-empty, literal-language-matched
    # source_ids/evidence_spans, and letting a documentary answer fan out
    # to 8 of those compounded the odds of a structured_schema_invalid
    # failure on long educational answers.
    assert schema["properties"]["claims"]["maxItems"] == 4
    assert claim_properties["policy_rule_ids"]["maxItems"] == 0
    assert evidence_properties["source_id"]["enum"] == ["source_safe"]


def test_request_schema_requires_authorized_patient_fact_ids() -> None:
    schema = StructuredResponseService.json_schema(
        allowed_fact_ids=("fact_wbc",),
        allowed_source_ids=(),
        allowed_policy_rule_ids=(),
        allowed_claim_types=(ClaimType.PATIENT_FACT,),
        require_patient_support=True,
        patient_text_options=("El valor de WBC es 10.4 ×10³/µL.",),
        required_patient_claim_count=1,
    )

    claim = schema["$defs"]["GeneratedClaim"]
    fact_schema = claim["properties"]["fact_ids"]
    assert schema["$defs"]["ClaimType"]["enum"] == ["PATIENT_FACT"]
    assert fact_schema["minItems"] == 1
    assert fact_schema["items"]["enum"] == ["fact_wbc"]
    assert "fact_ids" in claim["required"]
    # Etapa 4: the model writes its own Spanish sentence for the cited
    # fact_ids instead of selecting a backend-authored literal, so the
    # request schema deliberately leaves "text" without an enum.
    assert "enum" not in claim["properties"]["text"]
    assert "own words" in claim["properties"]["text"]["description"]
    # The patient claim count is a ceiling, not a quota. It used to be pinned
    # to exactly the number of authorized lab facts, which left no room for a
    # claim that answers the question itself, so targeted clinical questions
    # ("which values are out of range?", "what should I ask my vet?") could
    # only fail. Fact coverage is enforced per turn by the output validator's
    # own required_coverage, not by this count.
    assert schema["properties"]["claims"]["minItems"] == 1
    assert schema["properties"]["claims"]["maxItems"] == 5


def test_request_schema_never_demands_a_citation_a_claim_type_forbids() -> None:
    """Every claim type the grammar offers must have a satisfiable output.

    ``require_patient_support`` used to force ``fact_ids`` onto every claim.
    On a clinical turn that also authorized PARAMETRIC_VETERINARY_KNOWLEDGE or
    TRANSITION — both rejected by the validator for carrying fact_ids — that
    made those types impossible to emit: the grammar demanded exactly what
    validation forbade, and the repair pass reuses this schema, so it failed
    the same way. Asserted here as a property over the offered types, not as a
    fixed shape, so any future claim type is covered by construction.
    """

    allowed = (
        ClaimType.PATIENT_FACT,
        ClaimType.CONVERSATIONAL,
        ClaimType.LIMITATION,
        ClaimType.TRANSITION,
        ClaimType.PARAMETRIC_VETERINARY_KNOWLEDGE,
    )
    schema = StructuredResponseService.json_schema(
        allowed_fact_ids=("fact_wbc",),
        allowed_claim_types=allowed,
        require_patient_support=True,
        required_patient_claim_count=2,
    )
    claim = schema["$defs"]["GeneratedClaim"]

    assert claim["properties"]["fact_ids"].get("minItems") is None
    assert "fact_ids" not in claim["required"]
    # The stronger statement: every offered type can produce a claim the
    # validator accepts.
    for index, claim_type in enumerate(allowed):
        fact_ids = (
            ["fact_wbc"] if claim_type in FACT_BASED_CLAIM_TYPES else []
        )
        GeneratedClaim(
            claim_id=f"claim_{index}",
            text="Una frase.",
            claim_type=claim_type,
            fact_ids=fact_ids,
        )


def test_request_schema_requires_authorized_policy_rule_ids() -> None:
    schema = StructuredResponseService.json_schema(
        allowed_fact_ids=(),
        allowed_source_ids=(),
        allowed_policy_rule_ids=("direct_diagnosis",),
        allowed_claim_types=(ClaimType.SAFETY_GUIDANCE,),
        require_policy_support=True,
    )

    claim = schema["$defs"]["GeneratedClaim"]
    policy_schema = claim["properties"]["policy_rule_ids"]
    assert schema["$defs"]["ClaimType"]["enum"] == ["SAFETY_GUIDANCE"]
    assert policy_schema["minItems"] == 1
    assert policy_schema["items"]["enum"] == ["direct_diagnosis"]
    assert "policy_rule_ids" in claim["required"]
    assert schema["properties"]["claims"]["maxItems"] == 1


def test_support_validator_rejects_unknown_fact_and_source() -> None:
    service = StructuredResponseService()
    envelope = service.parse(json.dumps(_payload()))

    with pytest.raises(StructuredResponseError, match="unknown_fact_id"):
        service.validate_support(
            envelope,
            expected_intent="SELECTED_CBC",
            allowed_fact_ids=(),
            retained_sources={},
            allowed_policy_rule_ids=(),
        )


def test_support_validator_requires_evidence_span_to_exist_in_chunk() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": "La explicación documental.",
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [
                {"source_id": "source_1", "text": "frase inexistente"}
            ],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    with pytest.raises(StructuredResponseError, match="evidence_span_not_found"):
        StructuredResponseService().validate_support(
            envelope,
            expected_intent="SELECTED_CBC",
            allowed_fact_ids=(),
            retained_sources={"source_1": "Contenido documental autorizado."},
            allowed_policy_rule_ids=(),
        )


def test_support_validator_accepts_normalized_evidence_span() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": "La explicación documental.",
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [
                {"source_id": "source_1", "text": "Contenido documental"}
            ],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    StructuredResponseService().validate_support(
        envelope,
        expected_intent="SELECTED_CBC",
        allowed_fact_ids=(),
        retained_sources={"source_1": "  contenido   documental autorizado.  "},
        allowed_policy_rule_ids=(),
    )


def test_support_validator_accepts_grounded_spanish_claim_over_english_evidence() -> (
    None
):
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": "Los eritrocitos transportan oxígeno a los tejidos.",
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [
                {
                    "source_id": "source_1",
                    "text": "Erythrocytes transport oxygen to tissues.",
                }
            ],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    StructuredResponseService().validate_support(
        envelope,
        expected_intent="SELECTED_CBC",
        allowed_fact_ids=(),
        retained_sources={
            "source_1": "Erythrocytes transport oxygen to tissues."
        },
        allowed_policy_rule_ids=(),
    )


def test_cross_language_support_rejects_unrelated_spanish_claim() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": "Los eritrocitos causan cáncer en todos los perros.",
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [
                {
                    "source_id": "source_1",
                    "text": "Erythrocytes transport oxygen to tissues.",
                }
            ],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    with pytest.raises(StructuredResponseError, match="evidence_claim_mismatch"):
        StructuredResponseService().validate_support(
            envelope,
            expected_intent="SELECTED_CBC",
            allowed_fact_ids=(),
            retained_sources={
                "source_1": "Erythrocytes transport oxygen to tissues."
            },
            allowed_policy_rule_ids=(),
        )


def test_support_validator_rejects_unrelated_claim_with_a_real_span() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": "La exposición al frío siempre causa cambios permanentes en la sangre.",
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [
                {
                    "source_id": "source_1",
                    "text": "El hierro participa en funciones de la sangre",
                }
            ],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    with pytest.raises(StructuredResponseError, match="evidence_claim_mismatch") as captured:
        StructuredResponseService().validate_support(
            envelope,
            expected_intent="SELECTED_CBC",
            allowed_fact_ids=(),
            retained_sources={
                "source_1": "El hierro participa en funciones de la sangre."
            },
            allowed_policy_rule_ids=(),
        )
    assert captured.value.detail_code is not None
    assert captured.value.detail_code.startswith("proposition_1:overlap_")
    assert "frío" not in captured.value.detail_code


def test_documented_support_is_checked_for_each_proposition() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": (
                "Los leucocitos participan en la defensa inmunitaria y causan "
                "todos los cánceres."
            ),
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [
                {
                    "source_id": "source_1",
                    "text": "Los leucocitos participan en la defensa inmunitaria",
                }
            ],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    with pytest.raises(StructuredResponseError, match="evidence_claim_mismatch"):
        StructuredResponseService().validate_support(
            envelope,
            expected_intent="SELECTED_CBC",
            allowed_fact_ids=(),
            retained_sources={
                "source_1": (
                    "Los leucocitos participan en la defensa inmunitaria del organismo."
                )
            },
            allowed_policy_rule_ids=(),
        )


def test_documented_support_accepts_a_conservative_sentence_paraphrase() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_doc",
            "text": (
                "El hierro es un mineral relacionado con funciones de la sangre."
            ),
            "claim_type": "DOCUMENTED_GENERAL_KNOWLEDGE",
            "fact_ids": [],
            "source_ids": ["source_1"],
            "policy_rule_ids": [],
            "evidence_spans": [
                {"source_id": "source_1", "text": "El hierro es un mineral"}
            ],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    StructuredResponseService().validate_support(
        envelope,
        expected_intent="SELECTED_CBC",
        allowed_fact_ids=(),
        retained_sources={
            "source_1": (
                "El hierro es un mineral que participa en funciones de la sangre."
            )
        },
        allowed_policy_rule_ids=(),
    )


def test_support_validator_rejects_a_clinical_assertion_disguised_as_limitation() -> None:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_limitation",
            "text": "La exposición al frío siempre causa cambios permanentes en la sangre.",
            "claim_type": "LIMITATION",
            "fact_ids": [],
            "source_ids": [],
            "policy_rule_ids": [],
            "evidence_spans": [],
        }
    ]
    envelope = GeneratedResponseEnvelope.model_validate(payload)

    with pytest.raises(StructuredResponseError, match="limitation_claim_invalid"):
        StructuredResponseService().validate_support(
            envelope,
            expected_intent="SELECTED_CBC",
            allowed_fact_ids=(),
            retained_sources={},
            allowed_policy_rule_ids=(),
        )


def test_limitation_claim_cannot_assert_a_diagnosis_without_a_limitation() -> None:
    """Regression from the adversarial review of the validator relaxation.

    Removing the closed phrase whitelist left LIMITATION — the one claim type
    that needs no fact, no source and no evidence span — able to carry any
    prose that avoided a causal verb. The review confirmed "Lucas tiene
    anemia." being accepted end to end, because the last-resort diagnosis
    guard keys on "tu perro"/"el perro" and never on the pet's own name.
    """

    service = StructuredResponseService

    for accepted in (
        "No puedo emitir diagnosticos ni recomendar tratamientos.",
        "No realizo diagnosticos; consulta a un veterinario.",
        "No tengo acceso a datos clinicos en este momento.",
        "Un valor alto no significa que haya enfermedad.",
        "Un valor alto no necesariamente significa que haya enfermedad.",
        "Esta informacion no reemplaza la evaluacion profesional.",
        "Este hallazgo por si solo no es concluyente.",
        "El resultado es orientativo y requiere valoracion veterinaria.",
    ):
        assert service._limitation_text_is_safe(accepted), accepted

    for refused in (
        # A negation that does not govern the assertion must not license it.
        "sin duda la anemia causa debilidad",
        "la anemia no tratada causa debilidad severa",
        "No cabe duda: el paracetamol produce insuficiencia hepatica",
        # A measurement never belongs in a caveat.
        "El MCHC de 34.57 no permite confirmarlo",
    ):
        assert not service._limitation_text_is_safe(refused), refused

    # A diagnosis is refused, but by the clinical safety net rather than here.
    # Requiring this function to also recognize a closed list of "limitation"
    # wordings is what brought back `limitation_claim_invalid` in production
    # for a correct caveat. The division is deliberate: this contract keeps
    # measurements and unnegated mechanisms out of an uncited claim, and
    # OutputValidator decides what counts as asserting a disease — including
    # with the patient's own name as the subject, which it used to miss.
    from app.modules.llm_chat.application.services.output_validator import (
        OutputValidator,
    )

    validator = OutputValidator()
    for diagnosis in (
        "Lucas tiene anemia.",
        "Lucas presenta ehrlichiosis y necesita atencion.",
        "El hemograma confirma una infeccion.",
    ):
        assert validator._contains_definitive_diagnosis(diagnosis), diagnosis


def _shape_claim(claim_type: str, **support: object) -> dict[str, object]:
    return {
        "claim_id": "claim_001",
        "text": "Texto de prueba.",
        "claim_type": claim_type,
        "fact_ids": support.get("fact_ids", []),
        "source_ids": support.get("source_ids", []),
        "policy_rule_ids": support.get("policy_rule_ids", []),
        "evidence_spans": support.get("evidence_spans", []),
    }


def _shape_envelope(claim: dict[str, object]) -> dict[str, object]:
    payload = _payload()
    payload["claims"] = [claim]
    return payload


def test_conversational_claim_accepts_patient_facts_but_no_documentary_support() -> None:
    """The schema half of the relaxation.

    Citing a fact is what earns a conversational claim the right to name a
    value, and it is verified against that fact in send_chat_message. Source
    ids and policy rules stay closed to it, so it can never carry the
    evidence an interpretation would need.
    """

    service = StructuredResponseService()

    accepted = service.parse(
        json.dumps(
            _shape_envelope(
                _shape_claim("CONVERSATIONAL", fact_ids=["fact_analysis-1_WBC"])
            ),
            ensure_ascii=False,
        )
    )
    assert accepted.claims[0].fact_ids == ["fact_analysis-1_WBC"]

    with pytest.raises(StructuredResponseError):
        service.parse(
            json.dumps(
                _shape_envelope(_shape_claim("CONVERSATIONAL", source_ids=["S1"])),
                ensure_ascii=False,
            )
        )


def test_parametric_knowledge_still_cannot_cite_a_patient_fact() -> None:
    """Pretrained knowledge is not about this patient, so it cites no facts."""

    service = StructuredResponseService()

    with pytest.raises(StructuredResponseError):
        service.parse(
            json.dumps(
                _shape_envelope(
                    _shape_claim(
                        "PARAMETRIC_VETERINARY_KNOWLEDGE",
                        fact_ids=["fact_analysis-1_WBC"],
                    )
                ),
                ensure_ascii=False,
            )
        )


def test_transition_claim_cites_nothing_at_all() -> None:
    """A transition asserts nothing, so it has nothing to cite."""

    service = StructuredResponseService()

    assert service.parse(
        json.dumps(_shape_envelope(_shape_claim("TRANSITION")), ensure_ascii=False)
    ).claims[0].claim_type is ClaimType.TRANSITION

    for support in (
        {"fact_ids": ["fact_analysis-1_WBC"]},
        {"source_ids": ["S1"]},
        {"policy_rule_ids": ["selected_hemogram_context"]},
    ):
        with pytest.raises(StructuredResponseError):
            service.parse(
                json.dumps(
                    _shape_envelope(_shape_claim("TRANSITION", **support)),
                    ensure_ascii=False,
                ),
            )


def _alias_safety() -> dict[str, object]:
    return {
        "dx": False,
        "med": False,
        "dose": False,
        "freq": False,
        "dur": False,
        "pers": False,
        "urgent": False,
    }


def test_safety_schema_demands_the_short_aliases() -> None:
    """M-4: la gramática exige dx/med/dose/freq/dur/pers/urgent; los nombres
    largos siguen siendo válidos para cargas guardadas y fixtures."""

    schema = StructuredResponseService.json_schema()
    safety = schema["$defs"]["GeneratedSafety"]
    expected = {"dx", "med", "dose", "freq", "dur", "pers", "urgent"}

    assert set(safety["properties"]) == expected
    assert set(safety["required"]) == expected


def test_parse_accepts_alias_and_long_safety_names_alike() -> None:
    aliased = _payload()
    aliased["safety"] = {**_alias_safety(), "urgent": True}

    assert (
        StructuredResponseService.parse(json.dumps(aliased))
        .safety.requires_urgent_referral
        is True
    )
    assert (
        StructuredResponseService.parse(json.dumps(_payload()))
        .safety.requires_urgent_referral
        is False
    )


def _safety_guidance_payload() -> dict[str, object]:
    payload = _payload()
    payload["claims"] = [
        {
            "claim_id": "claim_001",
            "text": "No puedo indicar una dosis; esa decisión es del veterinario.",
            "claim_type": "SAFETY_GUIDANCE",
            "fact_ids": [],
            "source_ids": [],
            "policy_rule_ids": [],
            "evidence_spans": [],
        }
    ]
    return payload


def test_parse_materializes_the_sole_policy_rule_id() -> None:
    """M-1: con una única regla autorizada, el id omitido tiene un solo valor
    posible y lo rellena el backend, no la suerte del modelo."""

    envelope = StructuredResponseService.parse(
        json.dumps(_safety_guidance_payload()),
        sole_policy_rule_id="last_resort",
    )

    assert envelope.claims[0].policy_rule_ids == ["last_resort"]


def test_parse_without_a_sole_policy_rule_keeps_failing_closed() -> None:
    with pytest.raises(StructuredResponseError) as captured:
        StructuredResponseService.parse(json.dumps(_safety_guidance_payload()))

    assert captured.value.code == "structured_schema_invalid"


def test_parse_materializes_the_sole_fact_id_only_when_unambiguous() -> None:
    """M-2: el fact_id solo se rellena cuando existe exactamente un hecho
    autorizado; con ambigüedad el rechazo original se conserva."""

    payload = _payload()
    payload["claims"][0]["fact_ids"] = []

    envelope = StructuredResponseService.parse(
        json.dumps(payload),
        sole_fact_id="fact_wbc_001",
    )
    assert envelope.claims[0].fact_ids == ["fact_wbc_001"]

    with pytest.raises(StructuredResponseError):
        StructuredResponseService.parse(json.dumps(payload))


def test_materialized_support_survives_the_alias_rename() -> None:
    """Verificación del PASO 1: M-1 rellena un campo en un sobre cuyo bloque
    de seguridad llega con los alias de M-4, y las dos cosas aterrizan en el
    mismo sobre validado — ningún test anterior había visto ambas a la vez."""

    payload = _safety_guidance_payload()
    payload["safety"] = _alias_safety()

    envelope = StructuredResponseService.parse(
        json.dumps(payload),
        sole_policy_rule_id="educational_default",
    )

    assert envelope.claims[0].policy_rule_ids == ["educational_default"]
    assert envelope.safety.contains_dose is False

    StructuredResponseService().validate_support(
        envelope,
        expected_intent="SELECTED_CBC",
        allowed_fact_ids=(),
        retained_sources={},
        allowed_policy_rule_ids=("educational_default",),
    )


def test_refusal_grammar_pins_the_content_flags_to_false() -> None:
    """En un turno de rechazo el único patrón válido de los seis flags es
    todos-false (cualquier true muere en structured_safety_flags_invalid),
    así que la gramática lo fija: un campo con un solo valor válido no lleva
    información. GEN-13/GEN-14 morían porque el modelo marcaba los flags por
    el TEMA de la pregunta. En turnos clínicos los flags quedan libres."""

    refusal = StructuredResponseService.json_schema(
        allowed_policy_rule_ids=("direct_dose_request",),
        allowed_claim_types=(ClaimType.SAFETY_GUIDANCE, ClaimType.LIMITATION),
        require_policy_support=True,
    )
    safety = refusal["$defs"]["GeneratedSafety"]["properties"]
    for flag in ("dx", "med", "dose", "freq", "dur", "pers"):
        assert safety[flag].get("const") is False, flag
    assert "const" not in safety["urgent"]

    clinical = StructuredResponseService.json_schema(
        allowed_fact_ids=("fact_analysis-1_HCT",),
        require_patient_support=True,
    )
    safety_libre = clinical["$defs"]["GeneratedSafety"]["properties"]
    for flag in ("dx", "med", "dose", "freq", "dur", "pers"):
        assert "const" not in safety_libre[flag], flag
