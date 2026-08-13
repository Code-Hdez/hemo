from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.config import settings as _app_settings
from app.modules.llm_chat.api.schemas import chat_response_from_result
from app.modules.llm_chat.application.dto import ChatCommand
from app.modules.llm_chat.application.services.chat_profile_policy import ChatProfilePolicy
from app.modules.llm_chat.application.services.conversation_memory import ConversationMemoryService
from app.modules.llm_chat.application.services.output_sanitizer import OutputSanitizer
from app.modules.llm_chat.application.services.output_validator import OutputValidator
from app.modules.llm_chat.application.services.prompt_builder import PromptBuilder
from app.modules.llm_chat.application.services.retrieval_service import (
    RetrievalOutcome,
)
from app.modules.llm_chat.application.services.safety_policy import SafetyPolicy
from app.modules.llm_chat.application.services.structured_response import (
    StructuredResponseError,
    StructuredResponseService,
)
from app.modules.llm_chat.application.services.token_budget import TokenCounter
from app.modules.llm_chat.application.use_cases.send_chat_message import (
    SendChatMessageUseCase,
)
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    HemogramParameter,
    HemogramStudy,
    PatientContext,
    clinical_fact_id,
)
from app.modules.llm_chat.domain.entities import (
    ModelStreamChunk,
    RetrievedChunk,
    TokenUsage,
)
from app.modules.llm_chat.domain.exceptions import ChatRuntimeUnavailable
from app.modules.llm_chat.domain.generation_config import GenerationProfileSettings
from app.modules.llm_chat.domain.value_objects import SafetyAction

_TEST_CHAT_SETTINGS = dataclasses.replace(
    GenerationProfileSettings.from_settings(_app_settings),
    # Settings-class defaults (context_length=4096, max_input_tokens=3200)
    # are sized for the small local dev model. Structured-output envelopes
    # add real schema-instruction overhead on top of the prompt (observed
    # ~1.4k schema tokens alone), so this file's realistic clinical/RAG
    # fixtures need materially more room than the plain-prose files do.
    # Tests that specifically exercise budget-pressure/reservation behavior
    # build their own smaller, self-consistent profile instead of relying
    # on this shared default.
    context_length=16384,
    max_input_tokens=12000,
)


def _safety(*, urgent: bool = False) -> dict[str, bool]:
    return {
        "contains_diagnosis_confirmation": False,
        "contains_medication_recommendation": False,
        "contains_dose": False,
        "contains_frequency": False,
        "contains_treatment_duration": False,
        "contains_personalized_treatment": False,
        "requires_urgent_referral": urgent,
    }


def _envelope(
    *,
    response_type: str,
    intent: str,
    claims: list[dict[str, object]],
) -> str:
    return json.dumps(
        {
            "schema_version": "hemovet-response-v2",
            "response_type": response_type,
            "intent": intent,
            "claims": claims,
            "safety": _safety(),
        },
        ensure_ascii=False,
    )


def _claim(
    text: str,
    *,
    claim_id: str = "claim_001",
    claim_type: str = "CONVERSATIONAL",
    fact_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    policy_rule_ids: list[str] | None = None,
    evidence_spans: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "claim_id": claim_id,
        "text": text,
        "claim_type": claim_type,
        "fact_ids": fact_ids or [],
        "source_ids": source_ids or [],
        "policy_rule_ids": policy_rule_ids or [],
        "evidence_spans": evidence_spans or [],
    }


class ConversationRepository:
    def __init__(self) -> None:
        self.conversation_id = str(uuid4())
        self.messages = []

    async def get_or_create(
        self,
        conversation_id,
        _user_id,
        *,
        auth_session_id=None,
        browser_session_hash=None,
        context_scope="general",
        pet_id=None,
        analysis_id=None,
        context_fingerprint=None,
        force_new=False,
    ):
        return conversation_id or self.conversation_id

    async def get_completed_response(self, _conversation_id, _client_message_id):
        return None

    async def append(self, message) -> None:
        self.messages.append(message)

    async def complete_turn(self, message, *, memory_summary: str, memory_state: dict) -> None:
        self.messages.append(message)

    async def recent(self, _conversation_id, limit):
        return self.messages[-limit:]

    async def conversation_turns(self, *_args, **_kwargs):
        return [
            message
            for message in self.messages
            if message.status in {"completed", "refused"}
        ]


class ContextRepository:
    def __init__(self, clinical: ClinicalContext | None = None) -> None:
        self.clinical = clinical or ClinicalContext(mode="general")

    async def get_owned_context(self, **_kwargs) -> ClinicalContext:
        return self.clinical


class Retriever:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self.chunks = chunks or []

    async def retrieve(self, _query: str, **_kwargs) -> RetrievalOutcome:
        return RetrievalOutcome(chunks=self.chunks, available=True)


class StructuredSequenceLLM:
    model_name = "qwen-structured-test"

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.calls = 0
        self.requests = []

    async def stream(self, request):
        self.requests.append(request)
        output = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        yield ModelStreamChunk(text=output, model=self.model_name)
        yield ModelStreamChunk(
            done=True,
            model=self.model_name,
            usage=TokenUsage(prompt_tokens=40, completion_tokens=20),
            duration_ms=5,
            finish_reason="stop",
            provider_metrics={
                "prompt_eval_count": 40,
                "prompt_eval_duration_ms": 20,
                "eval_count": 20,
                "eval_duration_ms": 10,
                "total_duration_ms": 35,
            },
        )


def _selected_context() -> ClinicalContext:
    study = HemogramStudy(
        analysis_id="analysis-1",
        study_key="H1",
        date="2026-07-19",
        label="Hemograma",
        laboratory="Laboratorio autorizado",
        parameters=(
            HemogramParameter(
                canonical_name="WBC",
                display_name="Leucocitos",
                original_name="WBC",
                value=Decimal("10.4"),
                value_text="10.4",
                unit="×10³/µL",
                reference_min=Decimal("6"),
                reference_max=Decimal("17"),
                flag="normal",
                reference_origin="laboratory",
            ),
        ),
    )
    return ClinicalContext(
        mode="selected_hemogram",
        patient=PatientContext(pet_id="pet-1", name="Luna"),
        selected=study,
        history=(study,),
    )


def _use_case(
    outputs: list[str],
    *,
    clinical: ClinicalContext | None = None,
    chunks: list[RetrievedChunk] | None = None,
) -> tuple[SendChatMessageUseCase, ConversationRepository, StructuredSequenceLLM]:
    conversations = ConversationRepository()
    llm = StructuredSequenceLLM(outputs)
    use_case = SendChatMessageUseCase(
        conversations=conversations,
        analysis_context=ContextRepository(clinical),
        retriever=Retriever(chunks),
        llm=llm,
        safety=SafetyPolicy(),
        prompts=PromptBuilder(token_counter=TokenCounter()),
        output_sanitizer=OutputSanitizer(),
        output_validator=OutputValidator(),
        generation_settings=_TEST_CHAT_SETTINGS,
        public_response_builder=chat_response_from_result,
        chat_profiles=ChatProfilePolicy(settings=_TEST_CHAT_SETTINGS),
        memory_service=ConversationMemoryService(settings=_TEST_CHAT_SETTINGS.memory, token_counter=TokenCounter()),
        generation_limiter=asyncio.Semaphore(_TEST_CHAT_SETTINGS.runtime.max_concurrent_generations),
    )
    return use_case, conversations, llm


def _command(
    message: str,
    *,
    selected: bool = False,
) -> ChatCommand:
    return ChatCommand(
        user_id="user-1",
        client_message_id=str(uuid4()),
        conversation_id=None,
        message=message,
        context_scope="selected_hemogram" if selected else "general",
        analysis_id="analysis-1" if selected else None,
        pet_id="pet-1" if selected else None,
    )


def test_conversational_envelope_visible_and_schema_reaches_llm() -> None:
    output = _envelope(
        response_type="GREETING",
        intent="greeting",
        claims=[_claim("Hola, soy HemoVet. ¿En qué puedo ayudarte?")],
    )
    use_case, conversations, llm = _use_case([output])

    result = asyncio.run(use_case.execute(_command("Hola")))

    assert result.answer == "Hola, soy HemoVet. ¿En qué puedo ayudarte?"
    assert "schema_version" not in result.answer
    assert llm.requests[0].response_schema is not None
    assert llm.requests[0].response_schema["properties"]["intent"]["const"] == (
        "greeting"
    )
    claim_types = llm.requests[0].response_schema["$defs"]["ClaimType"]["enum"]
    assert "PATIENT_FACT" not in claim_types
    assert "DOCUMENTED_GENERAL_KNOWLEDGE" not in claim_types
    assert '"response_type":"GREETING"' in llm.requests[0].user_prompt
    metadata = conversations.messages[-1].metadata
    assert metadata["claim_ids"] == ["claim_001"]
    assert metadata["verified_fact_ids"] == []
    assert result.route_trace["structured_response_type"] == "GREETING"
    assert result.route_trace["claim_ids"] == ["claim_001"]
    assert result.route_trace["prompt_tokens"] == 40
    assert result.route_trace["generated_tokens"] == 20
    assert result.route_trace["prompt_tokens_per_second"] == 2000.0
    assert result.route_trace["generation_tokens_per_second"] == 2000.0
    assert result.route_trace["provider_metrics"]["queue_wait_ms"] >= 0


