from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.modules.llm_chat.application.services.clinical_code_registry import (
    PARAMETER_ALIASES,
)
from app.modules.llm_chat.application.services.intent_classifier import (
    IntentClassifier,
    extract_clinical_parameter,
    normalize_intent_text,
)
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    ConversationMemory,
    ResolvedQuestion,
)
from app.modules.llm_chat.domain.entities import ChatMessageRecord
from app.modules.llm_chat.domain.generation_config import MemoryProfileSettings
from app.modules.llm_chat.domain.value_objects import SafetyAction
from app.modules.llm_chat.application.services.token_budget import TokenCounter


# Backwards-compatible import surface for existing callers/tests.
_PARAMETER_ALIASES = PARAMETER_ALIASES

_DISPLAY = {
    "WBC": "leucocitos",
    "RBC": "eritrocitos",
    "HGB": "hemoglobina",
    "HCT": "hematocrito",
    "PLT": "plaquetas",
    "NEU": "neutrófilos",
    "LYM": "linfocitos",
    "MONO": "monocitos",
    "EOS": "eosinófilos",
    "BASO": "basófilos",
    "MCV": "VCM",
    "MCH": "HCM",
    "MCHC": "CHCM",
    "RDW": "RDW",
    "MPV": "VPM",
}

_STYLE_SIMPLE = re.compile(
    r"\b(mas simple|mas sencillo|en palabras simples|de forma simple|"
    r"sin tecnicismos|en terminos sencillos|explicamelo mas facil|"
    r"explicamelo mas sencillo|como si fuera nino|hazlo mas facil)\b"
)
_STYLE_DETAILED = re.compile(
    r"\b(mas detalle|mas detallado|mas tecnico|en profundidad|"
    r"explicalo a fondo|con mas detalle|nivel tecnico|se mas especifico|"
    r"dame mas detalles|quiero mas detalle)\b"
)

# Deterministic bookkeeping only (etapa 3, Block D): maps the safety action
# already decided elsewhere (SafetyPolicy/ConversationRouter, unchanged in
# this stage) to a stable insistence category. Never produces visible prose
# and never classifies anything itself. Public (no leading underscore):
# send_chat_message.py's _build_response_plan (etapa 4, Block B) reuses this
# exact mapping to recognize when the *current* turn's safety action matches
# the category already recorded in memory, instead of redeclaring it.
BLOCKED_ACTION_CATEGORIES: dict[SafetyAction, str] = {
    SafetyAction.REFUSE_MEDICATION: "medication_request",
    SafetyAction.REFUSE_DOSE: "dosage_request",
    SafetyAction.REFUSE_TREATMENT: "treatment_request",
    SafetyAction.REFUSE_DIAGNOSIS: "diagnosis_request",
}

_FOLLOW_UP = re.compile(
    r"^(?:y\s+)?(?:eso|esa|ese|esto|esta|este|estos|estas|lo|la|los|las|ellos|ellas|"
    r"lo anterior|que significa|por que|esta alto|esta bajo|estan altos|estan bajos|"
    r"es alto|es bajo|es normal|son normales|es grave|cual seria|que seria|"
    r"cual se considera|que se considera|que clasificacion|"
    r"que podria causar|que puede causar|en el anterior|en la anterior|"
    r"en el previo|en la previa|y antes|y ahora|que cambio|que ha cambiado|"
    # Subject-elided questions and enclitic imperatives: "¿De qué está
    # compuesto?", "¿Para qué sirven?", "Explícamelo más simple". The elided
    # subject / clitic IS the anaphor — grammatically incomplete without the
    # prior turn — so with prior context they are follow-ups by construction
    # (pruebas_conversacion_3modos 2026-08-09: GEN-02/07/12/13 were refused
    # as out-of-domain because these shapes produced no expansion).
    r"de que|para que|en que|con que|a que|"
    r"cual era|cuales eran|cual fue|cuales fueron|"
    r"explicamelo|explicame|explicalo|resumemelo|resumelo|"
    r"dime mas|cuentame mas)\b"
)

