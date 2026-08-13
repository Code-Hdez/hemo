from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = PROJECT_ROOT / "knowledge_base" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _write_raw_markdown(project_root: Path) -> Path:
    raw_dir = project_root / "knowledge_base" / "raw_md"
    raw_dir.mkdir(parents=True)
    source = raw_dir / "document1.md"
    source.write_text(
        "\n".join(
            [
                "ri.skooBteV",
                "Copyright 2020 Example Publisher",
                "Page 123",
                "Ch1 Clin Path.indd 1 01/01/2020",
                "",
                "# Disorders of erythrocytes",
                "",
                "Dogs and cats may have anemia with decreased erythrocyte mass.",
                "Reticulocyte counts and blood smear review can help characterize anemia.",
                "Reference intervals can use units such as g/dL and x10^9/L.",
                "",
                "## Platelet estimates",
                "",
                "Platelet clumping in an EDTA sample can lower an automated platelet count.",
                "A blood smear review is recommended when thrombocytopenia is suspected.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return source


def _frontmatter(path: Path) -> dict[str, object]:
    raw = path.read_text(encoding="utf-8")
    assert raw.startswith("---\n")
    frontmatter = raw[4:].split("\n---\n", 1)[0]
    parsed = yaml.safe_load(frontmatter)
    assert isinstance(parsed, dict)
    return parsed


def _write_split_section(
    project_root: Path,
    *,
    title: str,
    body: str,
    source_id: str = "source",
    source_file: str = "source.md",
    section_number: int = 1,
) -> Path:
    split_dir = project_root / "knowledge_base" / "processing" / "split_sections"
    split_dir.mkdir(parents=True, exist_ok=True)
    path = split_dir / f"{source_id}__section_{section_number:04d}.md"
    path.write_text(
        f"""---
source_id: "{source_id}"
source_file: "{source_file}"
source_path: "knowledge_base/staging_md/{source_file}"
section_number: {section_number}
title: "{title}"
word_count: 100
---

{body}
""",
        encoding="utf-8",
    )
    return path


class FakeDoclingDocument:
    def __init__(self, markdown: str) -> None:
        self.markdown = markdown

    def export_to_markdown(self) -> str:
        return self.markdown

    def model_dump_json(self, *, indent: int | None = None) -> str:
        return json.dumps({"schema": "fake-docling", "markdown": self.markdown}, indent=indent)


class FakeConversionResult:
    def __init__(self, markdown: str) -> None:
        self.document = FakeDoclingDocument(markdown)


class FakeConverter:
    def __init__(self) -> None:
        self.converted: list[dict[str, object]] = []

    def convert(
        self,
        source: Path,
        *,
        max_num_pages: int = 9223372036854775807,
        page_range: tuple[int, int] = (1, 9223372036854775807),
    ) -> FakeConversionResult:
        self.converted.append(
            {
                "source": source,
                "max_num_pages": max_num_pages,
                "page_range": page_range,
            }
        )
        return FakeConversionResult(
            f"# Erythrocyte disorders pages {page_range[0]}-{page_range[1]}\n\n"
            "Dogs and cats may have anemia. Reticulocyte counts are reviewed."
        )


def test_pipeline_generates_reviewable_candidates_without_touching_raw_md(
    tmp_path: Path,
) -> None:
    import run_knowledge_pipeline

    source = _write_raw_markdown(tmp_path)
    original_raw = source.read_text(encoding="utf-8")

    summary = run_knowledge_pipeline.run_pipeline(project_root=tmp_path, source_mode="raw-md")

    assert source.read_text(encoding="utf-8") == original_raw
    assert summary["raw_files_processed"] == 1
    assert summary["curated_candidates"] >= 1
    assert summary["chunks_generated"] >= 1

    candidates = sorted((tmp_path / "knowledge_base" / "curated_candidates").rglob("*.md"))
    assert candidates
    metadata = _frontmatter(candidates[0])
    assert metadata["status"] == "needs_expert_review"
    assert metadata["review_required"] is True
    assert metadata["version"] == "1"
    assert metadata["domain"] == "hematology"
    assert metadata["species"] == "canine_feline"

    validation_report = tmp_path / "knowledge_base" / "reports" / "validation_report.json"
    cleaning_report = tmp_path / "knowledge_base" / "reports" / "cleaning_report.json"
    corpus_summary = tmp_path / "knowledge_base" / "reports" / "corpus_summary.md"
    assert validation_report.exists()
    assert cleaning_report.exists()
    assert corpus_summary.exists()
    assert "Docling" in corpus_summary.read_text(encoding="utf-8")
    assert "status: approved" in corpus_summary.read_text(encoding="utf-8")

    chunk_files = sorted((tmp_path / "knowledge_base" / "chunks" / "candidates").glob("*.jsonl"))
    assert chunk_files
    first_chunk = json.loads(chunk_files[0].read_text(encoding="utf-8").splitlines()[0])
    assert {
        "chunk_id",
        "source_id",
        "source_file",
        "title",
        "domain",
        "species",
        "status",
        "section_file",
        "chunk_index",
        "text",
        "headings",
        "quality_flags",
    } <= set(first_chunk)
    assert "Disorders of erythrocytes" in first_chunk["text"]

    prompt_template = tmp_path / "knowledge_base" / "scripts" / "curation_prompt_template.txt"
    assert prompt_template.exists()
    assert "{SOURCE_ID}" in prompt_template.read_text(encoding="utf-8")


def test_reset_generated_outputs_preserves_raw_sources_and_approved_docs(
    tmp_path: Path,
) -> None:
    import reset_knowledge_outputs

    raw_md = tmp_path / "knowledge_base" / "raw_md" / "source.md"
    raw_pdf = tmp_path / "knowledge_base" / "raw_pdf" / "source.pdf"
    approved = tmp_path / "knowledge_base" / "expert_review" / "approved" / "approved.md"
    generated = [
        tmp_path / "knowledge_base" / "processing" / "precleaned_md" / "generated.md",
        tmp_path / "knowledge_base" / "curated_candidates" / "hematology" / "candidate.md",
        tmp_path / "knowledge_base" / "chunks" / "candidates" / "candidate.jsonl",
        tmp_path / "knowledge_base" / "reports" / "validation_report.json",
        tmp_path / "knowledge_base" / "docling_json" / "source.docling.json",
        tmp_path / "knowledge_base" / "staging_md" / "source.docling.md",
        tmp_path / "knowledge_base" / "expert_review" / "pending" / "generated.md",
        tmp_path / "knowledge_base" / "expert_review" / "rejected" / "generated.md",
    ]
    for path in [raw_md, raw_pdf, approved, *generated]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content", encoding="utf-8")

    summary = reset_knowledge_outputs.run_reset(project_root=tmp_path)

    assert summary["removed_files"] == len(generated)
    assert raw_md.exists()
    assert raw_pdf.exists()
    assert approved.exists()
    assert all(not path.exists() for path in generated)
    assert (tmp_path / "knowledge_base" / "reports" / "reset_report.json").exists()


def test_docling_conversion_writes_json_and_staging_markdown_from_raw_pdf(
    tmp_path: Path,
) -> None:
    import convert_raw_pdfs_docling

    pdf = tmp_path / "knowledge_base" / "raw_pdf" / "source.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")
    manifest = tmp_path / "knowledge_base" / "manifests" / "sources_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            [
                {
                    "source_id": "source_pdf",
                    "title": "Source PDF",
                    "path": "knowledge_base/raw_pdf/source.pdf",
                    "domain": "hematology",
                    "species": "canino_felino",
                }
            ]
        ),
        encoding="utf-8",
    )

    summary = convert_raw_pdfs_docling.run_docling_conversion(
        project_root=tmp_path,
        converter_factory=FakeConverter,
        page_count_provider=lambda _path: 1,
    )

    assert summary["converted"] == 1
    assert (
        tmp_path
        / "knowledge_base"
        / "docling_json"
        / "source_pdf__pages_0001_0001.docling.json"
    ).exists()
    staging = (
        tmp_path
        / "knowledge_base"
        / "staging_md"
        / "source_pdf__pages_0001_0001.docling.md"
    )
    assert staging.exists()
    assert "Erythrocyte disorders" in staging.read_text(encoding="utf-8")
    assert (tmp_path / "knowledge_base" / "reports" / "docling_conversion_report.json").exists()


