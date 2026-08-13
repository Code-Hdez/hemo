from __future__ import annotations

import hashlib

from tools.llm_cbc_eval.src.evidence_manifest import build_manifest, write_manifest


def test_evidence_manifest_inventory_is_complete_and_excludes_itself(tmp_path) -> None:
    (tmp_path / "raw").mkdir()
    first = tmp_path / "raw" / "run.jsonl"
    second = tmp_path / "report.md"
    output = tmp_path / "evidence-manifest.json"
    first.write_text('{"answer":"hola"}\n', encoding="utf-8")
    second.write_text("# Reporte\n", encoding="utf-8")

    manifest = build_manifest(
        tmp_path,
        output=output,
        metadata={"mode": "general"},
    )
    write_manifest(output, manifest)

    files = {item["path"]: item for item in manifest["files"]}
    assert set(files) == {"raw/run.jsonl", "report.md"}
    assert files["raw/run.jsonl"]["sha256"] == hashlib.sha256(
        first.read_bytes()
    ).hexdigest()
    assert manifest["metadata"] == {"mode": "general"}
    assert manifest["file_count"] == 2
    assert output.exists()
