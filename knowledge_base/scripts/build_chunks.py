#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from pipeline_common import (
    approx_token_count,
    ensure_directories,
    kb_root,
    markdown_heading_path,
    parse_markdown_with_frontmatter,
    read_json,
    relative_to_project,
    sha256_text,
    write_json,
    write_jsonl,
)


TARGET_MIN_TOKENS = 500
TARGET_MAX_TOKENS = 900


def chunk_markdown(body: str, *, title: str) -> list[dict[str, Any]]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", body.strip()) if block.strip()]
    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    current_lines: list[str] = []

    def flush() -> None:
        if not current:
            return
        chunk_body = "\n\n".join(current).strip()
        if not chunk_body:
            return
        chunk_text = f"{title}\n\n{chunk_body}".strip()
        chunks.append(
            {
                "text": chunk_text,
                "headings": markdown_heading_path(current_lines),
            }
        )
        current.clear()
        current_lines.clear()

    for block in blocks:
        block_tokens = approx_token_count(block)
        if block_tokens > TARGET_MAX_TOKENS:
            flush()
            for part in _split_large_block(block):
                chunk_text = f"{title}\n\n{part}".strip()
                chunks.append(
                    {
                        "text": chunk_text,
                        "headings": markdown_heading_path(part.splitlines()),
                    }
                )
            continue
        candidate = "\n\n".join(current + [block])
        if current and approx_token_count(candidate) > TARGET_MAX_TOKENS:
            flush()
        current.append(block)
        current_lines.extend(block.splitlines())
        if approx_token_count("\n\n".join(current)) >= TARGET_MIN_TOKENS:
            flush()
    flush()
    return chunks


def _split_large_block(block: str) -> list[str]:
    lines = block.splitlines()
    if _looks_like_table_or_list(lines):
        return [block]
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", block) if sentence.strip()]
    if len(sentences) <= 1:
        words = block.split()
        return [
            " ".join(words[start : start + int(TARGET_MAX_TOKENS / 1.25)])
            for start in range(0, len(words), int(TARGET_MAX_TOKENS / 1.25))
        ]
    parts: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        candidate = " ".join(current + [sentence])
        if current and approx_token_count(candidate) > TARGET_MAX_TOKENS:
            parts.append(" ".join(current))
            current = []
        current.append(sentence)
    if current:
        parts.append(" ".join(current))
    return parts


def _looks_like_table_or_list(lines: list[str]) -> bool:
    meaningful = [line.strip() for line in lines if line.strip()]
    if not meaningful:
        return False
    table_lines = sum(1 for line in meaningful if "|" in line or re.search(r"\S+\s{2,}\S+\s{2,}\S+", line))
    list_lines = sum(1 for line in meaningful if re.match(r"^(\d+[.)]|[-*])\s+", line))
    return table_lines >= 2 or list_lines >= 3


def run_build_chunks(
    *,
    project_root: Path,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    include_approved: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    ensure_directories(project_root)
    root = kb_root(project_root)
    input_dir = (input_dir or root / "curated_candidates").resolve()
    output_dir = (output_dir or root / "chunks" / "candidates").resolve()
    validation_report = read_json(root / "reports" / "validation_report.json", {"records": []})
    valid_files = {
        str(item.get("file"))
        for item in validation_report.get("records", [])
        if item.get("classification") == "valid_candidate"
    }
    if include_approved:
        approved_dir = root / "expert_review" / "approved"
        valid_files.update(
            relative_to_project(path, project_root) for path in approved_dir.rglob("*.md")
        )

    records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    duplicates: list[dict[str, str]] = []
    for relative_file in sorted(valid_files):
        path = (project_root / relative_file).resolve()
        if not path.exists():
            continue
        try:
            metadata, body = parse_markdown_with_frontmatter(path)
        except ValueError:
            continue
        if metadata.get("status") == "rejected":
            continue
        if metadata.get("status") not in {"needs_expert_review", "approved"}:
            continue
        for index, chunk in enumerate(chunk_markdown(body, title=str(metadata.get("title") or path.stem))):
            text_hash = sha256_text(" ".join(str(chunk["text"]).lower().split()))
            if text_hash in seen_hashes:
                duplicates.append(
                    {
                        "section_file": relative_to_project(path, project_root),
                        "duplicate_hash": text_hash,
                    }
                )
                continue
            seen_hashes.add(text_hash)
            chunk_id = sha256_text(
                "|".join(
                    [
                        str(metadata.get("source_id") or ""),
                        relative_to_project(path, project_root),
                        str(index),
                        text_hash,
                    ]
                )
            )
            records.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": metadata.get("source_id"),
                    "source_file": metadata.get("source_file"),
                    "title": metadata.get("title"),
                    "domain": metadata.get("domain"),
                    "species": metadata.get("species"),
                    "status": metadata.get("status"),
                    "section_file": relative_to_project(path, project_root),
                    "chunk_index": index,
                    "text": chunk["text"],
                    "headings": chunk["headings"],
                    "quality_flags": metadata.get("quality_flags") or [],
                }
            )

    output_path = output_dir / "corpus_candidates.jsonl"
    duplicate_report_path = root / "reports" / "duplicate_report.json"
    summary = {
        "input_dir": relative_to_project(input_dir, project_root),
        "output_file": relative_to_project(output_path, project_root),
        "chunks_generated": len(records),
        "duplicates_skipped": len(duplicates),
        "duplicates": duplicates,
    }
    if not dry_run:
        write_jsonl(output_path, records)
        write_json(duplicate_report_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build candidate JSONL chunks from validated Markdown.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--include-approved", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_build_chunks(
        project_root=args.project_root,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        include_approved=args.include_approved,
        dry_run=args.dry_run,
    )
    print(
        f"Generated {summary['chunks_generated']} chunks; "
        f"skipped {summary['duplicates_skipped']} duplicates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
