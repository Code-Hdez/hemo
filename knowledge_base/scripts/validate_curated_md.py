#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Any

from pipeline_common import (
    FRONTMATTER_FIELDS,
    REQUIRED_USER_FRONTMATTER_FIELDS,
    VALID_DOMAINS,
    VALID_SPECIES,
    VALID_STATUSES,
    editorial_rejection_reason,
    ensure_directories,
    has_heading,
    kb_root,
    normalize_text,
    parse_markdown_with_frontmatter,
    relative_to_project,
    remove_path,
    word_count,
    write_json,
)


MIN_WORDS = 25
MAX_WORDS = 8000


def validate_file(path: Path, *, project_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    metadata: dict[str, Any] = {}
    body = ""

    try:
        metadata, body = parse_markdown_with_frontmatter(path)
    except ValueError as exc:
        errors.append(str(exc))

    if metadata:
        missing = [field for field in REQUIRED_USER_FRONTMATTER_FIELDS if field not in metadata]
        if missing:
            errors.append(f"missing_required_frontmatter_fields:{','.join(missing)}")
        if "version" not in metadata:
            errors.append("missing_project_required_frontmatter_field:version")

        if metadata.get("status") == "approved":
            errors.append("curated_candidates_must_not_be_approved")
        if metadata.get("status") not in VALID_STATUSES:
            errors.append("invalid_status")
        if not str(metadata.get("title") or "").strip():
            errors.append("empty_title")
        if not str(metadata.get("source_id") or "").strip():
            errors.append("empty_source_id")
        if not str(metadata.get("source_file") or "").strip():
            errors.append("empty_source_file")
        if metadata.get("domain") not in VALID_DOMAINS:
            errors.append("invalid_domain")
        if metadata.get("species") not in VALID_SPECIES:
            errors.append("invalid_species")
        if not str(metadata.get("language") or "").strip():
            errors.append("empty_language")
        if metadata.get("created_by_pipeline") is not True:
            warnings.append("created_by_pipeline_not_true")
        if metadata.get("review_required") is not True and metadata.get("status") != "approved":
            warnings.append("review_required_not_true")

    stripped_body = body.strip()
    count = word_count(stripped_body)
    if not stripped_body:
        errors.append("empty_body")
    if count < MIN_WORDS:
        errors.append("body_too_short")
    if count > MAX_WORDS:
        errors.append("body_too_long")
    if "ri.skooBteV" in stripped_body:
        errors.append("contains_ri_skoobtev")
    if re.search(r"this page intentionally left blank", stripped_body, re.IGNORECASE):
        errors.append("contains_blank_page_text")
    if re.search(r"\n{4,}", stripped_body):
        errors.append("too_many_consecutive_blank_lines")
    if not has_heading(stripped_body):
        errors.append("missing_primary_heading")
    if _has_large_index_block(stripped_body):
        errors.append("possible_large_index_block")
    if _has_copyright_block(stripped_body):
        errors.append("possible_extensive_copyright")
    if _has_contributors_block(stripped_body):
        errors.append("possible_extensive_contributors")
    if metadata:
        rejection_reason = editorial_rejection_reason(
            str(metadata.get("title") or ""),
            stripped_body,
        )
        if rejection_reason:
            errors.append(rejection_reason)

    quality_flags = metadata.get("quality_flags") if metadata else []
    if isinstance(quality_flags, list):
        serious_flags = {
            "noisy_source",
            "possible_broken_table",
            "possible_index_content",
            "possible_copyright_content",
            "requires_manual_table_review",
        }
        warnings.extend(
            f"quality_flag:{flag}" for flag in quality_flags if flag in serious_flags
        )

    classification = "valid_candidate"
    if errors:
        classification = "rejected"
    elif warnings:
        classification = "warning"

    return {
        "file": relative_to_project(path, project_root),
        "classification": classification,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "word_count": count,
        "metadata": metadata,
    }


def _has_large_index_block(text: str) -> bool:
    dot_leader_lines = 0
    for line in text.splitlines():
        if re.search(r"\.{4,}\s*\d{1,4}\s*$", line):
            dot_leader_lines += 1
    return dot_leader_lines >= 8


def _has_copyright_block(text: str) -> bool:
    normalized = normalize_text(text)
    hits = sum(
        1
        for term in (
            "copyright",
            "all rights reserved",
            "library of congress",
            "publisher",
            "isbn",
        )
        if term in normalized
    )
    return hits >= 3


def _has_contributors_block(text: str) -> bool:
    normalized = normalize_text(text)
    return "contributors" in normalized and len(re.findall(r"\bdvm\b|\bdacvp\b|\bphd\b", normalized)) >= 6


def run_validation(
    *,
    project_root: Path,
    input_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    root = kb_root(project_root)
    input_dir = (input_dir or root / "curated_candidates").resolve()
    rejected_dir = root / "processing" / "rejected" / "auto"
    pending_dir = root / "expert_review" / "pending"
    report_path = root / "reports" / "validation_report.json"

    records = [validate_file(path, project_root=project_root) for path in sorted(input_dir.rglob("*.md"))]
    if not dry_run:
        remove_path(rejected_dir)
        remove_path(pending_dir)
        rejected_dir.mkdir(parents=True, exist_ok=True)
        pending_dir.mkdir(parents=True, exist_ok=True)
        for record in records:
            source = project_root / record["file"]
            if not source.exists():
                continue
            if record["classification"] == "rejected":
                shutil.copy2(source, rejected_dir / source.name)
            elif record["classification"] in {"valid_candidate", "warning"}:
                shutil.copy2(source, pending_dir / source.name)

    summary = {
        "input_dir": relative_to_project(input_dir, project_root),
        "total_files": len(records),
        "valid_candidate": sum(1 for item in records if item["classification"] == "valid_candidate"),
        "warning": sum(1 for item in records if item["classification"] == "warning"),
        "rejected": sum(1 for item in records if item["classification"] == "rejected"),
        "records": records,
    }
    if not dry_run:
        write_json(report_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate curated Markdown candidates.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_validation(
        project_root=args.project_root,
        input_dir=args.input_dir,
        dry_run=args.dry_run,
    )
    print(
        "Validated {total_files} files: {valid_candidate} valid, {warning} warnings, "
        "{rejected} rejected.".format(**summary)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