def test_docling_conversion_can_select_source_file_and_page_limits(tmp_path: Path) -> None:
    import convert_raw_pdfs_docling

    raw_pdf = tmp_path / "knowledge_base" / "raw_pdf"
    raw_pdf.mkdir(parents=True)
    (raw_pdf / "large.pdf").write_bytes(b"%PDF-1.4 fake large")
    (raw_pdf / "small.pdf").write_bytes(b"%PDF-1.4 fake small")

    summary = convert_raw_pdfs_docling.run_docling_conversion(
        project_root=tmp_path,
        converter_factory=FakeConverter,
        source_files=["small.pdf"],
        page_count_provider=lambda _path: 5,
        max_pages=5,
        page_range=(1, 5),
    )

    assert summary["total_pdfs"] == 1
    assert summary["converted"] == 1
    assert summary["source_files"] == ["small.pdf"]
    assert summary["max_pages"] == 5
    assert summary["page_range"] == [1, 5]
    assert (
        tmp_path
        / "knowledge_base"
        / "staging_md"
        / "small__pages_0001_0005.docling.md"
    ).exists()


def test_docling_conversion_batches_pdf_ranges_and_writes_page_named_outputs(
    tmp_path: Path,
) -> None:
    import convert_raw_pdfs_docling

    pdf = tmp_path / "knowledge_base" / "raw_pdf" / "source.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake = FakeConverter()
    summary = convert_raw_pdfs_docling.run_docling_conversion(
        project_root=tmp_path,
        converter_factory=lambda: fake,
        page_count_provider=lambda _path: 123,
        batch_pages=50,
        accelerator_device="cuda",
    )

    assert summary["total_batches"] == 3
    assert summary["converted_batches"] == 3
    assert summary["skipped_batches"] == 0
    assert summary["converted"] == 1
    assert summary["accelerator_device"] == "cuda"
    assert [call["page_range"] for call in fake.converted] == [
        (1, 50),
        (51, 100),
        (101, 123),
    ]
    assert all(call["max_num_pages"] == 9223372036854775807 for call in fake.converted)
    assert (
        tmp_path
        / "knowledge_base"
        / "staging_md"
        / "source__pages_0001_0050.docling.md"
    ).exists()
    assert (
        tmp_path
        / "knowledge_base"
        / "docling_json"
        / "source__pages_0101_0123.docling.json"
    ).exists()


