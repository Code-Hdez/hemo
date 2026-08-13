from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .metrics import MetricReport, MetricScore
from .records import MODE_LABELS, ContextMode, Turn, group_by_mode
from .semantic import GroundingCalibration, RelevanceScore


_COLUMNS: list[tuple[ContextMode | str, str]] = [
    *[(mode, label) for mode, label in MODE_LABELS.items()],
    ("total", "Total"),
]
_MAX_OFFENDERS = 10
_MAX_LISTED_SOURCES = 4

# Lo que un juez LLM externo mediría y aquí no se calcula. Se declara en el
# informe para que el tribunal no lea la ausencia como un resultado favorable.
_OUT_OF_SCOPE = [
    (
        "`faithfulness` de RAGAS/DeepEval",
        "Exige un juez LLM que descomponga la respuesta en afirmaciones y las "
        "contraste contra el pasaje recuperado. Aquí se sustituye por la "
        "fidelidad numérica, que es verificable sin juez pero solo cubre cifras.",
    ),
    (
        "`context_recall` y `context_precision` de RAGAS",
        "Necesitan un conjunto de pasajes correctos anotados pregunta por "
        "pregunta. La batería define el comportamiento esperado, no qué página "
        "del manual era la correcta, así que no existe el patrón de comparación.",
    ),
    (
        "`answer_correctness` frente a respuesta de referencia",
        "No hay respuestas modelo redactadas por el veterinario para las 62 "
        "preguntas; compararlas exigiría escribirlas primero.",
    ),
]


def render_markdown(
    turns: list[Turn],
    report: MetricReport,
    *,
    sources: list[Path],
    run_id: str | None = None,
    relevance: dict[ContextMode | str, RelevanceScore] | None = None,
    grounding: GroundingCalibration | None = None,
) -> str:
    grouped = group_by_mode(turns)
    lines = [
        "# Evaluación offline del asistente HemoVet",
        "",
        f"- Generado: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Respuestas analizadas: {len(turns)}",
        f"- Corrida: `{run_id or 'todas las presentes en los ficheros'}`",
        f"- Ficheros de entrada: {_format_sources(sources)}",
        "",
        "| Modo de contexto | Turnos |",
        "|---|---:|",
    ]
    for mode, label in MODE_LABELS.items():
        lines.append(f"| {label} | {len(grouped[mode])} |")
    lines += [
        "",
        "## Resultados por modo de contexto",
        "",
        "| Métrica | " + " | ".join(label for _, label in _COLUMNS) + " |",
        "|---" * (len(_COLUMNS) + 1) + "|",
    ]
    for definition in report.definitions:
        cells = [
            _format_score(report.scores[definition.key].get(column), definition.kind)
            for column, _ in _COLUMNS
        ]
        lines.append(f"| {definition.label} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Cada celda muestra el porcentaje y, entre paréntesis, los casos que lo "
        "sustentan. `n/d` significa que ningún turno de ese modo activa la métrica.",
        "",
        "## Qué mide cada métrica",
        "",
        "| Métrica | Qué comprueba |",
        "|---|---|",
    ]
    for definition in report.definitions:
        lines.append(f"| {definition.label} | {definition.detail} |")
    if relevance:
        lines += _relevance_section(relevance)
    if grounding:
        lines += _grounding_section(grounding)
    lines += [
        "",
        "## Métricas que quedan fuera y por qué",
        "",
        "| Métrica del marco original | Motivo de la exclusión |",
        "|---|---|",
    ]
    for name, reason in _OUT_OF_SCOPE:
        lines.append(f"| {name} | {reason} |")
    lines += _offenders_section(report)
    lines.append("")
    return "\n".join(lines)


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relevance_section(relevance: dict[ContextMode | str, RelevanceScore]) -> list[str]:
    lines = [
        "",
        "## Relevancia de la respuesta (medida con el mismo embebedor del buscador)",
        "",
        "| Modo de contexto | Turnos | Pregunta y su respuesta | Pregunta y una respuesta ajena | Acierto al distinguirlas |",
        "|---|---:|---:|---:|---:|",
    ]
    for column, label in _COLUMNS:
        score = relevance.get(column)
        if score is None:
            continue
        lines.append(
            f"| {label} | {score.turns} | {_decimal(score.own_mean)} | "
            f"{_decimal(score.mismatched_mean)} | {_percent(score.win_rate)} |"
        )
    lines += [
        "",
        "La columna de respuestas ajenas es la línea base: se compara cada "
        "pregunta con la respuesta de otra pregunta del mismo lote. La última "
        "columna indica con qué frecuencia la respuesta propia queda por encima "
        "de la ajena; sin esa separación, la cifra de la tercera columna no "
        "significaría nada.",
    ]
    return lines


def _grounding_section(grounding: GroundingCalibration) -> list[str]:
    verdict = (
        "no es utilizable como métrica"
        if grounding.win_rate < 0.75
        else "muestra separación suficiente"
    )
    return [
        "",
        "## Calibración del anclaje respuesta↔documento",
        "",
        f"- Turnos calibrados: {grounding.turns}",
        f"- Parecido con el documento que sí se recuperó: {_decimal(grounding.own_mean)}",
        f"- Parecido con otro documento cualquiera del corpus: {_decimal(grounding.rival_mean)}",
        f"- Acierto al distinguirlos: {_percent(grounding.win_rate)}",
        "",
        f"Con estas cifras, el anclaje semántico {verdict} en este sistema: la "
        "respuesta está en español y el corpus en inglés, y el modelo de "
        "búsqueda no separa el documento usado de otro documento de hematología. "
        "Por eso el informe no publica una cifra de fidelidad documental.",
    ]


def _offenders_section(report: MetricReport) -> list[str]:
    if not report.offenders:
        return []
    lines = ["", "## Casos que exigen revisión manual", ""]
    labels = {definition.key: definition.label for definition in report.definitions}
    for key, entries in report.offenders.items():
        lines.append(f"### {labels.get(key, key)} ({len(entries)})")
        lines.append("")
        for entry in entries[:_MAX_OFFENDERS]:
            lines.append(f"- {entry}")
        if len(entries) > _MAX_OFFENDERS:
            lines.append(f"- … y {len(entries) - _MAX_OFFENDERS} más.")
        lines.append("")
    return lines


def _format_sources(sources: list[Path]) -> str:
    listed = ", ".join(f"`{path}`" for path in sources[:_MAX_LISTED_SOURCES])
    if len(sources) <= _MAX_LISTED_SOURCES:
        return listed
    return f"{listed} y {len(sources) - _MAX_LISTED_SOURCES} ficheros más"


def _format_score(score: MetricScore | None, kind: str) -> str:
    if score is None or not score.applicable or score.value is None:
        return "n/d"
    if kind == "score":
        return f"{_decimal(score.value)} (n={score.total})"
    return f"{_percent(score.value)} ({score.passed}/{score.total})"


def _percent(value: float) -> str:
    return f"{value * 100:.1f} %".replace(".", ",")


def _decimal(value: float) -> str:
    return f"{value:.3f}".replace(".", ",")