def test_structured_generation_honors_the_configured_num_predict() -> None:
    """The old ``_STRUCTURED_RESPONSE_NUM_PREDICT = 512`` floor (introduced
    in c81950b3, silently bumping num_predict for any structured request
    regardless of the configured profile) is gone as of this migration:
    ``PromptBuilder`` now always uses ``generation_profile.num_predict``
    unmodified (see ``build``/``build_conversational`` in
    ``prompt_builder.py``) — structured output no longer overrides the
    explicit, typed profile configuration.
    """
    output = _envelope(
        response_type="GREETING",
        intent="greeting",
        claims=[_claim("Hola, soy HemoVet. ¿En qué puedo ayudarte?")],
    )
    use_case, _, llm = _use_case([output])
    reserve = _TEST_CHAT_SETTINGS.context_reserve_tokens
    # 4608, no 4096: las descripciones de los flags de seguridad del esquema
    # crecieron a propósito (GEN-13/GEN-14, 2026-08-09) y el presupuesto
    # diminuto de este test estaba calibrado al tamaño anterior. El invariante
    # vigilado — num_predict configurado se respeta sin pisos ocultos — no
    # depende del número exacto.
    _tiny = 4608
    small_budget_settings = dataclasses.replace(
        _TEST_CHAT_SETTINGS,
        context_length=_tiny,
        general_context_length=None,
        selected_context_length=None,
        history_context_length=None,
        max_input_tokens=_tiny - 384 - reserve,
        num_predict=384,
        repair_context_length=_tiny,
        repair_max_input_tokens=_tiny - 384 - reserve,
        repair_num_predict=384,
    )
    use_case.chat_profiles = ChatProfilePolicy(settings=small_budget_settings)

    asyncio.run(use_case.execute(_command("Hola")))

    assert llm.requests[0].num_predict == 384
    assert llm.requests[0].prompt_stats["input_token_budget"] == _tiny - 384 - reserve


def test_structured_sse_buffers_json_and_emits_only_validated_claim_text() -> None:
    output = _envelope(
        response_type="GREETING",
        intent="greeting",
        claims=[_claim("Hola, soy HemoVet. ¿En qué puedo ayudarte?")],
    )
    use_case, _, _ = _use_case([output])

    async def collect():
        return [event async for event in use_case.stream(_command("Hola"))]

    events = asyncio.run(collect())
    names = [name for name, _ in events]
    # etapa 8 replaced the old per-token "delta" event (which mislabeled the
    # complete, already-validated answer as a streaming increment) with a
    # single "final" event sharing its payload with "done" (field "answer").
    finals = [data["answer"] for name, data in events if name == "final"]

    assert finals == ["Hola, soy HemoVet. ¿En qué puedo ayudarte?"]
    assert names.index("final") > max(
        index
        for index, (name, data) in enumerate(events)
        if name == "status" and data.get("stage") == "validating"
    )
    assert "schema_version" not in json.dumps(events, ensure_ascii=False)


def test_patient_fact_envelope_uses_a_materialized_fact_id() -> None:
    fact_id = clinical_fact_id("analysis-1", "WBC")
    output = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "El valor de WBC es 10.4 ×10³/µL.",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_002",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )
    use_case, conversations, llm = _use_case(
        [output],
        clinical=_selected_context(),
    )

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    assert result.answer.startswith("El valor de WBC es 10.4 ×10³/µL.")
    assert llm.calls == 1
    assert fact_id in llm.requests[0].user_prompt
    schema = llm.requests[0].response_schema
    claim_schema = schema["$defs"]["GeneratedClaim"]
    assert fact_id in claim_schema["properties"]["fact_ids"]["items"]["enum"]
    # This turn authorizes claim types that are *rejected* for carrying a
    # fact_id (PARAMETRIC_VETERINARY_KNOWLEDGE, TRANSITION) alongside ones that
    # require one. The grammar must therefore not demand a fact_id of every
    # claim: doing so left those types with no valid output at all, so a model
    # that picked one failed structured_schema_invalid and failed the repair
    # identically, since the repair reuses this schema. The per-type rule is
    # enforced by GeneratedClaim.validate_support_shape instead.
    claim_types = set(schema["$defs"]["ClaimType"]["enum"])
    assert claim_types & {"PARAMETRIC_VETERINARY_KNOWLEDGE", "TRANSITION"}
    assert "minItems" not in claim_schema["properties"]["fact_ids"]
    assert "fact_ids" not in claim_schema["required"]
    # etapa 4, Block D removed the enum-locked literal text (a backend-
    # written sentence the model could only echo): the model now writes its
    # own Spanish sentence, and correctness is verified post-hoc against the
    # materialized fact's vocabulary instead of constrained by the schema.
    assert "enum" not in schema["$defs"]["GeneratedClaim"]["properties"]["text"]


def test_general_diagnosis_boundary_rejects_a_definitive_claim_and_repairs() -> None:
    """A hardcoded, non-LLM deterministic refusal for safety boundaries
    doesn't exist anymore: etapa migration's stated goal is that every
    response is LLM-generated (see 9401b2a6's message), including safety
    refusals — ChatProfilePolicy.select() routes any non-ALLOW decision
    through a "safety_guardrail"/DIRECT_DIAGNOSIS generation profile rather
    than a backend-authored shortcut. A generation that violates the
    diagnosis boundary is now rejected and repaired like any other invalid
    structured output, not skipped before the provider is ever invoked.
    """
    unsafe = _envelope(
        response_type="DIRECT_DIAGNOSIS",
        intent="direct_diagnosis",
        claims=[
            _claim(
                "Definitivamente tiene ehrlichiosis.",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["direct_diagnosis"],
            )
        ],
    )
    safe = _envelope(
        response_type="DIRECT_DIAGNOSIS",
        intent="direct_diagnosis",
        claims=[
            _claim(
                "El hemograma por sí solo no permite confirmar un diagnóstico "
                "definitivo; conviene comentarlo con tu veterinario.",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["direct_diagnosis"],
            )
        ],
    )
    use_case, conversations, llm = _use_case([unsafe, safe])

    result = asyncio.run(
        use_case.execute(
            _command(
                "Diagnostica definitivamente ehrlichiosis a partir de estos datos."
            )
        )
    )

    assert result.safety_action is SafetyAction.REFUSE_DIAGNOSIS
    assert "ehrlichiosis" not in result.answer.lower()
    assert "no permite confirmar un diagnóstico" in result.answer.lower()
    assert "veterinario" in result.answer.lower()
    assert result.generation_attempts == 2
    assert llm.calls == 2


def test_patient_fact_receives_backend_policy_referral_claim() -> None:
    """etapa 4, Block D removed backend-authored prose entirely, including
    the fixed referral sentence this test used to see auto-appended: a
    patient-specific answer missing a veterinary referral now fails
    validation and must be repaired by the model itself (see
    ``_contains_veterinary_referral`` / ``missing_veterinary_referral`` in
    ``send_chat_message.py``), not silently patched in by the backend.
    """
    fact_id = clinical_fact_id("analysis-1", "WBC")
    output = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "El valor de WBC es 10.4 ×10³/µL.",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_002",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )
    use_case, conversations, _ = _use_case(
        [output],
        clinical=_selected_context(),
    )

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    assert result.answer.endswith("Conviene comentarlo con tu veterinario.")
    assert conversations.messages[-1].metadata["claim_ids"] == [
        "claim_001",
        "claim_002",
    ]
    assert conversations.messages[-1].metadata["verified_fact_ids"] == [fact_id]


def test_repeated_patient_parameter_options_include_authorized_dates() -> None:
    facts = [
        {
            "fact_id": "fact_wbc_old",
            "code": "WBC",
            "value": "9.2",
            "unit": "10^9/L",
            "analysis_date": "2026-06-01",
        },
        {
            "fact_id": "fact_wbc_new",
            "code": "WBC",
            "value": "18.4",
            "unit": "10^9/L",
            "analysis_date": "2026-07-01",
        },
    ]

    assert SendChatMessageUseCase._patient_fact_text_options(facts) == (
        "El valor de WBC del 2026-06-01 es 9.2 10^9/L.",
        "El valor de WBC del 2026-07-01 es 18.4 10^9/L.",
    )


