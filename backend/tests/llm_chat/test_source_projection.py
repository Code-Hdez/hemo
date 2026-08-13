from __future__ import annotations

from app.modules.llm_chat.application.services.source_projection import (
    project_citation_sources,
)
from app.modules.llm_chat.domain.entities import RetrievedChunk


def _source(**overrides) -> RetrievedChunk:
    values = {
        "id": "internal-chunk-1",
        "text": "Evidence text",
        "source_id": "schalms_veterinary_hematology_6e_pdf_pages_0101",
        "title": "Schalm's Veterinary Hematology, 6th edition",
        "heading_path": "Leukocyte disorders > Leukocytosis",
        "source_path": "/private/corpus/schalm.pdf",
        "score": 0.91,
        "authors": ("Douglas J. Weiss", "K. Jane Wardrop"),
        "edition": "6th",
        "chapter": "Leukocyte disorders",
        "section": "Leukocytosis",
        "page_start": 123,
        "page_end": 125,
        "source_type": "book",
        "citation_allowed": True,
    }
    values.update(overrides)
    return RetrievedChunk(**values)


def test_projection_contains_only_readable_used_bibliography() -> None:
    sources = [
        _source(),
        _source(id="unused", section="Neutrophils"),
        _source(
            id="technical",
            title="schalms_veterinary_hematology_6e_pdf_pages_0101_docling",
        ),
    ]

    projected = project_citation_sources(
        sources,
        used_chunk_ids={"internal-chunk-1", "technical"},
    )

    assert len(projected) == 1
    payload = projected[0].as_dict()
    assert payload == {
        "citation_id": "S1",
        "display_title": "Schalm's Veterinary Hematology, 6th edition",
        "authors": ("Douglas J. Weiss", "K. Jane Wardrop"),
        "edition": "6th",
        "chapter": "Leukocyte disorders",
        "section": "Leukocytosis",
        "page_start": 123,
        "page_end": 125,
        "source_type": "book",
    }
    assert not ({"source_id", "source_path", "score", "chunk_id"} & payload.keys())


def test_projection_omits_unverified_pages_and_disallowed_citations() -> None:
    sources = [
        _source(page_start=None, page_end=150),
        _source(id="blocked", citation_allowed=False),
    ]

    projected = project_citation_sources(sources)

    assert len(projected) == 1
    assert "page_start" not in projected[0].as_dict()
    assert "page_end" not in projected[0].as_dict()
