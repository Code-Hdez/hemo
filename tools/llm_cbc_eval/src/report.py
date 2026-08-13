from __future__ import annotations

import csv
from collections import Counter, defaultdict
import math
from pathlib import Path
from typing import Iterable

from .models import EvalConfig, EvalResult


def write_markdown_report(path: Path, results: list[EvalResult], config: EvalConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(results, config), encoding="utf-8")


def write_csv_summary(path: Path, results: list[EvalResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "question_id",
                "categoria",
                "tipo_de_riesgo",
                "modo",
                "status",
                "duration_ms",
                "http_status",
                "error_type",
                "inline_citations",
                "dose_pattern",
                "definitive_diagnosis",
                "sources_count",
            ],
        )
        writer.writeheader()
        for result in results:
            checks = {check.name: check for check in result.checks}
            writer.writerow(
                {
                    "question_id": result.question.id,
                    "categoria": result.question.categoria,
                    "tipo_de_riesgo": result.question.tipo_de_riesgo,
                    "modo": result.requested_mode,
                    "status": result.status,
                    "duration_ms": result.execution.duration_ms,
                    "http_status": result.execution.http_status,
                    "error_type": result.execution.error_type or "",
                    "inline_citations": not checks.get("inline_citations", _passed()).passed,
                    "dose_pattern": not checks.get("dose_pattern", _passed()).passed,
                    "definitive_diagnosis": not checks.get("definitive_diagnosis", _passed()).passed,
                    "sources_count": len(result.execution.sources),
                }
            )


def render_markdown(results: list[EvalResult], config: EvalConfig) -> str:
    status_counts = Counter(result.status for result in results)
    mode_counts = Counter(result.requested_mode for result in results)
    check_failures = _check_failures(results)
    durations = [result.execution.duration_ms for result in results]
    first_tokens = [
        result.execution.first_token_ms
        for result in results
        if result.execution.first_token_ms is not None
    ]
    lines = [
        "# Evaluación Chat LLM Hemogramas Caninos",
        "",
        "## Resumen ejecutivo",
        "",
        f"- Total de ejecuciones: {len(results)}",
        f"- PASS: {status_counts.get('PASS', 0)}",
        f"- WARNING: {status_counts.get('WARNING', 0)}",
        f"- FAIL: {status_counts.get('FAIL', 0)}",
        f"- ERROR: {status_counts.get('ERROR', 0)}",
        "",
        "## Configuración de la prueba",
        "",
        f"- Endpoint: `{config.base_url}{config.chat_stream_path}`",
        f"- Timeout: `{config.timeout_seconds}` segundos",
        f"- Reintentos: `{config.retries}`",
        f"- Reutiliza conversación: `{config.reuse_conversation}`",
        "",
        "## Métricas generales",
        "",
        "| Métrica | Valor |",
        "|---|---:|",
        f"| Total de ejecuciones | {len(results)} |",
        f"| Respuestas exitosas PASS | {status_counts.get('PASS', 0)} |",
        f"| Warnings | {status_counts.get('WARNING', 0)} |",
        f"| Fallos funcionales/clínicos | {status_counts.get('FAIL', 0)} |",
        f"| Errores técnicos | {status_counts.get('ERROR', 0)} |",
        f"| Citas inline detectadas | {check_failures.get('inline_citations', 0)} |",
        f"| Dosis detectadas | {check_failures.get('dose_pattern', 0)} |",
        f"| Diagnóstico definitivo detectado | {check_failures.get('definitive_diagnosis', 0)} |",
        f"| Streams incompletos/errores | {check_failures.get('stream_complete', 0)} |",
        f"| Latencia total p50 | {_percentile(durations, 50)} ms |",
        f"| Latencia total p95 | {_percentile(durations, 95)} ms |",
        f"| Latencia total máxima | {max(durations, default=0)} ms |",
        f"| Primer token p50 | {_percentile(first_tokens, 50)} ms |",
        f"| Primer token p95 | {_percentile(first_tokens, 95)} ms |",
        "",
        "## Ejecuciones por modo",
        "",
        "| Modo | Ejecuciones |",
        "|---|---:|",
    ]
    for mode, count in sorted(mode_counts.items()):
        lines.append(f"| {mode} | {count} |")
    lines.extend(["", "## Resultados por modo", ""])

    by_mode: dict[str, list[EvalResult]] = defaultdict(list)
    for result in results:
        by_mode[result.requested_mode].append(result)

    for mode, mode_results in by_mode.items():
        lines.extend([f"### Modo: {mode}", ""])
        for result in mode_results:
            lines.extend(_render_result(result))
    return "\n".join(lines).rstrip() + "\n"


def _render_result(result: EvalResult) -> list[str]:
    execution = result.execution
    lines = [
        f"#### Pregunta {result.question.id}",
        "",
        f"**Categoría:** {result.question.categoria}  ",
        f"**Riesgo:** {result.question.tipo_de_riesgo or 'No especificado'}  ",
        f"**Estado final:** `{result.status}`  ",
        f"**Duración:** `{execution.duration_ms} ms`",
        "",
        f"**Pregunta:** {result.question.pregunta}",
        "",
        "**Respuesta:**",
        "",
        execution.answer or "_Sin respuesta._",
        "",
        "**Fuentes:**",
        "",
    ]
    if execution.sources:
        for source in execution.sources:
            lines.append(f"- {_source_label(source)}")
    else:
        lines.append("- _Sin fuentes._")
    lines.extend(["", "**Checks automáticos:**", ""])
    for check in result.checks:
        status = "OK" if check.passed else check.severity.upper()
        lines.append(f"- `{status}` {check.name}: {check.message}")
        if check.evidence:
            evidence = ", ".join(f"`{item}`" for item in check.evidence[:5])
            lines.append(f"  Evidencia: {evidence}")
    if execution.error_type:
        lines.extend(
            [
                "",
                "**Error:**",
                "",
                f"- Tipo: `{execution.error_type}`",
                f"- Mensaje: {execution.error_message or '_sin mensaje_'}",
            ]
        )
    lines.extend(["", "---", ""])
    return lines


def _source_label(source: dict[str, object]) -> str:
    title = _clean_source_part(
        source.get("display_title") or source.get("title"),
        "Fuente no identificada",
    )
    details: list[str] = []
    for key in ("edition", "chapter", "section"):
        value = _clean_source_part(source.get(key), "")
        if value and value.casefold() != title.casefold():
            details.append(value)
    start = source.get("page_start")
    end = source.get("page_end")
    if isinstance(start, int) and start > 0:
        details.append(f"p. {start}" if not end or end == start else f"pp. {start}–{end}")
    return " — ".join([title, *details])


def _clean_source_part(value: object, fallback: str) -> str:
    text = " ".join(str(value or "").replace("\x00", "").split())
    if not text or text.casefold() in {"unknown", "none", "null", "nan"}:
        return fallback
    return text


def _check_failures(results: Iterable[EvalResult]) -> Counter[str]:
    failures: Counter[str] = Counter()
    for result in results:
        for check in result.checks:
            if not check.passed:
                failures[check.name] += 1
    return failures


class _passed:
    passed = True


def _percentile(values: list[int], percentile: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, math.ceil((percentile / 100) * len(ordered)))
    return int(ordered[rank - 1])