# Property questions about the parameter already under discussion. Kept apart
# from _FOLLOW_UP because they resolve the REMEMBERED parameter directly (the
# question is unanswerable against anything else), not just the follow-up flag.
_PROPERTY_FOLLOW_UP = re.compile(
    r"^(?:y\s+)?(?:que|cual(?:\s+es)?(?:\s+su)?)\s+"
    r"(?:unidad|rango|fecha|valor|clasificacion|estado|referencia)\b"
)


def normalize_text(value: str) -> str:
    return normalize_intent_text(value)


def extract_parameter(message: str) -> str | None:
    return extract_clinical_parameter(message)


class ReferenceResolver:
    """Resolve high-confidence conversational references before retrieval."""

    def __init__(self, intent_classifier: IntentClassifier | None = None) -> None:
        self.intent_classifier = intent_classifier or IntentClassifier()

    def resolve(self, message: str, memory: ConversationMemory) -> ResolvedQuestion:
        normalized = normalize_text(message)
        explicit = extract_parameter(message)
        topics = list(memory.state.get("topics") or [])
        remembered = str(memory.state.get("last_parameter") or "") or None
        has_prior_context = bool(
            topics or remembered or memory.recent_messages or memory.summary
        )
        is_follow_up = bool(_FOLLOW_UP.search(normalized)) and has_prior_context
        detection = self.intent_classifier.classify(
            message,
            has_memory_parameter=bool(remembered),
        )
        is_clinical_follow_up = (
            is_follow_up
            and self.intent_classifier.permits_parameter_reference(detection)
        )
        parameter = explicit or (remembered if is_clinical_follow_up else None)
        # A property question about the parameter under discussion («¿Qué
        # unidad tiene?», «¿Cuál es su rango?») is only answerable against
        # that parameter — batería ronda 5: SEL-08 murió dos veces porque la
        # elipsis no resolvía parámetro y el turno no tenía objetivo clínico.
        if parameter is None and remembered and _PROPERTY_FOLLOW_UP.search(normalized):
            parameter = remembered
            is_follow_up = True

        topic_override: str | None = None
        if "primer tema" in normalized:
            first = topics[0] if topics else None
            if first:
                parameter = first
                is_follow_up = True
                # The chosen topic must also drive the expansion below;
                # without the override the standalone said topics[-1] while
                # referenced_parameter said topics[0], and the two halves of
                # the turn contradicted each other.
                topic_override = first

        if explicit:
            standalone = message
        elif parameter and is_clinical_follow_up:
            label = _DISPLAY.get(parameter, parameter)
            if re.search(r"\b(anterior|previo|antes)\b", normalized):
                standalone = (
                    f"Respecto a {label} ({parameter}), compara el hemograma de referencia "
                    "con el hemograma inmediatamente anterior del mismo perro: "
                    f"{message}"
                )
            else:
                standalone = f"Respecto a {label} ({parameter}): {message}"
        elif is_follow_up and topics:
            topic = topic_override or topics[-1]
            standalone = f"Retomando el tema {topic}: {message}"
        else:
            standalone = message

        return ResolvedQuestion(
            original=message,
            standalone=standalone,
            is_follow_up=is_follow_up or standalone != message,
            referenced_parameter=parameter,
            referenced_topic=(topics[-1] if topics else None),
        )