def test_docling_conversion_resume_skips_existing_batches(tmp_path: Path) -> None:
    import convert_raw_pdfs_docling

    pdf = tmp_path / "knowledge_base" / "raw_pdf" / "source.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")
    staging = tmp_path / "knowledge_base" / "staging_md"
    docling_json = tmp_path / "knowledge_base" / "docling_json"
    staging.mkdir(parents=True)
    docling_json.mkdir(parents=True)
    (staging / "source__pages_0001_0050.docling.md").write_text("existing", encoding="utf-8")
    (docling_json / "source__pages_0001_0050.docling.json").write_text("{}", encoding="utf-8")

    fake = FakeConverter()
    summary = convert_raw_pdfs_docling.run_docling_conversion(
        project_root=tmp_path,
        converter_factory=lambda: fake,
        page_count_provider=lambda _path: 75,
        batch_pages=50,
    )

    assert summary["total_batches"] == 2
    assert summary["skipped_batches"] == 1
    assert summary["converted_batches"] == 1
    assert [call["page_range"] for call in fake.converted] == [(51, 75)]
    assert (staging / "source__pages_0001_0050.docling.md").read_text(encoding="utf-8") == "existing"


def test_docling_conversion_force_reconverts_existing_batches(tmp_path: Path) -> None:
    import convert_raw_pdfs_docling

    pdf = tmp_path / "knowledge_base" / "raw_pdf" / "source.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")
    staging = tmp_path / "knowledge_base" / "staging_md"
    docling_json = tmp_path / "knowledge_base" / "docling_json"
    staging.mkdir(parents=True)
    docling_json.mkdir(parents=True)
    (staging / "source__pages_0001_0050.docling.md").write_text("existing", encoding="utf-8")
    (docling_json / "source__pages_0001_0050.docling.json").write_text("{}", encoding="utf-8")

    fake = FakeConverter()
    summary = convert_raw_pdfs_docling.run_docling_conversion(
        project_root=tmp_path,
        converter_factory=lambda: fake,
        page_count_provider=lambda _path: 50,
        batch_pages=50,
        force=True,
    )

    assert summary["skipped_batches"] == 0
    assert summary["converted_batches"] == 1
    assert [call["page_range"] for call in fake.converted] == [(1, 50)]
    assert "Erythrocyte disorders pages 1-50" in (
        staging / "source__pages_0001_0050.docling.md"
    ).read_text(encoding="utf-8")


