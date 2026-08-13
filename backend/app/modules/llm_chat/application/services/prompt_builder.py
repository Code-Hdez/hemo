from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Callable

from app.modules.llm_chat.domain.entities import (
    ChatMessageRecord,
    ModelRequest,
    RetrievedChunk,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from app.modules.llm_chat.domain.generation_config import EffectiveGenerationProfile
from app.modules.llm_chat.application.services.token_budget import (
    TokenCounter,
    input_token_budget,
)
from app.modules.llm_chat.application.services.prompt_budget_planner import (
    BudgetPlan,
    PromptBudgetExceededError,
    PromptBudgetPlanner,
    ReductionStep,
)


_PROMPT_ROOT = Path(__file__).resolve().parents[2] / "prompts"

# Block D/F (etapa 6): the schema/output-contract provider is keyed by the RAG
# source ids and the clinical study (analysis_id) ids that survived budget
# reduction so far — Block F requires a fact whose study left the prompt to
# also leave the schema's authorized fact_ids. Everything else the structured
# contract needs (policy, facts, plan) is fixed for the turn and lives in the
# caller's closure.
SchemaProvider = Callable[
    [tuple[str, ...], frozenset[str]], tuple[dict[str, Any] | None, str]
]


class PromptBuilder:
    def __init__(
        self,
        *,
        corpus_sources: tuple[dict[str, object], ...] = (),
        token_counter: TokenCounter,
    ) -> None:
        self.corpus_sources = corpus_sources
        self.token_counter = token_counter
        self.planner = PromptBudgetPlanner(token_counter)
        # Block A (etapa 6): every active system role derives from this same
        # canonical policy text — mode-specific files only append what is
        # genuinely specific to that route, never a divergent restatement of
        # the shared rules (identity, PostgreSQL authority, memory-is-not-
        # evidence, parametric-knowledge gate, RAG-is-optional, untrusted-
        # data framing, no-diagnosis/treatment, conditional referral,
        # no-fabrication, no internal exposure).
        self.core_policy = (
            (_PROMPT_ROOT / "core_policy_es.txt").read_text(encoding="utf-8").strip()
        )
        self.system_prompt = self._compose_policy(
            (_PROMPT_ROOT / "system_es.txt").read_text(encoding="utf-8").strip()
        )
        self.conversational_system_prompt = self._compose_policy(
            (_PROMPT_ROOT / "conversational_es.txt").read_text(encoding="utf-8").strip()
        )
        self.rag_template = (
            (_PROMPT_ROOT / "rag_es.txt").read_text(encoding="utf-8").strip()
        )

    def _compose_policy(self, mode_specific: str) -> str:
        return self.core_policy + "\n\n" + mode_specific

    def build_tool_selection(
        self,
        *,
        question: str,
        catalogue: str,
        generation_profile: EffectiveGenerationProfile,
        tools: tuple[ToolDefinition, ...],
        exchanges: tuple[tuple[ToolCall, ToolResult], ...] = (),
        correlation_id: str | None = None,
    ) -> ModelRequest:
        """The smallest prompt in the module: which values does this need?

        Deliberately carries no answer schema, no clinical instruction set and
        no history. Those exist to shape an answer, and this call does not
        write one — it decides what to read. The schema alone is 1.934 of the
        7.363 tokens a clinical turn currently sends, and sending it here would
        also leave no token sequence in which a tool call could be emitted.

        ``num_predict`` is a handful of tokens because the output is a tool
        call, not prose. At the 13 tok/s this hardware sustains, that is the
        difference between a round trip that costs seconds and one that costs
        as much as the answer.
        """

        system_prompt = (
            "Eres el componente de HemoVet que decide qué datos hacen falta "
            "para responder una pregunta sobre un hemograma canino.\n"
            "No respondas la pregunta. Tu única tarea es llamar a las "
            "herramientas necesarias para reunir los valores que hagan falta.\n"
            "Pide solo los parámetros que la pregunta necesite. Si la pregunta "
            "es general y no requiere ningún valor de la mascota, no llames a "
            "ninguna herramienta.\n"
            f"{catalogue}"
        )
        user_prompt = f"PREGUNTA DEL USUARIO:\n{question}"
        return ModelRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            thinking=False,
            model=generation_profile.model,
            profile_name=f"{generation_profile.name}_tool_selection",
            profile_kind=generation_profile.kind,
            num_predict=min(generation_profile.num_predict, 256),
            num_ctx=generation_profile.num_ctx,
            max_input_tokens=generation_profile.max_input_tokens,
            context_reserve_tokens=generation_profile.context_reserve_tokens,
            temperature=0.0,
            top_p=generation_profile.top_p,
            top_k=generation_profile.top_k,
            repeat_penalty=generation_profile.repeat_penalty,
            timeout_seconds=generation_profile.timeout_seconds,
            keep_alive=generation_profile.keep_alive,
            tools=tools,
            tool_exchanges=exchanges,
            correlation_id=correlation_id,
            prompt_stats={
                "tool_selection": True,
                "catalogue_chars": len(catalogue),
                "system_prompt_chars": len(system_prompt),
                "user_prompt_chars": len(user_prompt),
            },
        )

    def build_conversational(
        self,
        *,
        question: str,
        history: list[ChatMessageRecord],
        generation_profile: EffectiveGenerationProfile,
        history_limit: int,
        memory_summary: str = "",
        memory_state: dict[str, Any] | None = None,
        response_policy: dict[str, Any] | None = None,
        schema_provider: SchemaProvider | None = None,
    ) -> ModelRequest:
        """Build the small prompt used by identity, social and guardrail routes.

        Those routes do not need the clinical schema or the RAG contract. Keeping
        them out of the prompt both reduces first-token latency and prevents a
        small local model from narrating the much larger clinical instruction set.
        ``memory_state`` (active topic/parameter/analysis, style preference,
        insistence bookkeeping) still reaches this route: many follow-ups
        ("¿eso es preocupante?") land here precisely because they carry no
        clinical data of their own.
        """
        policy = response_policy or {}
        selected_history = self._select_history(
            history,
            question=question,
            message_limit=history_limit,
        )
        history_rows = [
            {
                "role": message.role,
                "content": str(message.content),
            }
            for message in selected_history
        ]
        catalog_block = ""
        if str(policy.get("intent") or "") == "corpus_capability":
            catalog_block = (
                "\nMETADATOS BIBLIOGRÁFICOS AUTORIZADOS:\n"
                + json.dumps(self.corpus_sources, ensure_ascii=False)[:2400]
            )
        summary = str(memory_summary or "")
        state = dict(memory_state or {})
        system_prompt = self._compose_system_prompt(
            self.conversational_system_prompt, policy
        )

        def render() -> str:
            return (
                "INTENCIÓN: "
                + str(policy.get("intent") or "conversation")
                + catalog_block
                + "\nRESUMEN CONVERSACIONAL:\n"
                + json.dumps(summary, ensure_ascii=False)
                + "\nESTADO CONVERSACIONAL:\n"
                + json.dumps(state, ensure_ascii=False)
                + "\nTURNOS RECIENTES:\n"
                + json.dumps(history_rows, ensure_ascii=False)
                + "\nPREGUNTA ACTUAL:\n"
                + json.dumps(question, ensure_ascii=False)
                + "\nEntrega únicamente la respuesta final para el usuario."
            )

        # This route never carries RAG evidence or clinical history, so the
        # contract is always keyed off empty source/dropped-study sets.
        contract_cache: dict[str, Any] = {}

        def schema_and_block() -> tuple[dict[str, Any] | None, str]:
            if schema_provider is None:
                return None, ""
            if "value" not in contract_cache:
                contract_cache["value"] = schema_provider((), frozenset())
            return contract_cache["value"]

        def render_with_contract() -> str:
            return render() + schema_and_block()[1]

        def schema_only() -> dict[str, Any] | None:
            return schema_and_block()[0]

        dropped_history = 0
        summary_trimmed = False
        state_trimmed = False

        def reduce_history() -> bool:
            nonlocal dropped_history
            if not history_rows:
                return False
            history_rows.pop(0)
            dropped_history += 1
            return True

        def reduce_summary() -> bool:
            nonlocal summary, summary_trimmed
            if not summary:
                return False
            summary = summary[: max(0, len(summary) // 2)]
            summary_trimmed = True
            return True

        def reduce_state() -> bool:
            nonlocal state, state_trimmed
            if not state:
                return False
            state = {}
            state_trimmed = True
            return True

        steps = [
            ReductionStep("history_messages", "history_compacted", reduce_history),
            ReductionStep("memory_summary", "memory_compacted", reduce_summary),
            ReductionStep("memory_state", "memory_compacted", reduce_state),
        ]
        budget = self._input_budget(generation_profile)
        plan, budget_exceeded = self._plan(
            system_prompt=system_prompt,
            render_with_contract=render_with_contract,
            render=render,
            schema_and_block=schema_and_block,
            schema_only=schema_only,
            budget=budget,
            steps=steps,
        )
        return ModelRequest(
            system_prompt=plan.system_prompt,
            user_prompt=plan.user_prompt,
            thinking=generation_profile.thinking,
            model=generation_profile.model,
            profile_name=generation_profile.name,
            profile_kind=generation_profile.kind,
            num_predict=generation_profile.num_predict,
            num_ctx=generation_profile.num_ctx,
            max_input_tokens=generation_profile.max_input_tokens,
            context_reserve_tokens=generation_profile.context_reserve_tokens,
            temperature=generation_profile.temperature,
            top_p=generation_profile.top_p,
            top_k=generation_profile.top_k,
            repeat_penalty=generation_profile.repeat_penalty,
            timeout_seconds=generation_profile.timeout_seconds,
            keep_alive=generation_profile.keep_alive,
            response_schema=plan.schema,
            prompt_stats={
                "user_prompt_chars": len(plan.user_prompt),
                "system_prompt_chars": len(plan.system_prompt),
                "rag_context_chars": 0,
                "history_chars": sum(len(row["content"]) for row in history_rows),
                "case_facts_chars": 0,
                "num_sources": 0,
                "num_history_messages": len(history_rows),
                "dropped_history_messages": dropped_history,
                "memory_summary_trimmed": summary_trimmed,
                "memory_state_trimmed": state_trimmed,
                "input_token_budget": budget,
                "estimated_prompt_tokens": plan.input_tokens,
                "schema_tokens": plan.schema_tokens,
                "token_count_exact": self.token_counter.exact,
                "token_counter_identity": self.token_counter.identity,
                "budget_exceeded": budget_exceeded,
                "reduction_log": plan.reduction_log,
            },
        )

    def build(
        self,
        *,
        question: str,
        facts: list[dict[str, object]],
        sources: list[RetrievedChunk],
        history: list[ChatMessageRecord],
        generation_profile: EffectiveGenerationProfile,
        history_limit: int,
        max_context_chars: int,
        memory_summary: str = "",
        memory_state: dict[str, Any] | None = None,
        response_policy: dict[str, Any] | None = None,
        clinical_context: dict[str, Any] | None = None,
        schema_provider: SchemaProvider | None = None,
    ) -> ModelRequest:
        # Etapa 6, Block E: sources arrive already ordered by etapa 5's fused
        # relevance (best first). Reduction only ever pops the tail — a whole
        # chunk removed as a unit, never a mid-text character cut — so the
        # relative order and every surviving chunk's original id/text/
        # language/permissions stay untouched.
        source_rows = [
            {
                "evidence_id": f"S{index}",
                "title": source.title,
                "heading": source.heading_path,
                "text": source.text,
                **(
                    {"language": source.source_language}
                    if source.source_language
                    else {}
                ),
            }
            for index, source in enumerate(sources, start=1)
        ]
        policy = dict(response_policy or {})
        selected_history = self._select_history(
            history,
            question=question,
            message_limit=history_limit,
        )
        history_rows = [
            {"role": message.role, "content": message.content}
            for message in selected_history
        ]
        summary = memory_summary
        state = dict(memory_state or {})
        # Capped at the source, not just at render time: a handful of short,
        # labeled findings placed right next to the question (recency zone)
        # is what a small model actually reads; the same text already exists
        # once inside clinical_context_json, buried mid-prompt where it gets
        # ignored ("lost in the middle").
        observations = self._extract_observations(clinical_context)[:3]
        # Block E (etapa 6): the clinical-context payload is now a real,
        # measured, reducible unit too — no longer json.dumps'd unmeasured.
        # Reduction only ever drops whole historical studies (oldest first,
        # per the authorized ascending query order), never the selected/
        # current study and never a value within a kept study.
        clinical_context_state = dict(clinical_context or {})
        system_prompt = self._compose_system_prompt(self.system_prompt, policy)

        def render() -> str:
            return self._render(
                facts=facts,
                sources=source_rows,
                history=history_rows,
                question=question,
                memory_summary=summary,
                memory_state=state,
                response_policy=policy,
                clinical_context=clinical_context_state,
                observations=observations,
            )

        def retained_source_ids() -> tuple[str, ...]:
            return tuple(str(source["evidence_id"]) for source in source_rows)

        dropped_analysis_ids: set[str] = set()
        contract_cache: dict[str, Any] = {}

        def schema_and_block() -> tuple[dict[str, Any] | None, str]:
            if schema_provider is None:
                return None, ""
            key = (retained_source_ids(), frozenset(dropped_analysis_ids))
            if contract_cache.get("key") != key:
                contract_cache["key"] = key
                contract_cache["value"] = schema_provider(*key)
            return contract_cache["value"]

        def render_with_contract() -> str:
            return render() + schema_and_block()[1]

        def schema_only() -> dict[str, Any] | None:
            return schema_and_block()[0]

        dropped_history = 0
        dropped_sources = 0
        summary_trimmed = False
        state_trimmed = False
        observations_trimmed = False
        clinical_history_dropped = 0

        def reduce_sources() -> bool:
            nonlocal dropped_sources
            if not source_rows:
                return False
            source_rows.pop()
            dropped_sources += 1
            return True

        def reduce_summary() -> bool:
            nonlocal summary, summary_trimmed
            if not summary:
                return False
            summary_lines = [line for line in summary.splitlines() if line.strip()]
            if len(summary_lines) <= 1:
                summary = ""
            else:
                summary = "\n".join(summary_lines[len(summary_lines) // 2 :])
            summary_trimmed = True
            return True

        def reduce_history() -> bool:
            nonlocal dropped_history
            if not history_rows:
                return False
            remove_count = 2 if len(history_rows) > 1 else 1
            del history_rows[:remove_count]
            dropped_history += remove_count
            return True

        def reduce_observations() -> bool:
            nonlocal observations, observations_trimmed
            if not observations:
                return False
            observations = observations[:-1]
            observations_trimmed = True
            return True

        def reduce_state() -> bool:
            nonlocal state, state_trimmed
            if not state:
                return False
            compact_state = {
                key: value
                for key, value in state.items()
                if key in {"first_user_question", "last_parameter", "last_analysis_id"}
            }
            # A second pass must make progress; otherwise a state already
            # limited to these keys would keep this loop alive forever.
            if compact_state == state:
                state = {}
            else:
                state = compact_state
            state_trimmed = True
            return True

        def reduce_clinical_history() -> bool:
            nonlocal clinical_history_dropped
            entries = clinical_context_state.get("hemogram_history")
            if not isinstance(entries, list) or len(entries) <= 1:
                return False
            # Authorized studies are queried oldest-first (ascending
            # created_at); dropping the oldest keeps the most recent,
            # directly-comparable studies in the prompt the longest.
            dropped, kept = entries[0], entries[1:]
            clinical_context_state["hemogram_history"] = kept
            if isinstance(dropped, dict):
                dropped_id = str(dropped.get("analysis_id") or "").strip()
                if dropped_id:
                    # Block F: a fact whose study left the prompt must also
                    # leave the schema's authorized fact_ids — the contract
                    # provider filters `facts` by this set so PATIENT_FACT
                    # claims can never cite a study no longer in the prompt.
                    dropped_analysis_ids.add(dropped_id)
            clinical_history_dropped += 1
            return True

        # Reduction order (Block E): lowest-priority evidence first. System/
        # safety policy, the current question, and the selected/current
        # clinical study are never touched by any of these steps.
        steps = [
            ReductionStep("rag_sources", "rag_not_delivered_budget", reduce_sources),
            ReductionStep("memory_summary", "memory_compacted", reduce_summary),
            ReductionStep("history_messages", "history_compacted", reduce_history),
            ReductionStep("observations", "observations_compacted", reduce_observations),
            ReductionStep("memory_state", "memory_compacted", reduce_state),
            ReductionStep(
                "clinical_history", "context_budget", reduce_clinical_history
            ),
        ]
        budget = self._input_budget(generation_profile)
        plan, budget_exceeded = self._plan(
            system_prompt=system_prompt,
            render_with_contract=render_with_contract,
            render=render,
            schema_and_block=schema_and_block,
            schema_only=schema_only,
            budget=budget,
            steps=steps,
        )
        final_user_prompt = plan.user_prompt
        # Source rows may be removed completely to protect the clinical core.
        # Keep the prompt policy consistent so the model is not asked to cite
        # evidence that no longer exists in its input. This can only shrink
        # the already-fitted request, so it is safe to apply after planning.
        if policy.get("include_sources") and not source_rows:
            policy["include_sources"] = False
            final_user_prompt = render() + schema_and_block()[1]
        return ModelRequest(
            system_prompt=plan.system_prompt,
            user_prompt=final_user_prompt,
            thinking=generation_profile.thinking,
            model=generation_profile.model,
            profile_name=generation_profile.name,
            profile_kind=generation_profile.kind,
            num_predict=generation_profile.num_predict,
            num_ctx=generation_profile.num_ctx,
            max_input_tokens=generation_profile.max_input_tokens,
            context_reserve_tokens=generation_profile.context_reserve_tokens,
            temperature=generation_profile.temperature,
            top_p=generation_profile.top_p,
            top_k=generation_profile.top_k,
            repeat_penalty=generation_profile.repeat_penalty,
            timeout_seconds=generation_profile.timeout_seconds,
            keep_alive=generation_profile.keep_alive,
            response_schema=plan.schema,
            prompt_stats={
                "user_prompt_chars": len(final_user_prompt),
                "system_prompt_chars": len(plan.system_prompt),
                "rag_context_chars": sum(
                    len(str(source.get("text") or "")) for source in source_rows
                ),
                "history_chars": sum(
                    len(str(row.get("content") or "")) for row in history_rows
                ),
                "case_facts_chars": len(json.dumps(facts, ensure_ascii=False)),
                "num_sources": len(source_rows),
                "num_history_messages": len(history_rows),
                "dropped_history_messages": dropped_history,
                "dropped_sources": dropped_sources,
                "memory_summary_trimmed": summary_trimmed,
                "memory_state_trimmed": state_trimmed,
                "num_observations": len(observations),
                "observations_trimmed": observations_trimmed,
                "clinical_history_dropped": clinical_history_dropped,
                "input_token_budget": budget,
                "estimated_prompt_tokens": plan.input_tokens,
                "schema_tokens": plan.schema_tokens,
                "token_count_exact": self.token_counter.exact,
                "token_counter_identity": self.token_counter.identity,
                "budget_exceeded": budget_exceeded,
                "reduction_log": plan.reduction_log,
            },
            retained_source_ids=retained_source_ids(),
        )

    def _plan(
        self,
        *,
        system_prompt: str,
        render_with_contract: Callable[[], str],
        render: Callable[[], str],
        schema_and_block: Callable[[], tuple[dict[str, Any] | None, str]],
        schema_only: Callable[[], dict[str, Any] | None],
        budget: int,
        steps: list[ReductionStep],
    ):
        """Run the single budget authority and, on failure, still return a plan.

        ``PromptBudgetPlanner`` raises when even the fully-reduced mandatory
        blocks do not fit. Callers key their terminal
        ``LLM_CONTEXT_BUDGET_EXCEEDED`` handling off ``prompt_stats
        ["budget_exceeded"]`` before ever invoking the provider (see
        ``send_chat_message._execute``), so this still returns a best-effort,
        fully-reduced ``BudgetPlan`` instead of raising through — nothing
        built from it is ever sent once that flag is observed.
        """
        try:
            return (
                self.planner.plan(
                    system_prompt=system_prompt,
                    render=render_with_contract,
                    budget=budget,
                    reduction_steps=steps,
                    schema_provider=schema_only,
                ),
                False,
            )
        except PromptBudgetExceededError:
            schema, contract_block = schema_and_block()
            user_prompt = render() + contract_block
            input_tokens = self.token_counter.count_request(
                system_prompt=system_prompt, user_prompt=user_prompt
            ) + self.token_counter.count_schema(schema)
            return (
                BudgetPlan(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    schema=schema,
                    input_tokens=input_tokens,
                    schema_tokens=self.token_counter.count_schema(schema),
                    budget=budget,
                    reduction_log=(),
                ),
                True,
            )

    @staticmethod
    def _select_history(
        history: list[ChatMessageRecord],
        *,
        question: str,
        message_limit: int,
    ) -> list[ChatMessageRecord]:
        """Choose complete turns by relevance and recency, preserving chronology."""
        limit = max(0, int(message_limit))
        if limit == 0 or not history:
            return []
        groups: list[list[ChatMessageRecord]] = []
        positions: dict[str, int] = {}
        for message in history:
            key = message.client_message_id or message.id
            position = positions.get(key)
            if position is None:
                positions[key] = len(groups)
                groups.append([message])
            else:
                groups[position].append(message)
        max_groups = max(1, limit // 2)
        terms = {
            token
            for token in re.findall(r"[a-záéíóúñ0-9]+", question.casefold())
            if len(token) > 2
        }
        ranked: list[tuple[int, int]] = []
        for index, group in enumerate(groups):
            content = " ".join(item.content for item in group).casefold()
            overlap = sum(1 for term in terms if term in content)
            ranked.append((overlap * 100 + index, index))
        chosen = {index for _, index in sorted(ranked, reverse=True)[:max_groups]}
        selected = [
            item
            for index, group in enumerate(groups)
            if index in chosen
            for item in group
        ]
        return selected[-limit:]

    @staticmethod
    def _input_budget(profile: EffectiveGenerationProfile) -> int:
        return input_token_budget(
            num_ctx=profile.num_ctx,
            num_predict=profile.num_predict,
            reserve_tokens=profile.context_reserve_tokens,
            max_input_tokens=profile.max_input_tokens,
        )

    @staticmethod
    def _compose_system_prompt(base: str, policy: dict[str, Any]) -> str:
        """Fold the per-turn routing instruction into the system role.

        A directive buried inside a JSON blob in the user turn (labeled "do
        not copy") competes poorly against the always-on base rules for a
        small model's attention. Promoting it to the system role, where the
        base rules already live, lets it govern tone/emphasis for that turn
        without re-litigating the underlying safety rules.
        """
        instruction = str(policy.get("generation_instruction") or "").strip()
        if not instruction:
            return base
        return (
            base + "\n\nINSTRUCCIÓN OBLIGATORIA PARA ESTE TURNO (define el enfoque de "
            "esta respuesta; no anula las reglas de seguridad anteriores):\n"
            + instruction
        )

    @staticmethod
    def _extract_observations(clinical_context: dict[str, Any] | None) -> list[str]:
        """Pull system-recorded findings (ej. "Hemolisis sugerida por MCHC").

        These already ride inside clinical_context_json, but a value nested
        under selected_hemogram.observations in a large JSON blob sits in the
        "lost in the middle" zone for a small model. Callers restate a capped
        copy of this list right next to the question instead.
        """
        if not clinical_context:
            return []
        collected: list[str] = []
        selected = clinical_context.get("selected_hemogram")
        if isinstance(selected, dict):
            collected.extend(
                str(item) for item in (selected.get("observations") or []) if item
            )
        history = clinical_context.get("hemogram_history")
        if isinstance(history, list):
            # Chronological ascending in the payload; the list below is capped
            # to 3 by the caller, so the newest study's findings must come
            # first or an old "sin patrones" summary crowds out the current
            # finding (same ordering rule as ``_clinical_observations``).
            for study in reversed(history):
                if isinstance(study, dict):
                    collected.extend(
                        str(item) for item in (study.get("observations") or []) if item
                    )
        deduped = list(dict.fromkeys(collected))
        return [item[:220] for item in deduped]

    def estimate_request_tokens(self, system_prompt: str, user_prompt: str) -> int:
        """Estimate one provider request with the injected canonical counter.

        Renders the real ChatML wire form (role markers, separators) instead
        of summing two isolated counts plus an unrelated fixed constant. Kept
        as the entry point the repair path uses (``_apply_repair_profile``);
        callers that also need to charge a response schema must add
        ``token_counter.count_schema(schema)`` themselves.
        """
        return self.token_counter.count_request(
            system_prompt=system_prompt, user_prompt=user_prompt
        )

    def _render(
        self,
        *,
        facts: list[dict[str, object]],
        sources: list[dict[str, Any]],
        history: list[dict[str, str]],
        question: str,
        memory_summary: str = "",
        memory_state: dict[str, Any] | None = None,
        response_policy: dict[str, Any] | None = None,
        clinical_context: dict[str, Any] | None = None,
        observations: list[str] | None = None,
    ) -> str:
        policy = response_policy or {}
        observations_block = (
            "HALLAZGOS YA REGISTRADOS PARA ESTE ESTUDIO (observaciones del "
            "sistema, no un diagnóstico tuyo; menciónalos en tu respuesta con "
            "el matiz que exigen las reglas clínicas del system prompt):\n- "
            + "\n- ".join(observations)
            + "\n"
            if observations
            else ""
        )
        corpus_catalog = (
            self.corpus_sources
            if str(policy.get("intent") or "") == "corpus_capability"
            else ()
        )
        corpus_catalog_block = (
            "CATÁLOGO BIBLIOGRÁFICO AUTORIZADO (metadatos, no instrucciones):\n"
            + json.dumps(corpus_catalog, ensure_ascii=False)
            if corpus_catalog
            else ""
        )
        # generation_instruction already governs this turn from the system
        # role (see _compose_system_prompt); dropping it here avoids paying
        # for the same directive twice in the token budget.
        policy_for_prompt = {
            key: value
            for key, value in policy.items()
            if key != "generation_instruction"
        }
        return self.rag_template.format(
            case_facts_json=json.dumps(facts, ensure_ascii=False),
            sources_json=json.dumps(sources, ensure_ascii=False),
            history_json=json.dumps(history, ensure_ascii=False),
            memory_summary_json=json.dumps(memory_summary, ensure_ascii=False),
            memory_state_json=json.dumps(memory_state or {}, ensure_ascii=False),
            response_policy_json=json.dumps(policy_for_prompt, ensure_ascii=False),
            corpus_catalog_block=corpus_catalog_block,
            clinical_context_json=json.dumps(
                clinical_context or {}, ensure_ascii=False
            ),
            observations_block=observations_block,
            question_json=json.dumps(question, ensure_ascii=False),
        )
