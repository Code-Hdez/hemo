#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pipeline_common import (
    classify_domain,
    classify_species,
    ensure_directories,
    infer_source,
    kb_root,
    relative_to_project,
    write_json,
)


LINE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ri.skooBteV", re.compile(r"^\s*ri\.skooBteV\s*$", re.IGNORECASE)),
    (
        "blank_page",
        re.compile(r"^\s*this page intentionally left blank\s*$", re.IGNORECASE),
    ),
    ("page_number", re.compile(r"^\s*page\s+[ivxlcdm0-9]+\b.*$", re.IGNORECASE)),
    ("isolated_number", re.compile(r"^\s*\d{1,4}\s*$")),
    ("isolated_roman", re.compile(r"^\s*[ivxlcdm]{1,10}\s*$", re.IGNORECASE)),
    ("indd_marker", re.compile(r"^.*\.indd\b.*$", re.IGNORECASE)),
    ("isbn", re.compile(r"^\s*(?:e-)?isbn\b.*$", re.IGNORECASE)),
    ("copyright", re.compile(r"^.*\bcopyright\b.*$", re.IGNORECASE)),
    ("all_rights_reserved", re.compile(r"^.*\ball rights reserved\b.*$", re.IGNORECASE)),
    (
        "publisher_url",
        re.compile(
            r"^.*\b(?:www\.|https?://|expertconsult|elsevier\.com/permissions)\b.*$",
            re.IGNORECASE,
        ),
    ),
)

EDITORIAL_BLOCK_START = re.compile(
    r"^\s*(contributors|contents|table of contents|preface|acknowledg(?:ment|ments)|dedication)\s*$",
    re.IGNORECASE,
)
EDITORIAL_BLOCK_STOP = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:chapter\s+\d+|[0-9]+\s+[A-Z][A-Za-z].{3,}|clinical pathology|hematology|haematology|cytology)\b",
    re.IGNORECASE,
)
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_raw_markdown(text: str) -> tuple[str, dict[str, int], list[str]]:
    pattern_counts: Counter[str] = Counter()
    warnings: list[str] = []
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = CONTROL_CHARS.sub(" ", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    raw_lines = text.splitlines()
    repeated = _repeated_noise_lines(raw_lines)
    cleaned_lines: list[str] = []
    skip_editorial = False
    editorial_skipped = 0
    max_editorial_skip = max(60, len(raw_lines) // 8)

    for line_index, raw_line in enumerate(raw_lines):
        line = re.sub(r"[ \t]+", " ", raw_line).rstrip()
        stripped = line.strip()

        if skip_editorial:
            if EDITORIAL_BLOCK_STOP.search(stripped) or editorial_skipped >= max_editorial_skip:
                skip_editorial = False
                editorial_skipped = 0
            else:
                pattern_counts["editorial_block"] += 1
                editorial_skipped += 1
                continue

        if not stripped:
            cleaned_lines.append("")
            continue

        if line_index < max(2500, len(raw_lines) // 5) and EDITORIAL_BLOCK_START.match(stripped):
            skip_editorial = True
            pattern_counts["editorial_block"] += 1
            continue

        normalized = re.sub(r"\s+", " ", stripped.lower())
        if normalized in repeated:
            pattern_counts["repeated_header_footer"] += 1
            continue

        matched = False
        for name, pattern in LINE_PATTERNS:
            if pattern.match(stripped):
                pattern_counts[name] += 1
                matched = True
                break
        if matched:
            continue

        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    cleaned = cleaned.strip() + "\n"

    if pattern_counts["editorial_block"]:
        warnings.append("editorial_blocks_removed_conservatively")
    if not cleaned.strip():
        warnings.append("empty_after_cleaning")
    return cleaned, dict(pattern_counts), warnings


def _repeated_noise_lines(lines: list[str]) -> set[str]:
    normalized_lines = [
        re.sub(r"\s+", " ", line.strip().lower())
        for line in lines
        if 8 <= len(line.strip()) <= 120
    ]
    counts = Counter(normalized_lines)
    repeated: set[str] = set()
    clinical_terms = re.compile(
        r"\b(anemia|erythrocyte|leukocyte|platelet|cytology|sample|reference|diagnostic)\b",
        re.IGNORECASE,
    )
    for line, count in counts.items():
        if count >= 4 and not clinical_terms.search(line):
            repeated.add(line)
    return repeated


def run_preclean(
    *,
    project_root: Path,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    root = kb_root(project_root)
    input_dir = (input_dir or root / "raw_md").resolve()
    output_dir = (output_dir or root / "processing" / "precleaned_md").resolve()
    report_path = root / "reports" / "cleaning_report.json"
    log_path = root / "processing" / "logs" / "preclean_raw_md.log"

    records: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(input_dir.glob("*.md")):
        raw = source.read_text(encoding="utf-8", errors="ignore")
        cleaned, pattern_counts, warnings = clean_raw_markdown(raw)
        source_id, _source_title = infer_source(raw, source.name)
        record = {
            "source_file": source.name,
            "source_path": relative_to_project(source, project_root),
            "output_path": relative_to_project(output_dir / source.name, project_root),
            "source_id": source_id,
            "original_lines": len(raw.splitlines()),
            "final_lines": len(cleaned.splitlines()),
            "original_characters": len(raw),
            "final_characters": len(cleaned),
            "patterns_removed": pattern_counts,
            "warnings": warnings,
            "possible_domain": classify_domain(cleaned),
            "possible_species": classify_species(cleaned),
        }
        records.append(record)
        if not dry_run:
            (output_dir / source.name).write_text(cleaned, encoding="utf-8")

    summary = {
        "input_dir": relative_to_project(input_dir, project_root),
        "output_dir": relative_to_project(output_dir, project_root),
        "files_processed": len(records),
        "records": records,
    }
    if not dry_run:
        write_json(report_path, summary)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "\n".join(
                f"{item['source_file']}: {item['original_lines']} -> {item['final_lines']} lines"
                for item in records
            )
            + ("\n" if records else ""),
            encoding="utf-8",
        )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preclean raw Markdown files for reviewable RAG curation.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_preclean(
        project_root=args.project_root,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    print(f"Precleaned {summary['files_processed']} raw Markdown files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
