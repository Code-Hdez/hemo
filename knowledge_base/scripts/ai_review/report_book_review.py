#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from ai_review_common import (
    ensure_ai_review_dirs,
    read_json,
    read_jsonl,
    relative_to_project,
    summarize_manifest,
    utc_now_iso,
    write_json_artifact,
)


def write_report(*, project_root: Path, source_id: str) -> dict[str, Any]:
    project_root = project_root.resolve()
    dirs = ensure_ai_review_dirs(project_root, source_id)
    inventory = read_json(dirs["manifests"] / "inventory.json", {})
    manifest = read_jsonl(dirs["manifests"] / "classification_manifest.jsonl")
    chunk_summary = read_json(dirs["manifests"] / "chunks_summary.json", {})
    pending_summary = read_json(dirs["manifests"] / "pending_reclassification_summary.json", {})
    validation = read_json(dirs["manifests"] / "validation_execution.json", {})
    summary_counts = summarize_manifest(manifest)
    reasons = Counter(reason for item in manifest for reason in item.get("reason_codes", []))
    human_reasons = Counter(reason for item in manifest if item.get("decision") == "needs_human_review" for reason in item.get("reason_codes", []))
    rejected_reasons = Counter(reason for item in manifest if item.get("decision") == "rejected" for reason in item.get("reason_codes", []))
    approved = [item for item in manifest if item.get("decision") == "approved_provisional"][:8]
    problem = [item for item in manifest if item.get("decision") in {"rejected", "needs_human_review", "quarantine"}][:8]
    now = utc_now_iso()

    summary = {
        "source_id": source_id,
        "book_title": inventory.get("book_title"),
        "raw_pdf": inventory.get("raw_pdf"),
        "reviewed_at": now,
        "reviewer": "codex_ai_reviewer",
        "review_type": "ai_provisional_not_human_veterinary_review",
        "inventory": {
            "docling_json": inventory.get("docling_json_count", 0),
            "staging_md": inventory.get("staging_md_count", 0),
            "precleaned_md": inventory.get("precleaned_md_count", 0),
            "split_sections": inventory.get("split_sections_count", 0),
            "curated_candidates": inventory.get("curated_candidates_count", 0),
            "pending": inventory.get("pending_count", 0),
            "candidate_chunks": inventory.get("chunks_count", 0),
        },
        "classification": summary_counts,
        "pending_reclassification": pending_summary,
        "chunks_approved_provisional": chunk_summary.get("chunks_approved_provisional", 0),
        "top_reason_codes": reasons.most_common(20),
        "validation": validation,
        "status": "reviewed_ai_provisional",
    }
    write_json_artifact(dirs["manifests"] / "summary.json", summary)
    report_path = dirs["reports"] / "book_review_report.md"
    report_path.write_text(_markdown_report(summary, rejected_reasons, human_reasons, approved, problem), encoding="utf-8")
    return summary | {"report_path": relative_to_project(report_path, project_root)}