def test_docling_conversion_batches_with_requested_page_range(tmp_path: Path) -> None:
    import convert_raw_pdfs_docling

    pdf = tmp_path / "knowledge_base" / "raw_pdf" / "source.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")

    fake = FakeConverter()
    summary = convert_raw_pdfs_docling.run_docling_conversion(
        project_root=tmp_path,
        converter_factory=lambda: fake,
        page_count_provider=lambda _path: 123,
        page_range=(35, 45),
        batch_pages=50,
    )

    assert summary["total_batches"] == 1
    assert summary["page_range"] == [35, 45]
    assert [call["page_range"] for call in fake.converted] == [(35, 45)]
    assert (
        tmp_path
        / "knowledge_base"
        / "staging_md"
        / "source__pages_0035_0045.docling.md"
    ).exists()


def test_docling_conversion_reports_missing_dependency(tmp_path: Path) -> None:
    import convert_raw_pdfs_docling

    pdf = tmp_path / "knowledge_base" / "raw_pdf" / "source.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 fake")

    def missing_factory() -> Any:
        raise convert_raw_pdfs_docling.DoclingUnavailableError("docling is not installed")

    summary = convert_raw_pdfs_docling.run_docling_conversion(
        project_root=tmp_path,
        converter_factory=missing_factory,
        page_count_provider=lambda _path: 1,
        fail_fast=False,
    )

    assert summary["converted"] == 0
    assert summary["failed"] == 1
    assert "docling is not installed" in summary["records"][0]["error"]


def test_split_rejected_section_writes_only_rejected_section(tmp_path: Path) -> None:
    import split_markdown_sections

    precleaned = tmp_path / "knowledge_base" / "processing" / "precleaned_md" / "source.md"
    precleaned.parent.mkdir(parents=True)
    precleaned.write_text(
        "# Good hematology\n\nDogs and cats may have anemia and platelet changes.\n\n# Noise\n\n%%%% %%%% %%%% %%%% %%%%\n",
        encoding="utf-8",
    )

    summary = split_markdown_sections.run_split(project_root=tmp_path)

    assert summary["sections_rejected"] == 1
    rejected = sorted((tmp_path / "knowledge_base" / "processing" / "rejected" / "auto").glob("*.md"))
    assert len(rejected) == 1
    rejected_text = rejected[0].read_text(encoding="utf-8")
    assert "%%%%" in rejected_text
    assert "Good hematology" not in rejected_text


