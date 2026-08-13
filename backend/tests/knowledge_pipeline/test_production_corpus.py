from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CORPUS_ROOT = PROJECT_ROOT / "knowledge_base" / "expert_review" / "approved"
PROVISIONAL_ROOT = (
    PROJECT_ROOT / "knowledge_base" / "ai_review" / "approved_provisional"
)
MANIFEST_PATH = (
    PROJECT_ROOT / "knowledge_base" / "manifests" / "production_corpus_manifest.json"
)


def _frontmatter_and_body(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_text(encoding="utf-8")
    assert raw.startswith("---\n"), path
    frontmatter, body = raw[4:].split("\n---\n", 1)
    parsed = yaml.safe_load(frontmatter)
    assert isinstance(parsed, dict), path
    assert body.strip(), path
    return parsed, body


def _corpus_sha256(paths: list[Path]) -> str:
    records = [
        (
            f"{path.relative_to(CORPUS_ROOT).as_posix()}\0"
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}"
        )
        for path in paths
    ]
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()


def _is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--no-index", path],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode == 0


def test_production_corpus_contains_only_consistent_expert_markdown() -> None:
    files = sorted(path for path in CORPUS_ROOT.rglob("*") if path.is_file())

    assert len(files) == 1250
    assert {path.suffix for path in files} == {".md"}
    for path in files:
        metadata, body = _frontmatter_and_body(path)
        assert metadata["status"] == "approved", path
        assert metadata["expert_reviewed"] is True, path
        assert metadata["review_required"] is False, path
        assert metadata["curation_level"] == "expert_reviewed", path
        assert metadata["reviewer"] == "repository_owner", path
        assert metadata.get("approved_at"), path
        assert metadata.get("expert_reviewer") == "Dr. Caceres", path
        assert metadata.get("expert_approved_at"), path
        assert not any(str(key).startswith("ai_") for key in metadata), path
        assert "codex" not in json.dumps(metadata, ensure_ascii=False).lower(), path
        original_path = metadata.get("expert_review_original_path")
        assert original_path is None or not str(original_path).startswith("/"), path
        notes = str(metadata.get("curation_notes") or "").lower()
        assert "review is required" not in notes, path
        assert "review remains recommended" not in notes, path
        source = PROVISIONAL_ROOT / path.relative_to(CORPUS_ROOT)
        if source.is_file():
            _, source_body = _frontmatter_and_body(source)
            assert body == source_body, path


def test_production_corpus_matches_integrity_manifest() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    files = sorted(CORPUS_ROOT.rglob("*.md"))

    assert manifest == {
        "schema_version": 2,
        "source_dir": "knowledge_base/expert_review/approved",
        "collection_name": "hemovet_canine_hematology_v2",
        "rag_schema_version": "hemovet-rag-v2",
        "chunk_schema_version": "markdown-v4",
        "source_manifest": "knowledge_base/manifests/sources_manifest.json",
        "corpus_revision": "20bb18ffff6684dba53b9f09f38c37d578268fe6377cdb6c4ab70304e75e6736",
        "document_count": 1250,
        "expected_chunk_count": 4696,
        "corpus_sha256": _corpus_sha256(files),
    }


@pytest.mark.parametrize(
    "path",
    [
        "knowledge_base/ai_review/approved_provisional/book/section.md",
        "knowledge_base/ai_review/approved_provisional/book/chunks.jsonl",
        "knowledge_base/expert_review/pending/section.md",
        "knowledge_base/expert_review/rejected/section.md",
        "knowledge_base/expert_review/approved/book/chunks.jsonl",
        "knowledge_base/raw_md/document1.md",
        "knowledge_base/raw_pdf/book.pdf",
        "knowledge_base/docling_json/page.json",
        "knowledge_base/staging_md/page.md",
        "knowledge_base/processing/logs/run.json",
        "knowledge_base/curated_candidates/hematology/section.md",
        "knowledge_base/chunks/corpus.jsonl",
        "knowledge_base/manifests/test_pdf_manifest.json",
        "knowledge_base/scripts/__pycache__/module.pyc",
        "backend/test.db",
        "outputs/seed_demo_run.log",
        "extraccion_ejemplos/sample.pdf",
        "images/local-photo.jpeg",
    ],
)
def test_generated_or_local_artifacts_are_ignored(path: str) -> None:
    assert _is_ignored(path), path


@pytest.mark.parametrize(
    "path",
    [
        "knowledge_base/README.md",
        "knowledge_base/scripts/promote_approved.py",
        "knowledge_base/scripts/ai_review/ai_review_common.py",
        "knowledge_base/scripts/curation_prompt_template.txt",
        "knowledge_base/manifests/example_sources_manifest.json",
        "knowledge_base/manifests/sources_manifest.json",
        "knowledge_base/manifests/curation_rules.json",
        "knowledge_base/manifests/production_corpus_manifest.json",
        "knowledge_base/microcards/cbc_core.json",
        "knowledge_base/policies/citizen_scope.json",
        "knowledge_base/raw_md/hemograma_canino_prueba.md",
        "knowledge_base/expert_review/approved/book/section.md",
    ],
)
def test_curated_rag_assets_are_not_ignored(path: str) -> None:
    assert not _is_ignored(path), path