def test_repeated_patient_fact_coverage_is_validated_not_rewritten() -> None:
    """etapa 4, Block D removed the backend-authored canonical-text rewrite
    (no backend prose ever replaces the model's own phrasing anymore) and
    replaced it with a coverage-only check: every repeated-analyte fact_id
    must be cited by some PATIENT_FACT claim, or validation fails and the
    model is asked to write the missing claim itself in a repair pass — the
    claim text/fact linkage the model wrote is never silently patched here.
    """
    facts = [
        {
            "fact_id": "fact_wbc_old",
            "code": "WBC",
            "value": "9.2",
            "unit": "10^9/L",
            "analysis_date": "2026-06-01",
        },
        {
            "fact_id": "fact_wbc_new",
            "code": "WBC",
            "value": "18.4",
            "unit": "10^9/L",
            "analysis_date": "2026-07-01",
        },
    ]

    def _envelope_with_fact_ids(fact_ids: list[list[str]]):
        return StructuredResponseService().parse(
            _envelope(
                response_type="HISTORY_COMPARISON",
                intent="history_comparison",
                claims=[
                    _claim(
                        f"Claim {index}.",
                        claim_id=f"claim_{index}",
                        claim_type="PATIENT_FACT",
                        fact_ids=ids,
                    )
                    for index, ids in enumerate(fact_ids)
                ],
            )
        )

    covering_envelope = _envelope_with_fact_ids([["fact_wbc_old"], ["fact_wbc_new"]])
    # Coverage is satisfied: no exception, and the model's own claim text and
    # fact linkage pass through completely unchanged.
    original_claims = [
        (claim.text, claim.fact_ids) for claim in covering_envelope.claims
    ]
    assert (
        SendChatMessageUseCase._validate_repeated_patient_fact_coverage(
            covering_envelope,
            facts=facts,
        )
        is None
    )
    assert [
        (claim.text, claim.fact_ids) for claim in covering_envelope.claims
    ] == original_claims

    incomplete_envelope = _envelope_with_fact_ids([["fact_wbc_old"]])
    with pytest.raises(
        StructuredResponseError, match="structured_patient_fact_coverage_missing"
    ):
        SendChatMessageUseCase._validate_repeated_patient_fact_coverage(
            incomplete_envelope,
            facts=facts,
        )


def test_patient_fact_accepts_materialized_date_and_laboratory() -> None:
    fact_id = clinical_fact_id("analysis-1", "WBC")
    output = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                (
                    "El WBC fue medido en el Laboratorio autorizado el "
                    "19 de julio de 2026 y su valor es 10.4 ×10³/µL."
                ),
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_002",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )
    use_case, _, llm = _use_case([output], clinical=_selected_context())

    result = asyncio.run(
        use_case.execute(_command("¿Cuándo se midió el WBC?", selected=True))
    )

    assert "Laboratorio autorizado" in result.answer
    assert "19 de julio de 2026" in result.answer
    assert llm.calls == 1


def _iron_source() -> RetrievedChunk:
    return RetrievedChunk(
        id="chunk-iron",
        text="El hierro es un mineral que participa en funciones de la sangre.",
        source_id="book-1",
        title="Hematología veterinaria",
        heading_path="Hierro",
        source_path="book.md",
        score=0.9,
    )


def _valid_iron_envelope() -> str:
    sentence = "El hierro es un mineral que participa en funciones de la sangre."
    return _envelope(
        response_type="MEDICATION_EDUCATION",
        intent="educational_allowed",
        claims=[
            _claim(
                sentence,
                claim_type="DOCUMENTED_GENERAL_KNOWLEDGE",
                source_ids=["S1"],
                evidence_spans=[{"source_id": "S1", "text": sentence}],
            )
        ],
    )


def test_documented_claim_accepts_a_literal_span_from_retained_evidence() -> None:
    use_case, conversations, llm = _use_case(
        [_valid_iron_envelope()],
        chunks=[_iron_source()],
    )

    result = asyncio.run(use_case.execute(_command("¿Qué es el hierro?")))

    assert result.answer.startswith("El hierro es un mineral")
    assert "EVIDENCE_USED" not in result.answer
    assert llm.calls == 1
    assert [source.id for source in result.sources] == ["chunk-iron"]
    schema = llm.requests[0].response_schema
    assert schema["$defs"]["ClaimType"]["enum"] == [
        "DOCUMENTED_GENERAL_KNOWLEDGE"
    ]
    claim_properties = schema["$defs"]["GeneratedClaim"]["properties"]
    assert claim_properties["source_ids"]["minItems"] == 1
    assert claim_properties["evidence_spans"]["minItems"] == 1
    assert claim_properties["policy_rule_ids"]["maxItems"] == 0
    assert conversations.messages[-1].metadata["claim_ids"] == ["claim_001"]
    assert '"documentary_evidence_required":true' in llm.requests[0].user_prompt
    assert "una oración literal de la evidencia retenida" in (
        llm.requests[0].user_prompt
    )
    assert "enum" not in claim_properties["text"]
    assert '"validator_names":["safety","intent","evidence","medication_education"]' in (
        llm.requests[0].user_prompt
    )


def test_documented_claim_translates_english_evidence_into_validated_spanish() -> None:
    source_sentence = "Erythrocytes transport oxygen to tissues."
    translated = "Los eritrocitos transportan oxígeno a los tejidos."
    source = RetrievedChunk(
        id="chunk-erythrocytes",
        text=source_sentence,
        source_id="book-erythrocytes",
        title="Veterinary hematology",
        heading_path="Erythrocytes",
        source_path="book.md",
        score=0.95,
    )
    output = _envelope(
        response_type="GENERAL_VETERINARY_EDUCATION",
        intent="allowed_cbc_general",
        claims=[
            _claim(
                translated,
                claim_type="DOCUMENTED_GENERAL_KNOWLEDGE",
                source_ids=["S1"],
                evidence_spans=[{"source_id": "S1", "text": source_sentence}],
            )
        ],
    )
    use_case, _, llm = _use_case([output], chunks=[source])

    result = asyncio.run(use_case.execute(_command("¿Qué son los eritrocitos?")))

    assert result.answer == translated
    assert [item.id for item in result.sources] == ["chunk-erythrocytes"]
    assert result.safety_action is SafetyAction.ALLOW
    assert llm.calls == 1
    schema = llm.requests[0].response_schema
    claim_schema = schema["$defs"]["GeneratedClaim"]["properties"]["text"]
    evidence_schema = schema["$defs"]["EvidenceSpan"]["properties"]["text"]
    assert "enum" not in claim_schema
    # Con el prompt ya renderizado, el enum del evidence_span se puebla con
    # las oraciones literales retenidas (_inject_documentary_sentence_options,
    # ronda 3 del 2026-08-09): copiar el span deja de ser una lotería de
    # transcripción y evidence_span_not_found se vuelve imposible por
    # construcción. La oración fuente de este test debe estar entre las
    # opciones.
    assert source_sentence in evidence_schema["enum"]
    assert "Redacta claim.text como una sola proposición en español" in (
        llm.requests[0].user_prompt
    )


def test_off_topic_retrieval_still_allows_a_parametric_education_answer() -> None:
    """Retrieval supports a safe educational answer; it never gates one.

    ``_build_response_plan`` and the empty-retrieval degradation both state
    this invariant ("documentary evidence only ever adds to what the model
    may claim, it is never the sole permission to answer"), but it was only
    ever implemented for the *empty* retrieval case. Any retrieved chunk,
    however unrelated to the question, collapsed the turn to
    documentary-only: the model had to cite material that did not support
    the answer and was then correctly blocked for doing so, so the question
    went unanswered. A claim that does cite a source is still validated
    literally; this only stops retrieval from being a precondition.
    """
    off_topic = RetrievedChunk(
        id="chunk-haemoplasma",
        text=(
            "Blood smear examination using routine Romanowsky stains permits "
            "the visualization of M. haemofelis in infected patients."
        ),
        source_id="book-haemoplasma",
        title="Veterinary hematology",
        heading_path="Haemoplasmas",
        source_path="book.md",
        score=0.7,
    )
    answer = "El hemograma evalúa la serie roja, la serie blanca y las plaquetas."
    output = _envelope(
        response_type="GENERAL_VETERINARY_EDUCATION",
        intent="allowed_cbc_general",
        claims=[_claim(answer, claim_type="PARAMETRIC_VETERINARY_KNOWLEDGE")],
    )
    use_case, _, llm = _use_case([output], chunks=[off_topic])

    result = asyncio.run(use_case.execute(_command("¿Qué evalúa un hemograma?")))

    assert result.answer == answer
    assert llm.calls == 1
    claim_definition = llm.requests[0].response_schema["$defs"]["GeneratedClaim"]
    claim_types = llm.requests[0].response_schema["$defs"]["ClaimType"]["enum"]
    # Both remain available: cite when the evidence genuinely supports the
    # point, answer from parametric knowledge when it does not.
    assert "DOCUMENTED_GENERAL_KNOWLEDGE" in claim_types
    assert "PARAMETRIC_VETERINARY_KNOWLEDGE" in claim_types
    assert "source_ids" not in claim_definition.get("required", [])
    assert "evidence_spans" not in claim_definition.get("required", [])
    assert "minItems" not in claim_definition["properties"]["source_ids"]