def test_split_skips_author_heading_without_losing_clinical_body(tmp_path: Path) -> None:
    import split_markdown_sections

    text = (
        "# Introduction to haematology\n\n"
        "## Elizabeth Villiers\n\n"
        "The complete blood count (CBC) includes packed cell volume, red blood cell count, "
        "white blood cell count, differential white blood cell count, and platelet count."
    )

    sections = split_markdown_sections.split_document(
        text,
        fallback_title="BSAVA Manual",
    )

    assert len(sections) == 1
    title, body = sections[0]
    assert title == "Introduction to haematology"
    assert "complete blood count" in body
    assert "## Elizabeth Villiers" not in body


def test_generate_candidates_rejects_suspicious_editorial_title(tmp_path: Path) -> None:
    import generate_curated_candidates

    _write_split_section(
        tmp_path,
        title="Contributors",
        body="# Contributors\n\nRobin W. Allison, DVM, PhD, DACVP\nJanice Cruz Cardona, DVM, DACVP\n",
    )

    summary = generate_curated_candidates.run_generate(project_root=tmp_path)

    assert summary["candidates_generated"] == 0
    assert summary["auto_rejected"] == 1
    assert not list((tmp_path / "knowledge_base" / "curated_candidates").rglob("*.md"))
    rejected = sorted((tmp_path / "knowledge_base" / "processing" / "rejected" / "auto").glob("*.md"))
    assert rejected


def test_generate_candidates_rejects_references_and_table_titles(tmp_path: Path) -> None:
    import generate_curated_candidates

    _write_split_section(
        tmp_path,
        title="References and further reading",
        body="# References and further reading\n\nSmith J (2020) Journal of Veterinary Clinical Pathology 1, 1-2.\n",
        section_number=1,
    )
    _write_split_section(
        tmp_path,
        title="| | SEN = 90% | SPEC = 95% | |",
        body="# | | SEN = 90% | SPEC = 95% | |\n\n| A | B |\n|---|---|\n| dogs | cats |\n",
        section_number=2,
    )

    summary = generate_curated_candidates.run_generate(project_root=tmp_path)

    assert summary["candidates_generated"] == 0
    assert summary["auto_rejected"] == 2
    assert not list((tmp_path / "knowledge_base" / "curated_candidates").rglob("*.md"))


def test_pipeline_docling_mode_uses_staging_markdown_instead_of_raw_md(
    tmp_path: Path,
) -> None:
    import run_knowledge_pipeline

    raw = tmp_path / "knowledge_base" / "raw_md" / "raw.md"
    raw.parent.mkdir(parents=True)
    raw.write_text("# Raw only\n\nRaw markdown should not be used by docling mode.", encoding="utf-8")
    staging = tmp_path / "knowledge_base" / "staging_md" / "source.docling.md"
    staging.parent.mkdir(parents=True)
    staging.write_text(
        "# Staged erythrocyte disorders\n\nDogs and cats may have anemia. Reticulocyte counts help characterize anemia.",
        encoding="utf-8",
    )

    summary = run_knowledge_pipeline.run_pipeline(
        project_root=tmp_path,
        source_mode="docling",
        skip_docling=True,
    )

    assert summary["source_mode"] == "docling"
    candidates = list((tmp_path / "knowledge_base" / "curated_candidates").rglob("*.md"))
    assert candidates
    candidate_text = "\n".join(path.read_text(encoding="utf-8") for path in candidates)
    assert "Staged erythrocyte disorders" in candidate_text
    assert "Raw only" not in candidate_text