class ConversationMemoryService:
    def __init__(
        self,
        *,
        settings: MemoryProfileSettings,
        token_counter: TokenCounter,
    ) -> None:
        self.settings = settings
        self.recent_turns = settings.history_limit
        self.summary_max_chars = settings.summary_max_chars
        self.summary_max_tokens = settings.summary_max_tokens
        self.token_counter = token_counter

    def update(
        self,
        *,
        memory: ConversationMemory,
        clinical: ClinicalContext,
        user_message: str,
        assistant_message: str,
        resolved: ResolvedQuestion,
        safety_action: SafetyAction = SafetyAction.ALLOW,
    ) -> tuple[str, dict[str, Any]]:
        state = dict(memory.state)
        topics = [str(item) for item in state.get("topics") or [] if item]
        parameter = resolved.referenced_parameter or extract_parameter(user_message)
        if parameter:
            topics = [item for item in topics if item != parameter]
            topics.append(parameter)
            state["last_parameter"] = parameter
        state["topics"] = topics[-self.settings.topic_limit :]
        state["last_mode"] = clinical.mode
        state["active_pet_id"] = clinical.pet_id
        state["active_analysis_id"] = clinical.analysis_id
        style = _detect_style_preference(user_message)
        if style:
            state["style_preference"] = style
        state["insistence"] = _update_insistence(state.get("insistence"), safety_action)
        # The database transcript remains authoritative. These literal fields
        # are a structured index for common memory questions and never replace
        # clinical values with a generated paraphrase.
        if not state.get("first_user_question"):
            state["first_user_question"] = user_message
        state["last_user_question"] = user_message
        state["user_question_count"] = int(state.get("user_question_count") or 0) + 1
        recent_questions = [
            str(item) for item in state.get("recent_user_questions") or [] if item
        ]
        recent_questions.append(user_message)
        state["recent_user_questions"] = recent_questions[
            -self.settings.recent_question_limit :
        ]
        state["last_answer_excerpt"] = _compact(
            assistant_message,
            self.settings.answer_excerpt_chars,
        )
        state["last_was_follow_up"] = resolved.is_follow_up
        if re.search(
            r"\b(compara|comparar|anterior|previo|subio|bajo|aumento|disminuyo)\b",
            normalize_text(user_message),
        ):
            state["last_comparison"] = {
                "parameter": parameter,
                "question": _compact(
                    user_message,
                    self.settings.question_excerpt_chars,
                ),
            }

        snapshot = _clinical_snapshot(clinical, parameter)
        if snapshot:
            state["last_clinical_context"] = snapshot
            if parameter:
                facts = dict(state.get("clinical_facts") or {})
                facts[parameter] = snapshot
                state["clinical_facts"] = dict(
                    list(facts.items())[-self.settings.clinical_fact_limit :]
                )

        previous_messages = list(memory.recent_messages)
        overflow = previous_messages + [
            _memory_record("user", user_message),
            _memory_record("assistant", assistant_message),
        ]
        keep = self.recent_turns * 2
        evicted = (
            overflow if keep == 0 else overflow[:-keep] if len(overflow) > keep else []
        )
        summary = memory.summary
        if evicted:
            summarized_ids = [
                str(item) for item in state.get("summarized_message_ids") or [] if item
            ]
            known_ids = set(summarized_ids)
            rows = [
                f"{'Usuario' if item.role == 'user' else 'HemoVet'}: "
                f"{_compact(item.content, self.settings.summary_entry_chars)}"
                for item in evicted
                if item.status in {"completed", "refused"} and item.id not in known_ids
            ]
            if rows:
                summary = _bounded_summary(
                    [*summary.splitlines(), *rows],
                    self.summary_max_tokens,
                    self.summary_max_chars,
                    self.token_counter,
                )
                summarized_ids.extend(
                    item.id
                    for item in evicted
                    if item.status in {"completed", "refused"}
                    and item.id not in known_ids
                )
                state["summarized_message_ids"] = summarized_ids[
                    -self.settings.summarized_message_id_limit :
                ]
        return summary, state


def _detect_style_preference(user_message: str) -> str | None:
    """High-confidence regex signal only — never gates whether memory exists.

    Persists across turns via ``state["style_preference"]`` once detected;
    silence on a later turn keeps the previously recorded preference.
    """
    normalized = normalize_text(user_message)
    if _STYLE_SIMPLE.search(normalized):
        return "simple"
    if _STYLE_DETAILED.search(normalized):
        return "detailed"
    return None


