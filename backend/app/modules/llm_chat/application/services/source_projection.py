from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable

from app.modules.llm_chat.domain.entities import RetrievedChunk

_TECHNICAL_SOURCE_PATTERN = re.compile(
    r"(?:_pdf(?:_|$)|_pages?_\d|docling|\.(?:pdf|md|json|epub)$|[/\\])",
    re.IGNORECASE,
)


def _clean(value: object) -> str | None:
    cleaned = " ".join(str(value or "").replace("\x00", "").split())
    return cleaned or None


def _safe_label(value: object) -> str | None:
    cleaned = _clean(value)
    if not cleaned or _TECHNICAL_SOURCE_PATTERN.search(cleaned):
        return None
    return cleaned


@dataclass(frozen=True, slots=True)
class CitationSource:
    citation_id: str
    display_title: str
    authors: tuple[str, ...]
    edition: str | None
    chapter: str | None
    section: str | None
    page_start: int | None
    page_end: int | None
    source_type: str
    # Etapa 5, Block E: shown so the user knows a citation is not Spanish;
    # never used to reject or downrank the source itself.
    source_language: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            key: value
            for key, value in asdict(self).items()
            if value not in (None, (), "")
        }


def project_citation_sources(
    sources: Iterable[RetrievedChunk],
    *,
    used_chunk_ids: set[str] | None = None,
) -> list[CitationSource]:
    """Return only display-safe bibliography for evidence used by the answer.

    Chunk IDs, source IDs, paths, filenames and retrieval scores deliberately do
    not exist in the returned DTO.
    """

    projected: list[CitationSource] = []
    seen: set[tuple[object, ...]] = set()
    for source in sources:
        if used_chunk_ids is not None and source.id not in used_chunk_ids:
            continue
        if not source.citation_allowed:
            continue
        title = _safe_label(source.title)
        if not title:
            continue
        chapter = _safe_label(source.chapter)
        section = _safe_label(source.section or source.heading_path)
        if section and section.casefold() == title.casefold():
            section = None
        edition = _safe_label(source.edition)
        authors = tuple(
            author
            for value in source.authors
            if (author := _safe_label(value)) is not None
        )
        page_start = source.page_start if (source.page_start or 0) > 0 else None
        page_end = source.page_end if (source.page_end or 0) > 0 else None
        if page_start is None or (page_end is not None and page_end < page_start):
            page_end = None
        key = (title, edition, chapter, section, page_start, page_end)
        if key in seen:
            continue
        seen.add(key)
        projected.append(
            CitationSource(
                citation_id=f"S{len(projected) + 1}",
                display_title=title,
                authors=authors,
                edition=edition,
                chapter=chapter,
                section=section,
                page_start=page_start,
                page_end=page_end,
                source_type=_safe_label(source.source_type) or "book",
                source_language=_clean(source.source_language),
            )
        )
    return projected