def test_unprovable_citation_is_dropped_instead_of_failing_the_turn() -> None:
    """Regression from the production battery: two textbook questions 502'd.

    "¿Qué información aporta un hemograma canino?" and "¿Qué diferencia hay
    entre hematocrito, hemoglobina y eritrocitos?" both ended in HTTP 502
    (`generation_repair_failed`, after 119 s and 79 s) with repair reasons
    `evidence_claim_mismatch` and `evidence_span_not_found`: the model cited a
    retrieved chunk whose literal wording its Spanish sentence could not
    reproduce closely enough. On a route that already allows parametric
    veterinary knowledge, the citation is dropped and the sentence stands on
    its own instead of the turn being lost.
    """

    source = RetrievedChunk(
        id="chunk-smear",
        text=(
            "Blood smear examination using routine Romanowsky stains permits "
            "the visualization of M. haemofelis in infected patients."
        ),
        source_id="book-haemoplasma",
        title="Veterinary hematology",
        heading_path="Haemoplasmas",
        source_path="book.md",
        score=0.7,
    )
    answer = "El hemograma evalúa la serie roja, la serie blanca y las plaquetas."
    output = _envelope(
        response_type="GENERAL_VETERINARY_EDUCATION",
        intent="allowed_cbc_general",
        claims=[
            _claim(
                answer,
                claim_type="DOCUMENTED_GENERAL_KNOWLEDGE",
                source_ids=["S1"],
                # A span the retained chunk does not contain: exactly the
                # `evidence_span_not_found` shape seen live.
                evidence_spans=[
                    {"source_id": "S1", "text": "El hemograma evalúa tres series."}
                ],
            )
        ],
    )
    use_case, conversations, llm = _use_case([output], chunks=[source])

    result = asyncio.run(use_case.execute(_command("¿Qué evalúa un hemograma?")))

    # The user reads the model's own sentence, unmodified.
    assert result.answer == answer
    assert llm.calls == 1
    # It just stops claiming a source it could not back.
    assert result.sources == []
    assert "EVIDENCE_USED" not in result.answer
    assert conversations.messages[-1].metadata["claim_ids"] == ["claim_001"]


def test_unprovable_citation_still_fails_where_the_route_must_cite() -> None:
    """Medication education has no parametric fallback, and keeps failing.

    The downgrade above is scoped to turns whose schema already offers
    PARAMETRIC_VETERINARY_KNOWLEDGE. A route whose whole contract is "answer
    only from the documentary corpus" must not silently become an uncited
    answer.
    """

    unprovable = _envelope(
        response_type="MEDICATION_EDUCATION",
        intent="educational_allowed",
        claims=[
            _claim(
                "El hierro participa en el transporte de oxígeno.",
                claim_type="DOCUMENTED_GENERAL_KNOWLEDGE",
                source_ids=["S1"],
                evidence_spans=[
                    {"source_id": "S1", "text": "El hierro transporta oxígeno."}
                ],
            )
        ],
    )
    use_case, _, _ = _use_case([unprovable, unprovable], chunks=[_iron_source()])

    with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
        asyncio.run(
            use_case.execute(_command("¿Puedo darle hierro a mi perro?"))
        )


def test_two_unverified_documentary_generations_raise_a_typed_technical_error() -> (
    None
):
    """The backend-authored "insufficient evidence" abstention that used to
    substitute a fixed, backend-written answer here was removed by etapa 4,
    Block D/E (see ``_persist_result``'s docstring: a response the provider
    never validly produced is not persisted under any response_origin — it
    becomes the same typed technical error regardless of route or safety
    action). Two invalid documentary generations now fail exactly like the
    non-documentary case in
    ``test_second_structured_failure_returns_a_typed_retryable_error``.
    """
    use_case, conversations, llm = _use_case(
        ["no es json", '{"claims": []}'],
        chunks=[_iron_source()],
    )

    with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
        asyncio.run(use_case.execute(_command("¿Qué son los eritrocitos?")))

    # Three calls, not two: after the generation and its repair both
    # fail, the last-resort contract gets one attempt to answer without
    # any patient data in scope. Here it fails too — the fake repeats
    # its last output — so the typed error still surfaces, which is the
    # floor of the floor and must keep working.
    assert llm.calls == 3
    assert not [
        message for message in conversations.messages if message.role == "assistant"
    ]


def test_wrong_intent_is_repaired_once_without_leaking_the_first_claim() -> None:
    invalid = _envelope(
        response_type="GREETING",
        intent="selected_value",
        claims=[_claim("Las plaquetas están bajas.")],
    )
    valid = _envelope(
        response_type="GREETING",
        intent="greeting",
        claims=[_claim("Hola, soy HemoVet. ¿Cómo puedo ayudarte?")],
    )
    use_case, _, llm = _use_case([invalid, valid])

    result = asyncio.run(use_case.execute(_command("Hola")))

    assert result.answer == "Hola, soy HemoVet. ¿Cómo puedo ayudarte?"
    assert "plaquetas" not in result.answer.casefold()
    assert result.generation_attempts == 2
    assert llm.calls == 2
    assert llm.requests[1].profile_name.endswith("_structured_repair")
    assert llm.requests[1].response_schema is not None


def test_unknown_fact_id_is_repaired_and_never_reaches_the_user() -> None:
    fact_id = clinical_fact_id("analysis-1", "WBC")
    invalid = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "El WBC inventado es 999 ×10³/µL.",
                claim_type="PATIENT_FACT",
                fact_ids=["fact_inventado"],
            )
        ],
    )
    valid = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "El valor de WBC es 10.4 ×10³/µL.",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_002",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )
    use_case, _, llm = _use_case([invalid, valid], clinical=_selected_context())

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    assert "999" not in result.answer
    assert "10.4" in result.answer
    assert llm.calls == 2


@pytest.mark.parametrize(
    "unsupported_text",
    [
        "Las PLT están normales.",
        "El WBC pertenece a una mascota de raza Husky.",
        "El WBC pertenece a un Labrador.",
        "El WBC corresponde a Luna.",
        "El WBC fue medido en Madrid.",
    ],
)
def test_valid_fact_id_cannot_support_a_different_patient_claim(
    unsupported_text: str,
) -> None:
    fact_id = clinical_fact_id("analysis-1", "WBC")
    invalid = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                unsupported_text,
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            )
        ],
    )
    valid = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "El valor de WBC es 10.4 ×10³/µL.",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_002",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )
    use_case, _, llm = _use_case([invalid, valid], clinical=_selected_context())

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    assert unsupported_text not in result.answer
    assert "10.4" in result.answer
    assert llm.calls == 2


@pytest.mark.parametrize(
    "invalid_claim",
    [
        _claim(
            "Afirmación con fuente inventada.",
            claim_type="DOCUMENTED_GENERAL_KNOWLEDGE",
            source_ids=["S999"],
            evidence_spans=[{"source_id": "S999", "text": "inventada"}],
        ),
        _claim(
            "Afirmación con fragmento inventado.",
            claim_type="DOCUMENTED_GENERAL_KNOWLEDGE",
            source_ids=["S1"],
            evidence_spans=[{"source_id": "S1", "text": "frase inexistente"}],
        ),
    ],
)
def test_unknown_source_or_span_is_repaired_before_visible_delivery(
    invalid_claim: dict[str, object],
) -> None:
    invalid = _envelope(
        response_type="MEDICATION_EDUCATION",
        intent="educational_allowed",
        claims=[invalid_claim],
    )
    use_case, _, llm = _use_case(
        [invalid, _valid_iron_envelope()],
        chunks=[_iron_source()],
    )

    result = asyncio.run(use_case.execute(_command("¿Qué es el hierro?")))

    assert "inventad" not in result.answer.casefold()
    assert llm.calls == 2


def _valid_insufficient_evidence_envelope() -> str:
    return _envelope(
        response_type="INSUFFICIENT_EVIDENCE",
        intent="educational_allowed",
        claims=[
            _claim(
                "No se recuperó evidencia documental suficiente para responder con seguridad.",
                claim_type="LIMITATION",
            )
        ],
    )


def _valid_iron_parametric_envelope() -> str:
    return _envelope(
        response_type="GENERAL_VETERINARY_EDUCATION",
        intent="educational_allowed",
        claims=[
            _claim(
                "El hierro es un mineral que participa en funciones de la sangre.",
                claim_type="PARAMETRIC_VETERINARY_KNOWLEDGE",
            )
        ],
    )


