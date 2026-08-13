from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal


ContextMode = Literal["general", "hemograma_seleccionado", "hemograma_historico"]

MODE_LABELS: dict[ContextMode, str] = {
    "general": "General",
    "hemograma_seleccionado": "Hemograma seleccionado",
    "hemograma_historico": "Historial",
}

# El arnés `llm_cbc_eval` guarda el modo pedido (`modo`), el backend guarda el
# `context_scope` y las capturas manuales suelen traer el nombre en inglés. Los
# tres apuntan a las mismas tres opciones de contexto del asistente.
_MODE_ALIASES: dict[str, ContextMode] = {
    "general": "general",
    "informacion_general": "general",
    "chat_general": "general",
    "hemograma_seleccionado": "hemograma_seleccionado",
    "selected_hemogram": "hemograma_seleccionado",
    "uploaded_analysis": "hemograma_seleccionado",
    "hemograma_historico": "hemograma_historico",
    "hemogram_history": "hemograma_historico",
    "historical_analysis": "hemograma_historico",
}

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "question": ("pregunta", "question", "message"),
    "answer": ("answer", "respuesta", "response"),
    "mode": ("modo", "mode", "backend_mode", "context_scope"),
    "sources": ("sources", "fuentes", "contexts", "retrieved_contexts"),
    "case_facts": ("case_facts", "hechos", "facts"),
    "question_id": ("question_id", "id", "caso"),
    "category": ("categoria", "category"),
    "expected": ("esperado", "expected", "ground_truth"),
    "safety_action": ("safety_action", "accion_seguridad"),
    "status": ("status", "estado"),
    "checks": ("checks", "validaciones"),
    "run_id": ("run_id", "corrida"),
}


@dataclass(frozen=True, slots=True)
class Source:
    identifier: str
    title: str
    score: float | None
    path: str = ""


@dataclass(frozen=True, slots=True)
class Turn:
    """Un turno capturado: lo que se preguntó, lo que se respondió y con qué."""

    question_id: str
    category: str
    mode: ContextMode
    question: str
    answer: str
    sources: list[Source] = field(default_factory=list)
    case_facts: list[dict[str, Any]] = field(default_factory=list)
    expected: str = ""
    safety_action: str | None = None
    status: str | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)
    run_id: str | None = None

    @property
    def delivered(self) -> bool:
        """Turno entregado al usuario: hay texto y el arnés no lo marcó ERROR."""
        return bool(self.answer.strip()) and self.status != "ERROR"

    @property
    def explanatory(self) -> bool:
        """Turno que sí intentó explicar, en vez de rechazar por seguridad.

        Los rechazos usan plantillas casi idénticas entre preguntas, así que
        mezclarlos con las explicaciones hunde cualquier medida de relevancia:
        en el corpus de julio, incluirlos baja el acierto del 95 % al 77 %.
        """
        return self.delivered and self.safety_action in {None, "allow"}


def load_turns(paths: Iterable[Path], *, run_id: str | None = None) -> list[Turn]:
    """Lee uno o varios JSONL de respuestas capturadas y los normaliza."""
    turns: list[Turn] = []
    for path in paths:
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL inválido en {path} línea {line_number}.") from exc
            turn = build_turn(record)
            if turn is None:
                continue
            if run_id and turn.run_id != run_id:
                continue
            turns.append(turn)
    return turns


def build_turn(record: dict[str, Any]) -> Turn | None:
    """Convierte un registro crudo en `Turn`; descarta los de modo desconocido."""
    mode = normalize_mode(_pick(record, "mode"))
    if mode is None:
        return None
    return Turn(
        question_id=str(_pick(record, "question_id") or "").strip(),
        category=str(_pick(record, "category") or "sin_categoria").strip(),
        mode=mode,
        question=str(_pick(record, "question") or "").strip(),
        answer=str(_pick(record, "answer") or ""),
        sources=[_build_source(item) for item in _pick(record, "sources") or []],
        case_facts=list(_pick(record, "case_facts") or []),
        expected=str(_pick(record, "expected") or "").strip(),
        safety_action=_optional_str(_pick(record, "safety_action")),
        status=_optional_str(_pick(record, "status")),
        checks=list(_pick(record, "checks") or []),
        run_id=_optional_str(_pick(record, "run_id")),
    )


def normalize_mode(value: Any) -> ContextMode | None:
    return _MODE_ALIASES.get(str(value or "").strip().lower())


def latest_run_id(paths: Iterable[Path]) -> str | None:
    """Devuelve el `run_id` más reciente por orden lexicográfico del sello UTC."""
    run_ids = {turn.run_id for turn in load_turns(paths) if turn.run_id}
    return max(run_ids) if run_ids else None


def group_by_mode(turns: Iterable[Turn]) -> dict[ContextMode, list[Turn]]:
    grouped: dict[ContextMode, list[Turn]] = {mode: [] for mode in MODE_LABELS}
    for turn in turns:
        grouped[turn.mode].append(turn)
    return grouped


def iter_case_values(turn: Turn) -> Iterator[float]:
    """Valores y límites de referencia del caso, únicos datos numéricos citables."""
    for fact in turn.case_facts:
        for key in ("value", "ref_min", "ref_max"):
            number = parse_number(fact.get(key))
            if number is not None:
                yield number


def case_labels(turn: Turn) -> set[str]:
    labels: set[str] = set()
    for fact in turn.case_facts:
        for key in ("code", "label"):
            value = str(fact.get(key) or "").strip().lower()
            if value:
                labels.add(value)
    return labels


def parse_number(value: Any) -> float | None:
    """Acepta la coma decimal del informe clínico y el punto del JSON."""
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _build_source(item: Any) -> Source:
    if not isinstance(item, dict):
        return Source(identifier=str(item), title=str(item), score=None)
    identifier = str(
        item.get("source_id") or item.get("citation_id") or item.get("id") or ""
    ).strip()
    title = str(item.get("title") or item.get("display_title") or identifier).strip()
    return Source(
        identifier=identifier,
        title=title,
        score=parse_number(item.get("score")),
        path=str(item.get("source_path") or "").strip(),
    )


def _pick(record: dict[str, Any], field_name: str) -> Any:
    for alias in _FIELD_ALIASES[field_name]:
        if record.get(alias) not in (None, ""):
            return record[alias]
    return None


def _optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
