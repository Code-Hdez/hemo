from __future__ import annotations

from dataclasses import dataclass
import re

from app.modules.llm_chat.application.services.intent_classifier import IntentClassifier
from app.modules.llm_chat.application.services.clinical_code_registry import (
    canonical_parameter_code,
    percentage_variant,
)
from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    ClinicalContextSnapshot,
    ClinicalFactKey,
    ClinicalTokenBudgetMetadata,
    HemogramParameter,
    HemogramStudy,
    ResolvedQuestion,
)
from app.modules.llm_chat.domain.value_objects import FunctionalIntent, IntentDetection


_CORE_PARAMETERS = ("WBC", "HGB", "HCT", "PLT")

# Breadth to fall back to when the configured limit demonstrably does not fit
# the turn's token budget. This is the behavior every non-explicit clinical
# question had before CHAT_CONTEXT_PARAMETER_LIMIT existed, kept as the safe
# floor: a narrower prompt is a worse answer, an overflowing one is no answer
# at all (context_budget_exceeded).
_FALLBACK_PARAMETER_LIMIT = 4

# Serialized cost of one PATIENT_FACT claim in the response envelope — text,
# claim id, type, fact id, unit, date and range — measured with the project's
# own TokenCounter over realistic envelopes (4 claims ≈ 524 tokens, 19 ≈ 2127,
# 24 ≈ 2664). Used to keep the number of parameters the model is asked to
# enumerate inside OLLAMA_NUM_PREDICT.
_TOKENS_PER_CLAIM = 110

# How many parameters a non-explicit clinical question may put in front of the
# model. This used to be the literals 4 (salient/changed) and 6 (pattern),
# written when the deployed model was a 4B with a 4096-token context, where
# sending the whole differential really did push it into memorized patterns.
# With the context budget the deployment now runs, those literals were the
# only thing keeping a full CBC out of the prompt: production logs showed
# `authorized_code_count: 12` against `materialized_fact_count: 4` with
# `omitted_fact_count: 0` — nothing was dropped for space, the selector
# simply never offered the other eight. The default is a full canonical CBC
# panel; the real ceiling stays the token budget, applied downstream by
# ClinicalContextMaterializer via CHAT_CLINICAL_FACT_MAX_COUNT.
_DEFAULT_PARAMETER_LIMIT = 24


