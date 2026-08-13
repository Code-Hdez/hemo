from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SafetyAction(StrEnum):
    ALLOW = "allow"
    REFUSE_OUT_OF_SCOPE = "refuse_out_of_scope"
    REFUSE_MEDICATION = "refuse_medication"
    REFUSE_DOSE = "refuse_dose"
    REFUSE_TREATMENT = "refuse_treatment"
    REFUSE_DIAGNOSIS = "refuse_diagnosis"
    URGENT_REFERRAL = "urgent_referral"
    REQUIRE_CONTEXT = "require_context"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    TECHNICAL_ERROR = "technical_error"
    # Distinct from REFUSE_OUT_OF_SCOPE: the follow-up is still inside the
    # clinical conversation, it just didn't name a parameter. Kept separate
    # so it is never miscategorized as an out-of-domain refusal downstream
    # (telemetry, the general-scope deterministic boundary short-circuit).
    AMBIGUOUS_CLARIFICATION = "ambiguous_clarification"


class TurnStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REFUSED = "refused"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    INCOMPLETE = "incomplete"


class ResponseOrigin(StrEnum):
    LLM = "llm"
    SAFETY_FALLBACK = "safety_fallback"
    LEGACY_DETERMINISTIC = "legacy_deterministic"
    # "deterministic_safety_boundary" (etapa 1's general-scope
    # deterministic_boundary short circuit) is deliberately not a member
    # here anymore: etapa 4, Block D removed that code path entirely, so no
    # production write can produce it. api/schemas.ChatResponse's
    # response_origin Literal still lists the raw string, purely to keep
    # serializing rows already persisted with it before this stage — that is
    # a read-compatibility concern for historical data, not a live value
    # this enum needs to express.


class StreamMode(StrEnum):
    LIVE_VALIDATED = "live_validated"
    BUFFERED_VALIDATED = "buffered_validated"


class SafetyIntent(StrEnum):
    IDENTITY = "identity"
    SOCIAL_INTERACTION = "social_interaction"
    GREETING = "greeting"
    SYSTEM_FUNCTIONALITY = "system_functionality"
    CORPUS_CAPABILITY = "corpus_capability"
    CHAT_HISTORY = "chat_history"
    FOLLOW_UP = "follow_up"
    SELECTED_VALUE = "selected_value"
    HISTORY_COMPARISON = "history_comparison"
    VET_QUESTIONS = "vet_questions"
    NEARBY_VETERINARY_CARE = "nearby_veterinary_care"
    HEMATOLOGIC_PATTERN = "hematologic_pattern"
    FULL_HEMOGRAM_SUMMARY = "full_hemogram_summary"
    ALLOWED_CBC_GENERAL = "allowed_cbc_general"
    ALLOWED_SELECTED_HEMOGRAM = "allowed_selected_hemogram"
    ALLOWED_HISTORICAL_HEMOGRAM = "allowed_historical_hemogram"
    ALLOWED_CBC_CONCEPT_WITH_TYPOS = "allowed_cbc_concept_with_typos"
    AMBIGUOUS_BUT_POSSIBLY_CBC = "ambiguous_but_possibly_cbc"
    EDUCATIONAL_ALLOWED = "educational_allowed"
    RESULT_EXPLANATION_ALLOWED = "result_explanation_allowed"
    SYMPTOM_GENERAL_INFO_ALLOWED = "symptom_general_info_allowed"
    DIAGNOSIS_REQUEST_LIMITED = "diagnosis_request_limited"
    DIRECT_DIAGNOSIS = "direct_diagnosis"
    MEDICATION_REQUEST_DISALLOWED = "medication_request_disallowed"
    DOSAGE_REQUEST_DISALLOWED = "dosage_request_disallowed"
    TREATMENT_REQUEST_DISALLOWED = "treatment_request_disallowed"
    EMERGENCY_REQUEST_DISALLOWED = "emergency_request_disallowed"
    PROMPT_INJECTION = "prompt_injection"
    OUT_OF_SCOPE = "out_of_scope"
    OUT_OF_SCOPE_GENERAL = "out_of_scope_general"
    OUT_OF_SCOPE_PROGRAMMING_OR_TECHNICAL = "out_of_scope_programming_or_technical"
    OUT_OF_SCOPE_CURRENT_EVENTS = "out_of_scope_current_events"
    OUT_OF_SCOPE_UNSAFE_NONMEDICAL = "out_of_scope_unsafe_nonmedical"
    SOURCE_OR_BIBLIOGRAPHY_REQUEST = "source_or_bibliography_request"
    COPYRIGHT_OR_LONG_SOURCE_REQUEST = "copyright_or_long_source_request"
    MISSING_AUTHORIZED_ANALYSIS = "missing_authorized_analysis"
    TECHNICAL_ERROR = "technical_error"
    VETERINARY_EDUCATION_ALLOWED = "veterinary_education_allowed"
    PET_PROFILE_ALLOWED = "pet_profile_allowed"


