#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from pipeline_common import (
    classify_domain,
    classify_species,
    contains_ranges_or_units,
    contains_table_hint,
    dump_markdown,
    editorial_rejection_reason,
    ensure_directories,
    extract_title,
    kb_root,
    parse_markdown_with_frontmatter,
    quality_flags_for_text,
    relative_to_project,
    slugify,
    write_rejected_section,
    word_count,
    write_json,
)


def normalize_candidate_body(title: str, body: str) -> str:
    lines = body.strip().splitlines()
    normalized: list[str] = []
    first_heading_seen = False
    for line in lines:
        stripped = line.rstrip()
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if match:
            heading = re.sub(r"\s+", " ", match.group(2)).strip()
            if not first_heading_seen:
                normalized.append(f"# {heading or title}")
                first_heading_seen = True
            else:
                level = max(2, min(6, len(match.group(1))))
                normalized.append(f"{'#' * level} {heading}")
            continue
        normalized.append(stripped)

    text = "\n".join(normalized).strip()
    if not re.match(r"^#\s+", text):
        text = f"# {title}\n\n{text}"
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def run_generate(
    *,
    project_root: Path,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    root = kb_root(project_root)
    input_dir = (input_dir or root / "processing" / "split_sections").resolve()
    output_dir = (output_dir or root / "curated_candidates").resolve()
    report_path = root / "processing" / "logs" / "generate_curated_candidates.json"

    records: list[dict[str, Any]] = []
    generated = 0
    auto_rejected = 0
    for section_path in sorted(input_dir.glob("*.md")):
        try:
            split_metadata, body = parse_markdown_with_frontmatter(section_path)
        except ValueError as exc:
            records.append(
                {
                    "section_file": relative_to_project(section_path, project_root),
                    "generated": False,
                    "error": str(exc),
                }
            )
            continue

        title = extract_title(body, fallback=str(split_metadata.get("title") or section_path.stem))
        source_id = str(split_metadata.get("source_id") or section_path.stem)
        source_file = str(split_metadata.get("source_file") or "")
        source_path = str(split_metadata.get("source_path") or "")
        section_number = int(split_metadata.get("section_number") or 0)
        rejection_reason = editorial_rejection_reason(title, body)
        if rejection_reason:
            rejected_path = None
            if not dry_run:
                rejected_path = write_rejected_section(
                    project_root=project_root,
                    source_name=source_file or section_path.name,
                    section_number=section_number,
                    title=title,
                    body=body,
                    reason=rejection_reason,
                )
            auto_rejected += 1
            records.append(
                {
                    "section_file": relative_to_project(section_path, project_root),
                    "candidate_file": None,
                    "source_id": source_id,
                    "title": title,
                    "generated": False,
                    "auto_rejected": True,
                    "rejection_reason": rejection_reason,
                    "rejected_path": (
                        relative_to_project(rejected_path, project_root)
                        if rejected_path
                        else None
                    ),
                }
            )
            continue
        classification_text = f"{title}\n\n{body}"
        domain = classify_domain(classification_text)
        species = classify_species(classification_text)
        count = word_count(body)
        quality_flags = quality_flags_for_text(
            body,
            domain=domain,
            species=species,
            section_word_count=count,
        )
        if title.lower().startswith("untitled"):
            quality_flags.append("missing_clear_title")
        quality_flags = sorted(set(quality_flags))

        candidate_body = normalize_candidate_body(title, body)
        metadata = {
            "source_id": source_id,
            "source_file": source_file,
            "source_path": source_path,
            "title": title,
            "domain": domain,
            "species": species,
            "language": "en",
            "status": "needs_expert_review",
            "version": "1",
            "source_type": "textbook",
            "curation_level": "machine_precleaned",
            "review_required": True,
            "reviewer": None,
            "approved_at": None,
            "chunking_policy": "section_based",
            "created_by_pipeline": True,
            "contains_tables": contains_table_hint(body),
            "contains_ranges_or_units": contains_ranges_or_units(body),
            "quality_flags": quality_flags,
            "curation_notes": "Generated by deterministic precleaning; expert veterinary review is required before productive RAG ingestion.",
        }
        folder = output_dir / domain
        folder.mkdir(parents=True, exist_ok=True)
        file_name = (
            f"{source_id}__{domain}__{slugify(title)}__section_{section_number:04d}.md"
        )
        destination = folder / file_name
        if not dry_run:
            destination.write_text(dump_markdown(metadata, candidate_body), encoding="utf-8")
        generated += 1
        records.append(
            {
                "section_file": relative_to_project(section_path, project_root),
                "candidate_file": relative_to_project(destination, project_root),
                "source_id": source_id,
                "title": title,
                "domain": domain,
                "species": species,
                "quality_flags": quality_flags,
                "generated": True,
            }
        )

    summary = {
        "input_dir": relative_to_project(input_dir, project_root),
        "output_dir": relative_to_project(output_dir, project_root),
        "candidates_generated": generated,
        "auto_rejected": auto_rejected,
        "records": records,
    }
    if not dry_run:
        write_json(report_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reviewable curated Markdown candidates.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_generate(
        project_root=args.project_root,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    print(f"Generated {summary['candidates_generated']} curated candidates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
