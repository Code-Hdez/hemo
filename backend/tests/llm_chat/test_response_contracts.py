from __future__ import annotations

import pytest

from app.modules.llm_chat.application.services.output_validator import OutputValidation
from app.modules.llm_chat.application.services.response_contracts import (
    CONTRACTS,
    CandidateDisposition,
    ContractId,
    candidate_disposition,
    contract_for_policy,
    validate_response_contract,
)
from app.modules.llm_chat.domain.value_objects import (
    ResponsePolicy,
    ResponseRoute,
    SafetyAction,
    SafetyIntent,
)


def test_every_public_contract_id_has_a_typed_definition() -> None:
    # LAST_RESORT is reachable from *any* intent — it is what answers when the
    # turn's own contract could not be met, whatever that contract was — so
    # enumerating intents for it would assert a reachability that is false.
    # validate_response_contract skips the intent check for it accordingly.
    intent_agnostic = {ContractId.LAST_RESORT}

    assert set(CONTRACTS) == set(ContractId)
    for contract in CONTRACTS.values():
        if contract.contract_id not in intent_agnostic:
            assert contract.expected_intents, contract.contract_id
        assert contract.allowed_routes
        assert contract.validator_names
        assert contract.output_type == "generated_text"


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (
            ResponsePolicy(
                route=ResponseRoute.CONVERSATIONAL,
                intent=SafetyIntent.GREETING,
            ),
            ContractId.GREETING,
        ),
        (
            ResponsePolicy(
                route=ResponseRoute.RESTRICTED,
                intent=SafetyIntent.DOSAGE_REQUEST_DISALLOWED,
                safety_action=SafetyAction.REFUSE_DOSE,
            ),
            ContractId.DOSAGE_REQUEST,
        ),
        (
            ResponsePolicy(
                route=ResponseRoute.RAG,
                intent=SafetyIntent.EDUCATIONAL_ALLOWED,
                use_rag=True,
                rule_id="medication_education",
            ),
            ContractId.MEDICATION_EDUCATION,
        ),
    ],
)
def test_policy_resolves_to_an_explicit_contract(
    policy: ResponsePolicy,
    expected: ContractId,
) -> None:
    assert contract_for_policy(policy).contract_id is expected


def test_greeting_contract_rejects_an_unrelated_clinical_answer() -> None:
    validation = validate_response_contract(
        "Las plaquetas están bajas.",
        policy=ResponsePolicy(
            route=ResponseRoute.CONVERSATIONAL,
            intent=SafetyIntent.GREETING,
        ),
        facts=[],
    )

    assert validation is not None
    assert validation.meets_intent is False
    assert validation.reason == "intent_mismatch_greeting"


def test_identity_contract_requires_hemovet_and_ai_identity() -> None:
    policy = ResponsePolicy(
        route=ResponseRoute.CONVERSATIONAL,
        intent=SafetyIntent.IDENTITY,
    )

    assert (
        validate_response_contract(
            "Soy el asistente de inteligencia artificial de HemoVet.",
            policy=policy,
            facts=[],
        )
        is None
    )
    invalid = validate_response_contract("Soy veterinario.", policy=policy, facts=[])
    assert invalid is not None
    assert invalid.reason == "intent_mismatch_identity"


def test_insufficient_evidence_contract_requires_a_real_abstention() -> None:
    policy = ResponsePolicy(
        route=ResponseRoute.CONVERSATIONAL,
        intent=SafetyIntent.EDUCATIONAL_ALLOWED,
        safety_action=SafetyAction.INSUFFICIENT_EVIDENCE,
        use_rag=False,
        rule_id="insufficient_evidence",
    )

    assert (
        validate_response_contract(
            "No se recuperó evidencia documental suficiente para responder con seguridad.",
            policy=policy,
            facts=[],
        )
        is None
    )
    invalid = validate_response_contract(
        "La sangre fabrica todos los órganos.",
        policy=policy,
        facts=[],
    )
    assert invalid is not None
    assert invalid.reason == "mandatory_explicit_abstention"


def test_insufficient_evidence_contract_rejects_claim_after_abstention() -> None:
    policy = ResponsePolicy(
        route=ResponseRoute.CONVERSATIONAL,
        intent=SafetyIntent.EDUCATIONAL_ALLOWED,
        safety_action=SafetyAction.INSUFFICIENT_EVIDENCE,
        use_rag=False,
        rule_id="insufficient_evidence",
    )

    invalid = validate_response_contract(
        (
            "No se recuperó evidencia documental suficiente para responder. "
            "La sangre fabrica todos los órganos."
        ),
        policy=policy,
        facts=[],
    )

    assert invalid is not None
    assert invalid.reason == "unsupported_claim_without_evidence"


