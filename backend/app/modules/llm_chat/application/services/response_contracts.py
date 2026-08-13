from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, replace
from enum import StrEnum

from app.modules.llm_chat.application.services.output_validator import OutputValidation
from app.modules.llm_chat.application.services.safety_policy import (
    VETERINARY_REFERRAL_FLAG,
)
from app.modules.llm_chat.domain.value_objects import (
    ResponsePolicy,
    ResponseRoute,
    SafetyIntent,
)


class ContractId(StrEnum):
    GREETING = "GREETING"
    CAPABILITIES = "CAPABILITIES"
    IDENTITY = "IDENTITY"
    CHAT_HISTORY = "CHAT_HISTORY"
    SOCIAL_CONVERSATION = "SOCIAL_CONVERSATION"
    LOVE_OR_EMOTIONAL_CHAT = "LOVE_OR_EMOTIONAL_CHAT"
    OUT_OF_DOMAIN = "OUT_OF_DOMAIN"
    PROGRAMMING = "PROGRAMMING"
    ANIMAL_ABUSE = "ANIMAL_ABUSE"
    EMERGENCY = "EMERGENCY"
    GENERAL_VETERINARY_EDUCATION = "GENERAL_VETERINARY_EDUCATION"
    SELECTED_CBC = "SELECTED_CBC"
    HISTORICAL_CBC = "HISTORICAL_CBC"
    PET_OR_PATIENT_DATA = "PET_OR_PATIENT_DATA"
    MEDICATION_EDUCATION = "MEDICATION_EDUCATION"
    MEDICATION_RECOMMENDATION = "MEDICATION_RECOMMENDATION"
    DOSAGE_REQUEST = "DOSAGE_REQUEST"
    DIRECT_DIAGNOSIS = "DIRECT_DIAGNOSIS"
    TREATMENT_REQUEST = "TREATMENT_REQUEST"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    AMBIGUOUS_FOLLOW_UP = "AMBIGUOUS_FOLLOW_UP"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    LAST_RESORT = "LAST_RESORT"


class CandidateDisposition(StrEnum):
    VALID = "VALID"
    COSMETIC_WARNING = "COSMETIC_WARNING"
    REPAIR_REQUIRED = "REPAIR_REQUIRED"
    MANDATORY_CONTRACT_FAILURE = "MANDATORY_CONTRACT_FAILURE"
    CLINICAL_SAFETY_FAILURE = "CLINICAL_SAFETY_FAILURE"
    EVIDENCE_FAILURE = "EVIDENCE_FAILURE"
    FACT_CONTRADICTION = "FACT_CONTRADICTION"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"

    @property
    def deliverable(self) -> bool:
        return self in {self.VALID, self.COSMETIC_WARNING}


@dataclass(frozen=True, slots=True)
class ResponseContract:
    contract_id: ContractId
    expected_intents: frozenset[SafetyIntent]
    allowed_routes: frozenset[ResponseRoute]
    use_rag: bool | None
    structured_data_required: bool
    documentary_evidence_required: bool
    required_elements: tuple[str, ...]
    prohibited_elements: tuple[str, ...]
    veterinary_referral_required: bool
    approximate_max_words: int
    output_type: str
    uncertainty_policy: str
    validator_names: tuple[str, ...]
    abstention_condition: str | None = None


# The rule id that selects ContractId.LAST_RESORT. Shared so send_chat_message
# names it once instead of repeating the literal that this selection depends on.
LAST_RESORT_RULE_ID = "last_resort"

_CONVERSATIONAL_ROUTES = frozenset({ResponseRoute.CONVERSATIONAL})
_CLINICAL_ROUTES = frozenset({ResponseRoute.DATABASE, ResponseRoute.DATABASE_RAG})


def _contract(
    contract_id: ContractId,
    *,
    intents: tuple[SafetyIntent, ...],
    routes: frozenset[ResponseRoute],
    use_rag: bool | None = None,
    structured: bool = False,
    evidence: bool = False,
    required: tuple[str, ...] = (),
    prohibited: tuple[str, ...] = ("dose", "treatment", "definitive_diagnosis"),
    referral: bool = False,
    max_words: int = 160,
    output_type: str = "generated_text",
    uncertainty: str = "contractual",
    validators: tuple[str, ...] = ("safety", "intent"),
    abstention: str | None = None,
) -> ResponseContract:
    return ResponseContract(
        contract_id=contract_id,
        expected_intents=frozenset(intents),
        allowed_routes=routes,
        use_rag=use_rag,
        structured_data_required=structured,
        documentary_evidence_required=evidence,
        required_elements=required,
        prohibited_elements=prohibited,
        veterinary_referral_required=referral,
        approximate_max_words=max_words,
        output_type=output_type,
        uncertainty_policy=uncertainty,
        validator_names=validators,
        abstention_condition=abstention,
    )


