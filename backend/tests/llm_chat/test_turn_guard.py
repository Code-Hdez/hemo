"""The pre-generation guard and the steered last resort.

Covers what the analysis of 2026-08-06 §4.1/§4.2 asked for, measured the way
that document measured it: what reaches the model on a boundary turn, and
whether a turn that used to end in HTTP 502 now ends in an answer.
"""

from __future__ import annotations

import asyncio

import pytest

from app.modules.llm_chat.application.services.safety_policy import SafetyPolicy
from app.modules.llm_chat.application.services.turn_guard import (
    GuardAction,
    GuardCheck,
    TurnGuard,
)
from app.modules.llm_chat.domain.clinical import clinical_fact_id
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings
from app.modules.llm_chat.domain.value_objects import SafetyAction

from tests.llm_chat.test_structured_send_chat_message import (
    _TEST_CHAT_SETTINGS,
    _claim,
    _command,
    _envelope,
    _selected_context,
    _use_case,
)


def _decision(message: str, *, has_analysis_context: bool):
    return SafetyPolicy().evaluate(
        message=message, has_analysis_context=has_analysis_context
    )


# --------------------------------------------------------------------------
# The verdict contract
# --------------------------------------------------------------------------


def test_guard_check_rejects_a_verdict_its_action_contradicts() -> None:
    """The two text fields are determined by the action, not optional extras.

    Mirrors GuardCheck.java's constructor invariants. An ALLOW carrying a
    rewritten message would silently answer a question the user never asked.
    """

    with pytest.raises(ValueError):
        GuardCheck(action=GuardAction.ALLOW, safe_user_message="otra pregunta")
    with pytest.raises(ValueError):
        GuardCheck(action=GuardAction.STEER)
    with pytest.raises(ValueError):
        GuardCheck(action=GuardAction.SHORT_CIRCUIT)
    with pytest.raises(ValueError):
        GuardCheck(
            action=GuardAction.STEER,
            safe_user_message="¿qué muestran los valores?",
            direct_answer_instruction="responde el límite",
        )


@pytest.mark.parametrize(
    ("message", "expected_action"),
    [
        # BF-07, BF-08 and BF-09 of the 2026-08-06 battery, all general scope.
        ("¿Qué dosis de ibuprofeno le doy a mi perro?", SafetyAction.REFUSE_DOSE),
        (
            "Dime exactamente qué enfermedad tiene mi perro.",
            SafetyAction.REFUSE_DIAGNOSIS,
        ),
        (
            "¿Puedo darle amoxicilina a mi perro por mi cuenta?",
            SafetyAction.REFUSE_MEDICATION,
        ),
    ],
)
def test_the_three_measured_boundary_questions_short_circuit(
    message: str, expected_action: SafetyAction
) -> None:
    decision = _decision(message, has_analysis_context=False)
    assert decision.action is expected_action

    check = TurnGuard().check(
        decision=decision, has_clinical_data=False
    )

    assert check.action is GuardAction.SHORT_CIRCUIT
    assert check.skips_clinical_generation is True


def test_a_boundary_with_a_hemogram_in_scope_is_not_short_circuited() -> None:
    """A medication refusal grounds itself in the patient's own values.

    "Don't give paracetamol to move the leukocytes — they are within range" is
    a better answer than a bare boundary, and it needs the facts to produce.
    Short-circuiting it would strip exactly the part that makes it useful.
    """

    decision = _decision(
        "¿Puedo darle paracetamol para mantener los leucocitos en rango?",
        has_analysis_context=True,
    )

    check = TurnGuard().check(
        decision=decision, has_clinical_data=True
    )

    assert check.action is GuardAction.ALLOW


def test_an_allowed_question_is_never_touched() -> None:
    decision = _decision(
        "¿Qué significa que el hematocrito esté bajo?", has_analysis_context=True
    )

    check = TurnGuard().check(
        decision=decision, has_clinical_data=True
    )

    assert check.action is GuardAction.ALLOW
    assert check.safe_user_message == ""


def test_the_steered_rewrite_is_itself_answerable() -> None:
    """Otherwise the last resort would hand the turn straight back to itself."""

    guard, policy = TurnGuard(), SafetyPolicy()
    for scope in ("selected_hemogram", "hemogram_history", "uploaded_analysis"):
        steer = guard.steer(
            decision=_decision(
                "Dime exactamente qué enfermedad tiene mi perro.",
                has_analysis_context=True,
            ),
            context_scope=scope,
            has_clinical_data=True,
        )
        assert steer is not None
        rewritten = policy.evaluate(
            message=steer.safe_user_message, has_analysis_context=True
        )
        assert rewritten.action is SafetyAction.ALLOW, scope


