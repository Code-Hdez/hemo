"""Clinical facts as tools the model calls, instead of a panel it is handed.

Why this exists
---------------
Measured on production, 2026-08-06: a turn sends **7.363 prompt tokens** and
spends 6 to 7 seconds evaluating them before the first word of the answer. The
patient's whole materialized panel travels in every prompt, whether the
question needs one value or nineteen.


The same shape applies here, and it buys three things at once:

* the prompt shrinks to an index, so prompt evaluation stops dominating;
* the model can reach a study that was never preselected, which is what
  "answer about any hemogram" actually requires;
* a question about one parameter stops paying for the other eighteen.

What does *not* change
----------------------
The clinical guarantee. A tool that returns a patient's values does not merely
inform the answer, it authorizes them: ``ToolResult.authorized_facts`` is the
registry the output validators check every claim against. Values the model was
never given remain unclaimable, exactly as when they travelled in the prompt.
This is the line the analysis of 2026-08-06 draws in §4.4 — their tutor has no
patient, ours does, so the output contract stays.

Authorization is not re-derived here either. These tools read the
``ClinicalContext`` the use case already loaded and ownership-verified for the
turn; they cannot reach a study it does not contain.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from app.modules.llm_chat.domain.clinical import (
    ClinicalContext,
    HemogramStudy,
    clinical_fact_id,
)
from app.modules.llm_chat.domain.entities import (
    ToolCall,
    ToolDefinition,
    ToolResult,
)

LIST_STUDIES = "listar_estudios"
READ_PARAMETERS = "leer_parametros"

# A tool result is a message the model reads, so it is capped like one. Wide
# enough for a full 24-parameter panel, narrow enough that a mistaken call
# cannot undo the prompt saving this whole module exists for.
_MAX_RESULT_CHARS = 6000


@dataclass(frozen=True, slots=True)
class ClinicalToolbox:
    """The tools one turn may call, bound to that turn's authorized context."""

    clinical: ClinicalContext

    def definitions(self) -> tuple[ToolDefinition, ...]:
        if not self._studies():
            return ()
        return (
            ToolDefinition(
                name=LIST_STUDIES,
                description=(
                    "Lista los hemogramas disponibles de esta mascota, con su "
                    "fecha, su identificador y qué parámetros contiene cada "
                    "uno. Úsala primero cuando necesites saber qué estudios "
                    "hay o cuál corresponde a una fecha."
                ),
                parameters={"type": "object", "properties": {}, "required": []},
            ),
            ToolDefinition(
                name=READ_PARAMETERS,
                description=(
                    "Lee los valores medidos de un hemograma: valor, unidad, "
                    "rango de referencia y estado. Pide solo los parámetros "
                    "que necesites para responder; si no indicas ninguno, "
                    "devuelve el panel completo."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "analysis_id": {
                            "type": "string",
                            "description": (
                                "Identificador del estudio, tal como aparece "
                                f"en {LIST_STUDIES}. Si se omite, se usa el "
                                "estudio seleccionado."
                            ),
                        },
                        "parametros": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Códigos o nombres de los parámetros a leer, "
                                "por ejemplo WBC, plaquetas, hematocrito."
                            ),
                        },
                    },
                    "required": [],
                },
            ),
        )

    def catalogue(self) -> str:
        """The index that replaces the panel in the prompt.

        Deliberately says what exists and never what it is worth: the values
        are the tool's job. Mirrors ``DynamicContextManagementAdvisor``'s
        "use this catalog only to decide whether to call the tool".
        """

        studies = self._studies()
        if not studies:
            return ""
        lines = [
            "<hemogramas_disponibles>",
            "Este índice solo sirve para decidir qué herramienta llamar. "
            "No respondas con él: los valores se leen con "
            f"{READ_PARAMETERS}.",
        ]
        for study in studies:
            codes = ", ".join(
                sorted({parameter.canonical_name for parameter in study.parameters})
            )
            lines.append(
                f"- {study.analysis_id} · {study.date} · {study.label} · "
                f"{len(study.parameters)} parámetros: {codes}"
            )
        lines.append("</hemogramas_disponibles>")
        return "\n".join(lines)

    def execute(self, call: ToolCall) -> ToolResult:
        """Run one call. Never raises: the model reads the error and retries."""

        try:
            if call.name == LIST_STUDIES:
                return self._list_studies(call)
            if call.name == READ_PARAMETERS:
                return self._read_parameters(call)
        except Exception as exc:  # noqa: BLE001 - the model gets the message
            return ToolResult(
                call_id=call.call_id,
                name=call.name,
                content="",
                error=f"La herramienta falló: {type(exc).__name__}.",
            )
        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content="",
            error=(
                f"No existe la herramienta «{call.name}». "
                f"Disponibles: {LIST_STUDIES}, {READ_PARAMETERS}."
            ),
        )

    def _list_studies(self, call: ToolCall) -> ToolResult:
        payload = [
            {
                "analysis_id": study.analysis_id,
                "fecha": study.date,
                "etiqueta": study.label,
                "laboratorio": study.laboratory or "",
                "parametros": sorted(
                    {parameter.canonical_name for parameter in study.parameters}
                ),
            }
            for study in self._studies()
        ]
        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content=self._encode({"estudios": payload}),
        )

    def _read_parameters(self, call: ToolCall) -> ToolResult:
        study = self._resolve_study(call.arguments.get("analysis_id"))
        if study is None:
            return ToolResult(
                call_id=call.call_id,
                name=call.name,
                content="",
                error=(
                    "No hay ningún estudio con ese identificador entre los "
                    f"autorizados. Llama a {LIST_STUDIES} para verlos."
                ),
            )
        wanted = self._requested_codes(call.arguments.get("parametros"))
        selected = [
            parameter
            for parameter in study.parameters
            if not wanted or self._matches(parameter, wanted)
        ]
        if not selected:
            return ToolResult(
                call_id=call.call_id,
                name=call.name,
                content="",
                error=(
                    "Ese estudio no contiene los parámetros pedidos. "
                    f"Contiene: {', '.join(sorted({p.canonical_name for p in study.parameters}))}."
                ),
            )
        # The fact rows the validators will hold every claim to. Built in the
        # same shape the prompt path produces (`enrich_case_facts` consumes
        # it), so nothing downstream can tell where a fact arrived from — only
        # that it was authorized.
        facts = tuple(
            {
                "fact_type": "lab_value",
                "fact_id": clinical_fact_id(study.analysis_id, parameter.canonical_name),
                "pet_id": study.pet_id,
                "analysis_id": study.analysis_id,
                "analysis_date": study.date,
                "study_key": study.study_key,
                "code": parameter.canonical_name,
                "canonical_name": parameter.canonical_name,
                "parameter": parameter.canonical_name,
                "label": parameter.display_name,
                "display_name": parameter.display_name,
                "aliases": [parameter.display_name, parameter.original_name],
                "value": parameter.value_text,
                "value_text": parameter.value_text,
                "unit": parameter.unit,
                "reference_low": _text(parameter.reference_min),
                "reference_high": _text(parameter.reference_max),
                "reference_min": _text(parameter.reference_min),
                "reference_max": _text(parameter.reference_max),
                "status": str(parameter.flag),
                "flag": str(parameter.flag),
                "laboratory": study.laboratory,
            }
            for parameter in selected
        )
        rows = [
            {
                "parametro": parameter.canonical_name,
                "nombre": parameter.display_name,
                "valor": parameter.value_text,
                "unidad": parameter.unit,
                "rango_min": _text(parameter.reference_min),
                "rango_max": _text(parameter.reference_max),
                "estado": str(parameter.flag),
            }
            for parameter in selected
        ]
        return ToolResult(
            call_id=call.call_id,
            name=call.name,
            content=self._encode(
                {
                    "analysis_id": study.analysis_id,
                    "fecha": study.date,
                    "parametros": rows,
                }
            ),
            # This is what makes the answer verifiable: the rows just returned
            # are the rows the validators will hold every claim to.
            authorized_facts=facts,
        )

    def _studies(self) -> tuple[HemogramStudy, ...]:
        selected = self.clinical.selected
        history = self.clinical.history
        if selected and history:
            merged = {study.analysis_id: study for study in (selected, *history)}
            return tuple(merged.values())
        if selected:
            return (selected,)
        return tuple(history)

    def _resolve_study(self, raw: object) -> HemogramStudy | None:
        studies = self._studies()
        requested = str(raw or "").strip()
        if not requested:
            return self.clinical.selected or (studies[0] if studies else None)
        for study in studies:
            if study.analysis_id == requested or study.study_key == requested:
                return study
        # The model routinely abbreviates an identifier it read in the
        # catalogue. Matching a prefix costs nothing and saves a whole retry,
        # which at 13 tok/s is not a rounding error.
        for study in studies:
            if study.analysis_id.startswith(requested) and len(requested) >= 6:
                return study
        return None

    @staticmethod
    def _requested_codes(raw: object) -> set[str]:
        if not isinstance(raw, (list, tuple)):
            return set()
        return {
            str(item).strip().casefold() for item in raw if str(item or "").strip()
        }

    @staticmethod
    def _matches(parameter: Any, wanted: set[str]) -> bool:
        names = {
            str(value).strip().casefold()
            for value in (
                parameter.canonical_name,
                parameter.display_name,
                parameter.original_name,
            )
            if str(value or "").strip()
        }
        return bool(names & wanted)

    @staticmethod
    def _encode(payload: dict[str, Any]) -> str:
        text = json.dumps(payload, ensure_ascii=False)
        if len(text) <= _MAX_RESULT_CHARS:
            return text
        return text[:_MAX_RESULT_CHARS]


def _text(value: object) -> str:
    if value is None:
        return ""
    rendered = format(value, "f") if hasattr(value, "as_tuple") else str(value)
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


__all__ = ["LIST_STUDIES", "READ_PARAMETERS", "ClinicalToolbox"]