CONTRACTS: dict[ContractId, ResponseContract] = {
    ContractId.GREETING: _contract(
        ContractId.GREETING,
        intents=(SafetyIntent.GREETING,),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("greeting",),
        prohibited=("patient_fact", "dose", "treatment", "definitive_diagnosis"),
        max_words=45,
        uncertainty="not_applicable",
    ),
    ContractId.CAPABILITIES: _contract(
        ContractId.CAPABILITIES,
        intents=(SafetyIntent.SYSTEM_FUNCTIONALITY, SafetyIntent.CORPUS_CAPABILITY),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("hemovet_identity", "scope_boundary"),
        max_words=130,
    ),
    ContractId.IDENTITY: _contract(
        ContractId.IDENTITY,
        intents=(SafetyIntent.IDENTITY,),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("ai_identity", "hemovet_identity"),
        prohibited=(
            "human_identity",
            "patient_fact",
            "dose",
            "treatment",
            "definitive_diagnosis",
        ),
        max_words=80,
        uncertainty="not_applicable",
    ),
    ContractId.CHAT_HISTORY: _contract(
        ContractId.CHAT_HISTORY,
        intents=(SafetyIntent.CHAT_HISTORY,),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("session_history",),
        prohibited=("invented_turn", "patient_fact", "dose", "treatment"),
        max_words=160,
        uncertainty="session_bounded",
        validators=("safety", "intent", "session_history"),
        abstention="requested_turn_is_not_available_in_active_session",
    ),
    ContractId.SOCIAL_CONVERSATION: _contract(
        ContractId.SOCIAL_CONVERSATION,
        intents=(SafetyIntent.SOCIAL_INTERACTION,),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("scope_boundary",),
        max_words=100,
    ),
    ContractId.LOVE_OR_EMOTIONAL_CHAT: _contract(
        ContractId.LOVE_OR_EMOTIONAL_CHAT,
        intents=(SafetyIntent.SOCIAL_INTERACTION,),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("no_personal_emotions", "scope_boundary"),
        max_words=100,
    ),
    ContractId.OUT_OF_DOMAIN: _contract(
        ContractId.OUT_OF_DOMAIN,
        intents=(
            SafetyIntent.OUT_OF_SCOPE,
            SafetyIntent.OUT_OF_SCOPE_GENERAL,
            SafetyIntent.OUT_OF_SCOPE_CURRENT_EVENTS,
        ),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("scope_boundary",),
        max_words=75,
    ),
    ContractId.PROGRAMMING: _contract(
        ContractId.PROGRAMMING,
        intents=(SafetyIntent.OUT_OF_SCOPE_PROGRAMMING_OR_TECHNICAL,),
        routes=_CONVERSATIONAL_ROUTES,
        use_rag=False,
        required=("scope_boundary",),
        max_words=75,
    ),
    ContractId.ANIMAL_ABUSE: _contract(
        ContractId.ANIMAL_ABUSE,
        intents=(SafetyIntent.OUT_OF_SCOPE_UNSAFE_NONMEDICAL,),
        routes=frozenset({ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=("harm_refusal", "animal_protection"),
        max_words=130,
        validators=("safety", "intent", "animal_harm"),
    ),
    ContractId.EMERGENCY: _contract(
        ContractId.EMERGENCY,
        intents=(SafetyIntent.EMERGENCY_REQUEST_DISALLOWED,),
        routes=frozenset({ResponseRoute.EMERGENCY}),
        use_rag=False,
        required=("immediate_veterinary_referral",),
        referral=True,
        max_words=90,
        validators=("safety", "intent", "urgent_referral"),
    ),
    ContractId.GENERAL_VETERINARY_EDUCATION: _contract(
        ContractId.GENERAL_VETERINARY_EDUCATION,
        intents=(
            SafetyIntent.EDUCATIONAL_ALLOWED,
            SafetyIntent.ALLOWED_CBC_GENERAL,
            SafetyIntent.ALLOWED_CBC_CONCEPT_WITH_TYPOS,
            SafetyIntent.RESULT_EXPLANATION_ALLOWED,
            SafetyIntent.SYMPTOM_GENERAL_INFO_ALLOWED,
            SafetyIntent.SOURCE_OR_BIBLIOGRAPHY_REQUEST,
            SafetyIntent.FOLLOW_UP,
            SafetyIntent.HEMATOLOGIC_PATTERN,
            SafetyIntent.FULL_HEMOGRAM_SUMMARY,
            SafetyIntent.VET_QUESTIONS,
            SafetyIntent.NEARBY_VETERINARY_CARE,
            SafetyIntent.VETERINARY_EDUCATION_ALLOWED,
            SafetyIntent.PET_PROFILE_ALLOWED,
        ),
        # DATABASE included: when RAG evidence gets removed by the token
        # budget (send_chat_message.py's rag_evidence_removed_by_token_budget
        # / rag_did_not_fit degradation), the route flips to DATABASE while
        # the intent stays the same. DATABASE is strictly more conservative
        # than RAG (authorized facts only, no external documents), so
        # allowing it here doesn't weaken the contract — it just stops a
        # safe, already-degraded answer from being rejected for having
        # degraded correctly.
        routes=frozenset(
            {ResponseRoute.RAG, ResponseRoute.CONVERSATIONAL, ResponseRoute.DATABASE}
        ),
        use_rag=None,
        evidence=True,
        required=("question_relevance",),
        abstention="documentary_evidence_unavailable",
        validators=("safety", "intent", "evidence"),
    ),
    ContractId.SELECTED_CBC: _contract(
        ContractId.SELECTED_CBC,
        intents=(
            SafetyIntent.SELECTED_VALUE,
            SafetyIntent.FOLLOW_UP,
            SafetyIntent.ALLOWED_SELECTED_HEMOGRAM,
            SafetyIntent.HEMATOLOGIC_PATTERN,
            SafetyIntent.FULL_HEMOGRAM_SUMMARY,
            SafetyIntent.VET_QUESTIONS,
            # contract_for_policy() picks this contract by route
            # (DATABASE/DATABASE_RAG) before it ever looks at intent. Any
            # intent whose RAG evidence can get dropped by token-budget
            # degradation (route flips to DATABASE) lands here regardless of
            # its original intent, so it must be listed even though its
            # "home" contract is GENERAL_VETERINARY_EDUCATION.
            SafetyIntent.NEARBY_VETERINARY_CARE,
        ),
        routes=_CLINICAL_ROUTES,
        use_rag=None,
        structured=True,
        required=("authorized_patient_facts",),
        referral=False,
        validators=("safety", "intent", "facts", "active_analysis"),
        abstention="required_patient_fact_unavailable",
    ),
    ContractId.HISTORICAL_CBC: _contract(
        ContractId.HISTORICAL_CBC,
        intents=(
            SafetyIntent.HISTORY_COMPARISON,
            SafetyIntent.FOLLOW_UP,
            SafetyIntent.ALLOWED_HISTORICAL_HEMOGRAM,
            SafetyIntent.VET_QUESTIONS,
        ),
        routes=_CLINICAL_ROUTES,
        use_rag=None,
        structured=True,
        required=("authorized_history", "comparison_validity"),
        referral=False,
        validators=("safety", "intent", "facts", "active_patient"),
        abstention="fewer_than_two_comparable_observations",
    ),
    ContractId.PET_OR_PATIENT_DATA: _contract(
        ContractId.PET_OR_PATIENT_DATA,
        intents=(SafetyIntent.MISSING_AUTHORIZED_ANALYSIS,),
        routes=frozenset({ResponseRoute.RESTRICTED}),
        use_rag=False,
        structured=True,
        required=("authorized_context_request",),
        abstention="authorized_analysis_unavailable",
    ),
    ContractId.MEDICATION_EDUCATION: _contract(
        ContractId.MEDICATION_EDUCATION,
        intents=(SafetyIntent.EDUCATIONAL_ALLOWED,),
        routes=frozenset({ResponseRoute.RAG}),
        use_rag=True,
        evidence=True,
        required=("educational_explanation", "non_personalized_boundary"),
        max_words=150,
        validators=("safety", "intent", "evidence", "medication_education"),
        abstention="documentary_evidence_unavailable",
    ),
    ContractId.MEDICATION_RECOMMENDATION: _contract(
        ContractId.MEDICATION_RECOMMENDATION,
        intents=(SafetyIntent.MEDICATION_REQUEST_DISALLOWED,),
        routes=frozenset({ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=("action_refusal", "veterinary_referral"),
        referral=True,
        max_words=120,
        validators=("safety", "intent", "medication_refusal"),
    ),
    ContractId.DOSAGE_REQUEST: _contract(
        ContractId.DOSAGE_REQUEST,
        intents=(SafetyIntent.DOSAGE_REQUEST_DISALLOWED,),
        routes=frozenset({ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=("dose_refusal", "veterinary_referral"),
        referral=True,
        max_words=110,
        validators=("safety", "intent", "dose_refusal"),
    ),
    ContractId.DIRECT_DIAGNOSIS: _contract(
        ContractId.DIRECT_DIAGNOSIS,
        intents=(SafetyIntent.DIRECT_DIAGNOSIS, SafetyIntent.DIAGNOSIS_REQUEST_LIMITED),
        routes=frozenset({ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=("diagnosis_limit", "veterinary_referral"),
        referral=True,
        max_words=150,
        validators=("safety", "intent", "diagnosis_boundary"),
    ),
    ContractId.TREATMENT_REQUEST: _contract(
        ContractId.TREATMENT_REQUEST,
        intents=(SafetyIntent.TREATMENT_REQUEST_DISALLOWED,),
        routes=frozenset({ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=("treatment_refusal", "veterinary_referral"),
        referral=True,
        max_words=120,
        validators=("safety", "intent", "treatment_refusal"),
    ),
    ContractId.PROMPT_INJECTION: _contract(
        ContractId.PROMPT_INJECTION,
        intents=(SafetyIntent.PROMPT_INJECTION,),
        routes=frozenset({ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=("role_boundary",),
        prohibited=("internal_policy", "dose", "treatment", "definitive_diagnosis"),
        max_words=80,
        validators=("safety", "intent", "prompt_injection"),
    ),
    ContractId.AMBIGUOUS_FOLLOW_UP: _contract(
        ContractId.AMBIGUOUS_FOLLOW_UP,
        intents=(SafetyIntent.AMBIGUOUS_BUT_POSSIBLY_CBC, SafetyIntent.FOLLOW_UP),
        routes=frozenset({ResponseRoute.RESTRICTED, ResponseRoute.CONVERSATIONAL}),
        use_rag=False,
        required=("clarification_request",),
        max_words=75,
        abstention="reference_cannot_be_resolved",
    ),
    ContractId.INSUFFICIENT_EVIDENCE: _contract(
        ContractId.INSUFFICIENT_EVIDENCE,
        intents=(
            SafetyIntent.EDUCATIONAL_ALLOWED,
            SafetyIntent.ALLOWED_CBC_GENERAL,
            SafetyIntent.ALLOWED_CBC_CONCEPT_WITH_TYPOS,
            SafetyIntent.RESULT_EXPLANATION_ALLOWED,
            SafetyIntent.SYMPTOM_GENERAL_INFO_ALLOWED,
            SafetyIntent.SOURCE_OR_BIBLIOGRAPHY_REQUEST,
            SafetyIntent.FOLLOW_UP,
            SafetyIntent.HEMATOLOGIC_PATTERN,
            SafetyIntent.FULL_HEMOGRAM_SUMMARY,
            SafetyIntent.VET_QUESTIONS,
            SafetyIntent.NEARBY_VETERINARY_CARE,
            SafetyIntent.SELECTED_VALUE,
            SafetyIntent.HISTORY_COMPARISON,
            SafetyIntent.TECHNICAL_ERROR,
            # This tuple documents the intents this contract is normally
            # reached for. It is NOT the enforcement mechanism for the
            # send_chat_message documentary-validation rescue (any allowed,
            # RAG-attempting route can land here after two failed generation
            # attempts, regardless of intent) — validate_response_contract()
            # skips the intent check entirely for ContractId.
            # INSUFFICIENT_EVIDENCE, since that rescue's answer text is a
            # fixed, intent-agnostic abstention. See the note there.
        ),
        routes=frozenset({ResponseRoute.CONVERSATIONAL, ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=("explicit_abstention",),
        max_words=90,
        abstention="evidence_quality_gate_failed",
    ),
    # The turn's floor: what is said when the generation and its repair both
    # failed their own contract. Reached only there, and the alternative it
    # replaces is HTTP 502 after 40 to 130 seconds — the outcome the battery of
    # 2026-08-06 produced six times out of twenty-five, and the single worst
    # thing this assistant can do to someone waiting for it.
    #
    # It is the only contract with no required elements, and that is the point:
    # every other contract states what a *good* answer of its kind must
    # contain, and requiring any of that here is what turns a recoverable turn
    # into an error. Safety is not what was relaxed — it moved to where it
    # cannot be argued with. This answer is generated with no authorized facts,
    # no retrieved sources and no policy rules in scope, so a claim about a
    # measured value is not merely forbidden, it is unconstructible: there is
    # nothing to construct it from. The prohibitions below and every clinical
    # validator outside this module still run on the text.
    ContractId.LAST_RESORT: _contract(
        ContractId.LAST_RESORT,
        # Intent-agnostic by construction, like INSUFFICIENT_EVIDENCE above:
        # any route can arrive here, and validate_response_contract skips the
        # intent check for it.
        intents=(),
        routes=frozenset({ResponseRoute.CONVERSATIONAL, ResponseRoute.RESTRICTED}),
        use_rag=False,
        required=(),
        prohibited=(
            "dose",
            "treatment",
            "definitive_diagnosis",
            "patient_fact",
        ),
        max_words=120,
        uncertainty="explicit",
        abstention="contract_unsatisfiable_after_repair",
    ),
}


def contract_for_policy(policy: ResponsePolicy) -> ResponseContract:
    contract = _contract_for_policy(policy)
    # An allowed answer about a drug, a vaccine, a supplement, a diet, a
    # treatment or a prognosis is education, and it is answered — but it closes
    # by deferring the decision to a vet. The requirement rides on the turn
    # rather than on the contract because the same contract
    # (GENERAL_VETERINARY_EDUCATION) serves "¿qué es la hemoglobina?", which
    # needs no referral, and "¿qué vacunas evitan la leucopenia?", which does.
    # Making it a property of the contract would put a boilerplate sentence on
    # every educational turn.
    if (
        VETERINARY_REFERRAL_FLAG in policy.risk_flags
        and not contract.veterinary_referral_required
    ):
        return replace(contract, veterinary_referral_required=True)
    return contract


def _contract_for_policy(policy: ResponsePolicy) -> ResponseContract:
    # First, and keyed on the rule id rather than the intent: the last resort
    # is reached from any route, so an intent-based selection would send it
    # back to the contract that had just failed.
    if policy.rule_id == LAST_RESORT_RULE_ID:
        return CONTRACTS[ContractId.LAST_RESORT]
    if "animal_harm" in policy.risk_flags:
        return CONTRACTS[ContractId.ANIMAL_ABUSE]
    if policy.rule_id == "medication_education":
        return CONTRACTS[ContractId.MEDICATION_EDUCATION]
    if policy.rule_id == "love_or_emotional_chat":
        return CONTRACTS[ContractId.LOVE_OR_EMOTIONAL_CHAT]
    if policy.rule_id in {"ambiguous_follow_up", "ambiguous_without_cbc_context"}:
        return CONTRACTS[ContractId.AMBIGUOUS_FOLLOW_UP]
    if policy.rule_id == "insufficient_evidence":
        return CONTRACTS[ContractId.INSUFFICIENT_EVIDENCE]
    if policy.intent is SafetyIntent.GREETING:
        return CONTRACTS[ContractId.GREETING]
    if policy.intent in {
        SafetyIntent.SYSTEM_FUNCTIONALITY,
        SafetyIntent.CORPUS_CAPABILITY,
    }:
        return CONTRACTS[ContractId.CAPABILITIES]
    if policy.intent is SafetyIntent.IDENTITY:
        return CONTRACTS[ContractId.IDENTITY]
    if policy.intent is SafetyIntent.CHAT_HISTORY:
        return CONTRACTS[ContractId.CHAT_HISTORY]
    if policy.intent is SafetyIntent.SOCIAL_INTERACTION:
        return CONTRACTS[ContractId.SOCIAL_CONVERSATION]
    if policy.intent is SafetyIntent.OUT_OF_SCOPE_PROGRAMMING_OR_TECHNICAL:
        return CONTRACTS[ContractId.PROGRAMMING]
    if policy.intent in {
        SafetyIntent.OUT_OF_SCOPE,
        SafetyIntent.OUT_OF_SCOPE_GENERAL,
        SafetyIntent.OUT_OF_SCOPE_CURRENT_EVENTS,
    }:
        return CONTRACTS[ContractId.OUT_OF_DOMAIN]
    if policy.intent is SafetyIntent.EMERGENCY_REQUEST_DISALLOWED:
        return CONTRACTS[ContractId.EMERGENCY]
    if policy.intent is SafetyIntent.MEDICATION_REQUEST_DISALLOWED:
        return CONTRACTS[ContractId.MEDICATION_RECOMMENDATION]
    if policy.intent is SafetyIntent.DOSAGE_REQUEST_DISALLOWED:
        return CONTRACTS[ContractId.DOSAGE_REQUEST]
    if policy.intent in {
        SafetyIntent.DIRECT_DIAGNOSIS,
        SafetyIntent.DIAGNOSIS_REQUEST_LIMITED,
    }:
        return CONTRACTS[ContractId.DIRECT_DIAGNOSIS]
    if policy.intent is SafetyIntent.TREATMENT_REQUEST_DISALLOWED:
        return CONTRACTS[ContractId.TREATMENT_REQUEST]
    if policy.intent is SafetyIntent.PROMPT_INJECTION:
        return CONTRACTS[ContractId.PROMPT_INJECTION]
    if policy.intent is SafetyIntent.MISSING_AUTHORIZED_ANALYSIS:
        return CONTRACTS[ContractId.PET_OR_PATIENT_DATA]
    if policy.route in _CLINICAL_ROUTES:
        if (
            policy.intent is SafetyIntent.HISTORY_COMPARISON
            or "history" in policy.rule_id
        ):
            return CONTRACTS[ContractId.HISTORICAL_CBC]
        return CONTRACTS[ContractId.SELECTED_CBC]
    if policy.intent is SafetyIntent.AMBIGUOUS_BUT_POSSIBLY_CBC:
        return CONTRACTS[ContractId.AMBIGUOUS_FOLLOW_UP]
    return CONTRACTS[ContractId.GENERAL_VETERINARY_EDUCATION]


# Opening and closing courtesy both land on this contract (see
# ConversationRouter._acknowledgement): a reply to "gracias, eso era todo" is a
# valid greeting-route answer even though it contains no "hola".
_GREETING = re.compile(
    r"\b(?:hola|buenas|saludos|bienvenid[oa]|gusto|"
    r"de\s+nada|con\s+gusto|un\s+placer|para\s+eso\s+estoy|"
    r"gracias|hasta\s+luego|hasta\s+pronto|cuando\s+(?:lo\s+)?necesites|"
    r"quedo\s+a\s+tu|estoy\s+(?:aqui|disponible))\b"
)
_CLINICAL_PARAMETER = re.compile(
    r"\b(plaquetas?|leucocitos?|eritrocitos?|hemoglobina|hematocrito|"
    r"neutrofilos?|linfocitos?|wbc|rbc|hgb|hct|plt)\b"
)
_AI_IDENTITY = re.compile(
    # Widened past the three memorized spellings this used to accept. A model
    # that answers "soy un asistente digital" or "soy un modelo de lenguaje"
    # is stating exactly the identity this contract wants proven, and failing
    # the turn over the synonym cost the user an answer, not safety.
    r"\b(?:inteligencia artificial|"
    r"asistente\s+(?:virtual|digital|automatizado|de\s+ia)|"
    r"soy\s+una?\s+(?:ia|inteligencia\s+artificial|modelo(?:\s+de\s+lenguaje)?|"
    r"programa|sistema|software|asistente)|"
    r"modelo\s+de\s+lenguaje|no\s+soy\s+(?:un[ao]?\s+)?(?:human[ao]|persona))\b"
)
_HEMOVET = re.compile(r"\bhemovet\b")
# Proof that the answer stayed inside the product's subject, not a fixed
# marketing phrase. The old pattern demanded the literal "hemogramas caninos"
# (plural + adjective) or "hematologia veterinaria"; an answer that said "te
# ayudo a entender el hemograma de tu perro" — correct, in scope, and the
# natural way to say it — was rejected as `intent_mismatch_capabilities` and,
# when the repair phrased it naturally too, returned to the user as a 502.
_SCOPE = re.compile(
    r"\bhemogramas?\b|\bhematolog\w+\b|\banalisis\s+de\s+sangre\b|"
    r"\bfuera\s+de\s+(?:mi|este|ese|tu|su)\s+(?:ambito|alcance|area|campo|"
    r"especialidad|funcion)\b|\bambito\s+de\s+hemovet\b|\bespecialidad\b"
)
# Proof that the answer hands the decision to a veterinarian. The verb list
# used to be closed and one-directional, so five of eight natural referrals
# failed it — "un veterinario debe valorar estos hallazgos", "coméntalo con tu
# veterinario", "solo un veterinario puede establecer el tratamiento" — and
# that is what killed the diagnosis and medication contracts in production
# (`mandatory_diagnosis_boundary`, `medical_refusal_contract`). The verbs are
# now matched on either side of the noun, because Spanish puts the subject
# first as readily as the imperative. Being generous here costs nothing: the
# risk this product guards against is giving a dose, not naming a vet too
# easily, and the dose/diagnosis prohibitions are enforced separately.
_VET_REFERRAL_VERB = (
    r"consult\w*|habl\w*|coment\w*|acud\w*|busc\w*|busqu\w*|contact\w*|llev\w*|"
    r"visit\w*|valor\w*|evalu\w*|revis\w*|interpret\w*|examin\w*|determin\w*|"
    r"establec\w*|indic\w*|decid\w*|confirm\w*|orient\w*|atend\w*|"
    # Asking the vet, and arranging to see one, are referrals too. Their
    # absence here was the same closed-list gap the sibling matcher in
    # send_chat_message.py had: "pregúntaselo a tu veterinario" and "programa
    # una cita con el veterinario" defer to a professional as plainly as
    # "consúltalo con tu veterinario". The two matchers gate the same answers,
    # so a verb missing from one is a rejection the other cannot rescue.
    r"pregunt\w*|program\w*|agend\w*|solicit\w*|"
    r"requiere|requieren|necesita|necesitan|corresponde|deriva\w*|remit\w*|"
    r"recomiend\w*|convien\w*|debe|deben|puede|pueden"
)
_VET_REFERRAL = re.compile(
    rf"\b(?:{_VET_REFERRAL_VERB})\b[^.!?\n]{{0,90}}\bveterinari[oa]s?\b|"
    rf"\bveterinari[oa]s?\b[^.!?\n]{{0,90}}\b(?:{_VET_REFERRAL_VERB})\b|"
    # "profesional/clínica/especialista veterinario" carries the same meaning
    # without ever using the bare noun as the subject.
    r"\b(?:profesional|clinica|especialista|centro|cita)\s+(?:con\s+(?:el|un)\s+)?"
    r"veterinari[oa]s?\b"
)
# Medido sobre redacciones reales: solo 1 de 5 negativas correctas pasaba
# ("no estoy autorizado a recetar", "eso no me corresponde", "prefiero no
# indicarte un tratamiento" fallaban todas), y este contrato gobierna las
# rutas de medicación y dosis.
_REFUSAL = re.compile(
    r"\bno\s+(?:te\s+|le\s+|se\s+)?"
    r"(?:puedo|podre|debo|debes|deberia|voy\s+a|estoy\s+autorizad[oa]|"
    r"corresponde|me\s+corresponde|doy|dare|indico|indicare|receto|"
    r"recetare|prescribo|sugiero|recomiendo|es\s+seguro|es\s+recomendable|"
    r"es\s+mi\s+funcion|puedo\s+recomendar)\b|"
    r"\b(?:prefiero\s+no|lamentablemente\s+no|evita|evitar|nunca|"
    r"queda\s+fuera\s+de\s+mi|no\s+es\s+algo\s+que)\b"
)
# El contrato de emergencia. Solo 1 de 5 formas naturales de expresar urgencia
# pasaba, así que una pregunta sobre una urgencia real podía morir en un 502 —
# el peor sitio posible para una lista cerrada.
_URGENT = re.compile(
    r"\b(?:urgen\w*|inmediat\w*|ahora\s+mismo|ya\s+mismo|sin\s+demora|"
    r"sin\s+esperar|cuanto\s+antes|lo\s+antes\s+posible|de\s+inmediato|"
    r"emergencia|prioritari[oa]|no\s+puede\s+esperar|no\s+esperes|"
    r"acude\s+ya|hoy\s+mismo|de\s+urgencia)\b"
)
# Proof that the answer refused to settle a diagnosis. The four phrasings this
# used to accept were a memorized subset: "un valor alto no significa que haya
# una enfermedad" — the correct answer to GEN-08 in the review battery — matched
# none of them, so the turn was rejected as `mandatory_diagnosis_boundary` and
# the user got HTTP 502 after 42 s for asking why an out-of-range value is not
# a disease.
_UNCERTAINTY = re.compile(
    r"\bno\s+(?:se\s+|te\s+|le\s+|lo\s+)?"
    r"(?:confirma\w*|permite\s+confirmar|puedo\s+confirmar|puede\s+confirmar\w*|"
    r"constituye|equivale|significa|implica|indica|demuestra|prueba|"
    r"determina|establece|diagnostica|es\s+posible\s+(?:confirmar|determinar)|"
    r"basta|alcanza|sustituye|reemplaza)\b|"
    r"\bno\s+(?:es|son|hay)\s+(?:un\s+|una\s+)?"
    r"(?:diagnostico|conclusion|certeza|prueba|confirmacion)\b|"
    r"\b(?:por\s+si\s+sol[oa]|requiere\s+(?:evaluacion|valoracion|confirmacion|"
    r"interpretacion|correlacion)|no\s+necesariamente|"
    r"no\s+puedo\s+(?:emitir|dar|ofrecer|establecer)|"
    r"orientativ[oa]|no\s+concluyente|sin\s+confirmar)\b"
)
_CLARIFY = re.compile(
    r"\b(?:a\s+que|cual|cuales|que\s+valor|que\s+parametro|que\s+analisis|"
    r"aclara\w*|precisa\w*|especifica\w*|selecciona\w*|indica\w*|"
    r"dime|podrias|puedes\s+(?:decirme|indicarme)|"
    r"no\s+me\s+queda\s+claro|no\s+entiendo\s+bien|te\s+refieres)\b"
)
_EXPLICIT_ABSTENTION = re.compile(
    r"\b(?:evidencia|documentacion|fuentes?|informacion)\b"
    r"[^.!?\n]{0,40}\b(?:insuficiente|insuficientes|no\s+basta)\b|"
    r"\bno\s+(?:hay|tengo|tenemos|dispongo\s+de|cuento\s+con|encontre|"
    r"encuentro|(?:se\s+)?(?:recupero|encontro|hallo))\b"
    r"[^.!?\n]{0,60}\b(?:evidencia|documentacion|fuentes?)\b|"
    r"\bno\s+(?:puedo|es\s+posible)\s+responder\b[^.!?\n]{0,80}"
    r"\b(?:evidencia|fuentes?)\b"
)
_CLINICAL_TOPIC = re.compile(
    r"\b(?:sangre|hemograma|hematologia|leucocitos?|eritrocitos?|plaquetas?|"
    r"hemoglobina|hematocrito|hierro|medicamento|anemia|infeccion|enfermedad|"
    r"organos?|wbc|rbc|hgb|hct|plt)\b"
)
_ANIMAL_PROTECTION = re.compile(
    r"\b(?:no|nunca|jamas)\b[^.!?\n]{0,50}"
    r"\b(?:dan\w*|lastim\w*|golpe\w*|maltrat\w*|castig\w*|pegu\w*|pegar)\b|"
    r"\b(?:mant(?:en|enga)l[oa]\s+a\s+salvo|proteccion\s+animal|bienestar|"
    r"seguridad\s+del\s+animal|alejate\s+del\s+animal|"
    r"separate\s+de\s+(?:tu|la|el)\s+mascota|pide\s+ayuda)\b"
)
_ROLE_BOUNDARY = re.compile(
    r"\bno\s+(?:puedo|voy\s+a|debo|comparto|compartire|revelo|revelare)\b"
    r"[^.!?\n]{0,40}"
    r"\b(?:cambiar|ignorar|revelar|compartir|mostrar|rol|funcion|"
    r"reglas|instrucciones|prompt)\b|"
    r"\b(?:mantengo\s+mi\s+(?:funcion|rol)|instrucciones\s+internas|"
    r"reglas\s+internas|ambito\s+de\s+hemovet|mi\s+funcion\s+es)\b"
)
_AUTHORIZED_CONTEXT_REQUEST = re.compile(
    r"\b(?:selecciona\w*|elige|elegir|abre|abrir|indica\w*|carga\w*|"
    r"necesito|necesitas|hace\s+falta|falta|no\s+hay|no\s+tengo|"
    r"no\s+veo|sin)\b[^.!?\n]{0,60}"
    r"\b(?:hemograma|analisis|estudio)\b|"
    r"\b(?:hemograma|analisis|estudio)\b[^.!?\n]{0,60}"
    r"\b(?:seleccionad[oa]|cargad[oa]|disponible)\b"
)
_CLAIMED_PERSONAL_EMOTION = re.compile(
    r"\b(?:te\s+amo|estoy\s+enamorado|siento\s+amor|"
    r"tengo\s+(?:emociones|sentimientos))\b"
)


def identity_claims_ai_nature(normalized_answer: str) -> bool:
    """Whether an already-normalized answer states its non-human nature.

    Public so ``send_chat_message`` can apply the identity contract from this
    single pattern instead of keeping a second, silently diverging copy.
    """

    return bool(_AI_IDENTITY.search(normalized_answer))


def validate_response_contract(
    answer: str,
    *,
    policy: ResponsePolicy,
    facts: list[dict[str, object]],
) -> OutputValidation | None:
    contract = contract_for_policy(policy)
    normalized = _normalize(answer)
    reason: str | None = None

    if (
        policy.intent not in contract.expected_intents
        # INSUFFICIENT_EVIDENCE is deliberately intent-agnostic: it is the
        # generic "couldn't produce a deliverable candidate" rescue for any
        # already-ALLOWED, RAG-attempting route (send_chat_message's
        # documentary-validation fallback), not an answer tailored to one
        # intent. Enumerating every SafetyIntent that can reach it is
        # fragile by construction — it has already missed
        # NEARBY_VETERINARY_CARE and SELECTED_VALUE/HISTORY_COMPARISON in
        # practice, each turning a safe generic abstention into a hard
        # 502/503 (mandatory_contract_intent -> safety_fallback_contract_
        # invalid) instead of the graceful fallback this contract exists to
        # provide. The fixed abstention text never varies by intent, so
        # there is nothing this check protects here.
        and contract.contract_id
        not in {ContractId.INSUFFICIENT_EVIDENCE, ContractId.LAST_RESORT}
    ):
        reason = "mandatory_contract_intent"
    elif policy.route not in contract.allowed_routes:
        reason = "mandatory_contract_route"
    elif contract.use_rag is not None and policy.use_rag is not contract.use_rag:
        reason = "mandatory_contract_rag_policy"
    elif (
        contract.structured_data_required
        and not facts
        and contract.contract_id
        in {
            ContractId.SELECTED_CBC,
            ContractId.HISTORICAL_CBC,
        }
    ):
        reason = "mandatory_contract_missing_structured_data"
    elif contract.contract_id is ContractId.GREETING:
        if not _GREETING.search(normalized):
            reason = "intent_mismatch_greeting"
        elif _CLINICAL_PARAMETER.search(normalized) or re.search(r"\d", normalized):
            reason = "intent_mismatch_greeting_clinical_content"
    elif contract.contract_id is ContractId.IDENTITY:
        if not _AI_IDENTITY.search(normalized) or not _HEMOVET.search(normalized):
            reason = "intent_mismatch_identity"
        elif _CLINICAL_PARAMETER.search(normalized) or re.search(r"\d", normalized):
            reason = "intent_mismatch_identity_clinical_content"
    elif contract.contract_id is ContractId.CAPABILITIES:
        if not _HEMOVET.search(normalized) or not _SCOPE.search(normalized):
            reason = "intent_mismatch_capabilities"
    elif contract.contract_id in {
        ContractId.SOCIAL_CONVERSATION,
        ContractId.OUT_OF_DOMAIN,
        ContractId.PROGRAMMING,
    }:
        if not (_HEMOVET.search(normalized) or _SCOPE.search(normalized)):
            reason = "intent_mismatch_scope_boundary"
    elif contract.contract_id is ContractId.LOVE_OR_EMOTIONAL_CHAT:
        if _CLAIMED_PERSONAL_EMOTION.search(normalized):
            reason = "incorrect_personal_emotion_claim"
        elif not (_HEMOVET.search(normalized) or _SCOPE.search(normalized)):
            reason = "intent_mismatch_scope_boundary"
    elif contract.contract_id is ContractId.ANIMAL_ABUSE:
        if not _ANIMAL_PROTECTION.search(normalized):
            reason = "animal_harm_safety_contract"
    elif contract.contract_id is ContractId.EMERGENCY:
        if not (_URGENT.search(normalized) and _VET_REFERRAL.search(normalized)):
            reason = "missing_urgent_veterinary_referral"
    elif contract.contract_id in {
        ContractId.MEDICATION_RECOMMENDATION,
        ContractId.DOSAGE_REQUEST,
        ContractId.TREATMENT_REQUEST,
    }:
        if not (_REFUSAL.search(normalized) and _VET_REFERRAL.search(normalized)):
            reason = "mandatory_medical_refusal_contract"
    elif contract.contract_id is ContractId.DIRECT_DIAGNOSIS:
        if not (_UNCERTAINTY.search(normalized) and _VET_REFERRAL.search(normalized)):
            reason = "mandatory_diagnosis_boundary"
    elif contract.contract_id is ContractId.PET_OR_PATIENT_DATA:
        if not _AUTHORIZED_CONTEXT_REQUEST.search(normalized):
            reason = "mandatory_authorized_context_request"
    elif contract.contract_id is ContractId.MEDICATION_EDUCATION:
        if not _CLINICAL_TOPIC.search(normalized):
            reason = "mandatory_educational_explanation"
    elif contract.contract_id is ContractId.PROMPT_INJECTION:
        if not _ROLE_BOUNDARY.search(normalized):
            reason = "mandatory_role_boundary"
    elif contract.contract_id is ContractId.AMBIGUOUS_FOLLOW_UP:
        if not _CLARIFY.search(normalized):
            reason = "mandatory_clarification_request"
    elif contract.contract_id is ContractId.INSUFFICIENT_EVIDENCE:
        if not _EXPLICIT_ABSTENTION.search(normalized):
            reason = "mandatory_explicit_abstention"
        else:
            # A valid abstention cannot be followed by an uncited clinical
            # proposition.  This also protects the legacy free-text mode; the
            # structured path additionally requires LIMITATION claim types.
            sentences = [
                sentence.strip()
                for sentence in re.split(r"[.!?]+|\n+", normalized)
                if sentence.strip()
            ]
            if any(
                _CLINICAL_TOPIC.search(sentence)
                and not _EXPLICIT_ABSTENTION.search(sentence)
                for sentence in sentences
            ):
                reason = "unsupported_claim_without_evidence"

    if (
        reason is None
        and contract.veterinary_referral_required
        and not _VET_REFERRAL.search(normalized)
    ):
        reason = "mandatory_veterinary_referral"

    if reason is None:
        return None
    return OutputValidation(
        is_safe=True,
        text=answer,
        reason=reason,
        detail=f"contract={contract.contract_id.value}",
        meets_intent=False,
    )


_SAFETY_REASONS = {
    "animal_harm_safety_contract",
    "definitive_diagnosis",
    "medical_refusal_contract",
    "mandatory_diagnosis_boundary",
    "mandatory_medical_refusal_contract",
    "missing_urgent_veterinary_referral",
    "unsafe_clinical_decision",
    "unsafe_instruction",
}
_EVIDENCE_REASONS = {
    "missing_evidence_attribution",
    "unsupported_clinical_interpretation",
    "unsupported_evidence_claim",
    "unknown_source",
}
_FACT_REASONS = {
    "cross_analysis_claim",
    "invalid_numeric_claim",
    "unsupported_clinical_claim",
    "unsupported_historical_claim",
    "unsupported_numeric_claim",
    "unsupported_status_claim",
    "unsupported_unit_claim",
}


def candidate_disposition(
    validation: OutputValidation,
    *,
    finish_reason: str,
) -> CandidateDisposition:
    reason = str(validation.reason or "")
    if finish_reason == "length":
        return CandidateDisposition.REPAIR_REQUIRED
    if validation.is_safe and validation.meets_intent:
        return (
            CandidateDisposition.COSMETIC_WARNING
            if validation.removed_invalid_citations
            else CandidateDisposition.VALID
        )
    if not validation.meets_intent:
        return CandidateDisposition.MANDATORY_CONTRACT_FAILURE
    if reason in _EVIDENCE_REASONS or "evidence" in reason or "source" in reason:
        return CandidateDisposition.EVIDENCE_FAILURE
    if reason in _FACT_REASONS or any(
        marker in reason for marker in ("numeric", "unit", "status", "fact", "analysis")
    ):
        return CandidateDisposition.FACT_CONTRADICTION
    if reason in _SAFETY_REASONS or any(
        marker in reason
        for marker in ("dose", "treatment", "diagnos", "safety", "urgent")
    ):
        return CandidateDisposition.CLINICAL_SAFETY_FAILURE
    if reason in {"provider_unavailable", "stream_final_mismatch"}:
        return CandidateDisposition.TECHNICAL_FAILURE
    return CandidateDisposition.REPAIR_REQUIRED


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", str(value or "").casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", plain).strip()
