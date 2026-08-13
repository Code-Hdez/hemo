from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class SourceCatalogError(ValueError):
    """The bibliographic catalog is invalid or cannot resolve a source safely."""


@dataclass(frozen=True, slots=True)
class BibliographicSource:
    canonical_source_id: str
    title: str
    authors: tuple[str, ...]
    edition: str | None
    language: str
    source_type: str
    citation_allowed: bool
    license: str | None = None

    @property
    def display_title(self) -> str:
        if not self.edition:
            return self.title
        edition = self.edition
        if not edition.casefold().endswith("edition"):
            edition = f"{edition} edition"
        return f"{self.title}, {edition}"


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())


def parse_semantic_bool(value: object, *, default: bool) -> bool:
    """Parse a catalog/frontmatter boolean without a falsy string reading as true.

    Etapa 5, Block G: ``bool("false")`` is ``True`` in Python because it is a
    non-empty string. Curated YAML/JSON metadata is usually a real boolean,
    but any text-typed value must be interpreted semantically, not cast.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if not normalized:
            return default
        if normalized in {"false", "0", "no", "off", "none", "null"}:
            return False
        if normalized in {"true", "1", "yes", "on"}:
            return True
        return default
    return bool(value)


def _authors(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        values: Iterable[object] = value
    else:
        values = str(value or "").split(",")
    return tuple(cleaned for item in values if (cleaned := _clean_text(item)))


def _source_type(value: object) -> str:
    normalized = _clean_text(value).casefold()
    if normalized in {"pdf", "epub", "book", "textbook"}:
        return "book"
    return normalized or "book"


class SourceCatalog:
    """Maps pipeline identifiers to a canonical, citation-safe bibliography.

    Resolution deliberately prefers explicit provenance fields (canonical ID and
    source file) over the historical ``source_id`` field. Some approved records
    carry a stale source ID even though their source file and canonical ID point to
    the correct book.
    """

    SCHEMA_VERSION = "bibliography-v2"
    _KNOWN_ALIASES = {
        # Historical ingestion typo: the final "f" was truncated in both the
        # approved directory and the staged filenames.
        "duncan_prasses_veterinary_laboratory_medicine_clinical_pathology_5e_pd": (
            "duncan_prasses_veterinary_laboratory_medicine_clinical_pathology_5e_pdf"
        ),
    }

    def __init__(
        self,
        entries: Iterable[BibliographicSource],
        *,
        revision: str,
    ) -> None:
        self.revision = revision
        self._entries = {entry.canonical_source_id: entry for entry in entries}
        if not self._entries:
            raise SourceCatalogError("The source catalog is empty")
        self._aliases = self._build_aliases()

    @classmethod
    def from_json(cls, path: Path) -> SourceCatalog:
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceCatalogError(f"Cannot read source catalog: {path}") from exc
        if not isinstance(payload, list):
            raise SourceCatalogError("Source catalog root must be a JSON list")

        entries: list[BibliographicSource] = []
        seen: set[str] = set()
        for index, value in enumerate(payload):
            if not isinstance(value, dict):
                raise SourceCatalogError(
                    f"Invalid source catalog entry at index {index}"
                )
            source_id = _clean_text(value.get("source_id"))
            title = _clean_text(value.get("title"))
            if not source_id or not title:
                raise SourceCatalogError(
                    f"Catalog entry {index} requires source_id and title"
                )
            if source_id in seen:
                raise SourceCatalogError(f"Duplicate catalog source_id: {source_id}")
            seen.add(source_id)
            entries.append(
                BibliographicSource(
                    canonical_source_id=source_id,
                    title=title,
                    authors=_authors(value.get("authors", value.get("author"))),
                    edition=_clean_text(value.get("edition")) or None,
                    language=_clean_text(value.get("language")) or "unknown",
                    source_type=_source_type(
                        value.get("source_type", value.get("document_type"))
                    ),
                    citation_allowed=(
                        parse_semantic_bool(
                            value.get("citation_allowed"), default=True
                        )
                        and parse_semantic_bool(
                            value.get("allowed_for_citizen_explanation"),
                            default=True,
                        )
                    ),
                    license=_clean_text(value.get("license")) or None,
                )
            )
        revision = hashlib.sha256(raw).hexdigest()
        return cls(entries, revision=revision)

    def get(self, canonical_source_id: str) -> BibliographicSource | None:
        resolved = self._resolve_identifier(canonical_source_id)
        return self._entries.get(resolved) if resolved else None

    def citable_sources(self) -> tuple[BibliographicSource, ...]:
        """Return the authorized bibliography without internal paths or IDs."""
        return tuple(
            sorted(
                (entry for entry in self._entries.values() if entry.citation_allowed),
                key=lambda entry: (entry.title.casefold(), entry.edition or ""),
            )
        )

    def resolve_metadata(
        self,
        metadata: dict[str, Any],
        *,
        relative_path: str = "",
    ) -> BibliographicSource | None:
        # These fields are generated from document provenance. They outrank the
        # original/source IDs, which are known to contain cross-book stale values.
        provenance_candidates = (
            metadata.get("canonical_source_id"),
            metadata.get("source_file"),
            metadata.get("source_path"),
            relative_path.split("/", 1)[0] if relative_path else None,
        )
        for value in provenance_candidates:
            if resolved := self._resolve_identifier(value):
                return self._entries[resolved]

        fallback_candidates = (
            metadata.get("original_source_id"),
            metadata.get("source_id"),
        )
        for value in fallback_candidates:
            if resolved := self._resolve_identifier(value):
                return self._entries[resolved]
        return None

    def _build_aliases(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for source_id in self._entries:
            variants = {source_id}
            if source_id.endswith("_pdf"):
                variants.add(source_id[:-4])
            for alias in variants:
                existing = aliases.get(alias)
                if existing and existing != source_id:
                    raise SourceCatalogError(f"Ambiguous source alias: {alias}")
                aliases[alias] = source_id
        for alias, source_id in self._KNOWN_ALIASES.items():
            if source_id in self._entries:
                aliases[alias] = source_id
        return aliases

    def _resolve_identifier(self, value: object) -> str | None:
        candidate = _clean_text(value)
        if not candidate:
            return None
        # Work with a basename but never derive page numbers from it.
        candidate = candidate.replace("\\", "/").rsplit("/", 1)[-1]
        candidate = re.sub(r"\.(?:docling\.)?(?:md|json|pdf|epub)$", "", candidate)
        if candidate in self._aliases:
            return self._aliases[candidate]
        # Page-block and Docling suffixes are pipeline identifiers. Prefix
        # resolution is allowed only at an explicit boundary and only if unique.
        matches = {
            canonical
            for alias, canonical in self._aliases.items()
            if candidate.startswith(f"{alias}_pages_")
            or candidate.startswith(f"{alias}__")
        }
        if len(matches) == 1:
            return matches.pop()
        return None


def discover_source_catalog(source_root: Path) -> SourceCatalog | None:
    """Find the repository catalog relative to the approved corpus directory."""

    candidates = [
        source_root.parent / "manifests" / "sources_manifest.json",
        source_root.parent.parent / "manifests" / "sources_manifest.json",
    ]
    for path in candidates:
        if path.is_file():
            return SourceCatalog.from_json(path)
    return None
