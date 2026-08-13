from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

from app.modules.llm_chat.domain.entities import KnowledgeDocument
from app.modules.llm_chat.infrastructure.documents.source_catalog import (
    SourceCatalog,
    discover_source_catalog,
    parse_semantic_bool,
)


class MarkdownLoadError(ValueError):
    """A curated Markdown document violates the ingestion contract."""


@dataclass(frozen=True, slots=True)
class MarkdownLoadIssue:
    source_path: str
    reason: str


def _page_number(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        page = int(value)  # explicit numeric metadata only
    except (TypeError, ValueError):
        return None
    return page if page > 0 else None


class MarkdownLoader:
    REQUIRED_FIELDS = {
        "source_id",
        "title",
        "language",
        "species",
        "version",
        "status",
    }
    _UNTRUSTED_INSTRUCTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "ignore_previous_instructions",
            re.compile(
                r"\b(?:ignore (?:all |the )?(?:previous|prior) instructions|"
                r"ignora (?:todas )?(?:las )?instrucciones (?:anteriores|previas))\b",
                re.IGNORECASE,
            ),
        ),
        (
            "reveal_system_prompt",
            re.compile(
                r"\b(?:reveal|show|print|repeat|revela|muestra|imprime|repite)\b"
                r".{0,80}\b(?:system prompt|prompt del sistema|instrucciones internas)\b",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
        (
            "role_override",
            re.compile(
                r"(?:<\|(?:system|developer)\|>|\[/?INST\]|"
                r"\b(?:act as|you are now|ahora eres|actua como)\b.{0,80}"
                r"\b(?:system|developer|sistema|desarrollador)\b)",
                re.IGNORECASE | re.DOTALL,
            ),
        ),
        (
            "forced_clinical_output",
            re.compile(
                r"\b(?:di|afirma|responde) que (?:el )?perro tiene\b|"
                r"\bproporciona (?:una |la )?dosis\b",
                re.IGNORECASE,
            ),
        ),
    )

    def __init__(
        self,
        source_root: Path,
        *,
        allow_test_documents: bool,
        allow_ai_provisional_documents: bool = False,
        max_file_bytes: int = 2 * 1024 * 1024,
        source_catalog: SourceCatalog | None = None,
        require_catalog_match: bool | None = None,
    ) -> None:
        self.source_root = source_root.resolve()
        self.allow_test_documents = allow_test_documents
        self.allow_ai_provisional_documents = allow_ai_provisional_documents
        self.max_file_bytes = max_file_bytes
        self.source_catalog = source_catalog or discover_source_catalog(
            self.source_root
        )
        self.require_catalog_match = (
            self.source_catalog is not None
            if require_catalog_match is None
            else require_catalog_match
        )
        self.last_issues: list[MarkdownLoadIssue] = []

    @property
    def corpus_revision(self) -> str:
        return self.source_catalog.revision if self.source_catalog else "unversioned"

    def load(self) -> list[KnowledgeDocument]:
        self.last_issues = []
        if not self.source_root.exists():
            return []
        documents: list[KnowledgeDocument] = []
        normalized_content_paths: dict[str, str] = {}
        for path in sorted(self.source_root.rglob("*.md")):
            resolved = path.resolve()
            if not resolved.is_relative_to(self.source_root):
                # A structural misconfiguration of the whole ingestion run
                # (not a single defective document): still a hard abort.
                raise MarkdownLoadError(
                    f"Markdown path resolves outside source root: {path}"
                )
            relative = path.relative_to(self.source_root).as_posix()
            try:
                document = self._load_one(path, relative=relative)
            except (
                MarkdownLoadError,
                OSError,
                UnicodeDecodeError,
                yaml.YAMLError,
            ) as exc:
                # Etapa 5, Block G: one malformed, unreadable, oversized, or
                # metadata-invalid document must not abort ingestion for the
                # rest of the corpus. Every other reject path in this method
                # already reports through ``last_issues`` instead of raising;
                # this folds the previously-fatal per-file failures into the
                # same structured-diagnostic mechanism.
                self.last_issues.append(
                    MarkdownLoadIssue(
                        source_path=relative,
                        reason=f"load_failed:{type(exc).__name__}",
                    )
                )
                continue
            if document is None:
                continue
            normalized_body = " ".join(document.body.casefold().split())
            if len(normalized_body) >= 200:
                normalized_digest = hashlib.sha256(
                    normalized_body.encode("utf-8")
                ).hexdigest()
                duplicate_of = normalized_content_paths.get(normalized_digest)
                if duplicate_of is not None:
                    self.last_issues.append(
                        MarkdownLoadIssue(
                            source_path=relative,
                            reason=f"duplicate_content:{duplicate_of}",
                        )
                    )
                    continue
                normalized_content_paths[normalized_digest] = relative
            documents.append(document)
        return documents

    def _load_one(self, path: Path, *, relative: str) -> KnowledgeDocument | None:
        """Load and validate exactly one document, or return None if skipped.

        Every raised exception here is caught by ``load()`` and recorded as a
        structured, per-document issue instead of aborting the whole corpus.
        """
        if path.stat().st_size > self.max_file_bytes:
            raise MarkdownLoadError(f"Markdown file exceeds size limit: {path}")
        raw = path.read_text(encoding="utf-8")
        metadata, body = self._parse_frontmatter(raw, path)
        if metadata["status"] not in self._allowed_statuses():
            return None
        metadata = self._normalized_metadata(metadata, relative_path=relative)
        if metadata is None:
            self.last_issues.append(
                MarkdownLoadIssue(
                    source_path=relative,
                    reason="canonical_source_not_in_manifest",
                )
            )
            return None
        untrusted_reason = self._untrusted_instruction_reason(body)
        if untrusted_reason is not None:
            self.last_issues.append(
                MarkdownLoadIssue(
                    source_path=relative,
                    reason=f"untrusted_instruction:{untrusted_reason}",
                )
            )
            return None
        revision_material = f"{self.corpus_revision}\n{raw}".encode("utf-8")
        return KnowledgeDocument(
            source_id=str(metadata["canonical_source_id"]),
            source_path=relative,
            source_hash=hashlib.sha256(revision_material).hexdigest(),
            title=str(metadata["display_title"]),
            language=str(metadata["language"]),
            species=str(metadata["species"]),
            version=str(metadata["version"]),
            status=str(metadata["status"]),
            body=body.strip(),
            metadata=dict(metadata),
        )

    @classmethod
    def _untrusted_instruction_reason(cls, body: str) -> str | None:
        for rule_id, pattern in cls._UNTRUSTED_INSTRUCTION_PATTERNS:
            if pattern.search(body):
                return rule_id
        return None

    def _normalized_metadata(
        self,
        metadata: dict[str, Any],
        *,
        relative_path: str,
    ) -> dict[str, Any] | None:
        normalized = dict(metadata)
        fragment_source_id = str(metadata.get("source_id") or "").strip()
        section_title = " ".join(str(metadata.get("title") or "").split())
        source = (
            self.source_catalog.resolve_metadata(metadata, relative_path=relative_path)
            if self.source_catalog
            else None
        )
        if self.require_catalog_match and source is None:
            return None

        if source is not None:
            normalized.update(
                {
                    "source_id": source.canonical_source_id,
                    "canonical_source_id": source.canonical_source_id,
                    "fragment_source_id": fragment_source_id,
                    "bibliographic_title": source.title,
                    "display_title": source.display_title,
                    "authors_json": json.dumps(source.authors, ensure_ascii=False),
                    "edition": source.edition or "",
                    "source_type": source.source_type,
                    "citation_allowed": source.citation_allowed,
                    "catalog_schema_version": SourceCatalog.SCHEMA_VERSION,
                    "corpus_revision": self.corpus_revision,
                }
            )
        else:
            canonical_id = str(
                metadata.get("canonical_source_id") or fragment_source_id
            ).strip()
            normalized.update(
                {
                    "source_id": canonical_id,
                    "canonical_source_id": canonical_id,
                    "fragment_source_id": fragment_source_id,
                    "bibliographic_title": section_title,
                    "display_title": section_title,
                    "authors_json": "[]",
                    "citation_allowed": parse_semantic_bool(
                        metadata.get("citation_allowed"), default=True
                    ),
                    "catalog_schema_version": "none",
                    "corpus_revision": self.corpus_revision,
                }
            )

        normalized["section"] = str(metadata.get("section") or section_title).strip()
        normalized["rag_eligible"] = parse_semantic_bool(
            metadata.get("rag_eligible"), default=True
        )
        page_start = _page_number(metadata.get("page_start"))
        page_end = _page_number(metadata.get("page_end"))
        if page_start and page_end and page_start > page_end:
            page_start = page_end = None
        if page_start:
            normalized["page_start"] = page_start
        else:
            normalized.pop("page_start", None)
        if page_end:
            normalized["page_end"] = page_end
        else:
            normalized.pop("page_end", None)
        return normalized

    def _parse_frontmatter(self, raw: str, path: Path) -> tuple[dict[str, Any], str]:
        if not raw.startswith("---\n"):
            raise MarkdownLoadError(f"Missing YAML frontmatter: {path}")
        try:
            frontmatter, body = raw[4:].split("\n---\n", 1)
        except ValueError as exc:
            raise MarkdownLoadError(f"Unclosed YAML frontmatter: {path}") from exc
        metadata = yaml.safe_load(frontmatter)
        if not isinstance(metadata, dict):
            raise MarkdownLoadError(f"Invalid YAML frontmatter: {path}")
        missing = self.REQUIRED_FIELDS - metadata.keys()
        if missing:
            raise MarkdownLoadError(
                f"Missing frontmatter fields {sorted(missing)} in {path}"
            )
        return metadata, body

    def _allowed_statuses(self) -> set[str]:
        statuses = {"approved"}
        if self.allow_test_documents:
            statuses.add("test")
        if self.allow_ai_provisional_documents:
            statuses.add("ai_approved_provisional")
        return statuses