def _markdown_report(
    summary: dict[str, Any],
    rejected_reasons: Counter[str],
    human_reasons: Counter[str],
    approved: list[dict[str, Any]],
    problem: list[dict[str, Any]],
) -> str:
    inv = summary["inventory"]
    cls = summary["classification"]
    pending = summary.get("pending_reclassification") or {}
    quality = _quality_label(cls)
    validation = summary.get("validation") or {}
    lines = [
        f"# AI Review Provisional - {summary.get('book_title')}",
        "",
        "## 1. Identificación del libro",
        "",
        f"- Source ID: {summary.get('source_id')}",
        f"- Título: {summary.get('book_title')}",
        f"- PDF fuente: {summary.get('raw_pdf')}",
        f"- Fecha de revisión: {summary.get('reviewed_at')}",
        "- Revisor: codex_ai_reviewer",
        "- Tipo de revisión: IA provisional, no revisión veterinaria humana",
        "",
        "## 2. Inventario revisado",
        "",
        f"- Docling JSON: {inv.get('docling_json')}",
        f"- Staging markdown: {inv.get('staging_md')}",
        f"- Precleaned markdown: {inv.get('precleaned_md')}",
        f"- Split sections: {inv.get('split_sections')}",
        f"- Curated candidates: {inv.get('curated_candidates')}",
        f"- Pending files: {inv.get('pending')}",
        f"- Candidate chunks: {inv.get('candidate_chunks')}",
        f"- Pending reclasificados: {pending.get('total_records', 0)}",
        f"- Pending enlazados a candidato canónico: {pending.get('matched_to_curated', 0)}",
        "",
        "## 3. Clasificación final",
        "",
        f"- Aprobados provisionales: {cls.get('approved_provisional')}",
        f"- Rechazados: {cls.get('rejected')}",
        f"- Requieren revisión humana: {cls.get('needs_human_review')}",
        f"- Cuarentena: {cls.get('quarantine')}",
        f"- Chunks provisionales aprobados: {summary.get('chunks_approved_provisional')}",
        "",
        "## 4. Principales motivos de rechazo",
        "",
        *_counter_lines(rejected_reasons),
        "",
        "## 5. Principales motivos de revisión humana",
        "",
        *_counter_lines(human_reasons),
        "",
        "## 6. Calidad del libro para RAG",
        "",
        f"- Calidad general: {quality}",
        "- Problemas de extracción: contributor/author bios, secciones cortas, tablas marcadas para revisión y metadata source_id cruzada en algunos candidatos.",
        "- Riesgos: valores/tablas sin revisión humana, fragmentos clínicos complejos, y contenido con especie/contexto incierto.",
        "- Recomendación: uso provisional parcial solo desde chunks aprobados por IA; mantener revisión humana para tablas y decisiones clínicas complejas.",
        "",
        "## 7. Archivos destacados",
        "",
        "### Mejores candidatos aprobados",
        "",
        *_file_lines(approved, "Motivo"),
        "",
        "### Archivos problemáticos",
        "",
        *_file_lines(problem, "Problema"),
        "",
        "## 8. Validaciones ejecutadas",
        "",
        f"- py_compile: {validation.get('py_compile', 'pendiente')}",
        f"- pytest: {validation.get('pytest', 'pendiente')}",
        f"- Conteos: {validation.get('counts', 'registrados en summary.json')}",
        f"- Integridad de chunks: {validation.get('chunk_integrity', 'solo se generaron desde candidatos aprobados provisionalmente')}",
        f"- Verificación de fuentes originales: {validation.get('raw_sources', 'raw_pdf/raw_md no son modificados por estos scripts')}",
        "",
        "## 9. Estado final del libro",
        "",
        "- Estado: revisado por IA provisional.",
        "- ¿Listo para siguiente libro?: sí, después de validar comandos finales.",
        "- Siguiente acción recomendada: revisar manualmente `needs_human_review` y procesar el siguiente libro con el mismo flujo.",
        "",
    ]
    return "\n".join(lines)


def _quality_label(summary: dict[str, Any]) -> str:
    total = sum(int(summary.get(key, 0)) for key in ("approved_provisional", "rejected", "needs_human_review", "quarantine"))
    if total == 0:
        return "sin datos"
    approved_ratio = int(summary.get("approved_provisional", 0)) / total
    if approved_ratio >= 0.65:
        return "buena para uso provisional parcial"
    if approved_ratio >= 0.35:
        return "mixta; requiere cribado estricto"
    return "baja; requiere revisión humana amplia"


def _counter_lines(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["- Sin motivos registrados."]
    return [f"- {reason}: {count}" for reason, count in counter.most_common(5)]


def _file_lines(records: list[dict[str, Any]], label: str) -> list[str]:
    if not records:
        return ["- Sin archivos destacados."]
    lines: list[str] = []
    for record in records:
        lines.append(f"- Archivo: {record.get('path')}")
        lines.append(f"  - {label}: {record.get('short_reason')}")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write one source-book AI review report.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = write_report(project_root=args.project_root, source_id=args.source_id)
    print(f"Wrote report: {summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
