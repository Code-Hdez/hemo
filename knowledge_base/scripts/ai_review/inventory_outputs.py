#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ai_review_common import (
    batch_info_for_metadata,
    build_batch_index,
    candidate_paths_for_source,
    ensure_ai_review_dirs,
    load_docling_report,
    page_range_from_batch_name,
    parse_markdown_with_frontmatter,
    pending_paths_for_source,
    read_jsonl,
    relative_to_project,
    utc_now_iso,
    write_json_artifact,
)


def build_inventory(*, project_root: Path, source_id: str) -> dict[str, Any]:
    project_root = project_root.resolve()
    report = load_docling_report(project_root)
    batch_index = build_batch_index(report)
    source_info = batch_index["by_source"].get(source_id)
    if not source_info:
        raise ValueError(f"Unknown source_id: {source_id}")
    dirs = ensure_ai_review_dirs(project_root, source_id)
    batches = source_info["record"].get("batches", [])
    batch_md_names = {Path(batch["staging_markdown_path"]).name for batch in batches}

    docling_json_records = []
    staging_records = []
    precleaned_records = []
    for batch in batches:
        json_path = project_root / batch["json_path"]
        staging_path = project_root / batch["staging_markdown_path"]
        precleaned_path = project_root / "knowledge_base/processing/precleaned_md" / staging_path.name
        docling_json_records.append(_file_integrity_record(project_root, json_path, parse_json=True))
        staging_records.append(_file_integrity_record(project_root, staging_path))
        precleaned_records.append(_file_integrity_record(project_root, precleaned_path))

    split_sections = []
    for path in (project_root / "knowledge_base/processing/split_sections").glob("*.md"):
        try:
            metadata, body = parse_markdown_with_frontmatter(path)
        except ValueError as exc:
            continue
        info = batch_info_for_metadata(metadata, batch_index)
        if info and Path(str(metadata.get("source_file") or "")).name in batch_md_names:
            split_sections.append(
                {
                    "path": relative_to_project(path, project_root),
                    "title": metadata.get("title"),
                    "word_count": metadata.get("word_count"),
                    "empty": not bool(body.strip()),
                }
            )

    candidates = candidate_paths_for_source(project_root=project_root, source_id=source_id, batch_index=batch_index)
    pending = pending_paths_for_source(project_root=project_root, source_id=source_id, batch_index=batch_index)
    chunks = [
        chunk
        for chunk in read_jsonl(project_root / "knowledge_base/chunks/candidates/corpus_candidates.jsonl")
        if Path(str(chunk.get("source_file") or "")).name in batch_md_names
    ]
    inventory = {
        "source_id": source_id,
        "book_title": source_info["book_title"],
        "raw_pdf": source_info["raw_pdf"],
        "docling_json_count": len(docling_json_records),
        "staging_md_count": len(staging_records),
        "precleaned_md_count": len(precleaned_records),
        "split_sections_count": len(split_sections),
        "curated_candidates_count": len(candidates),
        "pending_count": len(pending),
        "chunks_count": len(chunks),
        "started_at": utc_now_iso(),
        "status": "in_progress",
        "batches": [
            {
                "page_start": batch.get("page_start"),
                "page_end": batch.get("page_end"),
                "json_path": batch.get("json_path"),
                "staging_markdown_path": batch.get("staging_markdown_path"),
            }
            for batch in batches
        ],
        "docling_json": docling_json_records,
        "staging_md": staging_records,
        "precleaned_md": precleaned_records,
        "split_sections": split_sections,
        "curated_candidates": [relative_to_project(path, project_root) for path in candidates],
        "pending": [relative_to_project(path, project_root) for path in pending],
        "chunk_source_files": sorted({str(chunk.get("source_file") or "") for chunk in chunks}),
        "page_ranges": [page_range_from_batch_name(Path(batch["staging_markdown_path"]).name) for batch in batches],
    }
    write_json_artifact(dirs["manifests"] / "inventory.json", inventory)
    return inventory


def _file_integrity_record(project_root: Path, path: Path, *, parse_json: bool = False) -> dict[str, Any]:
    record = {
        "path": relative_to_project(path, project_root),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "valid": False,
        "error": None,
    }
    if not path.exists():
        record["error"] = "missing_file"
        return record
    if path.stat().st_size == 0:
        record["error"] = "empty_file"
        return record
    if parse_json:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            record["error"] = f"invalid_json:{exc}"
            return record
    else:
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            record["error"] = f"invalid_encoding:{exc}"
            return record
    record["valid"] = True
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory generated knowledge outputs for one source book.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = build_inventory(project_root=args.project_root, source_id=args.source_id)
    print(
        f"Inventory {inventory['source_id']}: "
        f"{inventory['curated_candidates_count']} candidates, {inventory['chunks_count']} chunks."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
