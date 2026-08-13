#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from ai_review_common import (
    build_batch_index,
    ensure_ai_review_dirs,
    filter_chunks_for_approved_candidates,
    load_docling_report,
    read_jsonl,
    relative_to_project,
    write_json_artifact,
    write_jsonl_artifact,
)


def build_chunks(*, project_root: Path, source_id: str) -> dict[str, object]:
    project_root = project_root.resolve()
    report = load_docling_report(project_root)
    batch_index = build_batch_index(report)
    source_info = batch_index["by_source"].get(source_id)
    if not source_info:
        raise ValueError(f"Unknown source_id: {source_id}")
    dirs = ensure_ai_review_dirs(project_root, source_id)
    manifest = read_jsonl(dirs["manifests"] / "classification_manifest.jsonl")
    approved_original_paths = {
        str(item["path"])
        for item in manifest
        if item.get("decision") == "approved_provisional"
    }
    all_chunks = read_jsonl(project_root / "knowledge_base/chunks/candidates/corpus_candidates.jsonl")
    records = filter_chunks_for_approved_candidates(
        chunks=all_chunks,
        approved_original_paths=approved_original_paths,
        canonical_source_id=source_id,
        book_title=source_info["book_title"],
    )
    output = dirs["approved_provisional"] / "chunks_approved_provisional.jsonl"
    write_jsonl_artifact(output, records)
    summary = {
        "source_id": source_id,
        "book_title": source_info["book_title"],
        "approved_candidate_sources": len(approved_original_paths),
        "chunks_approved_provisional": len(records),
        "output_file": relative_to_project(output, project_root),
    }
    write_json_artifact(dirs["manifests"] / "chunks_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build provisional approved chunks for one reviewed source book.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_chunks(project_root=args.project_root, source_id=args.source_id)
    print(f"Generated {summary['chunks_approved_provisional']} provisional chunks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