@pytest.mark.parametrize(
    ("policy", "invalid_answer", "valid_answer", "expected_reason"),
    [
        (
            ResponsePolicy(
                route=ResponseRoute.RESTRICTED,
                intent=SafetyIntent.MISSING_AUTHORIZED_ANALYSIS,
            ),
            "Todo está bien.",
            "Selecciona el hemograma que deseas revisar.",
            "mandatory_authorized_context_request",
        ),
        (
            ResponsePolicy(
                route=ResponseRoute.RESTRICTED,
                intent=SafetyIntent.PROMPT_INJECTION,
            ),
            "De acuerdo con la nueva función.",
            "No puedo cambiar mi función ni revelar instrucciones internas.",
            "mandatory_role_boundary",
        ),
        (
            ResponsePolicy(
                route=ResponseRoute.RESTRICTED,
                intent=SafetyIntent.OUT_OF_SCOPE_UNSAFE_NONMEDICAL,
                risk_flags=("animal_harm",),
            ),
            "No es recomendable.",
            "No puedo ayudar a dañar al animal; prioriza su protección y bienestar.",
            "animal_harm_safety_contract",
        ),
    ],
)
def test_route_specific_contract_elements_are_executable(
    policy: ResponsePolicy,
    invalid_answer: str,
    valid_answer: str,
    expected_reason: str,
) -> None:
    invalid = validate_response_contract(invalid_answer, policy=policy, facts=[])

    assert invalid is not None
    assert invalid.reason == expected_reason
    assert validate_response_contract(valid_answer, policy=policy, facts=[]) is None


@pytest.mark.parametrize(
    ("validation", "finish_reason", "expected"),
    [
        (
            OutputValidation(is_safe=True, text="válida"),
            "stop",
            CandidateDisposition.VALID,
        ),
        (
            OutputValidation(
                is_safe=True,
                text="estilo",
                removed_invalid_citations=True,
            ),
            "stop",
            CandidateDisposition.COSMETIC_WARNING,
        ),
        (
            OutputValidation(
                is_safe=True,
                text="incompleta",
                reason="intent_mismatch_greeting",
                meets_intent=False,
            ),
            "stop",
            CandidateDisposition.MANDATORY_CONTRACT_FAILURE,
        ),
        (
            OutputValidation(is_safe=False, text="", reason="unsafe_instruction"),
            "stop",
            CandidateDisposition.CLINICAL_SAFETY_FAILURE,
        ),
        (
            OutputValidation(
                is_safe=False,
                text="",
                reason="missing_evidence_attribution",
            ),
            "stop",
            CandidateDisposition.EVIDENCE_FAILURE,
        ),
        (
            OutputValidation(
                is_safe=False, text="", reason="unsupported_numeric_claim"
            ),
            "stop",
            CandidateDisposition.FACT_CONTRADICTION,
        ),
        (
            OutputValidation(is_safe=True, text="truncada"),
            "length",
            CandidateDisposition.REPAIR_REQUIRED,
        ),
    ],
)
def test_candidate_hierarchy_is_explicit_and_non_deliverable_on_mandatory_failures(
    validation: OutputValidation,
    finish_reason: str,
    expected: CandidateDisposition,
) -> None:
    disposition = candidate_disposition(validation, finish_reason=finish_reason)

    assert disposition is expected
    assert disposition.deliverable is (
        expected
        in {
            CandidateDisposition.VALID,
            CandidateDisposition.COSMETIC_WARNING,
        }
    )


