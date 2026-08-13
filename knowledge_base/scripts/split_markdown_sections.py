#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from pipeline_common import (
    dump_markdown,
    ensure_directories,
    extract_title,
    infer_source,
    kb_root,
    noise_ratio,
    relative_to_project,
    write_rejected_section,
    word_count,
    write_json,
)


TARGET_MIN_WORDS = 1500
TARGET_MAX_WORDS = 4000
MAX_SECTION_WORDS = 6000

MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+.+$")
CHAPTER_HEADING = re.compile(
    r"^\s*(?:chapter\s+\d+|ch(?:apter)?\.\s*\d+|[0-9]{1,2}\s+[A-Z][A-Za-z].{5,})\s*$",
    re.IGNORECASE,
)


def split_document(text: str, *, fallback_title: str) -> list[tuple[str, str]]:
    blocks = _heading_blocks(text, fallback_title=fallback_title)
    sections: list[tuple[str, str]] = []
    for title, body in blocks:
        sections.extend(_pack_body(title, body))
    return [(title, body) for title, body in sections if word_count(body) > 0]


def _heading_blocks(text: str, *, fallback_title: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    active_title = fallback_title
    active_lines: list[str] = []
    saw_heading = False

    def flush() -> None:
        body = "\n".join(active_lines).strip()
        if body:
            blocks.append((active_title, active_lines.copy()))

    for line in lines:
        stripped = line.strip()
        if _is_author_heading(stripped):
            continue
        if _is_heading(stripped):
            saw_heading = True
            flush()
            active_lines = []
            active_title = _title_from_heading(stripped)
            if not stripped.startswith("#"):
                active_lines.append(f"# {active_title}")
            else:
                active_lines.append(stripped)
            continue
        active_lines.append(line)
    flush()

    if saw_heading and blocks:
        return [(title, "\n".join(body_lines).strip()) for title, body_lines in blocks]
    return [(fallback_title, text.strip())] if text.strip() else []


def _is_heading(stripped: str) -> bool:
    if MARKDOWN_HEADING.match(stripped):
        return True
    if CHAPTER_HEADING.match(stripped):
        return True
    if 8 <= len(stripped) <= 90 and stripped.isupper() and re.search(r"[A-Z]{3}", stripped):
        return True
    return False


def _title_from_heading(stripped: str) -> str:
    markdown = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
    if markdown:
        return extract_title(markdown.group(1), fallback="Section")
    return extract_title(stripped, fallback="Section")


def _is_author_heading(stripped: str) -> bool:
    match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
    if not match:
        return False
    heading = match.group(1).strip()
    normalized = heading.lower()
    clinical_terms = {
        "blood",
        "cell",
        "cells",
        "count",
        "counts",
        "haematology",
        "hematology",
        "clinical",
        "pathology",
        "sample",
        "test",
        "analysis",
        "quality",
        "platelet",
        "erythrocyte",
        "leukocyte",
        "cytology",
    }
    if any(term in normalized for term in clinical_terms):
        return False
    return bool(
        re.fullmatch(
            r"[A-Z][A-Za-z'’.-]+(?:\s+[A-Z]\.)?(?:\s+[A-Z][A-Za-z'’.-]+){1,3}",
            heading,
        )
    )


def _pack_body(title: str, body: str) -> list[tuple[str, str]]:
    if word_count(body) <= MAX_SECTION_WORDS:
        return [(title, _ensure_primary_heading(title, body))]

    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", body) if block.strip()]
    sections: list[tuple[str, str]] = []
    current: list[str] = []
    current_words = 0
    part = 1
    for paragraph in paragraphs:
        paragraph_words = word_count(paragraph)
        if current and current_words + paragraph_words > TARGET_MAX_WORDS:
            part_title = f"{title} part {part}" if part > 1 else title
            sections.append((part_title, _ensure_primary_heading(part_title, "\n\n".join(current))))
            current = []
            current_words = 0
            part += 1
        if paragraph_words > MAX_SECTION_WORDS:
            for subpart in _split_large_paragraph(paragraph, MAX_SECTION_WORDS):
                part_title = f"{title} part {part}"
                sections.append((part_title, _ensure_primary_heading(part_title, subpart)))
                part += 1
            continue
        current.append(paragraph)
        current_words += paragraph_words
    if current:
        part_title = f"{title} part {part}" if part > 1 else title
        sections.append((part_title, _ensure_primary_heading(part_title, "\n\n".join(current))))
    return sections


def _split_large_paragraph(text: str, max_words: int) -> list[str]:
    words = text.split()
    return [" ".join(words[start : start + max_words]) for start in range(0, len(words), max_words)]


def _ensure_primary_heading(title: str, body: str) -> str:
    stripped = body.strip()
    if re.match(r"^#\s+", stripped):
        return stripped
    return f"# {title}\n\n{stripped}"


def run_split(
    *,
    project_root: Path,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    root = kb_root(project_root)
    input_dir = (input_dir or root / "processing" / "precleaned_md").resolve()
    output_dir = (output_dir or root / "processing" / "split_sections").resolve()
    rejected_dir = root / "processing" / "rejected"
    report_path = root / "processing" / "logs" / "split_markdown_sections.json"

    output_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    total_sections = 0

    for source in sorted(input_dir.glob("*.md")):
        text = source.read_text(encoding="utf-8", errors="ignore")
        source_id, source_title = infer_source(text, source.name)
        fallback_title = extract_title(text, fallback=source_title)
        sections = split_document(text, fallback_title=fallback_title)
        source_records: list[dict[str, Any]] = []
        for index, (title, body) in enumerate(sections, start=1):
            words = word_count(body)
            section_name = f"{source_id}__section_{index:04d}.md"
            destination = output_dir / section_name
            section_record = {
                "section_number": index,
                "title": title,
                "word_count": words,
                "path": relative_to_project(destination, project_root),
            }
            if words < 5 or noise_ratio(body) > 0.58:
                rejected_record = {
                    **section_record,
                    "source_file": source.name,
                    "reason": "empty_or_noisy_section",
                }
                rejected.append(rejected_record)
                if not dry_run:
                    rejected_path = write_rejected_section(
                        project_root=project_root,
                        source_name=source.name,
                        section_number=index,
                        title=title,
                        body=body,
                        reason="empty_or_noisy_section",
                    )
                    rejected_record["rejected_path"] = relative_to_project(
                        rejected_path,
                        project_root,
                    )
                continue
            source_path = _source_path_for_precleaned(source, root=root, project_root=project_root)
            metadata = {
                "source_id": source_id,
                "source_file": source.name,
                "source_path": source_path,
                "section_number": index,
                "title": title,
                "word_count": words,
            }
            if not dry_run:
                destination.write_text(dump_markdown(metadata, body), encoding="utf-8")
            source_records.append(section_record)
            total_sections += 1
        records.append(
            {
                "source_file": source.name,
                "source_id": source_id,
                "sections": source_records,
                "rejected_sections": [
                    item for item in rejected if item.get("source_file") == source.name
                ],
            }
        )

    summary = {
        "input_dir": relative_to_project(input_dir, project_root),
        "output_dir": relative_to_project(output_dir, project_root),
        "sections_generated": total_sections,
        "sections_rejected": len(rejected),
        "records": records,
        "rejected": rejected,
    }
    if not dry_run:
        write_json(report_path, summary)
    return summary


def _source_path_for_precleaned(source: Path, *, root: Path, project_root: Path) -> str:
    staging = root / "staging_md" / source.name
    if staging.exists():
        return relative_to_project(staging, project_root)
    raw = root / "raw_md" / source.name
    if raw.exists():
        return relative_to_project(raw, project_root)
    return relative_to_project(source, project_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split precleaned Markdown into manageable sections.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_split(
        project_root=args.project_root,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    print(
        f"Generated {summary['sections_generated']} sections; "
        f"rejected {summary['sections_rejected']} sections."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
