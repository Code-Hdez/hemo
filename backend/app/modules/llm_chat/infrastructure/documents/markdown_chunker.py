from __future__ import annotations

import hashlib
import re

from app.modules.llm_chat.domain.entities import KnowledgeChunk, KnowledgeDocument


class MarkdownChunker:
    """Deterministic, heading-aware chunking with paragraph/table continuity."""

    SCHEMA_VERSION = "markdown-v5"
    CORPUS_SCHEMA_VERSION = "hemovet-rag-v2"
    FILTER_METADATA_FIELDS = (
        "canonical_source_id",
        "fragment_source_id",
        "bibliographic_title",
        "display_title",
        "authors_json",
        "edition",
        "source_type",
        "citation_allowed",
        "catalog_schema_version",
        "corpus_revision",
        "domain",
        "curation_level",
        "rag_eligible",
        "ai_review_risk_level",
        "contains_ranges_or_units",
        "chapter",
        "section",
        "page_start",
        "page_end",
    )

    def __init__(self, *, chunk_size_words: int, overlap_words: int) -> None:
        if chunk_size_words < 1:
            raise ValueError("chunk_size_words must be positive")
        if overlap_words < 0 or overlap_words >= chunk_size_words:
            raise ValueError("overlap_words must be lower than chunk_size_words")
        self.chunk_size_words = chunk_size_words
        self.overlap_words = overlap_words

    def chunk(
        self,
        document: KnowledgeDocument,
        *,
        index_fingerprint: str = "unversioned",
        chunk_identity_fingerprint: str | None = None,
    ) -> list[KnowledgeChunk]:
        if not index_fingerprint.strip():
            raise ValueError("index_fingerprint cannot be empty")
        # Etapa 5, Block G: the chunk id must not shift for a document that
        # did not change just because some *other* document in the corpus
        # did. ``index_fingerprint`` (stored in metadata below, unchanged)
        # can legitimately include corpus-wide content hashing; the identity
        # used to derive the id defaults to it only for backward
        # compatibility with callers that do not yet distinguish the two —
        # production ingestion passes the narrower structural fingerprint
        # (embedding/chunking/schema only) explicitly.
        identity_fingerprint = chunk_identity_fingerprint or index_fingerprint
        if not identity_fingerprint.strip():
            raise ValueError("chunk_identity_fingerprint cannot be empty")
        drafts: list[KnowledgeChunk] = []
        for heading_path, section_text in self._sections(document.body):
            units = self._semantic_units(section_text)
            for ordinal, text in enumerate(self._pack_units(units)):
                identity = "|".join(
                    [
                        self.SCHEMA_VERSION,
                        identity_fingerprint,
                        document.source_path,
                        document.source_hash,
                        heading_path,
                        str(ordinal),
                        " ".join(text.lower().split()),
                    ]
                )
                chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
                metadata = {
                    "source_id": document.source_id,
                    "source_path": document.source_path,
                    "source_hash": document.source_hash,
                    "title": document.title,
                    "heading_path": heading_path,
                    "section": heading_path,
                    "chunk_index": ordinal,
                    "language": document.language,
                    "species": document.species,
                    "version": document.version,
                    "status": document.status,
                    "schema_version": self.SCHEMA_VERSION,
                    "corpus_schema_version": self.CORPUS_SCHEMA_VERSION,
                    "index_fingerprint": index_fingerprint,
                    **self._filter_metadata(document.metadata),
                }
                # The explicit heading is more specific than the frontmatter's
                # section title, while chapter/page provenance remains untouched.
                metadata["section"] = heading_path
                drafts.append(KnowledgeChunk(id=chunk_id, text=text, metadata=metadata))

        chunks: list[KnowledgeChunk] = []
        for index, draft in enumerate(drafts):
            metadata = dict(draft.metadata)
            if index:
                metadata["previous_chunk_id"] = drafts[index - 1].id
            if index + 1 < len(drafts):
                metadata["next_chunk_id"] = drafts[index + 1].id
            chunks.append(
                KnowledgeChunk(id=draft.id, text=draft.text, metadata=metadata)
            )
        return chunks

    def _pack_units(self, units: list[str]) -> list[str]:
        expanded: list[str] = []
        for unit in units:
            expanded.extend(self._split_oversized_unit(unit))

        chunks: list[str] = []
        current: list[str] = []
        current_words = 0
        for unit in expanded:
            unit_words = len(unit.split())
            if current and current_words + unit_words > self.chunk_size_words:
                chunks.append("\n\n".join(current).strip())
                overlap = self._overlap_tail(current)
                overlap_words = len(overlap.split()) if overlap else 0
                if overlap and overlap_words + unit_words <= self.chunk_size_words:
                    current = [overlap, unit]
                    current_words = overlap_words + unit_words
                else:
                    current = [unit]
                    current_words = unit_words
                continue
            current.append(unit)
            current_words += unit_words
        if current:
            chunks.append("\n\n".join(current).strip())
        return [chunk for chunk in chunks if chunk]

    def _split_oversized_unit(self, unit: str) -> list[str]:
        if len(unit.split()) <= self.chunk_size_words:
            return [unit]
        if self._is_markdown_table(unit):
            return self._split_table(unit)

        # Etapa 5, Block B: the previous pattern required a Latin uppercase
        # letter or digit right after the punctuation, so it silently failed
        # to split before a lowercase sentence and never split non-Latin
        # scripts at all (no case, or full-width punctuation with no
        # trailing space). Splitting on the punctuation itself — Latin
        # .!? followed by whitespace, or CJK full-width 。！？ which
        # conventionally carry no trailing space — is a more reasonable,
        # language-general default without requiring a dedicated per-script
        # tokenizer.
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+|(?<=[。！？])", unit)
            if sentence.strip()
        ]
        pieces: list[str] = []
        current: list[str] = []
        count = 0
        for sentence in sentences or [unit]:
            words = sentence.split()
            if len(words) > self.chunk_size_words:
                if current:
                    pieces.append(" ".join(current))
                    current, count = [], 0
                pieces.extend(
                    " ".join(words[start : start + self.chunk_size_words])
                    for start in range(0, len(words), self.chunk_size_words)
                )
            elif current and count + len(words) > self.chunk_size_words:
                pieces.append(" ".join(current))
                current, count = words, len(words)
            else:
                current.extend(words)
                count += len(words)
        if current:
            pieces.append(" ".join(current))
        return pieces

    def _split_table(self, table: str) -> list[str]:
        lines = table.splitlines()
        if len(lines) < 3:
            return self._split_words(table)
        header = lines[:2]
        rows = lines[2:]
        header_words = len(" ".join(header).split())
        available = max(1, self.chunk_size_words - header_words)
        pieces: list[str] = []
        current: list[str] = []
        count = 0
        for row in rows:
            row_words = len(row.split())
            if current and count + row_words > available:
                pieces.append("\n".join([*header, *current]))
                current, count = [], 0
            current.append(row)
            count += row_words
        if current:
            pieces.append("\n".join([*header, *current]))
        return pieces or [table]

    def _split_words(self, value: str) -> list[str]:
        words = value.split()
        return [
            " ".join(words[start : start + self.chunk_size_words])
            for start in range(0, len(words), self.chunk_size_words)
        ]

    def _overlap_tail(self, units: list[str]) -> str:
        if not self.overlap_words:
            return ""
        words = " ".join(units).split()
        return " ".join(words[-self.overlap_words :])

    @staticmethod
    def _is_markdown_table(value: str) -> bool:
        lines = [line.strip() for line in value.splitlines() if line.strip()]
        return len(lines) >= 2 and all(line.startswith("|") for line in lines)

    @staticmethod
    def _semantic_units(section_text: str) -> list[str]:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", section_text)]
        return [block for block in blocks if block]

    @classmethod
    def _filter_metadata(cls, metadata: dict[str, object]) -> dict[str, object]:
        return {
            field: value
            for field in cls.FILTER_METADATA_FIELDS
            if (value := metadata.get(field)) is not None
            and value != ""
            and isinstance(value, (str, int, float, bool))
        }

    @staticmethod
    def _sections(body: str) -> list[tuple[str, str]]:
        headings: list[str] = []
        active_heading = "Documento"
        active_lines: list[str] = []
        sections: list[tuple[str, str]] = []

        def flush() -> None:
            text = "\n".join(active_lines).strip()
            if text:
                sections.append((active_heading, text))

        for line in body.splitlines():
            match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if not match:
                active_lines.append(line)
                continue
            flush()
            active_lines = []
            level = len(match.group(1))
            title = match.group(2).strip()
            headings = headings[: level - 1]
            # The production corpus often repeats the same title as H1/H2.
            if headings and headings[-1].casefold() == title.casefold():
                active_heading = " > ".join(headings)
                continue
            headings.append(title)
            active_heading = " > ".join(headings)
        flush()
        return sections
