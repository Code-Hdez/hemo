"""Pre-generation guard over the user's message.

The shape is taken from ``socratic-tutor``'s ``TutorGuardAdvisor``: a verdict
computed *before* the model is asked for an answer, with three outcomes —
``ALLOW`` (pass the message through), ``STEER`` (answer a rewritten, safe
version of it) and ``SHORT_CIRCUIT`` (answer the boundary itself, without
spending a full clinical generation).

Two things differ from theirs, both on purpose.

*Their guard is a second, small model; ours is not.* They need one because they
have no deterministic policy — the classifier is where scope and intent are
decided. We already decide both before generating, in ``SafetyPolicy``, for
free. What we lacked was not the verdict but the *action*: every verdict, even
"this is a dose request and the answer is a refusal", was routed into a full
clinical generation. Measured against production on 2026-08-06, that cost 41 s
for a correct refusal (BF-07) and 21 s for another (BF-09), and it is what gave
BF-08 two chances to fail validation and return HTTP 502. Adding a model call to
learn what we already knew would have made the common path slower, not faster.

*Their SHORT_CIRCUIT skips the model entirely; ours does not.* Since etapa 4
Block D every completed message in this project is produced by the model
(``response_origin="llm"``), and backend-authored answer text is not a category
new turns may persist — see ``ChatResponse.response_origin``. So SHORT_CIRCUIT
here means "generate the boundary and nothing else": the patient's values, the
retrieved sources, the conversation history and the clinical contract are all
dropped from the prompt, leaving a short policy answer to write. It is the same
saving for the same reason — the expensive part was never the refusal, it was
carrying the whole clinical turn to reach one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.modules.llm_chat.domain.value_objects import SafetyAction, SafetyDecision


class GuardAction(StrEnum):
    ALLOW = "allow"
    STEER = "steer"
    SHORT_CIRCUIT = "short_circuit"


@dataclass(frozen=True, slots=True)
class GuardCheck:
    """A guard verdict, with the invariants checked on construction.

    Mirrors ``GuardCheck.java``: the two text fields are not free-form
    companions to the action, they are *determined* by it. An ``ALLOW`` that
    carried a rewritten message would silently answer a question the user never
    asked; a ``STEER`` without one would rewrite it to nothing.
    """

    action: GuardAction
    safe_user_message: str = ""
    direct_answer_instruction: str = ""
    rule_id: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if self.action is GuardAction.ALLOW and (
            self.safe_user_message or self.direct_answer_instruction
        ):
            raise ValueError("an allowed turn carries no rewritten message")
        if self.action is GuardAction.STEER:
            if not self.safe_user_message.strip():
                raise ValueError("a steered turn requires a safe user message")
            if self.direct_answer_instruction:
                raise ValueError("a steered turn is answered by the model, not the guard")
        if self.action is GuardAction.SHORT_CIRCUIT:
            if not self.direct_answer_instruction.strip():
                raise ValueError("a short-circuited turn requires an answer instruction")
            if self.safe_user_message:
                raise ValueError("a short-circuited turn rewrites nothing")

    @property
    def skips_clinical_generation(self) -> bool:
        return self.action is GuardAction.SHORT_CIRCUIT


# Refusals whose answer is fully determined by the boundary itself: what the
# assistant may say about a dose, a prescription, a treatment plan or an
# off-domain request does not depend on a single value in the patient's
# hemogram. Carrying the clinical context into these turns bought nothing and
# cost a full-size generation.
#
# URGENT_REFERRAL is here for a clinical reason rather than an economic one: an
# emergency answer is the one place where latency is itself a safety property,
# and its content ("go to a vet now") is likewise fixed by the boundary.
_SHORT_CIRCUIT_ACTIONS = frozenset(
    {
        SafetyAction.REFUSE_DOSE,
        SafetyAction.REFUSE_MEDICATION,
        SafetyAction.REFUSE_TREATMENT,
        SafetyAction.REFUSE_OUT_OF_SCOPE,
        SafetyAction.URGENT_REFERRAL,
    }
)

# A diagnosis request with a hemogram in scope is the opposite case: the honest
# answer *is* about the patient's data ("the hemogram does not establish a
# diagnosis; here is what these values show"), and this codebase's diagnosis
# boundary already produces exactly that. Steering it pre-generation would
# replace a grounded answer with a generic one, so STEER is not applied on the
# way in. It is applied on the way out, by ``steer``, when that grounded answer
# is what failed — the §11 "último recurso" the audit asks for.
#
# Without a hemogram there is nothing to ground and nothing to steer toward, so
# the same action short-circuits instead: that is BF-08, whose 502 came from
# carrying a clinical contract a general-scope turn could never satisfy.
_STEER_ACTIONS = frozenset({SafetyAction.REFUSE_DIAGNOSIS})


class TurnGuard:
    """Decide, before generating, whether a turn is answered as asked."""

    _STEER_BY_SCOPE = {
        "selected_hemogram": (
            "¿Qué muestran los valores de este hemograma y qué conviene "
            "preguntarle al veterinario sobre ellos?"
        ),
        "uploaded_analysis": (
            "¿Qué muestran los valores de este hemograma y qué conviene "
            "preguntarle al veterinario sobre ellos?"
        ),
        "hemogram_history": (
            "¿Qué muestran estos hemogramas a lo largo del tiempo y qué "
            "conviene preguntarle al veterinario sobre esa evolución?"
        ),
        "historical_analysis": (
            "¿Qué muestran estos hemogramas a lo largo del tiempo y qué "
            "conviene preguntarle al veterinario sobre esa evolución?"
        ),
    }
    _STEER_GENERAL = (
        "¿Qué información aporta un hemograma canino y qué conviene "
        "consultar con un veterinario a partir de él?"
    )

    _SHORT_CIRCUIT_INSTRUCTION = (
        "Responde únicamente el límite de la consulta: explica en dos o tres "
        "frases, en un tono cercano y sin tecnicismos, qué no puedes hacer y "
        "por qué, y remite a la valoración de un veterinario. No menciones "
        "ningún valor, parámetro ni dato de la mascota, aunque estén "
        "disponibles: esta respuesta no los usa."
    )
    _URGENT_INSTRUCTION = (
        "Responde únicamente la derivación urgente: indica con claridad y en "
        "dos o tres frases que los signos descritos requieren atención "
        "veterinaria inmediata y qué debe hacer ahora mismo. No menciones "
        "ningún valor, parámetro ni dato de la mascota."
    )

    def check(
        self,
        *,
        decision: SafetyDecision,
        has_clinical_data: bool,
    ) -> GuardCheck:
        action = decision.action
        # Only without authorized patient data in scope. Not every refusal in
        # this project is data-independent: with a hemogram selected, a
        # medication refusal is contractually required to ground itself in the
        # relevant parameter's status ("don't give paracetamol to move the
        # leukocytes — they are within range"), which is better clinical
        # behaviour than a bare boundary and needs the facts to produce. The
        # three cases this guard was built for (BF-07/08/09, battery of
        # 2026-08-06) are all general-scope, where no such grounding exists and
        # the whole clinical apparatus was being carried for nothing.
        if (
            action in _SHORT_CIRCUIT_ACTIONS or action in _STEER_ACTIONS
        ) and not has_clinical_data:
            return GuardCheck(
                action=GuardAction.SHORT_CIRCUIT,
                direct_answer_instruction=(
                    self._URGENT_INSTRUCTION
                    if action is SafetyAction.URGENT_REFERRAL
                    else self._SHORT_CIRCUIT_INSTRUCTION
                ),
                rule_id=decision.rule_id,
                reason=action.value,
            )
        return GuardCheck(action=GuardAction.ALLOW)

    def steer(
        self,
        *,
        decision: SafetyDecision,
        context_scope: str,
        has_clinical_data: bool,
    ) -> GuardCheck | None:
        """Return a safe rewrite for a turn whose own contract just failed it.

        Called after a generation and its repair have both been rejected —
        the point where the turn used to become HTTP 502 having spent 40 to
        120 seconds. There is a question next to the one that was asked which
        the same authorized data *can* answer ("what do these values show, and
        what should I ask the vet"), so answering that is strictly better than
        answering nothing. Returns ``None`` when no such neighbour exists,
        which is the honest outcome for a dose or an off-domain request: those
        have no safe rewrite, only a boundary.
        """

        if decision.action not in _STEER_ACTIONS or not has_clinical_data:
            return None
        return GuardCheck(
            action=GuardAction.STEER,
            safe_user_message=self._STEER_BY_SCOPE.get(
                context_scope, self._STEER_GENERAL
            ),
            rule_id=decision.rule_id,
            reason=decision.action.value,
        )


__all__ = ["GuardAction", "GuardCheck", "TurnGuard"]