def test_empty_retrieval_falls_back_to_parametric_knowledge_not_insufficient_evidence() -> (
    None
):
    """No RAG evidence for an otherwise RAG-optional educational question no
    longer forces an INSUFFICIENT_EVIDENCE abstention (etapa 5's RAG
    decoupling): send_chat_message's evidence gate degrades the effective
    contract from the strict, evidence-required MEDICATION_EDUCATION down to
    GENERAL_VETERINARY_EDUCATION ("retrieval_gap_degraded_to_parametric_or_
    database"), which allows an unsourced PARAMETRIC_VETERINARY_KNOWLEDGE
    claim — the model's own knowledge — instead of a forced abstention.
    """
    use_case, conversations, llm = _use_case(
        [_valid_iron_parametric_envelope()],
        chunks=[],
    )

    result = asyncio.run(use_case.execute(_command("¿Qué es el hierro?")))

    assert result.safety_action is SafetyAction.ALLOW
    assert result.answer.startswith("El hierro es un mineral")
    assert result.sources == []
    assert llm.calls == 1
    assert (
        llm.requests[0].response_schema["properties"]["response_type"]["const"]
        == "GENERAL_VETERINARY_EDUCATION"
    )
    assert "PARAMETRIC_VETERINARY_KNOWLEDGE" in (
        llm.requests[0].response_schema["$defs"]["ClaimType"]["enum"]
    )
    assert conversations.messages[-1].metadata["structured_response_type"] == (
        "GENERAL_VETERINARY_EDUCATION"
    )


def test_empty_required_retrieval_rejects_wrong_response_type_and_repairs() -> None:
    """A generation for a RAG-optional, evidence-empty educational question
    must use the degraded GENERAL_VETERINARY_EDUCATION contract (see
    test_empty_retrieval_falls_back_to_parametric_knowledge_not_insufficient_
    evidence); a claim using the wrong response_type is rejected by
    ``_contract_for``'s ``expected_response_type`` check and repaired.
    """
    invalid = _envelope(
        response_type="INSUFFICIENT_EVIDENCE",
        intent="educational_allowed",
        claims=[_claim("La sangre fabrica todos los órganos.")],
    )
    use_case, _, llm = _use_case(
        [invalid, _valid_iron_parametric_envelope()],
        chunks=[],
    )

    result = asyncio.run(use_case.execute(_command("¿Qué es el hierro?")))

    assert "fabrica" not in result.answer.casefold()
    assert result.safety_action is SafetyAction.ALLOW
    assert result.answer.startswith("El hierro es un mineral")
    assert result.generation_attempts == 2
    assert llm.calls == 2
    assert result.generation_attempts == 2


def test_second_structured_failure_returns_a_typed_retryable_error() -> None:
    use_case, conversations, llm = _use_case(["no es json", '{"claims": []}'])

    with pytest.raises(
        ChatRuntimeUnavailable,
        match="generation_repair_failed",
    ) as failed:
        asyncio.run(use_case.execute(_command("Hola")))

    assert failed.value.code == "generation_repair_failed"
    # Three calls, not two: after the generation and its repair both
    # fail, the last-resort contract gets one attempt to answer without
    # any patient data in scope. Here it fails too — the fake repeats
    # its last output — so the typed error still surfaces, which is the
    # floor of the floor and must keep working.
    assert llm.calls == 3
    assert not [
        message for message in conversations.messages if message.role == "assistant"
    ]


def test_schema_rejection_logs_the_envelope_size_next_to_the_error_code() -> None:
    """§8.3 of the 2026-08-05 audit: ``structured_schema_invalid`` survived 6
    of 62 questions with the schema already travelling to Ollama as ``format``,
    and the logs could not say whether the envelope had been cut off at
    ``num_predict`` or whether llama.cpp's JSON-Schema→GBNF conversion had
    dropped a constraint. Both facts now sit on the same event as the code.
    """
    envelope = '{"claims": []}'
    use_case, _, llm = _use_case([envelope, envelope])
    logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[method-assign]
    logger.addHandler(handler)
    try:
        with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
            asyncio.run(use_case.execute(_command("Hola")))
    finally:
        logger.removeHandler(handler)

    events = [
        json.loads(record.getMessage().split(" ", 1)[1])
        for record in records
        if record.getMessage().startswith("llm_chat.validation ")
    ]
    # Three now: the generation, its repair, and the last-resort attempt that
    # answers without patient data when both fail. Each logs its own envelope
    # size next to its own error code, which is the property under test.
    assert len(events) == 3
    for event, request in zip(events, llm.requests, strict=True):
        assert event["structured_error_code"] == "structured_schema_invalid"
        assert event["finish_reason"] == "stop"
        assert event["envelope_chars"] == len(envelope)
        assert event["completion_tokens"] == 20
        assert event["num_predict"] == request.num_predict
    # The repair runs on its own profile, so the ceiling the second envelope
    # was measured against is the repair one, not the first request's.
    assert llm.requests[1].num_predict == _TEST_CHAT_SETTINGS.repair_num_predict


def test_envelope_size_is_not_logged_for_semantic_structured_failures() -> None:
    """A wrong ``response_type`` is a semantic rejection: the envelope parsed
    whole, so its size explains nothing and would only add noise to the event.
    """
    envelope = _envelope(
        response_type="SELECTED_CBC",
        intent="greeting",
        claims=[_claim("Hola, soy HemoVet. ¿En qué puedo ayudarte?")],
    )
    use_case, _, _ = _use_case([envelope, envelope])
    logger = logging.getLogger("uvicorn.error.hemovet.llm_chat")
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append  # type: ignore[method-assign]
    logger.addHandler(handler)
    try:
        with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
            asyncio.run(use_case.execute(_command("Hola")))
    finally:
        logger.removeHandler(handler)

    events = [
        json.loads(record.getMessage().split(" ", 1)[1])
        for record in records
        if record.getMessage().startswith("llm_chat.validation ")
    ]
    assert events
    for event in events:
        assert event["structured_error_code"] == "structured_response_type_mismatch"
        assert "envelope_chars" not in event


def test_nearby_care_repeated_failure_raises_a_typed_technical_error() -> None:
    """Originally a regression test (confirmed live 2026-08-04, the day
    before this migration commit) for a per-intent graceful-degradation
    allowlist that NEARBY_VETERINARY_CARE was missing from. etapa 4 later
    replaced that whole allowlist-based rescue with a uniform rule: any
    route whose generation fails validation twice raises the same typed
    technical error, with no per-intent exceptions (see
    ``_persist_result``'s docstring) — so this is no longer a gap to patch,
    it is the deliberate, uniform behavior for every intent.
    """
    use_case, conversations, llm = _use_case(["no es json", "no es json"])

    with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
        asyncio.run(
            use_case.execute(_command("¿Hay alguna veterinaria cerca de mi casa?"))
        )

    # Three calls, not two: after the generation and its repair both
    # fail, the last-resort contract gets one attempt to answer without
    # any patient data in scope. Here it fails too — the fake repeats
    # its last output — so the typed error still surfaces, which is the
    # floor of the floor and must keep working.
    assert llm.calls == 3
    assert not [
        message for message in conversations.messages if message.role == "assistant"
    ]


def test_interpretive_question_about_selected_value_raises_a_typed_technical_error() -> (
    None
):
    """Originally a regression test (confirmed live 2026-08-04, the day
    before this migration commit) for a per-intent/per-scope graceful-
    degradation rescue that selected_hemogram/hemogram_history were missing
    from. etapa 4 later replaced that whole rescue with a uniform rule: any
    route whose generation fails validation twice raises the same typed
    technical error, with no per-intent or per-scope exceptions (see
    ``_persist_result``'s docstring) — so the interpretive-question-without-
    RAG-grounding case is no longer a gap to patch, it is the deliberate,
    uniform behavior.
    """
    use_case, conversations, llm = _use_case(
        ["no es json", "no es json"],
        clinical=_selected_context(),
    )

    with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
        asyncio.run(
            use_case.execute(
                _command(
                    "¿Que significa que el WBC este alto en un perro?", selected=True
                )
            )
        )

    # Three calls, not two: after the generation and its repair both
    # fail, the last-resort contract gets one attempt to answer without
    # any patient data in scope. Here it fails too — the fake repeats
    # its last output — so the typed error still surfaces, which is the
    # floor of the floor and must keep working.
    assert llm.calls == 3
    assert not [
        message for message in conversations.messages if message.role == "assistant"
    ]