@dataclass(frozen=True, slots=True)
class ClinicalContextSelection:
    detection: IntentDetection
    # None means the user explicitly requested the complete hemogram. An empty
    # set means that no patient values are needed for this turn.
    parameter_codes: frozenset[str] | None
    history_sufficient: bool

    @property
    def is_complete_summary(self) -> bool:
        return self.parameter_codes is None

    @property
    def prioritized_parameter_codes(self) -> frozenset[str] | None:
        return self.parameter_codes

    def filter_facts(
        self,
        facts: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Return the facts made claimable by this turn's prompt selection.

        The complete snapshot remains the immutable authorization/audit
        universe. Validators receive this materialized subset so a value that
        never reached the model cannot accidentally legitimize an invented
        claim.
        """
        if self.parameter_codes is None:
            return facts
        return [
            fact
            for fact in facts
            if str(fact.get("code") or "") in self.parameter_codes
        ]

    def prioritized_keys(
        self,
        snapshot: ClinicalContextSnapshot,
    ) -> tuple[ClinicalFactKey, ...]:
        if self.parameter_codes is None:
            return tuple(parameter.key for parameter in snapshot.authorized_parameters)
        return tuple(
            parameter.key
            for parameter in snapshot.authorized_parameters
            if parameter.code in self.parameter_codes
        )


class ClinicalContextMaterializer:
    """Records prompt materialization without mutating authorization."""

    def materialize(
        self,
        *,
        snapshot: ClinicalContextSnapshot,
        selection: ClinicalContextSelection,
        maximum_fact_count: int | None = None,
        maximum_tokens: int = 0,
        materialized_tokens: int = 0,
    ) -> ClinicalContextSnapshot:
        prioritized = selection.prioritized_keys(snapshot)
        if maximum_fact_count is None or maximum_fact_count >= len(prioritized):
            materialized = prioritized
        else:
            materialized = self._balanced_history_subset(
                snapshot=snapshot,
                keys=prioritized,
                limit=max(0, maximum_fact_count),
            )
        return snapshot.with_materialization(
            prioritized_fact_keys=prioritized,
            materialized_fact_keys=materialized,
            token_budget_metadata=ClinicalTokenBudgetMetadata(
                maximum_tokens=maximum_tokens,
                materialized_tokens=materialized_tokens,
                omitted_fact_count=len(prioritized) - len(materialized),
                history_study_count=len(snapshot.authorized_studies),
            ),
        )

    @staticmethod
    def _balanced_history_subset(
        *,
        snapshot: ClinicalContextSnapshot,
        keys: tuple[ClinicalFactKey, ...],
        limit: int,
    ) -> tuple[ClinicalFactKey, ...]:
        if limit <= 0:
            return ()
        if snapshot.mode != "hemogram_history":
            return keys[:limit]

        # Select round-robin by study, starting with the newest CBC. This
        # reserves the first two available slots for the latest study and its
        # immediately preceding study instead of spending a tight budget on
        # the oldest history prefix. ``omitted_fact_count`` remains explicit,
        # so a compressed prompt can never be presented as a complete review.
        allowed = set(keys)
        queues = [
            [
                parameter.key
                for parameter in study.parameters
                if parameter.key in allowed
            ]
            for study in reversed(snapshot.authorized_studies)
        ]
        selected: list[ClinicalFactKey] = []
        position = 0
        while len(selected) < limit:
            progressed = False
            for queue in queues:
                if position < len(queue):
                    selected.append(queue[position])
                    progressed = True
                    if len(selected) == limit:
                        return tuple(selected)
            if not progressed:
                break
            position += 1
        return tuple(selected)


class ClinicalContextSelector:
    """Prioritize evidence while leaving the authorized snapshot untouched."""

    def __init__(
        self,
        classifier: IntentClassifier | None = None,
        *,
        parameter_limit: int = _DEFAULT_PARAMETER_LIMIT,
    ) -> None:
        self.classifier = classifier or IntentClassifier()
        self.parameter_limit = max(1, parameter_limit)

    def limit_for_budget(
        self,
        *,
        input_budget: int,
        tokens_per_parameter: int,
        output_budget: int | None = None,
    ) -> int:
        """Widen the panel only when it demonstrably fits, with room to spare.

        Two budgets have to hold, and the output one is the binding constraint
        in practice:

        The clinical block is the one part of the *prompt* that cannot be
        reduced later — PromptBuilder's budget loop drops history, sources and
        whole older studies, never a value inside a study it kept — so a
        breadth the input budget cannot absorb fails the turn with
        context_budget_exceeded rather than degrading. Requiring it to fit in
        half the input budget leaves the other half for the system prompt, the
        schema and the question.

        The *output* budget matters just as much, because a patient turn asks
        the model for one claim per authorized fact. Measured with this
        project's own token counter, a realistic PATIENT_FACT claim costs
        about 110 tokens once its text, unit, date and range are serialized:
        19 claims are ~2100 tokens and 24 are ~2660. Sizing the panel against
        the input budget alone let it exceed OLLAMA_NUM_PREDICT, and a
        truncated envelope is invalid JSON — structured_schema_invalid, then
        generation_repair_failed, then HTTP 502. That is the exact failure
        this breadth work exists to remove, so it must not be reintroduced
        through the response side.
        """

        limit = self.parameter_limit
        if input_budget < limit * max(1, tokens_per_parameter) * 2:
            limit = min(limit, _FALLBACK_PARAMETER_LIMIT)
        if output_budget is not None:
            affordable = max(0, output_budget) // _TOKENS_PER_CLAIM
            limit = min(limit, max(_FALLBACK_PARAMETER_LIMIT, affordable))
        return max(1, limit)

    def select(
        self,
        *,
        question: ResolvedQuestion,
        clinical: ClinicalContext,
        parameter_limit: int | None = None,
    ) -> ClinicalContextSelection:
        detection = self.classifier.classify(
            question.original,
            has_memory_parameter=bool(question.referenced_parameter),
        )
        parameter = self._resolve_available_parameter(
            clinical,
            question.referenced_parameter or detection.parameter,
        )
        history_sufficient = self._history_sufficient(clinical, parameter)
        limit = max(1, parameter_limit or self.parameter_limit)

        if not clinical.has_data:
            return ClinicalContextSelection(detection, frozenset(), False)
        if detection.intent is FunctionalIntent.FULL_HEMOGRAM_SUMMARY:
            return ClinicalContextSelection(detection, None, history_sufficient)
        if parameter:
            return ClinicalContextSelection(
                detection,
                frozenset({parameter}),
                history_sufficient,
            )
        if detection.intent is FunctionalIntent.VET_QUESTIONS:
            return self._selection(detection, clinical, history_sufficient, limit=limit)
        if detection.intent is FunctionalIntent.HEMATOLOGIC_PATTERN:
            return self._selection(
                detection,
                clinical,
                history_sufficient,
                codes=self._pattern_codes(clinical, limit=limit),
                limit=limit,
            )
        if detection.intent in {
            FunctionalIntent.HISTORY_CHANGE,
            FunctionalIntent.HEMOGRAM_COMPARISON,
        }:
            return self._selection(
                detection,
                clinical,
                history_sufficient,
                codes=self._changed_codes(clinical, limit=limit),
                limit=limit,
            )
        # A broad, non-explicit query receives salient evidence first; the
        # ordering matters, the truncation point is the token budget.
        return self._selection(detection, clinical, history_sufficient, limit=limit)

    def _selection(
        self,
        detection: IntentDetection,
        clinical: ClinicalContext,
        history_sufficient: bool,
        *,
        codes: list[str] | None = None,
        limit: int,
    ) -> ClinicalContextSelection:
        """Build a selection that is never empty while the study has values.

        ``_changed_codes`` legitimately returns nothing — a single study, two
        studies whose units were reported differently, or a history where no
        value moved. Passing that empty list straight through made the turn
        materialize zero facts: production logged `materialized_fact_count: 0`
        for "¿qué cambió entre los estudios?", so the model was asked to
        compare studies while holding no value at all, and answered with a
        limitation because that is all it could honestly say. A question about
        a patient that has authorized data must never reach generation with
        none of it.
        """

        resolved = list(codes) if codes is not None else self._salient_codes(
            clinical,
            limit=limit,
        )
        if not resolved:
            resolved = self._salient_codes(clinical, limit=limit)
        if not resolved:
            resolved = self._present_codes(clinical)[:limit]
        return ClinicalContextSelection(
            detection,
            frozenset(resolved),
            history_sufficient,
        )

    @classmethod
    def _present_codes(cls, clinical: ClinicalContext) -> list[str]:
        studies = cls._studies(clinical)
        return list(
            dict.fromkeys(
                item.canonical_name
                for study in reversed(studies)
                for item in study.parameters
            )
        )

    @staticmethod
    def _studies(clinical: ClinicalContext) -> tuple[HemogramStudy, ...]:
        if clinical.mode == "selected_hemogram" and clinical.selected:
            return (clinical.selected,)
        return clinical.history

    @classmethod
    def _resolve_available_parameter(
        cls,
        clinical: ClinicalContext,
        parameter: str | None,
    ) -> str | None:
        if not parameter:
            return None
        code = canonical_parameter_code(parameter)
        present = {
            item.canonical_name
            for study in cls._studies(clinical)
            for item in study.parameters
        }
        if code in present:
            return code
        percent = percentage_variant(code)
        if percent and percent in present:
            # A bare family reference ("neutrófilos") can safely resolve to the
            # percentage when no absolute count exists in the authorized scope.
            return percent
        return code

    @classmethod
    def _salient_codes(cls, clinical: ClinicalContext, *, limit: int) -> list[str]:
        """Order the panel by salience; do not amputate it.

        What changed, then what is out of range, then everything else that was
        authorized. Previously this returned *only* the changed/abnormal head
        and stopped, so a question like "¿ves algún problema?" reached the
        model holding four values out of twelve and could not answer anything
        about the eight it never saw — including "these came back normal",
        which is often the honest answer. The head still comes first so a
        genuinely tight token budget truncates the least important tail.
        """

        studies = cls._studies(clinical)
        if not studies:
            return []
        ordered: list[str] = []
        if clinical.mode == "hemogram_history":
            ordered.extend(cls._changed_codes(clinical, limit=limit))
        ordered.extend(
            item.canonical_name
            for study in reversed(studies)
            for item in study.parameters
            if cls._direction(item) in {"high", "low", "critical"}
        )
        present = cls._present_codes(clinical)
        ordered.extend(code for code in _CORE_PARAMETERS if code in set(present))
        ordered.extend(present)
        return list(dict.fromkeys(ordered))[:limit]

    @classmethod
    def _pattern_codes(cls, clinical: ClinicalContext, *, limit: int) -> list[str]:
        studies = cls._studies(clinical)
        if not studies:
            return []
        if clinical.mode == "hemogram_history":
            changed = cls._changed_codes(clinical, limit=limit)
            abnormal = [
                item.canonical_name
                for study in reversed(studies)
                for item in study.parameters
                if cls._direction(item) in {"high", "low", "critical"}
            ]
            prioritized = list(dict.fromkeys((*changed, *abnormal)))
            if prioritized:
                return prioritized[:limit]
        parameters = studies[-1].parameters
        present = {item.canonical_name for item in parameters}
        abnormal = [
            item.canonical_name
            for item in parameters
            if cls._direction(item) in {"high", "low", "critical"}
        ]
        if abnormal:
            # Abnormal components lead, because a pattern question is about
            # them and a truncating budget must keep them. The rest of the
            # panel follows instead of being withheld: a pattern is read
            # against the values that stayed normal, and the professor's
            # complaint was precisely that the assistant spoke about a study
            # it had only seen a quarter of.
            ordered = list(dict.fromkeys(abnormal))
            remainder = [
                item.canonical_name
                for item in parameters
                if item.canonical_name not in set(ordered)
            ]
            return (ordered + remainder)[:limit]
        return [code for code in _CORE_PARAMETERS if code in present] or [
            item.canonical_name for item in parameters
        ][:limit]

    @classmethod
    def _changed_codes(cls, clinical: ClinicalContext, *, limit: int) -> list[str]:
        studies = clinical.history
        if len(studies) < 2:
            return []
        series: dict[str, list[tuple[int, HemogramParameter]]] = {}
        for position, study in enumerate(studies):
            for parameter in study.parameters:
                series.setdefault(parameter.canonical_name, []).append(
                    (position, parameter)
                )

        changed: list[tuple[int, int, str]] = []
        for code, values in series.items():
            best_priority: int | None = None
            first_change = len(studies)
            for (before_position, before), (after_position, after) in zip(
                values, values[1:]
            ):
                if cls._normalized_unit(before.unit) != cls._normalized_unit(
                    after.unit
                ):
                    continue
                before_status = cls._direction(before)
                after_status = cls._direction(after)
                if before.value == after.value and before_status == after_status:
                    continue
                priority = 0 if before_status != after_status else 1
                best_priority = (
                    priority if best_priority is None else min(best_priority, priority)
                )
                first_change = min(first_change, before_position, after_position)
            if best_priority is not None:
                changed.append((best_priority, first_change, code))
        return [code for _, _, code in sorted(changed)[:limit]]

    @classmethod
    def _history_sufficient(
        cls,
        clinical: ClinicalContext,
        parameter: str | None,
    ) -> bool:
        if len(clinical.history) < 2:
            return False
        if not parameter:
            return bool(cls._changed_codes(clinical, limit=1))
        values: list[HemogramParameter] = []
        for study in clinical.history:
            match = next(
                (item for item in study.parameters if item.canonical_name == parameter),
                None,
            )
            if match is not None:
                values.append(match)
        if len(values) < 2:
            return False
        normalized_units = [cls._normalized_unit(value.unit) for value in values]
        return any(
            before == after
            for before, after in zip(normalized_units, normalized_units[1:])
        )

    @staticmethod
    def _direction(parameter: HemogramParameter) -> str:
        if (
            parameter.reference_min is not None
            and parameter.value < parameter.reference_min
        ):
            return "low"
        if (
            parameter.reference_max is not None
            and parameter.value > parameter.reference_max
        ):
            return "high"
        return parameter.flag or "unknown"

    @staticmethod
    def _normalized_unit(unit: str | None) -> str:
        translation = str.maketrans(
            {"×": "x", "·": "x", "µ": "u", "μ": "u", "³": "3", "⁶": "6", "⁹": "9"}
        )
        return re.sub(
            r"[\s^*()]", "", str(unit or "").casefold().translate(translation)
        )
