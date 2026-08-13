from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.modules.llm_chat.application.services.token_budget import TokenCounter


class PromptBudgetExceededError(RuntimeError):
    """Raised when the mandatory blocks of a request do not fit the effective window.

    Mandatory blocks (global policy, the turn's objective, required safety
    elements, the complete current question, and the complete output schema)
    are never reduced. When they alone exceed the effective budget after every
    authorized reduction step has been exhausted, callers must surface a typed
    technical error instead of sending an over-budget request or silently
    degrading a mandatory block.
    """

    def __init__(self, *, mandatory_tokens: int, budget: int) -> None:
        self.mandatory_tokens = mandatory_tokens
        self.budget = budget
        super().__init__(
            "mandatory prompt blocks need "
            f"{mandatory_tokens} tokens but the effective input budget is {budget}"
        )


@dataclass(frozen=True, slots=True)
class ReductionStep:
    """One authorized, whole-unit reduction action, tried in priority order.

    ``apply`` mutates the caller's composition state and returns True if it
    made progress (something whole was actually removed/compacted), False
    once that category is exhausted — the planner then falls through to the
    next step. ``reason`` is the canonical omission reason recorded in the
    plan's log when this step fires (Block F).
    """

    name: str
    reason: str
    apply: Callable[[], bool]


@dataclass(slots=True)
class BudgetPlan:
    """The single, immutable projection of what will actually be sent."""

    system_prompt: str
    user_prompt: str
    schema: dict[str, Any] | None
    input_tokens: int
    schema_tokens: int
    budget: int
    reduction_log: tuple[str, ...] = field(default_factory=tuple)


class PromptBudgetPlanner:
    """Single authority that fits one candidate request into its effective window.

    Consumed identically by every prompt-building route (clinical/RAG,
    conversational, repair): given a callback that renders the current
    composition state into prompt text (and, when structured output is
    active, a schema provider keyed off whatever is still authorized), it
    repeatedly counts the COMPLETE request — same chat template and the same
    schema serialization the provider client will send — and, only if it does
    not fit, applies the next available authorized reduction step and
    recounts the whole request again. No caller may clamp or trim the result
    afterward; the returned ``BudgetPlan`` is final.
    """

    def __init__(self, token_counter: TokenCounter) -> None:
        self.token_counter = token_counter

    def plan(
        self,
        *,
        system_prompt: str,
        render: Callable[[], str],
        budget: int,
        reduction_steps: list[ReductionStep],
        schema_provider: Callable[[], dict[str, Any] | None] | None = None,
    ) -> BudgetPlan:
        reduction_log: list[str] = []
        schema = schema_provider() if schema_provider else None
        user_prompt = render()
        input_tokens = self._count(system_prompt, user_prompt, schema)
        while input_tokens > budget:
            progressed = False
            for step in reduction_steps:
                if step.apply():
                    reduction_log.append(step.reason)
                    progressed = True
                    break
            if not progressed:
                break
            schema = schema_provider() if schema_provider else None
            user_prompt = render()
            input_tokens = self._count(system_prompt, user_prompt, schema)
        if input_tokens > budget:
            raise PromptBudgetExceededError(mandatory_tokens=input_tokens, budget=budget)
        return BudgetPlan(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema,
            input_tokens=input_tokens,
            schema_tokens=self.token_counter.count_schema(schema),
            budget=budget,
            reduction_log=tuple(reduction_log),
        )

    def _count(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any] | None,
    ) -> int:
        return self.token_counter.count_request(
            system_prompt=system_prompt, user_prompt=user_prompt
        ) + self.token_counter.count_schema(schema)


__all__ = ["BudgetPlan", "PromptBudgetExceededError", "PromptBudgetPlanner", "ReductionStep"]