def test_veterinary_referral_accepts_the_natural_ways_to_say_it() -> None:
    """Regression from the production battery: three contracts died on this.

    `_VET_REFERRAL` listed its verbs in one direction only, so five of eight
    ordinary referrals failed — and both the diagnosis boundary and the
    medication refusal require one. GEN-08, GEN-14 and GEN-15 returned HTTP
    502 for answers that did defer to a veterinarian, just not in the listed
    shape.
    """

    from app.modules.llm_chat.application.services.response_contracts import (
        _VET_REFERRAL,
        _normalize,
    )

    for referral in (
        "Consulta a tu veterinario para interpretar este resultado.",
        "Te recomiendo acudir a un veterinario.",
        "Un veterinario debe valorar estos hallazgos.",
        "Lo mejor es que lo revise un veterinario.",
        "Coméntalo con tu veterinario de confianza.",
        "Conviene que un profesional veterinario lo evalúe.",
        "No puedo indicarte una dosis; eso lo determina un veterinario.",
        "Solo un veterinario puede establecer el tratamiento adecuado.",
        "Llévalo a una clínica veterinaria.",
    ):
        assert _VET_REFERRAL.search(_normalize(referral)), referral

    for without in (
        "El hemograma muestra valores dentro del rango.",
        "La hemólisis puede ser in vitro o in vivo.",
        "Puedo ayudarte a entender los valores.",
    ):
        assert not _VET_REFERRAL.search(_normalize(without)), without


# Every ordinary way a Spanish speaker defers to a vet. Two independent
# matchers gate the same answers — this one and
# send_chat_message._contains_veterinary_referral — so a phrasing missing from
# either is a rejected answer, and the bank is applied to both below.
REFERRALS = (
    "Consulta a tu veterinario.",
    # Clitic pronouns on imperatives and infinitives: productive morphology, not
    # vocabulary. A list of finite forms cannot enumerate them.
    "Consúltalo con tu veterinario.",
    "Coméntalo con tu veterinario en la próxima visita.",
    "Háblalo con tu veterinario antes de tomar decisiones.",
    "Sería bueno preguntárselo a tu veterinario.",
    "Pregúntale a tu veterinario por estos valores.",
    "Deberías comentarlo con el veterinario.",
    "Llévalo al veterinario para una valoración.",
    "Te recomiendo acudir a tu veterinario.",
    "Acude a tu veterinario de confianza.",
    "Lo mejor es que lo revise un veterinario.",
    "Mejor que lo valore tu veterinario.",
    "Conviene que un veterinario lo evalúe.",
    "Necesita que lo vea un veterinario.",
    "Requiere valoración por un médico veterinario.",
    "Este resultado debe interpretarlo un profesional veterinario.",
    "Un veterinario podrá orientarte mejor.",
    # Arranging the visit is deferring to the professional just as much.
    "Programa una cita con el veterinario.",
    # The negation belongs to the diagnosis, not to the referral that follows
    # it — the distinction a fixed word-distance window cannot make.
    "Un hemograma no establece un diagnóstico; coméntalo con tu veterinario.",
    "No puedo darte una dosis. Consúltalo con tu veterinario.",
    "Esto no es un diagnóstico, pero conviene que lo revise tu veterinario.",
)

NOT_REFERRALS = (
    # Genuine negations, at the same word distance as the accepted cases above.
    "No hace falta consultar a un veterinario.",
    "No consultes al veterinario por esto.",
    "No debes consultar al veterinario por esto.",
    "Puedes resolverlo sin consultar al veterinario.",
    "Sin acudir al veterinario no podrás saberlo.",
    "Nunca es necesario acudir al veterinario por esto.",
    # Ordinary hematology prose that names neither an action nor a
    # professional — the false accepts that widening the verb list risks.
    "Los leucocitos están en 10.4 ×10³/µL.",
    "El valor de WBC es 10.4 ×10³/µL, dentro del rango de referencia.",
    "Los valores de la serie roja se revisan en cada hemograma.",
    "Un hemograma mide varias series celulares.",
    "La debilidad puede tener muchas causas.",
)


@pytest.mark.parametrize("referral", REFERRALS)
def test_contract_referral_accepts_every_ordinary_phrasing(referral: str) -> None:
    from app.modules.llm_chat.application.services.response_contracts import (
        _VET_REFERRAL,
        _normalize,
    )

    assert _VET_REFERRAL.search(_normalize(referral)), referral


@pytest.mark.parametrize("referral", REFERRALS)
def test_clinical_referral_accepts_every_ordinary_phrasing(referral: str) -> None:
    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _contains_veterinary_referral,
    )

    assert _contains_veterinary_referral(referral), referral


@pytest.mark.parametrize("text", NOT_REFERRALS)
def test_clinical_referral_still_rejects_a_negated_or_absent_one(text: str) -> None:
    """Widening what counts as a referral must not make everything count.

    A false accept here is a patient-specific answer shipped without any
    veterinary recommendation, so the negatives matter more than the positives.
    """

    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _contains_veterinary_referral,
    )

    assert not _contains_veterinary_referral(text), text