def test_interpretive_history_question_raises_a_typed_technical_error() -> None:
    """Same failure family as
    test_interpretive_question_about_selected_value_raises_a_typed_technical_error,
    for hemogram_history scope. Originally written for a per-intent/per-scope
    graceful-degradation rescue; etapa 4 later replaced that rescue with a
    uniform rule (see ``_persist_result``'s docstring): any route whose
    generation fails validation twice raises the same typed technical error,
    with no per-intent or per-scope exceptions. The exact/interpret-overlap
    routing nuance this docstring used to flag is a routing concern
    (conversation_routing.py), independent of this now-uniform failure
    behavior, and out of scope here.

    Deliberately avoids words like "anterior"/"cambio"/"comparacion" in the
    question: conversation_routing._exact_value also matches those (natural
    vocabulary for a history question) and, unlike selected_hemogram_context,
    hemogram_history_context ANDs interpret with `not exact` — so a message
    combining both would read as a pure exact-value lookup (use_rag=False
    from routing itself, never attempting RAG) instead of reaching this path.
    """

    def study(key: str, date: str, wbc: str) -> HemogramStudy:
        return HemogramStudy(
            analysis_id=key,
            study_key=key,
            date=date,
            label="Hemograma",
            laboratory="Laboratorio autorizado",
            parameters=(
                HemogramParameter(
                    canonical_name="WBC",
                    display_name="Leucocitos",
                    original_name="WBC",
                    value=Decimal(wbc),
                    value_text=wbc,
                    unit="×10³/µL",
                    reference_min=Decimal("5.5"),
                    reference_max=Decimal("16.9"),
                    flag="normal",
                ),
            ),
        )

    history_context = ClinicalContext(
        mode="hemogram_history",
        history=(
            study("previous", "2026-07-09", "8.2"),
            study("current", "2026-07-16", "10.4"),
        ),
    )

    use_case, conversations, llm = _use_case(
        ["no es json", "no es json"],
        clinical=history_context,
    )

    with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
        asyncio.run(
            use_case.execute(
                ChatCommand(
                    user_id="user-1",
                    client_message_id=str(uuid4()),
                    conversation_id=None,
                    message="¿Por que el WBC se observa asi en un perro?",
                    context_scope="hemogram_history",
                    analysis_id=None,
                    pet_id=None,
                )
            )
        )

    # Three calls, not two: after the generation and its repair both
    # fail, the last-resort contract gets one attempt to answer without
    # any patient data in scope. Here it fails too — the fake repeats
    # its last output — so the typed error still surfaces, which is the
    # floor of the floor and must keep working.
    assert llm.calls == 3
    assert not [
        message for message in conversations.messages if message.role == "assistant"
    ]


def test_interpretive_selected_value_question_gets_a_grounded_explanation() -> None:
    """Before allow_grounded_explanation existed, an interpretive question
    about a specific selected-hemogram value ("que significa que el MCHC
    este alto") was structurally unanswerable: the SELECTED_CBC contract's
    patient_supported branch only ever allowed a PATIENT_FACT claim whose
    text is locked (by the generation schema itself) to an exact literal
    projection of the value — no claim type in that branch could add any
    explanation, regardless of what evidence was available. The question
    either got a bare, unhelpful value citation or the model tried to
    explain anyway and failed the "no interpretation" contract, eventually
    degrading to the generic INSUFFICIENT_EVIDENCE abstention after two
    failed attempts (or, before an earlier fix in this same session, a hard
    502/503).

    Now, when conversation_routing classifies the question as interpretive
    (allow_grounded_explanation=True) and RAG retrieval finds a real
    source, the model can emit a second PATIENT_FACT_EXPLANATION claim
    grounded in a literal evidence_span from that source. This is the
    actual "conversational, with context" behavior asked for — an
    explanation, not just a number — while staying anti-hallucination safe:
    fact_ids/source_ids stay restricted to the authorized/retained sets,
    and any interpretive claim still requires a literal quoted source.
    """
    study = HemogramStudy(
        analysis_id="analysis-1",
        study_key="H1",
        date="2026-07-19",
        label="Hemograma",
        laboratory="Laboratorio autorizado",
        parameters=(
            HemogramParameter(
                canonical_name="MCHC",
                display_name="MCHC",
                original_name="MCHC",
                value=Decimal("40.2"),
                value_text="40.2",
                unit="g/dL",
                reference_min=Decimal("31"),
                reference_max=Decimal("38"),
                flag="high",
            ),
        ),
    )
    clinical = ClinicalContext(
        mode="selected_hemogram",
        patient=PatientContext(pet_id="pet-1", name="Lucas"),
        selected=study,
        history=(study,),
    )
    chunk_text = (
        "Un MCHC elevado puede sugerir hemolisis in vitro o in vivo, y conviene "
        "correlacionarlo con el frotis y el contexto clinico del paciente."
    )
    chunk = RetrievedChunk(
        id="chunk-mchc",
        text=chunk_text,
        source_id="veterinary-hematology",
        title="Hematologia Veterinaria",
        heading_path="MCHC",
        source_path="hematology.md",
        score=0.9,
    )
    fact_id = clinical_fact_id("analysis-1", "MCHC")
    output = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "El MCHC es 40.2 g/dL.",
                claim_id="claim_001",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
            _claim(
                chunk_text,
                claim_id="claim_002",
                claim_type="PATIENT_FACT_EXPLANATION",
                fact_ids=[fact_id],
                source_ids=["S1"],
                evidence_spans=[{"source_id": "S1", "text": chunk_text}],
            ),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_003",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )
    use_case, _, llm = _use_case([output], clinical=clinical, chunks=[chunk])

    result = asyncio.run(
        use_case.execute(
            _command(
                "¿Qué significa que el MCHC esté alto en un perro?", selected=True
            )
        )
    )

    assert result.safety_action is SafetyAction.ALLOW
    assert "El MCHC es 40.2 g/dL." in result.answer
    assert "hemolisis" in result.answer.casefold()
    assert llm.calls == 1
    # Two claims for one fact_id must be schema-representable: the rigid
    # "exactly one claim, enum-locked text" shape used for plain PATIENT_FACT
    # answers (maxItems == minItems == fact count) would make this second,
    # free-text explanatory claim impossible to emit at all.
    assert llm.requests[0].response_schema["properties"]["claims"].get("maxItems") != 1


def _conversational_value_envelope(text: str, fact_id: str) -> str:
    return _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(text, claim_type="CONVERSATIONAL", fact_ids=[fact_id]),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_002",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )


def test_conversational_claim_may_state_an_authorized_value_in_its_own_register() -> None:
    """A value can now be said the way a person would say it.

    Before this, a conversational claim could not carry fact_ids at all, so
    naming a value obliged the model to open a separate PATIENT_FACT claim
    whose text had to be a materialized projection of the fact. The visible
    answer is a concatenation of claim texts, so an answer that mixed a
    greeting register with a value came out as two blocks joined by a blank
    line. The sentence below is rejected as a PATIENT_FACT (see the test
    right after this one) precisely because "Te cuento" is not part of the
    fact's own vocabulary.
    """

    fact_id = clinical_fact_id("analysis-1", "WBC")
    output = _conversational_value_envelope(
        "Te cuento: los leucocitos están en 10.4 ×10³/µL.", fact_id
    )
    use_case, conversations, llm = _use_case([output], clinical=_selected_context())

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    assert "Te cuento: los leucocitos están en 10.4 ×10³/µL." in result.answer
    assert llm.calls == 1
    # The fact is still recorded as verified: citing conversationally is
    # citing, not an escape from attribution.
    assert conversations.messages[-1].metadata["verified_fact_ids"] == [fact_id]


def test_patient_fact_without_referral_is_completed_not_killed() -> None:
    """Ronda 5: este turno moría con missing_veterinary_referral (dos
    generaciones y generation_repair_failed) porque el sobre válido no traía
    el cierre. La frase de derivación es boilerplate: la añade el código y el
    turno entrega a la primera. (La regla de proyección de PATIENT_FACT
    acepta esta frase desde la exención de alias — verificado también en el
    código anterior.)"""

    fact_id = clinical_fact_id("analysis-1", "WBC")
    output = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "Te cuento: los leucocitos están en 10.4 ×10³/µL.",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
        ],
    )
    use_case, _, llm = _use_case([output, output], clinical=_selected_context())

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    assert llm.calls == 1
    assert result.answer.startswith("Te cuento: los leucocitos están en 10.4 ×10³/µL.")
    assert "veterinario" in result.answer


def test_conversational_claim_cannot_state_a_value_the_facts_do_not_carry() -> None:
    """The register is free; the numbers are not.

    This is the check that makes the relaxation safe: a claim carrying
    fact_ids is verified against them whatever its type, so an invented
    figure fails exactly as it would in a PATIENT_FACT claim.
    """

    fact_id = clinical_fact_id("analysis-1", "WBC")
    output = _conversational_value_envelope(
        "Te cuento: los leucocitos están en 25.9 ×10³/µL.", fact_id
    )
    use_case, _, _ = _use_case([output, output], clinical=_selected_context())

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    # La claim con la cifra inventada se descarta igual que siempre — nunca
    # llega al usuario. Ronda 5: el turno ya no muere tras dos generaciones;
    # el dato correcto lo aporta el completado determinista desde el hecho
    # autorizado.
    assert "25.9" not in result.answer
    assert "10.4" in result.answer