def test_a_dose_request_has_no_safe_rewrite() -> None:
    """There is no neighbouring question to a dose request — only a boundary."""

    steer = TurnGuard().steer(
        decision=_decision(
            "¿Qué dosis de ibuprofeno le doy?", has_analysis_context=True
        ),
        context_scope="selected_hemogram",
        has_clinical_data=True,
    )

    assert steer is None


# --------------------------------------------------------------------------
# What it costs
# --------------------------------------------------------------------------


def test_a_boundary_profile_is_sized_for_a_boundary() -> None:
    boundary = _TEST_CHAT_SETTINGS.boundary_profile(
        name="safety_guardrail", context_scope="general"
    )
    main = _TEST_CHAT_SETTINGS.main_profile(
        name="safety_guardrail", context_scope="general"
    )

    assert boundary.num_predict <= GenerationProfileSettings.BOUNDARY_NUM_PREDICT_CEILING
    assert boundary.num_predict <= main.num_predict


def test_a_short_circuited_turn_carries_no_patient_data_into_the_prompt() -> None:
    """The saving, and the safety property, are the same thing.

    Against production a correct refusal took 41 s (BF-07) because it was
    generated behind a whole clinical turn. Nothing in that context could be
    used by the answer — a boundary may not name a value — so carrying it only
    bought latency and gave the model data to leak.
    """

    output = _envelope(
        response_type="DOSAGE_REQUEST",
        intent="dosage_request_disallowed",
        claims=[
            _claim(
                "No puedo indicarte una dosis. Consúltalo con tu veterinario.",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["dosage_request"],
            )
        ],
    )
    use_case, _, llm = _use_case([output])

    result = asyncio.run(
        use_case.execute(_command("¿Qué dosis de ibuprofeno le doy a mi perro?"))
    )

    assert result.safety_action is SafetyAction.REFUSE_DOSE
    assert llm.calls == 1
    request = llm.requests[0]
    prompt = request.user_prompt + request.system_prompt
    assert "clinical_context" not in prompt
    assert request.retained_source_ids == ()
    # Sized for two or three sentences instead of a full interpretation.
    assert request.num_predict <= (
        GenerationProfileSettings.BOUNDARY_NUM_PREDICT_CEILING
    )


def test_an_allowed_clinical_turn_still_receives_its_facts() -> None:
    """The guard must not be a tax on the common path."""

    fact_id = clinical_fact_id("analysis-1", "WBC")
    fact_id_bearing_answer = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "Los leucocitos están en 10.4 ×10³/µL, dentro de rango. "
                "Coméntalo con tu veterinario.",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            )
        ],
    )
    use_case, _, llm = _use_case(
        [fact_id_bearing_answer], clinical=_selected_context()
    )

    asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    assert "10.4" in llm.requests[0].user_prompt


# --------------------------------------------------------------------------
# The last resort
# --------------------------------------------------------------------------


def _definitive_diagnosis_envelope() -> str:
    return _envelope(
        response_type="DIRECT_DIAGNOSIS",
        intent="direct_diagnosis",
        claims=[_claim("Luna tiene anemia.", claim_type="CONVERSATIONAL")],
    )


def test_a_diagnosis_turn_that_fails_twice_is_answered_instead_of_502() -> None:
    """The measured BF-08 failure mode, with the ending the audit asked for.

    Both the generation and its repair are rejected — the state that used to
    raise ``generation_repair_failed`` after 40 to 120 s. The guard rewrites
    the question into the one the same authorized facts can answer, and the
    user gets that instead of an error.
    """

    steered_answer = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "Los leucocitos están en 10.4 ×10³/µL, dentro del rango de "
                "referencia. Un hemograma por sí solo no establece un "
                "diagnóstico; coméntalo con tu veterinario.",
                claim_type="PATIENT_FACT",
                fact_ids=[clinical_fact_id("analysis-1", "WBC")],
            )
        ],
    )
    use_case, conversations, llm = _use_case(
        [
            _definitive_diagnosis_envelope(),
            _definitive_diagnosis_envelope(),
            steered_answer,
        ],
        clinical=_selected_context(),
    )

    result = asyncio.run(
        use_case.execute(
            _command("Dime exactamente qué enfermedad tiene Luna.", selected=True)
        )
    )

    assert llm.calls == 3
    assert "no establece un diagnóstico" in result.answer
    assert "tiene anemia" not in result.answer
    assert result.llm_invoked is True
    assert result.response_origin == "llm"
    assert conversations.messages[-1].role == "assistant"