def test_pipeline_docling_mode_passes_batch_options_to_converter(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    import run_knowledge_pipeline

    captured: dict[str, object] = {}
    staging = tmp_path / "knowledge_base" / "staging_md"
    staging.mkdir(parents=True)
    (staging / "source__pages_0001_0050.docling.md").write_text(
        "# Staged erythrocyte disorders\n\nDogs and cats may have anemia. Reticulocyte counts help characterize anemia.",
        encoding="utf-8",
    )

    def fake_run_docling_conversion(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "converted": 1,
            "failed": 0,
            "source_files": ["source.pdf"],
            "max_pages": None,
            "page_range": None,
            "batch_pages": 25,
            "total_batches": 2,
            "converted_batches": 2,
            "skipped_batches": 0,
            "failed_batches": 0,
            "accelerator_device": "cuda",
        }

    monkeypatch.setattr(
        run_knowledge_pipeline.convert_raw_pdfs_docling,
        "run_docling_conversion",
        fake_run_docling_conversion,
    )

    summary = run_knowledge_pipeline.run_pipeline(
        project_root=tmp_path,
        source_mode="docling",
        docling_batch_pages=25,
        docling_force=True,
        docling_device="cuda",
    )

    assert captured["batch_pages"] == 25
    assert captured["force"] is True
    assert captured["accelerator_device"] == "cuda"
    assert summary["docling_batch_pages"] == 25
    assert summary["docling_total_batches"] == 2
    assert summary["docling_device"] == "cuda"


def test_validator_rejects_approved_status_inside_curated_candidates(
    tmp_path: Path,
) -> None:
    import validate_curated_md

    candidate_dir = tmp_path / "knowledge_base" / "curated_candidates" / "hematology"
    candidate_dir.mkdir(parents=True)
    candidate = candidate_dir / "bad.md"
    candidate.write_text(
        """---
source_id: "source"
source_file: "source.md"
source_path: "knowledge_base/raw_md/source.md"
title: "Approved candidate"
domain: "hematology"
species: "canine"
language: "en"
status: "approved"
version: "1"
source_type: "textbook"
curation_level: "machine_precleaned"
review_required: true
reviewer: null
approved_at: null
chunking_policy: "section_based"
created_by_pipeline: true
contains_tables: false
contains_ranges_or_units: false
quality_flags: []
curation_notes: ""
---

# Approved candidate

This candidate should not be approved before expert promotion.
""",
        encoding="utf-8",
    )

    report = validate_curated_md.run_validation(project_root=tmp_path)

    assert report["rejected"] == 1
    rejected_copy = tmp_path / "knowledge_base" / "processing" / "rejected" / "auto" / "bad.md"
    assert rejected_copy.exists()


def test_promote_approved_requires_reviewer_and_approved_at(tmp_path: Path) -> None:
    import promote_approved

    pending_dir = tmp_path / "knowledge_base" / "expert_review" / "pending"
    pending_dir.mkdir(parents=True)
    reviewed = pending_dir / "reviewed.md"
    reviewed.write_text(
        """---
source_id: "source"
source_file: "source.md"
source_path: "knowledge_base/raw_md/source.md"
title: "Reviewed document"
domain: "hematology"
species: "canine"
language: "en"
status: "approved"
version: "1"
source_type: "textbook"
curation_level: "expert_reviewed"
review_required: false
reviewer: null
approved_at: null
chunking_policy: "section_based"
created_by_pipeline: true
contains_tables: false
contains_ranges_or_units: false
quality_flags: []
curation_notes: ""
---

# Reviewed document

Expert-reviewed hematology content.
""",
        encoding="utf-8",
    )

    first = promote_approved.run_promotion(project_root=tmp_path)

    assert first["promoted"] == 0
    assert first["rejected"] == 1
    assert not (tmp_path / "knowledge_base" / "expert_review" / "approved" / "reviewed.md").exists()

    reviewed.write_text(
        reviewed.read_text(encoding="utf-8")
        .replace("reviewer: null", 'reviewer: "Dr. Reviewer"')
        .replace("approved_at: null", 'approved_at: "2026-06-29T10:00:00Z"'),
        encoding="utf-8",
    )

    second = promote_approved.run_promotion(project_root=tmp_path)

    assert second["promoted"] == 1
    assert second["rejected"] == 0
    assert (tmp_path / "knowledge_base" / "expert_review" / "approved" / "reviewed.md").exists()