def _update_insistence(
    previous: Any,
    safety_action: SafetyAction,
) -> dict[str, Any]:
    """Track whether the user is repeating a blocked request.

    Deterministic bookkeeping only: this stage does not classify safety
    (that remains ``SafetyPolicy``/``ConversationRouter``, unaffected here)
    and never produces visible prose — any refusal/derivation text is still
    authored entirely by the generative stage. Repeating the *same* blocked
    category increments the count; any allowed (non-blocked) turn resets it,
    so an unrelated or educational question never accumulates as a false
    positive.
    """
    prior = previous if isinstance(previous, dict) else {}
    category = BLOCKED_ACTION_CATEGORIES.get(safety_action)
    if category is not None:
        count = int(prior.get("blocked_action_count") or 0)
        count = count + 1 if prior.get("blocked_action") == category else 1
        return {
            "blocked_action": category,
            "blocked_action_count": count,
            "last_safety_level": "referral_required",
            "last_boundary_explained": True,
        }
    if safety_action is SafetyAction.URGENT_REFERRAL:
        # An escalation is not the user insisting on a blocked action; leave
        # any existing blocked-action streak untouched and only record the
        # heightened safety level.
        return {
            "blocked_action": prior.get("blocked_action"),
            "blocked_action_count": int(prior.get("blocked_action_count") or 0),
            "last_safety_level": "urgent",
            "last_boundary_explained": True,
        }
    return {
        "blocked_action": None,
        "blocked_action_count": 0,
        "last_safety_level": "allowed",
        "last_boundary_explained": False,
    }


def _memory_record(role: str, content: str) -> ChatMessageRecord:
    return ChatMessageRecord(
        id="memory-update",
        conversation_id="memory-update",
        client_message_id="memory-update",
        role=role,
        content=content,
        status="completed",
    )


def _compact(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    prefix = cleaned[: limit - 1].rstrip()
    boundary = prefix.rfind(" ")
    if boundary >= max(1, limit // 2):
        prefix = prefix[:boundary]
    return prefix.rstrip() + "…"


def _bounded_summary(
    lines: list[str],
    max_tokens: int,
    max_chars: int,
    counter: TokenCounter,
) -> str:
    """Keep complete rows and retain the beginning plus the newest context."""
    rows = [line.strip() for line in lines if line.strip()]
    if not rows:
        return ""
    joined = "\n".join(rows)
    if len(joined) <= max_chars and counter.count(joined) <= max_tokens:
        return joined

    first = rows[0]
    marker = "[… turnos anteriores conservados en el transcript …]"
    selected: list[str] = []
    used = counter.count(first) + counter.count(marker)
    for row in reversed(rows[1:]):
        extra = counter.count(row)
        candidate = "\n".join([first, marker, *reversed([*selected, row])])
        if used + extra > max_tokens or len(candidate) > max_chars:
            continue
        selected.append(row)
        used += extra
    result = "\n".join([first, marker, *reversed(selected)])
    if len(result) <= max_chars and counter.count(result) <= max_tokens:
        return result
    # Do not cut through a value or unit. The literal first question remains in
    # memory_state and all turns remain in chat_messages.
    return marker if counter.count(marker) <= max_tokens else ""


def _clinical_snapshot(
    clinical: ClinicalContext,
    parameter_code: str | None,
) -> dict[str, Any]:
    if not clinical.has_data:
        return {}
    studies = list(clinical.history)
    if clinical.selected and not any(
        item.analysis_id == clinical.selected.analysis_id for item in studies
    ):
        studies.append(clinical.selected)
    if not studies:
        return {}

    selected_studies = studies if parameter_code else studies[-2:]
    study_rows: list[dict[str, Any]] = []
    for study in selected_studies:
        parameters = [
            value
            for value in study.parameters
            if parameter_code is None or value.canonical_name == parameter_code
        ]
        if not parameters:
            continue
        study_rows.append(
            {
                "study_id": study.analysis_id,
                "study_key": study.study_key,
                "date": study.date,
                "parameters": [
                    {
                        "code": value.canonical_name,
                        "value": value.value_text,
                        "unit": value.unit,
                        "reference_min": _decimal_text(value.reference_min),
                        "reference_max": _decimal_text(value.reference_max),
                        "classification": value.flag,
                        "range_source": value.reference_origin,
                    }
                    for value in parameters
                ],
            }
        )
    if not study_rows:
        return {}
    return {
        "species": clinical.patient.species if clinical.patient else "canine",
        "parameter": parameter_code,
        "studies": study_rows,
    }


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"
