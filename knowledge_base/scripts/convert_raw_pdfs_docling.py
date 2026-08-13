#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Protocol

from pipeline_common import ensure_directories, kb_root, slugify, write_json


class DoclingUnavailableError(RuntimeError):
    """Docling is not installed or cannot be imported in this environment."""


class DoclingLikeDocument(Protocol):
    def export_to_markdown(self) -> str: ...

    def model_dump_json(self, *, indent: int | None = None) -> str: ...


class DoclingLikeResult(Protocol):
    document: DoclingLikeDocument


class DoclingLikeConverter(Protocol):
    def convert(
        self,
        source: Path,
        *,
        max_num_pages: int = ...,
        page_range: tuple[int, int] = ...,
    ) -> DoclingLikeResult: ...


ConverterFactory = Callable[[], DoclingLikeConverter]
PageCountProvider = Callable[[Path], int]
DEFAULT_BATCH_PAGES = 50
UNLIMITED_PAGES = 9223372036854775807


def default_converter_factory(
    *,
    do_ocr: bool = False,
    accelerator_device: str = "auto",
) -> DoclingLikeConverter:
    try:
        from docling.datamodel.accelerator_options import AcceleratorOptions
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter
        from docling.document_converter import PdfFormatOption
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise DoclingUnavailableError(
            "Docling is not installed. Install the offline knowledge dependency set, "
            "for example: pip install -r backend/requirements.knowledge.txt"
        ) from exc
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = do_ocr
    pipeline_options.do_table_structure = True
    pipeline_options.accelerator_options = AcceleratorOptions(device=accelerator_device)
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def run_docling_conversion(
    *,
    project_root: Path,
    input_dir: Path | None = None,
    json_dir: Path | None = None,
    staging_dir: Path | None = None,
    converter_factory: ConverterFactory | None = None,
    limit: int | None = None,
    source_files: list[str] | None = None,
    max_pages: int | None = None,
    page_range: tuple[int, int] | None = None,
    batch_pages: int = DEFAULT_BATCH_PAGES,
    force: bool = False,
    page_count_provider: PageCountProvider | None = None,
    accelerator_device: str = "auto",
    do_ocr: bool = False,
    fail_fast: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    root = kb_root(project_root)
    input_dir = (input_dir or root / "raw_pdf").resolve()
    json_dir = (json_dir or root / "docling_json").resolve()
    staging_dir = (staging_dir or root / "staging_md").resolve()
    converter_factory = converter_factory or (
        lambda: default_converter_factory(
            do_ocr=do_ocr,
            accelerator_device=accelerator_device,
        )
    )
    page_count_provider = page_count_provider or _count_pdf_pages
    if batch_pages < 1:
        raise ValueError("batch_pages must be >= 1")
    manifest = _load_manifest(root)
    pdfs = _select_pdfs(input_dir=input_dir, source_files=source_files)
    if limit is not None:
        pdfs = pdfs[:limit]

    records: list[dict[str, Any]] = []
    batch_records: list[dict[str, Any]] = []
    converter: DoclingLikeConverter | None = None
    for pdf in pdfs:
        source_metadata = _metadata_for_pdf(pdf, project_root=project_root, manifest=manifest)
        source_id = source_metadata["source_id"]
        total_pages = page_count_provider(pdf)
        ranges = _build_page_ranges(
            total_pages=total_pages,
            batch_pages=batch_pages,
            requested_range=page_range,
        )
        pdf_batch_records: list[dict[str, Any]] = []
        record: dict[str, Any] = {
            "source_id": source_id,
            "source_file": pdf.name,
            "source_path": pdf.relative_to(project_root).as_posix(),
            "total_pages": total_pages,
            "batch_count": len(ranges),
            "status": "pending",
            "error": None,
            "batches": pdf_batch_records,
        }
        for start_page, end_page in ranges:
            batch_suffix = f"pages_{start_page:04d}_{end_page:04d}"
            json_path = json_dir / f"{source_id}__{batch_suffix}.docling.json"
            md_path = staging_dir / f"{source_id}__{batch_suffix}.docling.md"
            batch_record: dict[str, Any] = {
                "source_id": source_id,
                "source_file": pdf.name,
                "page_start": start_page,
                "page_end": end_page,
                "json_path": json_path.relative_to(project_root).as_posix(),
                "staging_markdown_path": md_path.relative_to(project_root).as_posix(),
                "status": "pending",
                "error": None,
            }
            if not force and json_path.exists() and md_path.exists():
                batch_record["status"] = "skipped"
                pdf_batch_records.append(batch_record)
                batch_records.append(batch_record)
                continue
            try:
                if converter is None:
                    converter = converter_factory()
                if dry_run:
                    batch_record["status"] = "dry_run"
                else:
                    print(
                        f"Docling converting {pdf.name} pages {start_page}-{end_page}...",
                        flush=True,
                    )
                    json_dir.mkdir(parents=True, exist_ok=True)
                    staging_dir.mkdir(parents=True, exist_ok=True)
                    _write_report(root, records + [record], batch_records=batch_records + [batch_record])
                    result = converter.convert(
                        pdf,
                        max_num_pages=UNLIMITED_PAGES,
                        page_range=(start_page, end_page),
                    )
                    markdown = result.document.export_to_markdown()
                    json_payload = result.document.model_dump_json(indent=2)
                    json_path.write_text(json_payload, encoding="utf-8")
                    md_path.write_text(markdown.strip() + "\n", encoding="utf-8")
                    batch_record["status"] = "converted"
            except Exception as exc:
                batch_record["status"] = "failed"
                batch_record["error"] = str(exc)
                pdf_batch_records.append(batch_record)
                batch_records.append(batch_record)
                record["status"] = "failed"
                record["error"] = str(exc)
                _write_report(root, records + [record], batch_records=batch_records)
                if fail_fast:
                    records.append(record)
                    raise
                continue
            pdf_batch_records.append(batch_record)
            batch_records.append(batch_record)
            if not dry_run:
                _write_report(root, records + [record], batch_records=batch_records)

        if any(batch["status"] == "failed" for batch in pdf_batch_records):
            record["status"] = "failed"
        elif all(batch["status"] == "skipped" for batch in pdf_batch_records):
            record["status"] = "skipped"
        else:
            record["status"] = "converted"
        records.append(record)

    summary = _summary(
        project_root=project_root,
        input_dir=input_dir,
        json_dir=json_dir,
        staging_dir=staging_dir,
        pdfs=pdfs,
        records=records,
        batch_records=batch_records,
        source_files=source_files or [],
        max_pages=max_pages,
        page_range=page_range,
        batch_pages=batch_pages,
        force=force,
        accelerator_device=accelerator_device,
        do_ocr=do_ocr,
        dry_run=dry_run,
    )
    if not dry_run:
        _write_report(root, records, batch_records=batch_records, summary=summary)
    return summary


def _summary(
    *,
    project_root: Path,
    input_dir: Path,
    json_dir: Path,
    staging_dir: Path,
    pdfs: list[Path],
    records: list[dict[str, Any]],
    batch_records: list[dict[str, Any]],
    source_files: list[str],
    max_pages: int | None,
    page_range: tuple[int, int] | None,
    batch_pages: int,
    force: bool,
    accelerator_device: str,
    do_ocr: bool,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "input_dir": input_dir.relative_to(project_root).as_posix(),
        "docling_json_dir": json_dir.relative_to(project_root).as_posix(),
        "staging_md_dir": staging_dir.relative_to(project_root).as_posix(),
        "total_pdfs": len(pdfs),
        "converted": sum(1 for record in records if record["status"] in {"converted", "skipped"}),
        "failed": sum(1 for record in records if record["status"] == "failed"),
        "records": records,
        "batch_records": batch_records,
        "total_batches": len(batch_records),
        "converted_batches": sum(1 for record in batch_records if record["status"] == "converted"),
        "skipped_batches": sum(1 for record in batch_records if record["status"] == "skipped"),
        "failed_batches": sum(1 for record in batch_records if record["status"] == "failed"),
        "source_files": source_files,
        "max_pages": max_pages,
        "page_range": list(page_range) if page_range else None,
        "batch_pages": batch_pages,
        "force": force,
        "accelerator_device": accelerator_device,
        "do_ocr": do_ocr,
        "dry_run": dry_run,
    }


def _write_report(
    root: Path,
    records: list[dict[str, Any]],
    *,
    batch_records: list[dict[str, Any]] | None = None,
    summary: dict[str, Any] | None = None,
) -> None:
    payload = summary or {
        "total_pdfs": len(records),
        "converted": sum(1 for record in records if record["status"] in {"converted", "skipped"}),
        "failed": sum(1 for record in records if record["status"] == "failed"),
        "records": records,
        "batch_records": batch_records or [],
        "total_batches": len(batch_records or []),
        "converted_batches": sum(1 for record in batch_records or [] if record["status"] == "converted"),
        "skipped_batches": sum(1 for record in batch_records or [] if record["status"] == "skipped"),
        "failed_batches": sum(1 for record in batch_records or [] if record["status"] == "failed"),
    }
    write_json(root / "reports" / "docling_conversion_report.json", payload)
    write_json(root / "processing" / "logs" / "docling_conversion_report.json", payload)


def _build_page_ranges(
    *,
    total_pages: int,
    batch_pages: int,
    requested_range: tuple[int, int] | None,
) -> list[tuple[int, int]]:
    if total_pages < 1:
        raise ValueError("PDF has no pages")
    start_page, end_page = requested_range or (1, total_pages)
    start_page = max(1, start_page)
    end_page = min(total_pages, end_page)
    if start_page > end_page:
        raise ValueError(
            f"Invalid page range {requested_range}; PDF has {total_pages} pages."
        )
    ranges: list[tuple[int, int]] = []
    current = start_page
    while current <= end_page:
        batch_end = min(current + batch_pages - 1, end_page)
        ranges.append((current, batch_end))
        current = batch_end + 1
    return ranges


def _count_pdf_pages(pdf: Path) -> int:
    try:
        import pypdfium2

        document = pypdfium2.PdfDocument(pdf)
        try:
            return len(document)
        finally:
            document.close()
    except Exception:
        result = subprocess.run(
            ["pdfinfo", str(pdf)],
            check=True,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
        raise ValueError(f"Could not determine page count for {pdf}")


def _select_pdfs(*, input_dir: Path, source_files: list[str] | None) -> list[Path]:
    all_pdfs = sorted(input_dir.glob("*.pdf"))
    if not source_files:
        return all_pdfs

    by_name = {pdf.name: pdf for pdf in all_pdfs}
    by_stem = {pdf.stem: pdf for pdf in all_pdfs}
    selected: list[Path] = []
    missing: list[str] = []
    for requested in source_files:
        candidate = Path(requested)
        if candidate.exists():
            selected.append(candidate.resolve())
            continue
        match = by_name.get(requested) or by_stem.get(requested)
        if match is None:
            missing.append(requested)
        else:
            selected.append(match)
    if missing:
        raise FileNotFoundError(
            "Requested PDF source file(s) were not found: " + ", ".join(missing)
        )
    return selected


def _load_manifest(root: Path) -> list[dict[str, Any]]:
    path = root / "manifests" / "sources_manifest.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return raw if isinstance(raw, list) else []


def _metadata_for_pdf(
    pdf: Path,
    *,
    project_root: Path,
    manifest: list[dict[str, Any]],
) -> dict[str, str]:
    pdf_relative = pdf.relative_to(project_root).as_posix()
    for item in manifest:
        path = str(item.get("path") or "")
        if Path(path).name == pdf.name or path == pdf_relative:
            return {
                "source_id": slugify(str(item.get("source_id") or pdf.stem)),
                "title": str(item.get("title") or pdf.stem),
                "domain": _normalize_manifest_domain(str(item.get("domain") or "unknown")),
                "species": _normalize_manifest_species(str(item.get("species") or "unknown")),
            }
    return {
        "source_id": slugify(pdf.stem),
        "title": pdf.stem,
        "domain": "unknown",
        "species": "unknown",
    }


def _normalize_manifest_domain(value: str) -> str:
    value = slugify(value, fallback="unknown")
    if value == "cytology_hematology":
        return "cytology"
    return value


def _normalize_manifest_species(value: str) -> str:
    normalized = slugify(value, fallback="unknown")
    if normalized in {"canino_felino", "canine_feline"}:
        return "canine_feline"
    if normalized in {"canino", "dog", "dogs"}:
        return "canine"
    if normalized in {"felino", "cat", "cats"}:
        return "feline"
    if normalized == "multiespecie":
        return "other"
    return normalized if normalized in {"canine", "feline", "canine_feline", "other", "unknown"} else "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert raw PDFs to Docling JSON and staging Markdown.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--json-dir", type=Path)
    parser.add_argument("--staging-dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--source-file", action="append", help="PDF filename, stem, or path to convert.")
    parser.add_argument(
        "--max-pages",
        type=int,
        help="Deprecated compatibility flag; use --page-range to limit processed pages.",
    )
    parser.add_argument(
        "--batch-pages",
        type=int,
        default=DEFAULT_BATCH_PAGES,
        help=f"Pages per Docling conversion batch. Default: {DEFAULT_BATCH_PAGES}.",
    )
    parser.add_argument("--force", action="store_true", help="Reconvert existing page batches.")
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "cuda", "mps", "xpu"],
        default="auto",
        help="Docling accelerator device. Use 'cuda' to require NVIDIA GPU when available.",
    )
    parser.add_argument(
        "--page-range",
        nargs=2,
        type=int,
        metavar=("START", "END"),
        help="Inclusive PDF page range to convert.",
    )
    parser.add_argument("--ocr", action="store_true", help="Enable OCR for scanned PDFs.")
    parser.add_argument("--fail-fast", action="store_true", default=True)
    parser.add_argument("--no-fail-fast", dest="fail_fast", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_docling_conversion(
        project_root=args.project_root,
        input_dir=args.input_dir,
        json_dir=args.json_dir,
        staging_dir=args.staging_dir,
        limit=args.limit,
        source_files=args.source_file,
        max_pages=args.max_pages,
        page_range=tuple(args.page_range) if args.page_range else None,
        batch_pages=args.batch_pages,
        force=args.force,
        accelerator_device=args.device,
        do_ocr=args.ocr,
        fail_fast=args.fail_fast,
        dry_run=args.dry_run,
    )
    print(
        f"Docling conversion: {summary['converted']} converted, "
        f"{summary['failed']} failed."
    )
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
