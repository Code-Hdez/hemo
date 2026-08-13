#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import build_chunks
import convert_raw_pdfs_docling
import generate_curated_candidates
import preclean_raw_md
import split_markdown_sections
import validate_curated_md
from pipeline_common import ensure_directories, ensure_prompt_template, kb_root, read_json


def run_pipeline(
    *,
    project_root: Path,
    source_mode: str = "docling",
    skip_docling: bool = False,
    docling_limit: int | None = None,
    docling_source_files: list[str] | None = None,
    docling_max_pages: int | None = None,
    docling_page_range: tuple[int, int] | None = None,
    docling_batch_pages: int = convert_raw_pdfs_docling.DEFAULT_BATCH_PAGES,
    docling_force: bool = False,
    docling_device: str = "auto",
    docling_ocr: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    ensure_prompt_template(project_root)
    root = kb_root(project_root)

    if source_mode not in {"docling", "raw-md"}:
        raise ValueError("source_mode must be 'docling' or 'raw-md'")

    docling_summary: dict[str, Any] | None = None
    if source_mode == "docling" and not skip_docling:
        docling_summary = convert_raw_pdfs_docling.run_docling_conversion(
            project_root=project_root,
            limit=docling_limit,
            source_files=docling_source_files,
            max_pages=docling_max_pages,
            page_range=docling_page_range,
            batch_pages=docling_batch_pages,
            force=docling_force,
            accelerator_device=docling_device,
            do_ocr=docling_ocr,
            dry_run=dry_run,
        )
        if docling_summary["failed"]:
            raise RuntimeError(
                f"Docling conversion failed for {docling_summary['failed']} PDFs."
            )

    source_input = root / "staging_md" if source_mode == "docling" else root / "raw_md"

    cleaning = preclean_raw_md.run_preclean(
        project_root=project_root,
        input_dir=source_input,
        dry_run=dry_run,
    )
    split = split_markdown_sections.run_split(project_root=project_root, dry_run=dry_run)
    candidates = generate_curated_candidates.run_generate(project_root=project_root, dry_run=dry_run)
    validation = validate_curated_md.run_validation(project_root=project_root, dry_run=dry_run)
    chunks = build_chunks.run_build_chunks(project_root=project_root, dry_run=dry_run)

    summary = {
        "source_mode": source_mode,
        "source_input": source_input.relative_to(project_root).as_posix(),
        "docling_converted": docling_summary["converted"] if docling_summary else None,
        "docling_failed": docling_summary["failed"] if docling_summary else None,
        "docling_source_files": docling_summary.get("source_files", []) if docling_summary else [],
        "docling_max_pages": docling_summary.get("max_pages") if docling_summary else None,
        "docling_page_range": docling_summary.get("page_range") if docling_summary else None,
        "docling_batch_pages": docling_summary.get("batch_pages") if docling_summary else None,
        "docling_total_batches": docling_summary.get("total_batches") if docling_summary else None,
        "docling_converted_batches": docling_summary.get("converted_batches") if docling_summary else None,
        "docling_skipped_batches": docling_summary.get("skipped_batches") if docling_summary else None,
        "docling_failed_batches": docling_summary.get("failed_batches") if docling_summary else None,
        "docling_device": docling_summary.get("accelerator_device") if docling_summary else None,
        "raw_files_processed": cleaning["files_processed"],
        "sections_generated": split["sections_generated"],
        "curated_candidates": candidates["candidates_generated"],
        "auto_rejected": candidates.get("auto_rejected", 0) + split["sections_rejected"],
        "valid_candidates": validation["valid_candidate"],
        "warnings": validation["warning"],
        "rejected": validation["rejected"] + split["sections_rejected"],
        "chunks_generated": chunks["chunks_generated"],
        "reports_dir": str(kb_root(project_root) / "reports"),
        "candidate_chunks": chunks["output_file"],
    }
    if not dry_run:
        write_corpus_summary(project_root=project_root, pipeline_summary=summary)
    return summary


def write_corpus_summary(*, project_root: Path, pipeline_summary: dict[str, Any]) -> Path:
    root = kb_root(project_root)
    report_path = root / "reports" / "corpus_summary.md"
    cleaning = read_json(root / "reports" / "cleaning_report.json", {"records": []})
    validation = read_json(root / "reports" / "validation_report.json", {"records": []})
    duplicate = read_json(root / "reports" / "duplicate_report.json", {})

    noisy_records = sorted(
        cleaning.get("records", []),
        key=lambda item: (
            sum(int(value) for value in item.get("patterns_removed", {}).values()),
            item.get("original_characters", 0) - item.get("final_characters", 0),
        ),
        reverse=True,
    )[:10]
    urgent_records = [
        item
        for item in validation.get("records", [])
        if item.get("classification") in {"warning", "rejected"}
    ][:20]
    raw_pdf_dir = root / "raw_pdf"
    has_source_pdfs = raw_pdf_dir.exists() and any(raw_pdf_dir.glob("*.pdf"))

    lines = [
        "# Corpus Summary",
        "",
        "## Pipeline summary",
        "",
        f"- Source mode: {pipeline_summary.get('source_mode')}",
        f"- Source input: {pipeline_summary.get('source_input')}",
        f"- PDFs converted with Docling: {pipeline_summary.get('docling_converted')}",
        f"- Docling failures: {pipeline_summary.get('docling_failed')}",
        f"- Docling selected PDFs: {pipeline_summary.get('docling_source_files') or 'all'}",
        f"- Docling max pages: {pipeline_summary.get('docling_max_pages') or 'all'}",
        f"- Docling page range: {pipeline_summary.get('docling_page_range') or 'all'}",
        f"- Docling batch pages: {pipeline_summary.get('docling_batch_pages') or 'n/a'}",
        f"- Docling total batches: {pipeline_summary.get('docling_total_batches')}",
        f"- Docling converted batches: {pipeline_summary.get('docling_converted_batches')}",
        f"- Docling skipped batches: {pipeline_summary.get('docling_skipped_batches')}",
        f"- Docling failed batches: {pipeline_summary.get('docling_failed_batches')}",
        f"- Docling accelerator device: {pipeline_summary.get('docling_device') or 'auto'}",
        f"- Raw Markdown files processed: {pipeline_summary['raw_files_processed']}",
        f"- Split sections generated: {pipeline_summary['sections_generated']}",
        f"- Curated candidates generated: {pipeline_summary['curated_candidates']}",
        f"- Auto-rejected sections: {pipeline_summary.get('auto_rejected', 0)}",
        f"- Valid candidates: {pipeline_summary['valid_candidates']}",
        f"- Candidates with warnings: {pipeline_summary['warnings']}",
        f"- Rejected sections/files: {pipeline_summary['rejected']}",
        f"- Candidate chunks generated: {pipeline_summary['chunks_generated']}",
        f"- Duplicate chunks skipped: {duplicate.get('duplicates_skipped', 0)}",
        "",
        "## Source files processed",
        "",
    ]
    if cleaning.get("records"):
        lines.extend(
            f"- {record['source_file']}: {record['original_lines']} -> {record['final_lines']} lines; "
            f"domain={record['possible_domain']}; species={record['possible_species']}"
            for record in cleaning["records"]
        )
    else:
        lines.append("- No source Markdown files were processed.")

    lines.extend(["", "## Main detected problems", ""])
    if noisy_records:
        for record in noisy_records:
            removed = sum(int(value) for value in record.get("patterns_removed", {}).values())
            lines.append(f"- {record['source_file']}: {removed} noise-pattern removals.")
    else:
        lines.append("- No major cleaning problems were detected.")

    lines.extend(["", "## Urgent expert review", ""])
    if urgent_records:
        for record in urgent_records:
            issues = ", ".join(record.get("errors") or record.get("warnings") or [])
            lines.append(f"- {record['file']}: {record['classification']} ({issues})")
    else:
        lines.append("- No warning or rejected candidate was reported.")

    lines.extend(
        [
            "",
            "## Recommendations for the veterinary reviewer",
            "",
            "- Review every candidate before changing `status: needs_expert_review` to `status: approved`.",
            "- Fill `reviewer`, `approved_at`, and set `review_required: false` before promotion.",
            "- Prioritize files with table flags, copyright/index flags, or noisy-source flags.",
            "- Do not use these documents in productive RAG until they have `status: approved`.",
            "- After approval, run `python knowledge_base/scripts/promote_approved.py --project-root <project>` and point the official RAG ingest to `knowledge_base/expert_review/approved`.",
            "",
            "## Docling compatibility",
            "",
            "- Docling is the preferred source path when original PDFs exist; the raw Markdown path remains available only as a fallback.",
            "- PDFs should be processed with Docling before Markdown curation because PDF layout, tables, reading order, images, provenance, headers and footers are better preserved before text is flattened.",
            "- Do not clone Docling or use unofficial forks by default; use the official package/API to write `knowledge_base/docling_json/` and `knowledge_base/staging_md/`.",
        ]
    )
    if has_source_pdfs:
        lines.append(
            f"- Source PDFs were found in `{raw_pdf_dir.relative_to(project_root).as_posix()}`; these should be preferred for future Docling conversion."
        )
    else:
        lines.append("- No source PDFs were found in `knowledge_base/raw_pdf`.")

    lines.extend(
        [
            "",
            "## Safety warning",
            "",
            "These generated files are review candidates only. They must not be ingested into productive RAG until an expert changes the frontmatter to `status: approved` and promotion succeeds.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local veterinary knowledge pipeline.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-mode", choices=["docling", "raw-md"], default="docling")
    parser.add_argument("--skip-docling", action="store_true")
    parser.add_argument("--docling-limit", type=int)
    parser.add_argument("--docling-source-file", action="append", help="PDF filename, stem, or path to convert.")
    parser.add_argument("--docling-max-pages", type=int)
    parser.add_argument("--docling-page-range", nargs=2, type=int, metavar=("START", "END"))
    parser.add_argument(
        "--docling-batch-pages",
        type=int,
        default=convert_raw_pdfs_docling.DEFAULT_BATCH_PAGES,
    )
    parser.add_argument("--docling-force", action="store_true")
    parser.add_argument(
        "--docling-device",
        choices=["auto", "cpu", "cuda", "mps", "xpu"],
        default="auto",
    )
    parser.add_argument("--docling-ocr", action="store_true", help="Enable OCR during Docling PDF conversion.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_pipeline(
        project_root=args.project_root,
        source_mode=args.source_mode,
        skip_docling=args.skip_docling,
        docling_limit=args.docling_limit,
        docling_source_files=args.docling_source_file,
        docling_max_pages=args.docling_max_pages,
        docling_page_range=tuple(args.docling_page_range) if args.docling_page_range else None,
        docling_batch_pages=args.docling_batch_pages,
        docling_force=args.docling_force,
        docling_device=args.docling_device,
        docling_ocr=args.docling_ocr,
        dry_run=args.dry_run,
    )
    print("Knowledge pipeline summary:")
    print(f"- raw files processed: {summary['raw_files_processed']}")
    print(f"- sections generated: {summary['sections_generated']}")
    print(f"- curated candidates: {summary['curated_candidates']}")
    print(f"- valid candidates: {summary['valid_candidates']}")
    print(f"- warnings: {summary['warnings']}")
    print(f"- rejected: {summary['rejected']}")
    print(f"- chunks generated: {summary['chunks_generated']}")
    print(f"- reports: {summary['reports_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