def test_conversational_claim_may_not_interpret_the_value_it_cites() -> None:
    """Saying it naturally is not the same as saying what it means.

    A conversational claim cannot carry source_ids by schema, so it can
    never quote the evidence an interpretation would need. Allowing it to
    interpret anyway would be the one way this change could widen what the
    assistant asserts, and it does not.
    """

    fact_id = clinical_fact_id("analysis-1", "WBC")
    output = _conversational_value_envelope(
        "Te cuento: los leucocitos están en 10.4 ×10³/µL, lo que sugiere una infección.",
        fact_id,
    )
    use_case, _, _ = _use_case([output, output], clinical=_selected_context())

    result = asyncio.run(
        use_case.execute(_command("¿Qué valor tienen los leucocitos?", selected=True))
    )

    # La interpretación sin evidencia se descarta igual que siempre. Ronda 5:
    # el turno entrega el dato autorizado en vez de morir tras dos intentos.
    assert "sugiere una infección" not in result.answer
    assert "10.4" in result.answer


def test_conversational_claim_citing_nothing_still_cannot_write_a_value() -> None:
    """The old guard is untouched for claims that cite nothing.

    Only citing buys the right to name a parameter or write a digit while
    patient data is in scope.
    """

    output = _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(
                "Te cuento: los leucocitos están en 10.4 ×10³/µL.",
                claim_type="CONVERSATIONAL",
            ),
        ],
    )
    use_case, _, _ = _use_case([output, output], clinical=_selected_context())

    with pytest.raises(ChatRuntimeUnavailable, match="generation_repair_failed"):
        asyncio.run(
            use_case.execute(
                _command("¿Qué valor tienen los leucocitos?", selected=True)
            )
        )


def _mchc_case() -> tuple[ClinicalContext, RetrievedChunk, str]:
    study = HemogramStudy(
        analysis_id="analysis-1",
        study_key="H1",
        date="2026-07-19",
        label="Hemograma",
        laboratory="Laboratorio autorizado",
        parameters=(
            HemogramParameter(
                canonical_name="MCHC",
                display_name="MCHC",
                original_name="MCHC",
                value=Decimal("40.2"),
                value_text="40.2",
                unit="g/dL",
                reference_min=Decimal("31"),
                reference_max=Decimal("38"),
                flag="high",
            ),
        ),
    )
    clinical = ClinicalContext(
        mode="selected_hemogram",
        patient=PatientContext(pet_id="pet-1", name="Lucas"),
        selected=study,
        history=(study,),
    )
    chunk_text = (
        "Un MCHC elevado puede sugerir hemolisis in vitro o in vivo, y conviene "
        "correlacionarlo con el frotis y el contexto clinico del paciente."
    )
    chunk = RetrievedChunk(
        id="chunk-mchc",
        text=chunk_text,
        source_id="veterinary-hematology",
        title="Hematologia Veterinaria",
        heading_path="MCHC",
        source_path="hematology.md",
        score=0.9,
    )
    return clinical, chunk, chunk_text


def _transition_envelope(transition_text: str, fact_id: str, chunk_text: str) -> str:
    return _envelope(
        response_type="SELECTED_CBC",
        intent="selected_value",
        claims=[
            _claim(transition_text, claim_id="claim_001", claim_type="TRANSITION"),
            _claim(
                "El MCHC es 40.2 g/dL.",
                claim_id="claim_002",
                claim_type="PATIENT_FACT",
                fact_ids=[fact_id],
            ),
            _claim(
                chunk_text,
                claim_id="claim_003",
                claim_type="PATIENT_FACT_EXPLANATION",
                fact_ids=[fact_id],
                source_ids=["S1"],
                evidence_spans=[{"source_id": "S1", "text": chunk_text}],
            ),
            _claim(
                "Conviene comentarlo con tu veterinario.",
                claim_id="claim_004",
                claim_type="SAFETY_GUIDANCE",
                policy_rule_ids=["selected_hemogram_context"],
            ),
        ],
    )


def test_transition_claim_may_name_the_topic_it_announces() -> None:
    """Connective tissue had nowhere to live.

    The answer is a concatenation of claim texts, and every existing type
    either asserts a fact or has to avoid naming a parameter at all
    (structured_patient_fact_id_required). So "vamos con el MCHC" — which
    asserts nothing and is what makes an answer read as prose rather than a
    list — could not be written. TRANSITION is exempt from the
    parameter-name guard and from nothing else.
    """

    clinical, chunk, chunk_text = _mchc_case()
    fact_id = clinical_fact_id("analysis-1", "MCHC")
    output = _transition_envelope(
        "Vamos con el MCHC, que es el que llama la atención aquí.",
        fact_id,
        chunk_text,
    )
    use_case, _, llm = _use_case([output], clinical=clinical, chunks=[chunk])

    result = asyncio.run(
        use_case.execute(
            _command("¿Qué significa que el MCHC esté alto en un perro?", selected=True)
        )
    )

    assert result.answer.startswith("Vamos con el MCHC")
    assert "El MCHC es 40.2 g/dL." in result.answer
    assert llm.calls == 1
    assert "TRANSITION" in llm.requests[0].response_schema["$defs"]["ClaimType"]["enum"]


@pytest.mark.parametrize(
    "texto, aguja",
    [
        # La cifra del propio hecho. Aun siendo cierta, el claim no la cita.
        ("Vamos con el MCHC, que está en 40.2 g/dL.", "40.2"),
        # Una cifra inventada del mismo analito: el riesgo clínico de verdad.
        ("Vamos con el MCHC, que está en 99.9 g/dL.", "99.9"),
        # Y de otro analito, que ni siquiera está en alcance.
        ("Ojo que los leucocitos están en 45.7 mil/uL.", "45.7"),
    ],
)
def test_transition_claim_cannot_carry_a_number(texto: str, aguja: str) -> None:
    r"""The trade that lets it name parameters freely.

    A transition announces a topic; the moment it states a quantity it is
    asserting something it cites nothing for. The digit ban on it is
    unconditional, unlike the general one, which only applies when patient
    values are in scope.

    **Qué cambió aquí, y por qué no es relajar nada.** Este test exigía que el
    turno MURIERA con `generation_repair_failed`. Se puso rojo en `bd70e0d8`
    —«salvage the envelope»—, que junto con `671483f9` —«give the turn a floor
    instead of an error page»— sustituyó a propósito esa consecuencia: un claim
    rechazado ya no tumba el turno, se descarta y el resto se entrega. La regla
    no se movió ni se perdió: sigue en send_chat_message.py, `if re.search(r"\d",
    claim.text) and (authorized_codes or claim.claim_type is
    ClaimType.TRANSITION)`, lanzando `structured_numeric_support_required`.

    Lo que este test vigilaba era el mecanismo de entrega, no la regla. Ahora
    vigila la regla: **el texto ofensivo y su cifra no llegan al lector**. Es
    estrictamente más fuerte que la versión anterior, que sólo probaba la cifra
    real del hecho; los dos casos inventados —99.9 y 45.7— son el riesgo
    clínico auténtico y no estaban cubiertos. Y se falsificó: neutralizando la
    guarda, los tres casos fallan.

    El contraste con `test_transition_claim_can_name_the_parameter_it_announces`
    es lo que hace del dígito el discriminador: sin cifra, el mismo claim
    sobrevive y encabeza la respuesta.
    """

    clinical, chunk, chunk_text = _mchc_case()
    fact_id = clinical_fact_id("analysis-1", "MCHC")
    output = _transition_envelope(texto, fact_id, chunk_text)
    use_case, _, _ = _use_case(
        [output, output], clinical=clinical, chunks=[chunk, chunk]
    )

    result = asyncio.run(
        use_case.execute(
            _command("¿Qué significa que el MCHC esté alto en un perro?", selected=True)
        )
    )

    assert texto not in result.answer, "el claim prohibido llegó al lector"
    # La cifra sólo puede aparecer si la puso el relleno determinista desde un
    # hecho autorizado y citado, nunca arrastrada por el claim descartado.
    if aguja != "40.2":
        assert aguja not in result.answer, f"se filtró una cifra sin respaldo: {aguja}"


