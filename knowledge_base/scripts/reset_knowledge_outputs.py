#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from pipeline_common import ensure_directories, kb_root, remove_path, write_json


GENERATED_PATHS = (
    ("processing",),
    ("curated_candidates",),
    ("expert_review", "pending"),
    ("expert_review", "rejected"),
    ("chunks", "candidates"),
    ("reports",),
    ("docling_json",),
    ("staging_md",),
)


def run_reset(*, project_root: Path, dry_run: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    root = kb_root(project_root)
    removed_records: list[dict[str, Any]] = []
    total_removed = 0

    for parts in GENERATED_PATHS:
        path = root.joinpath(*parts)
        if not path.exists():
            removed_records.append({"path": path.relative_to(project_root).as_posix(), "removed_files": 0})
            continue
        file_count = len([item for item in path.rglob("*") if item.is_file() or item.is_symlink()]) if path.is_dir() else 1
        if not dry_run:
            file_count = remove_path(path)
        total_removed += file_count
        removed_records.append(
            {
                "path": path.relative_to(project_root).as_posix(),
                "removed_files": file_count,
            }
        )

    if not dry_run:
        ensure_directories(project_root)

    summary = {
        "removed_files": total_removed,
        "removed_paths": removed_records,
        "preserved_paths": [
            "knowledge_base/raw_md",
            "knowledge_base/raw_pdf",
            "knowledge_base/expert_review/approved",
            "knowledge_base/microcards",
            "knowledge_base/policies",
            "knowledge_base/manifests",
            "knowledge_base/chunks/corpus_official.jsonl",
        ],
        "dry_run": dry_run,
    }
    if not dry_run:
        write_json(root / "reports" / "reset_report.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely remove generated knowledge-pipeline outputs.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_reset(project_root=args.project_root, dry_run=args.dry_run)
    print(f"Removed {summary['removed_files']} generated files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