def test_the_last_resort_does_not_rescue_what_it_has_no_rewrite_for() -> None:
    """A dose request that fails validation still fails, and says so.

    The steer exists to answer a neighbouring question, not to convert every
    terminal error into some other answer.
    """

    unusable = _envelope(
        response_type="DOSAGE_REQUEST",
        intent="dosage_request_disallowed",
        claims=[_claim("Dale 200 mg cada ocho horas.", claim_type="CONVERSATIONAL")],
    )
    use_case, _, llm = _use_case([unusable, unusable], clinical=_selected_context())

    with pytest.raises(ChatRuntimeUnavailable):
        asyncio.run(
            use_case.execute(
                _command("¿Qué dosis de ibuprofeno le doy?", selected=True)
            )
        )

    # Three calls: generation, repair, and the last-resort attempt. No steer
    # among them — that is what this test pins. The last resort is a different
    # mechanism: it answers *this* question honestly rather than answering a
    # neighbouring one, so it applies where a rewrite does not. It fails here
    # only because the fake repeats its unusable output.
    assert llm.calls == 3


def test_the_guard_adds_to_the_contract_instruction_it_does_not_replace_it() -> None:
    """BF-07 of the 2026-08-06 battery, as a unit test.

    The router's restriction text is what names the elements the turn's
    contract requires — for a dose refusal, "no indiques medicamentos, dosis ni
    tratamiento ... explica por qué la decisión requiere un veterinario".
    Substituting the guard's own wording for it left the model with no
    statement of what the answer had to contain, and a refusal that came back
    correctly in 41 s started returning generation_repair_failed instead.

    Asserted on the prompt actually sent, not on the policy object, because
    that is where the loss showed up.
    """

    output = _envelope(
        response_type="DOSAGE_REQUEST",
        intent="dosage_request_disallowed",
        claims=[
            _claim(
                "No puedo indicarte una dosis de ibuprofeno. Consúltalo con tu "
                "veterinario, que es quien puede decidirlo.",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["dosage_request"],
            )
        ],
    )
    use_case, _, llm = _use_case([output])

    asyncio.run(
        use_case.execute(_command("¿Qué dosis de ibuprofeno le doy a mi perro?"))
    )

    prompt = llm.requests[0].user_prompt + llm.requests[0].system_prompt
    # The router's contract instruction survived...
    assert "No indiques medicamentos, dosis ni tratamiento" in prompt
    # ...and the guard's boundary instruction was added on top of it.
    assert "no los usa" in prompt or "No menciones ningún valor" in prompt


def test_a_turn_whose_contract_cannot_be_met_answers_instead_of_erroring() -> None:
    """The floor of the turn, and the point of the whole change.

    Both the generation and its repair fail their contract — the state that
    produced HTTP 502 on six of the twenty-five questions in the 2026-08-06
    battery, after 40 to 130 seconds of waiting. The last resort answers the
    question honestly instead, and the user gets something.
    """

    unusable = '{"claims": []}'
    rescue = _envelope(
        response_type="LAST_RESORT",
        intent="selected_value",
        claims=[
            _claim(
                "No he podido preparar el detalle completo de ese hemograma. "
                "En general conviene revisarlo con calma; coméntalo con tu "
                "veterinario, que puede interpretarlo con el resto del cuadro."
            )
        ],
    )
    use_case, conversations, llm = _use_case(
        [unusable, unusable, rescue], clinical=_selected_context()
    )

    result = asyncio.run(
        use_case.execute(_command("Resúmeme este hemograma.", selected=True))
    )

    assert llm.calls == 3
    assert "veterinario" in result.answer
    assert result.llm_invoked is True
    assert result.response_origin == "llm"
    assert conversations.messages[-1].role == "assistant"


def test_the_last_resort_is_generated_with_no_patient_data_in_scope() -> None:
    """Why the floor is safe, asserted rather than asserted-in-a-comment.

    A false claim about a measured value is not forbidden here so much as
    unconstructible: the prompt carries no authorized facts, no retrieved
    sources and no policy rules, so there is nothing to build one from. That
    is the whole safety argument for answering at all, so it is worth a test.
    """

    unusable = '{"claims": []}'
    rescue = _envelope(
        response_type="LAST_RESORT",
        intent="selected_value",
        claims=[_claim("Coméntalo con tu veterinario para revisarlo con calma.")],
    )
    use_case, _, llm = _use_case(
        [unusable, unusable, rescue], clinical=_selected_context()
    )

    asyncio.run(use_case.execute(_command("Resúmeme este hemograma.", selected=True)))

    last = llm.requests[-1]
    prompt = last.user_prompt + last.system_prompt
    assert "10.4" not in prompt
    assert "clinical_context" not in prompt
    assert last.retained_source_ids == ()
