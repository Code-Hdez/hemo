#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

from pipeline_common import (
    ensure_directories,
    kb_root,
    parse_markdown_with_frontmatter,
    relative_to_project,
    write_json,
)


def run_promotion(
    *,
    project_root: Path,
    input_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    root = kb_root(project_root)
    approved_dir = root / "expert_review" / "approved"
    rejected_dir = root / "expert_review" / "rejected"
    log_path = root / "processing" / "logs" / "promote_approved.json"
    scan_dirs = [input_dir.resolve()] if input_dir else [
        root / "expert_review" / "pending",
        root / "curated_candidates",
    ]

    promoted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    seen: set[Path] = set()

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for path in sorted(scan_dir.rglob("*.md")):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                metadata, _body = parse_markdown_with_frontmatter(path)
            except ValueError as exc:
                rejected.append({"file": relative_to_project(path, project_root), "reason": str(exc)})
                if not dry_run:
                    shutil.copy2(path, rejected_dir / path.name)
                continue

            status = metadata.get("status")
            if status != "approved":
                skipped.append(
                    {
                        "file": relative_to_project(path, project_root),
                        "reason": f"status_is_{status}",
                    }
                )
                continue
            if not metadata.get("reviewer"):
                rejected.append(
                    {
                        "file": relative_to_project(path, project_root),
                        "reason": "missing_reviewer",
                    }
                )
                continue
            if not metadata.get("approved_at"):
                rejected.append(
                    {
                        "file": relative_to_project(path, project_root),
                        "reason": "missing_approved_at",
                    }
                )
                continue
            if metadata.get("review_required") is True:
                rejected.append(
                    {
                        "file": relative_to_project(path, project_root),
                        "reason": "review_required_still_true",
                    }
                )
                continue

            destination = approved_dir / path.name
            if not dry_run:
                approved_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
            promoted.append(
                {
                    "file": relative_to_project(path, project_root),
                    "destination": relative_to_project(destination, project_root),
                }
            )

    summary: dict[str, Any] = {
        "promoted": len(promoted),
        "rejected": len(rejected),
        "skipped": len(skipped),
        "promoted_files": promoted,
        "rejected_files": rejected,
        "skipped_files": skipped,
    }
    if not dry_run:
        write_json(log_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote manually approved Markdown documents.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_promotion(
        project_root=args.project_root,
        input_dir=args.input_dir,
        dry_run=args.dry_run,
    )
    print(
        f"Promoted {summary['promoted']} files; rejected {summary['rejected']} "
        f"approval attempts; skipped {summary['skipped']} non-approved files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
