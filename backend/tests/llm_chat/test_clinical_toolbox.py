"""Facts the model asks for, instead of a panel it is handed.

The measurement that motivates the whole thing, taken from production on
2026-08-06: a clinical turn sends 7.363 prompt tokens and spends 6 to 7 seconds
evaluating them before the first word, because the patient's whole materialized
panel travels in every prompt whether the question needs one value or nineteen.

``socratic-tutor`` puts a catalogue in the prompt and fetches content with a
tool. These tests pin the same shape here, and — more importantly — pin the
line the analysis draws in §4.4: their tutor has no patient, ours does, so what
a tool returns must still be exactly what the validators hold the answer to.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest

from app.modules.llm_chat.application.services.clinical_toolbox import (
    LIST_STUDIES,
    READ_PARAMETERS,
    ClinicalToolbox,
)
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    HemogramParameter,
    HemogramStudy,
    PatientContext,
    clinical_fact_id,
)
from app.modules.llm_chat.domain.entities import ToolCall


def _parameter(
    code: str,
    display: str,
    value: str,
    low: str,
    high: str,
    unit: str = "×10³/µL",
) -> HemogramParameter:
    return HemogramParameter(
        canonical_name=code,
        display_name=display,
        original_name=display,
        value=Decimal(value),
        value_text=value,
        unit=unit,
        reference_min=Decimal(low),
        reference_max=Decimal(high),
        flag="normal",
        reference_origin="laboratory",
    )


def _context() -> ClinicalContext:
    study = HemogramStudy(
        analysis_id="aabbaa43",
        study_key="H1",
        date="2026-07-04",
        label="Hemograma",
        laboratory="Laboratorio autorizado",
        pet_id="pet-1",
        parameters=(
            _parameter("WBC", "Leucocitos", "9.9", "5.5", "16.9"),
            _parameter("PLT", "Plaquetas", "481", "175", "500"),
            _parameter("MCHC", "MCHC", "34.57", "31", "38", "g/dL"),
        ),
    )
    return ClinicalContext(
        mode="selected_hemogram",
        patient=PatientContext(pet_id="pet-1", name="Lucas"),
        selected=study,
    )


def _toolbox() -> ClinicalToolbox:
    return ClinicalToolbox(clinical=_context())


def test_the_catalogue_says_what_exists_and_never_what_it_is_worth() -> None:
    """The prompt's whole clinical payload, in a few hundred characters.

    It names the studies and their parameters so the model can decide what to
    read. It carries no value, no range and no status: those are the tool's
    job, and putting them here would rebuild the panel this replaces.
    """

    catalogue = _toolbox().catalogue()

    assert "aabbaa43" in catalogue
    assert "2026-07-04" in catalogue
    assert "WBC" in catalogue and "PLT" in catalogue
    # No measurement leaked into the index.
    assert "9.9" not in catalogue
    assert "481" not in catalogue
    assert "34.57" not in catalogue
    assert len(catalogue) < 600


def test_reading_one_parameter_authorizes_one_parameter() -> None:
    """The saving and the safety property are the same property.

    A question about leukocytes returns one row, so the answer prompt carries
    one row — and only that row becomes claimable. Before, all nineteen
    travelled and all nineteen were claimable.
    """

    result = _toolbox().execute(
        ToolCall(name=READ_PARAMETERS, arguments={"parametros": ["leucocitos"]})
    )

    assert result.error is None
    assert "9.9" in result.content
    assert "481" not in result.content
    assert [fact["code"] for fact in result.authorized_facts] == ["WBC"]


def test_the_analyte_can_be_named_the_way_the_question_named_it() -> None:
    """Whatever the laboratory printed on the row.

    The same defect that made claims fail — the answer side reading only the
    lab's own label — would make the tool unusable if it were repeated here.
    """

    for phrase in ("WBC", "Leucocitos", "leucocitos"):
        result = _toolbox().execute(
            ToolCall(name=READ_PARAMETERS, arguments={"parametros": [phrase]})
        )
        assert [fact["code"] for fact in result.authorized_facts] == ["WBC"], phrase


def test_asking_for_nothing_returns_the_whole_panel() -> None:
    result = _toolbox().execute(ToolCall(name=READ_PARAMETERS, arguments={}))

    assert {fact["code"] for fact in result.authorized_facts} == {
        "WBC",
        "PLT",
        "MCHC",
    }


def test_an_unauthorized_study_is_refused_with_a_usable_message() -> None:
    """The model reads the error and corrects itself; nothing raises.

    A tool that throws costs the turn. A tool that explains costs one round.
    """

    result = _toolbox().execute(
        ToolCall(name=READ_PARAMETERS, arguments={"analysis_id": "de-otro-usuario"})
    )

    assert result.authorized_facts == ()
    assert result.error is not None
    assert LIST_STUDIES in result.error


def test_an_unknown_tool_is_refused_with_the_names_that_exist() -> None:
    result = _toolbox().execute(ToolCall(name="borrar_hemograma", arguments={}))

    assert result.error is not None
    assert READ_PARAMETERS in result.error


def test_no_tools_are_offered_without_an_authorized_study() -> None:
    """A general-scope turn has nothing to read, so it is offered nothing.

    Offering them anyway invites a round trip that can only come back empty,
    and at 13 tok/s a wasted round trip is seconds the user waits for nothing.
    """

    toolbox = ClinicalToolbox(clinical=ClinicalContext(mode="general"))

    assert toolbox.definitions() == ()
    assert toolbox.catalogue() == ""


def test_the_returned_facts_are_the_shape_the_validators_expect() -> None:
    """Otherwise the guarantee moves with the facts and quietly breaks.

    Downstream must not be able to tell whether a fact arrived through the
    prompt or through a tool — only that it was authorized. The fact_id is the
    load-bearing part: it is what a claim cites and what the registry is keyed
    by.
    """

    result = _toolbox().execute(
        ToolCall(name=READ_PARAMETERS, arguments={"parametros": ["PLT"]})
    )
    fact = result.authorized_facts[0]

    assert fact["fact_id"] == clinical_fact_id("aabbaa43", "PLT")
    assert fact["fact_type"] == "lab_value"
    assert fact["value"] == "481"
    assert fact["reference_min"] == "175"
    assert fact["reference_max"] == "500"
    assert fact["status"] == "normal"
    assert fact["analysis_date"] == "2026-07-04"


@pytest.mark.parametrize("enabled", [False, True])
def test_the_flow_is_switched_by_configuration(enabled: bool) -> None:
    """Both flows must be reachable, because only measurement decides.

    The tool round adds a generation and removes prompt tokens; which wins is
    a question about this hardware, not about design taste. The battery answers
    it, and it can only answer it if both shapes can be run.
    """

    from app.core.config import settings as app_settings
    from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings

    profile = dataclasses.replace(
        GenerationProfileSettings.from_settings(app_settings),
        tools_enabled=enabled,
    )

    assert profile.tools_enabled is enabled
    assert 1 <= profile.tool_max_rounds <= 5


# --------------------------------------------------------------------------
# The turn, end to end, with the new flow switched on
# --------------------------------------------------------------------------


class _ToolThenAnswerLLM:
    """Asks for one parameter, then answers. What the real model should do."""

    model_name = "qwen-tools-test"

    def __init__(self, envelope: str) -> None:
        self.envelope = envelope
        self.tool_requests: list[object] = []
        self.answer_requests: list[object] = []

    async def generate(self, request):
        from app.modules.llm_chat.domain.entities import ModelResponse, TokenUsage

        self.tool_requests.append(request)
        return ModelResponse(
            text="",
            model=self.model_name,
            usage=TokenUsage(prompt_tokens=120, completion_tokens=12),
            duration_ms=400,
            finish_reason="stop",
            tool_calls=(
                ToolCall(
                    name=READ_PARAMETERS,
                    arguments={"parametros": ["leucocitos"]},
                    call_id="0",
                ),
            )
            if not self.tool_requests[:-1]
            else (),
        )

    async def stream(self, request):
        from app.modules.llm_chat.domain.entities import ModelStreamChunk, TokenUsage

        self.answer_requests.append(request)
        yield ModelStreamChunk(text=self.envelope, model=self.model_name)
        yield ModelStreamChunk(
            done=True,
            model=self.model_name,
            usage=TokenUsage(prompt_tokens=900, completion_tokens=90),
            duration_ms=9000,
            finish_reason="stop",
        )


def test_the_answer_prompt_carries_only_what_the_model_asked_for() -> None:
    """The whole point, asserted on the prompt that reaches the model.

    The study has three parameters. The model asks for leukocytes. The answer
    prompt must contain that value and not the other two — that is the 7.363
    prompt tokens coming down, and it is also two fewer claims that can fail
    and cost a 50-second repair.
    """

    import asyncio
    import dataclasses

    from tests.llm_chat.test_structured_send_chat_message import (
        _claim,
        _command,
        _envelope,
        _use_case,
    )

    envelope = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "Los leucocitos están en 9.9 ×10³/µL, dentro del rango. "
                "Coméntalo con tu veterinario.",
                claim_type="PATIENT_FACT",
                fact_ids=[clinical_fact_id("aabbaa43", "WBC")],
            )
        ],
    )
    use_case, _, _ = _use_case([envelope], clinical=_context())
    use_case.llm = _ToolThenAnswerLLM(envelope)
    use_case.generation_settings = dataclasses.replace(
        use_case.generation_settings, tools_enabled=True
    )

    asyncio.run(
        use_case.execute(
            _command("¿Cómo están los leucocitos?", selected=True)
        )
    )

    answer_prompt = use_case.llm.answer_requests[0].user_prompt
    assert "9.9" in answer_prompt
    assert "481" not in answer_prompt
    assert "34.57" not in answer_prompt


def test_the_tool_prompt_carries_no_answer_schema() -> None:
    """1.934 of the 7.363 tokens, and the reason a tool call is possible.

    A grammar that forces the answer envelope leaves no token sequence in
    which a function call could be emitted, so sending the schema here would
    not merely be wasteful — it would make the round trip impossible.
    """

    import asyncio
    import dataclasses

    from tests.llm_chat.test_structured_send_chat_message import (
        _claim,
        _command,
        _envelope,
        _use_case,
    )

    envelope = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "Los leucocitos están en 9.9 ×10³/µL, dentro del rango. "
                "Coméntalo con tu veterinario.",
                claim_type="PATIENT_FACT",
                fact_ids=[clinical_fact_id("aabbaa43", "WBC")],
            )
        ],
    )
    use_case, _, _ = _use_case([envelope], clinical=_context())
    use_case.llm = _ToolThenAnswerLLM(envelope)
    use_case.generation_settings = dataclasses.replace(
        use_case.generation_settings, tools_enabled=True
    )

    asyncio.run(
        use_case.execute(_command("¿Cómo están los leucocitos?", selected=True))
    )

    tool_request = use_case.llm.tool_requests[0]
    assert tool_request.response_schema is None
    assert tool_request.tools
    assert {tool.name for tool in tool_request.tools} == {
        LIST_STUDIES,
        READ_PARAMETERS,
    }
    # And it is small: the catalogue, the question, and nothing else.
    assert len(tool_request.system_prompt) < 1200