def test_series_coverage_requires_the_endpoints_not_every_middle_point() -> None:
    """La instrucción de historial pide comparar «el estudio anterior y el más
    reciente»; exigir las ocho repeticiones contradecía esa misma instrucción
    y mataba cada pregunta de historial con serie real (2026-08-09). Los
    extremos conservan la propiedad anti-cereza: el valor de hoy no puede
    mostrarse fingiendo que la serie no existe."""

    facts = [
        {
            "fact_id": "fact_plt_a",
            "code": "PLT",
            "value": "220",
            "unit": "10^9/L",
            "study_date": "2026-05-01",
        },
        {
            "fact_id": "fact_plt_b",
            "code": "PLT",
            "value": "255",
            "unit": "10^9/L",
            "study_date": "2026-06-01",
        },
        {
            "fact_id": "fact_plt_c",
            "code": "PLT",
            "value": "290",
            "unit": "10^9/L",
            "study_date": "2026-07-01",
        },
    ]

    def _envelope_with_fact_ids(fact_ids: list[list[str]]):
        return StructuredResponseService().parse(
            _envelope(
                response_type="HISTORY_COMPARISON",
                intent="history_comparison",
                claims=[
                    _claim(
                        f"Claim {index}.",
                        claim_id=f"claim_{index}",
                        claim_type="PATIENT_FACT",
                        fact_ids=ids,
                    )
                    for index, ids in enumerate(fact_ids)
                ],
            )
        )

    endpoints = _envelope_with_fact_ids([["fact_plt_a"], ["fact_plt_c"]])
    assert (
        SendChatMessageUseCase._validate_repeated_patient_fact_coverage(
            endpoints, facts=facts
        )
        is None
    )

    solo_reciente = _envelope_with_fact_ids([["fact_plt_c"]])
    with pytest.raises(
        StructuredResponseError, match="structured_patient_fact_coverage_missing"
    ):
        SendChatMessageUseCase._validate_repeated_patient_fact_coverage(
            solo_reciente, facts=facts
        )

    sin_extremo_antiguo = _envelope_with_fact_ids([["fact_plt_b"], ["fact_plt_c"]])
    with pytest.raises(
        StructuredResponseError, match="structured_patient_fact_coverage_missing"
    ):
        SendChatMessageUseCase._validate_repeated_patient_fact_coverage(
            sin_extremo_antiguo, facts=facts
        )

    # Sin study_date los extremos no existen: el requisito completo se
    # conserva, cerrado al fallo.
    sin_fechas = [dict(fact, study_date="") for fact in facts]
    with pytest.raises(
        StructuredResponseError, match="structured_patient_fact_coverage_missing"
    ):
        SendChatMessageUseCase._validate_repeated_patient_fact_coverage(
            _envelope_with_fact_ids([["fact_plt_a"], ["fact_plt_c"]]),
            facts=sin_fechas,
        )


def test_false_incapacity_phrases_are_matched_narrowly() -> None:
    """La puerta rechaza negar el ACCESO a datos que el contexto sí autoriza
    (SEL-07), sin tocar las declaraciones legítimas de un dato ausente."""

    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _FALSE_INCAPACITY,
    )

    positivas = [
        "No tengo acceso a los valores del paciente en este momento.",
        "no puedo acceder a sus estudios clínicos",
        "No dispongo de los datos del hemograma.",
    ]
    negativas = [
        "El valor de reticulocitos no está disponible en este estudio.",
        "Ese parámetro no aparece en el estudio seleccionado.",
        "El MPV es un campo imputado, no medido.",
    ]
    for frase in positivas:
        assert _FALSE_INCAPACITY.search(frase.lower()), frase
    for frase in negativas:
        assert not _FALSE_INCAPACITY.search(frase.lower()), frase


def test_false_source_incapacity_phrases_are_matched_narrowly() -> None:
    """Negar referencias con evidencia retenida es la variante sobre fuentes
    de la falsa incapacidad; declarar que la fuente no sostiene una
    afirmación sigue siendo válido."""

    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _FALSE_SOURCE_INCAPACITY,
    )

    positivas = [
        "No tengo acceso a una lista de referencias específicas.",
        "No puedo proporcionar referencias bibliográficas en este momento.",
        "no dispongo de fuentes para citarte",
    ]
    negativas = [
        "La fuente retenida no sostiene esa afirmación.",
        "El valor no tiene rango de referencia informado.",
        "Esta explicación viene de conocimiento veterinario general.",
    ]
    for frase in positivas:
        assert _FALSE_SOURCE_INCAPACITY.search(frase.lower()), frase
    for frase in negativas:
        assert not _FALSE_SOURCE_INCAPACITY.search(frase.lower()), frase


def test_series_endpoint_ids_mirror_the_coverage_rule() -> None:
    """Lo que el contrato promete en prosa debe ser exactamente lo que el
    validador de cobertura exige: extremos por analito repetido, misma
    precedencia de fecha, series sin fecha descartadas."""

    from app.modules.llm_chat.application.use_cases.send_chat_message import (
        _series_endpoint_ids,
    )

    facts = [
        {"fact_id": "f_plt_a", "code": "PLT", "analysis_date": "2026-05-01"},
        {"fact_id": "f_plt_b", "code": "PLT", "analysis_date": "2026-06-01"},
        {"fact_id": "f_plt_c", "code": "PLT", "analysis_date": "2026-07-01"},
        {"fact_id": "f_wbc_unico", "code": "WBC", "analysis_date": "2026-07-01"},
        {"fact_id": "f_hct_sin_fecha_1", "code": "HCT"},
        {"fact_id": "f_hct_sin_fecha_2", "code": "HCT"},
    ]

    extremos = _series_endpoint_ids(facts)

    assert extremos == {"PLT": ["f_plt_a", "f_plt_c"]}


def test_unverifiable_citation_downgrades_to_conversational_in_clinical_turns() -> None:
    """Las rutas clínicas grounded no autorizan PARAMETRIC en su enum, así que
    la cita inverificable era fatal justo en los turnos de interpretación
    (FLU-06/08 con claim_entailment_rejected, ~100-170 s de reparación). El
    destino CONVERSATIONAL conserva los fact_ids —el anclaje se sigue
    verificando idéntico— y suelta solo la insignia documental."""

    from unittest.mock import MagicMock

    from app.modules.llm_chat.application.services.structured_response import (
        ClaimType,
    )

    envelope = StructuredResponseService().parse(
        _envelope(
            response_type="SELECTED_CBC",
            intent="selected_cbc",
            claims=[
                _claim(
                    "El RDW mide la variabilidad del tamaño eritrocitario.",
                    claim_id="claim_1",
                    claim_type="PATIENT_FACT_EXPLANATION",
                    fact_ids=["fact_analysis-1_RDW"],
                    source_ids=["S1"],
                    evidence_spans=[
                        {
                            "source_id": "S1",
                            "text": "a sentence the retained chunk never contains",
                        }
                    ],
                )
            ],
        )
    )
    use_case = MagicMock()
    use_case.structured_response_service = StructuredResponseService()
    use_case._log_event = MagicMock()
    request = MagicMock()
    request.response_schema = {
        "$defs": {
            "ClaimType": {
                "enum": [
                    ClaimType.CONVERSATIONAL.value,
                    ClaimType.PATIENT_FACT.value,
                    ClaimType.PATIENT_FACT_EXPLANATION.value,
                ]
            }
        }
    }

    rewritten = SendChatMessageUseCase._drop_unverifiable_citations(
        use_case,
        envelope,
        request=request,
        retained_sources={"S1": "texto retenido que no contiene el span"},
    )

    claim = rewritten.claims[0]
    assert claim.claim_type is ClaimType.CONVERSATIONAL
    assert claim.fact_ids == ["fact_analysis-1_RDW"]
    assert claim.source_ids == []
    assert claim.evidence_spans == []


def test_evidence_span_enum_is_populated_from_retained_sources() -> None:
    """La gramática siempre supo imponer el enum del evidence_span; nadie lo
    poblaba porque en _contract_for el prompt aún no existía. Con el prompt
    renderizado, las opciones salen de los mismos textos que validate_support
    verifica: evidence_span_not_found imposible por construcción."""

    from unittest.mock import MagicMock

    use_case = MagicMock()
    use_case._documentary_sentence_options = (
        SendChatMessageUseCase._documentary_sentence_options
    )
    request = MagicMock()
    request.retained_source_ids = ("S1",)
    request.response_schema = {
        "$defs": {"EvidenceSpan": {"properties": {"text": {"type": "string"}}}}
    }
    oraciones = (
        "Hemoglobin concentration reflects the oxygen-carrying capacity.",
        "x" * 300,
    )

    with_options = SendChatMessageUseCase._inject_documentary_sentence_options(
        MagicMock(
            _documentary_sentence_options=MagicMock(return_value=oraciones)
        ),
        request,
    )

    enum = with_options.response_schema["$defs"]["EvidenceSpan"]["properties"][
        "text"
    ]["enum"]
    assert enum == [oraciones[0]]

    sin_fuentes = MagicMock()
    sin_fuentes.retained_source_ids = ()
    assert (
        SendChatMessageUseCase._inject_documentary_sentence_options(
            MagicMock(), sin_fuentes
        )
        is sin_fuentes
    )