class FunctionalIntent(StrEnum):
    """User-facing intent, independent from the safety action and data route."""

    VALUE_REQUEST = "value_request"
    VALUE_CLASSIFICATION = "value_classification"
    RANGE_EXPLANATION = "range_explanation"
    RANGE_THRESHOLD = "range_threshold"
    HEMOGRAM_COMPARISON = "hemogram_comparison"
    HISTORY_CHANGE = "history_change"
    VET_QUESTIONS = "vet_questions"
    NEARBY_VETERINARY_CARE = "nearby_veterinary_care"
    HEMATOLOGIC_PATTERN = "hematologic_pattern"
    FULL_HEMOGRAM_SUMMARY = "full_hemogram_summary"
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    ANIMAL_HARM = "animal_harm"
    VETERINARY_URGENCY = "veterinary_urgency"
    HUMAN_HEALTH = "human_health"
    IDENTITY = "identity"
    CHAT_HISTORY = "chat_history"
    GREETING = "greeting"
    CAPABILITY = "capability"
    SOCIAL_GENERAL = "social_general"
    OUT_OF_DOMAIN = "out_of_domain"
    PROMPT_INJECTION = "prompt_injection"
    GENERAL_CBC = "general_cbc"
    AMBIGUOUS = "ambiguous"
    # Broad veterinary/animal-health topic with no hematology signal (e.g.
    # "por que jadean los perros?"). Previously fell through to OUT_OF_DOMAIN
    # because every prior branch required a CBC/hematology keyword — the
    # audited false positive this etapa corrects.
    VETERINARY_EDUCATION = "veterinary_education"
    # Question about the pet's own profile (breed/age/weight/notes/residence)
    # rather than a hemogram parameter. Distinct from GENERAL_CBC so general
    # mode with an authorized pet profile (etapa 2) can route to the
    # patient's own data instead of falling to REQUIRE_CONTEXT/OUT_OF_DOMAIN.
    PET_PROFILE_QUESTION = "pet_profile_question"


@dataclass(frozen=True, slots=True)
class IntentDetection:
    intent: FunctionalIntent
    parameter: str | None = None
    requested_boundary: str | None = None
    is_clinical_follow_up: bool = False
    confidence: float = 1.0
    secondary_intents: tuple[FunctionalIntent, ...] = ()
    classification_method: str = "hierarchical_rules"


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    action: SafetyAction
    response: str = ""
    intent: SafetyIntent = SafetyIntent.EDUCATIONAL_ALLOWED
    secondary_intents: tuple[SafetyIntent, ...] = ()
    rule_id: str = "educational_default"
    confidence: float = 1.0
    should_use_rag_value: bool = True
    should_use_selected_hemogram: bool = False
    load_selected_analysis: bool = False
    load_history: bool = False
    include_sources: bool = True
    route_selected: str = "rag_generation"
    response_policy: str = "educational_answer"
    risk_flags: tuple[str, ...] = ()
    reason_internal: str = ""
    fallback_type: str | None = None

    @property
    def should_call_retriever(self) -> bool:
        return self.action is SafetyAction.ALLOW and self.should_use_rag_value

    @property
    def should_call_llm(self) -> bool:
        # Safety decisions constrain generation; they do not normally provide
        # user-visible prose. A non-empty response is reserved for the explicit
        # immediate-safety fallback that must not depend on provider availability.
        return not self.response


class ResponseRoute(StrEnum):
    CONVERSATIONAL = "conversational_generation"
    DATABASE = "database_generation"
    RAG = "rag_generation"
    DATABASE_RAG = "database_rag_generation"
    EMERGENCY = "emergency_generation"
    RESTRICTED = "restricted_generation"


@dataclass(frozen=True, slots=True)
class ResponsePolicy:
    """Typed response constraints; it intentionally contains no final answer."""

    route: ResponseRoute
    intent: SafetyIntent
    safety_action: SafetyAction = SafetyAction.ALLOW
    use_rag: bool = False
    use_clinical_context: bool = False
    include_sources: bool = False
    generation_instruction: str = ""
    risk_flags: tuple[str, ...] = ()
    rule_id: str = "conversation_default"
    # Selected-value/history routes normally lock the structured contract to
    # PATIENT_FACT-only (a literal, unmodified citation of the authorized
    # value) — correct for "what's the value" questions, but structurally
    # unable to answer "what does this value mean" ones. When the question
    # was classified as interpretive (conversation_routing's `interpret`),
    # this lets send_chat_message allow PATIENT_FACT_EXPLANATION alongside
    # real RAG source citation, so the model can ground a brief explanation
    # in retrieved evidence instead of only reciting the number or falling
    # back to a generic abstention. Defaults to False: every other route's
    # behavior is unchanged.
    allow_grounded_explanation: bool = False

    @property
    def is_restricted(self) -> bool:
        return self.safety_action is not SafetyAction.ALLOW
