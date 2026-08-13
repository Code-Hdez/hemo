from __future__ import annotations

import json
from pathlib import Path

from app.modules.llm_chat.infrastructure.documents.markdown_loader import MarkdownLoader
from app.modules.llm_chat.infrastructure.documents.source_catalog import SourceCatalog

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_MANIFEST = (
    PROJECT_ROOT / "knowledge_base" / "manifests" / "sources_manifest.json"
)


def test_production_catalog_maps_fragment_and_known_duncan_typo() -> None:
    catalog = SourceCatalog.from_json(PRODUCTION_MANIFEST)

    schalm = catalog.resolve_metadata(
        {
            "canonical_source_id": "schalms_veterinary_hematology_6e_pdf",
            "source_id": "schalms_veterinary_hematology_6e_pdf_pages_0101_0150_docling",
        }
    )
    duncan = catalog.resolve_metadata(
        {
            "canonical_source_id": (
                "duncan_prasses_veterinary_laboratory_medicine_"
                "clinical_pathology_5e_pd"
            )
        }
    )

    assert schalm is not None
    assert schalm.display_title == "Schalm's Veterinary Hematology, 6th edition"
    assert schalm.authors == ("Douglas J. Weiss", "K. Jane Wardrop")
    assert duncan is not None
    assert duncan.canonical_source_id.endswith("_5e_pdf")
    assert duncan.display_title.endswith("5th edition")
    public = catalog.citable_sources()
    assert len(public) == 5
    assert [source.title for source in public] == sorted(
        (source.title for source in public), key=str.casefold
    )


def test_catalog_prefers_provenance_over_stale_fragment_source_id() -> None:
    catalog = SourceCatalog.from_json(PRODUCTION_MANIFEST)

    source = catalog.resolve_metadata(
        {
            # This exact stale combination exists in the approved corpus.
            "source_id": "fundamentals_veterinary_clinical_pathology_2e",
            "canonical_source_id": (
                "bsava_manual_canine_feline_clinical_pathology_3e_pdf"
            ),
            "source_file": (
                "bsava_manual_canine_feline_clinical_pathology_3e_pdf__"
                "pages_0151_0200.docling.md"
            ),
        }
    )

    assert source is not None
    assert source.title == "BSAVA Manual of Canine and Feline Clinical Pathology"


def test_loader_enriches_bibliography_and_quarantines_unknown_sources(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "sources.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "source_id": "book_pdf",
                    "title": "Readable Veterinary Book",
                    "author": "Ada Vet, Bruno Vet",
                    "edition": "2nd",
                    "language": "en",
                    "document_type": "pdf",
                    "allowed_for_citizen_explanation": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    catalog = SourceCatalog.from_json(manifest)
    source_root = tmp_path / "approved"
    source_root.mkdir()
    (source_root / "known.md").write_text(
        """---
source_id: book_pdf_pages_0001_0050_docling
canonical_source_id: book_pdf
title: Leukocytosis
language: en
species: canine
version: '1'
status: approved
page_start: 14
page_end: 15
---

# Leukocytosis

Leukocytosis is an increased leukocyte count.
""",
        encoding="utf-8",
    )
    (source_root / "unknown.md").write_text(
        """---
source_id: internal_unknown_pdf_pages_0001
title: Unknown
language: en
species: canine
version: '1'
status: approved
---

# Unknown

This document has no verified bibliography.
""",
        encoding="utf-8",
    )
    loader = MarkdownLoader(
        source_root,
        allow_test_documents=False,
        source_catalog=catalog,
        require_catalog_match=True,
    )

    documents = loader.load()

    assert len(documents) == 1
    document = documents[0]
    assert document.source_id == "book_pdf"
    assert document.title == "Readable Veterinary Book, 2nd edition"
    assert document.metadata["section"] == "Leukocytosis"
    assert document.metadata["page_start"] == 14
    assert json.loads(document.metadata["authors_json"]) == ["Ada Vet", "Bruno Vet"]
    assert [issue.reason for issue in loader.last_issues] == [
        "canonical_source_not_in_manifest"
    ]
