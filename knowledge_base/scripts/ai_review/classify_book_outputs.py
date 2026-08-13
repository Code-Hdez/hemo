#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from ai_review_common import (
    apply_review_frontmatter,
    batch_info_for_metadata,
    build_batch_index,
    candidate_paths_for_source,
    classify_candidate,
    copy_raw_artifact_to_quarantine,
    copy_reviewed_markdown,
    decision_to_manifest_record,
    ensure_ai_review_dirs,
    hash_file,
    load_docling_report,
    load_validation_by_file,
    match_candidate_by_filename,
    parse_markdown_with_frontmatter,
    pending_paths_for_source,
    relative_to_project,
    summarize_manifest,
    utc_now_iso,
    write_json_artifact,
    write_jsonl_artifact,
)


def classify_book(*, project_root: Path, source_id: str) -> dict[str, int]:
    project_root = project_root.resolve()
    report = load_docling_report(project_root)
    batch_index = build_batch_index(report)
    source_info = batch_index["by_source"].get(source_id)
    if not source_info:
        raise ValueError(f"Unknown source_id: {source_id}")
    dirs = ensure_ai_review_dirs(project_root, source_id)
    reviewed_at = utc_now_iso()
    records: list[dict[str, object]] = []

    for artifact_record in _quarantine_invalid_batch_artifacts(project_root, source_id, source_info):
        records.append(artifact_record)

    validation_by_file = load_validation_by_file(project_root)
    candidate_paths = candidate_paths_for_source(project_root=project_root, source_id=source_id, batch_index=batch_index)
    for path in candidate_paths:
        relative_path = relative_to_project(path, project_root)
        try:
            metadata, body = parse_markdown_with_frontmatter(path)
        except ValueError as exc:
            records.append(copy_raw_artifact_to_quarantine(project_root=project_root, path=path, source_id=source_id, reason=str(exc)))
            continue
        validation_record = validation_by_file.get(relative_path, {})
        decision = classify_candidate(metadata=metadata, body=body, validation_record=validation_record)
        reviewed_metadata = apply_review_frontmatter(
            metadata=metadata,
            decision=decision,
            canonical_source_id=source_id,
            reviewed_at=reviewed_at,
        )
        destination = copy_reviewed_markdown(
            source_path=path,
            destination_dir=dirs[decision.decision],
            metadata=reviewed_metadata,
            body=body,
        )
        records.append(
            decision_to_manifest_record(
                project_root=project_root,
                source_path=path,
                destination_path=destination,
                metadata=metadata,
                body=body,
                canonical_source_id=source_id,
                book_title=source_info["book_title"],
                decision=decision,
                batch_info=batch_info_for_metadata(metadata, batch_index),
            )
        )

    manifest_path = dirs["manifests"] / "classification_manifest.jsonl"
    write_jsonl_artifact(manifest_path, records)
    summary = summarize_manifest(records)
    summary.update(
        {
            "source_id": source_id,
            "book_title": source_info["book_title"],
            "reviewed_at": reviewed_at,
            "manifest": relative_to_project(manifest_path, project_root),
            "total_records": len(records),
        }
    )
    write_json_artifact(dirs["manifests"] / "classification_summary.json", summary)
    _write_pending_reclassification_manifest(
        project_root=project_root,
        source_id=source_id,
        source_info=source_info,
        batch_index=batch_index,
        candidate_paths=candidate_paths,
        validation_by_file=validation_by_file,
        dirs=dirs,
    )
    return {
        "approved_provisional": int(summary["approved_provisional"]),
        "rejected": int(summary["rejected"]),
        "needs_human_review": int(summary["needs_human_review"]),
        "quarantine": int(summary["quarantine"]),
    }


def _quarantine_invalid_batch_artifacts(project_root: Path, source_id: str, source_info: dict[str, object]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for batch in source_info["record"].get("batches", []):
        for key in ("json_path", "staging_markdown_path"):
            path = project_root / str(batch.get(key) or "")
            if not path.exists() or path.stat().st_size == 0:
                records.append(
                    copy_raw_artifact_to_quarantine(
                        project_root=project_root,
                        path=path,
                        source_id=source_id,
                        reason=f"invalid_batch_artifact:{key}",
                    )
                )
    return records


def _write_pending_reclassification_manifest(
    *,
    project_root: Path,
    source_id: str,
    source_info: dict[str, object],
    batch_index: dict[str, object],
    candidate_paths: list[Path],
    validation_by_file: dict[str, dict[str, object]],
    dirs: dict[str, Path],
) -> None:
    records: list[dict[str, object]] = []
    for path in pending_paths_for_source(project_root=project_root, source_id=source_id, batch_index=batch_index):
        relative_path = relative_to_project(path, project_root)
        matched_candidate = match_candidate_by_filename(path, candidate_paths)
        matched_candidate_rel = relative_to_project(matched_candidate, project_root) if matched_candidate else None
        try:
            metadata, body = parse_markdown_with_frontmatter(path)
        except ValueError as exc:
            quarantine_record = copy_raw_artifact_to_quarantine(project_root=project_root, path=path, source_id=source_id, reason=str(exc))
            quarantine_record["artifact_layer"] = "expert_review_pending"
            quarantine_record["matched_curated_path"] = matched_candidate_rel
            records.append(quarantine_record)
            continue
        validation_record = validation_by_file.get(relative_path) or validation_by_file.get(matched_candidate_rel or "", {})
        decision = classify_candidate(metadata=metadata, body=body, validation_record=validation_record)
        records.append(
            {
                "artifact_layer": "expert_review_pending",
                "path": relative_path,
                "matched_curated_path": matched_candidate_rel,
                "source_id": source_id,
                "original_source_id": metadata.get("source_id"),
                "book_title": source_info["book_title"],
                "decision": decision.decision,
                "confidence": decision.confidence,
                "reason_codes": decision.reason_codes,
                "short_reason": decision.short_reason,
                "content_type": decision.content_type,
                "risk_level": decision.risk_level,
                "recommended_for_rag": decision.recommended_for_rag,
                "original_status": metadata.get("status"),
                "new_status": "pending_reclassified_only",
                "page_start": (batch_info_for_metadata(metadata, batch_index) or {}).get("page_start"),
                "page_end": (batch_info_for_metadata(metadata, batch_index) or {}).get("page_end"),
                "section_title": metadata.get("title"),
                "hash": hash_file(path),
            }
        )
    manifest_path = dirs["manifests"] / "pending_reclassification.jsonl"
    write_jsonl_artifact(manifest_path, records)
    summary = summarize_manifest(records)
    summary.update(
        {
            "source_id": source_id,
            "book_title": source_info["book_title"],
            "manifest": relative_to_project(manifest_path, project_root),
            "total_records": len(records),
            "matched_to_curated": sum(1 for record in records if record.get("matched_curated_path")),
            "unmatched_to_curated": sum(1 for record in records if not record.get("matched_curated_path")),
        }
    )
    write_json_artifact(dirs["manifests"] / "pending_reclassification_summary.json", summary)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify generated Markdown candidates for one source book.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = classify_book(project_root=args.project_root, source_id=args.source_id)
    print(
        "Classified "
        f"{summary['approved_provisional']} approved, "
        f"{summary['rejected']} rejected, "
        f"{summary['needs_human_review']} human-review, "
        f"{summary['quarantine']} quarantine."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
