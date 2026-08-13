#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pipeline_common import (  # noqa: E402
    dump_markdown,
    parse_markdown_with_frontmatter,
    read_json,
    relative_to_project,
    sha256_text,
    slugify,
    utc_now_iso,
    word_count,
    write_json,
    write_jsonl,
)


AI_REVIEWER = "codex_ai_reviewer"
AI_REVIEW_ROOT = Path("knowledge_base/ai_review")

CLINICAL_TERMS = {
    "anemia",
    "anaemia",
    "erythrocyte",
    "leukocyte",
    "neutrophil",
    "lymphocyte",
    "eosinophil",
    "monocyte",
    "platelet",
    "thrombocyte",
    "reticulocyte",
    "hemogram",
    "haematology",
    "hematology",
    "cytology",
    "smear",
    "aspirate",
    "bone marrow",
    "lymph node",
    "effusion",
    "neoplasia",
    "inflammation",
    "diagnosis",
    "diagnostic",
    "sample",
    "stain",
    "urine",
    "renal",
    "hepatic",
    "coagulation",
    "reference interval",
    "blood",
    "cell",
    "cells",
    "canine",
    "feline",
    "dog",
    "cat",
}

EDITORIAL_TERMS = {
    "copyright",
    "isbn",
    "all rights reserved",
    "table of contents",
    "contents",
    "index",
    "bibliography",
    "references",
    "contributors",
    "preface",
    "acknowledgment",
    "acknowledgement",
    "acknowledge",
    "acknowledgements",
    "acknowledgments",
    "dedication",
    "publisher",
    "unlock your ebook",
    "expert consult",
}

REFERENCE_TERMS = {
    "vol.",
    "journal",
    "proceedings",
    "editor",
    "edition",
    "et al",
    "doi",
    "pmid",
}


@dataclass(frozen=True)
class ReviewDecision:
    decision: str
    confidence: str
    reason_codes: list[str]
    short_reason: str
    content_type: str
    risk_level: str
    recommended_for_rag: bool


def project_ai_review_root(project_root: Path) -> Path:
    return project_root / AI_REVIEW_ROOT


def load_docling_report(project_root: Path) -> dict[str, Any]:
    return read_json(project_root / "knowledge_base/reports/docling_conversion_report.json", {"records": []})


def build_batch_index(docling_report: dict[str, Any]) -> dict[str, Any]:
    by_batch: dict[str, dict[str, Any]] = {}
    by_source: dict[str, dict[str, Any]] = {}
    for record in docling_report.get("records", []):
        source_id = str(record.get("source_id") or "")
        if not source_id:
            continue
        batch_names: set[str] = set()
        for batch in record.get("batches", []):
            md_path = str(batch.get("staging_markdown_path") or "")
            json_path = str(batch.get("json_path") or "")
            md_name = Path(md_path).name
            json_name = Path(json_path).name
            if md_name:
                batch_names.add(md_name)
                by_batch[md_name] = {
                    "source_id": source_id,
                    "source_file": record.get("source_file"),
                    "book_title": _book_title_from_record(record),
                    "raw_pdf": record.get("source_path"),
                    "page_start": batch.get("page_start"),
                    "page_end": batch.get("page_end"),
                    "json_path": json_path,
                    "staging_markdown_path": md_path,
                }
            if json_name:
                by_batch[json_name] = {
                    "source_id": source_id,
                    "source_file": record.get("source_file"),
                    "book_title": _book_title_from_record(record),
                    "raw_pdf": record.get("source_path"),
                    "page_start": batch.get("page_start"),
                    "page_end": batch.get("page_end"),
                    "json_path": json_path,
                    "staging_markdown_path": md_path,
                }
        by_source[source_id] = {
            "source_id": source_id,
            "source_file": record.get("source_file"),
            "book_title": _book_title_from_record(record),
            "raw_pdf": record.get("source_path"),
            "batches": sorted(batch_names),
            "batch_count": len(batch_names),
            "record": record,
        }
    return {"by_batch": by_batch, "by_source": by_source}


def _book_title_from_record(record: dict[str, Any]) -> str:
    filename = str(record.get("source_file") or record.get("source_id") or "unknown")
    stem = Path(filename).stem
    return stem.replace("_", " ").strip()


def canonical_source_for_metadata(
    metadata: dict[str, Any],
    batch_index: dict[str, Any],
) -> str | None:
    source_file = Path(str(metadata.get("source_file") or "")).name
    if source_file and source_file in batch_index.get("by_batch", {}):
        return str(batch_index["by_batch"][source_file]["source_id"])
    source_path = Path(str(metadata.get("source_path") or "")).name
    if source_path and source_path in batch_index.get("by_batch", {}):
        return str(batch_index["by_batch"][source_path]["source_id"])
    source_id = str(metadata.get("source_id") or "")
    if source_id in batch_index.get("by_source", {}):
        return source_id
    for known_source_id in batch_index.get("by_source", {}):
        if source_id and source_id.startswith(known_source_id.removesuffix("_pdf")):
            return str(known_source_id)
    return None


def batch_info_for_metadata(
    metadata: dict[str, Any],
    batch_index: dict[str, Any],
) -> dict[str, Any] | None:
    source_file = Path(str(metadata.get("source_file") or "")).name
    if source_file:
        return batch_index.get("by_batch", {}).get(source_file)
    source_path = Path(str(metadata.get("source_path") or "")).name
    if source_path:
        return batch_index.get("by_batch", {}).get(source_path)
    return None


def classify_candidate(
    *,
    metadata: dict[str, Any],
    body: str,
    validation_record: dict[str, Any] | None = None,
) -> ReviewDecision:
    validation_record = validation_record or {}
    title = str(metadata.get("title") or "")
    text = f"{title}\n{body}"
    normalized = _norm(text)
    flags = set(metadata.get("quality_flags") or [])
    errors = set(validation_record.get("errors") or [])
    warnings = set(validation_record.get("warnings") or [])
    wc = word_count(body)
    reason_codes: list[str] = []

    if _looks_like_contributor(title, body):
        return _decision(
            "rejected",
            "high",
            ["contributors_like_content"],
            "Contributor or author bio without clinical substance.",
            "other",
            "low",
            False,
        )
    if _looks_like_author_title(title):
        return _decision(
            "needs_human_review",
            "medium",
            ["author_title_requires_relabeling"],
            "Clinical text is useful but the extracted title is an author list and needs human relabeling.",
            _content_type(metadata, body),
            "medium",
            False,
        )
    if _looks_like_reference_title(title):
        return _decision(
            "rejected",
            "high",
            ["bibliographic_reference_title"],
            "Section title is a bibliographic reference, not curated clinical content.",
            "bibliography",
            "low",
            False,
        )
    if _contains_editorial_noise(normalized):
        return _decision(
            "rejected",
            "high",
            ["editorial_or_legal_content"],
            "Editorial, legal, index, bibliography, or publisher content.",
            _content_type(metadata, body, forced="legal" if "copyright" in normalized else None),
            "low",
            False,
        )
    if "requires_manual_table_review" in flags or "possible_broken_table" in flags:
        return _decision(
            "needs_human_review",
            "high",
            sorted((flags | warnings) & {"requires_manual_table_review", "possible_broken_table", "quality_flag:requires_manual_table_review", "quality_flag:possible_broken_table"}),
            "Potentially useful table or table-derived text requires human review.",
            "table",
            "high",
            False,
        )
    if _looks_like_ocr_corruption(title, body):
        return _decision(
            "needs_human_review",
            "medium",
            ["ocr_corruption"],
            "Clinical text appears useful but OCR corruption makes it unsafe for provisional RAG.",
            _content_type(metadata, body),
            "high",
            False,
        )
    if "body_too_short" in errors or wc < 35:
        return _decision(
            "rejected",
            "high",
            ["body_too_short"],
            "Section is too short to provide safe clinical context.",
            "other",
            "medium",
            False,
        )
    if _looks_like_bibliography(normalized):
        return _decision(
            "rejected",
            "high",
            ["bibliography_dominant"],
            "Bibliographic references dominate the section.",
            "bibliography",
            "low",
            False,
        )
    if _looks_like_broken_extraction(body):
        return _decision(
            "quarantine",
            "medium",
            ["broken_extraction"],
            "Text appears technically damaged or internally inconsistent.",
            "broken_extraction",
            "high",
            False,
        )
    if _looks_like_malformed_table(body):
        return _decision(
            "needs_human_review",
            "medium",
            ["possible_broken_table"],
            "Table-like Markdown is not consistently structured.",
            "table",
            "high",
            False,
        )
    if _looks_like_damaged_title(title):
        return _decision(
            "needs_human_review",
            "medium",
            ["damaged_or_missing_title"],
            "Clinical text has a damaged or generic extraction title and needs human relabeling.",
            _content_type(metadata, body),
            "medium",
            False,
        )
    if _looks_like_fragment_title(title):
        return _decision(
            "needs_human_review",
            "medium",
            ["damaged_or_missing_title"],
            "Clinical text has a sentence-fragment extraction title and needs human relabeling.",
            _content_type(metadata, body),
            "medium",
            False,
        )

    contains_ranges = bool(metadata.get("contains_ranges_or_units")) or _has_numeric_units(body)
    species = str(metadata.get("species") or "unknown")
    if contains_ranges and species == "unknown":
        return _decision(
            "needs_human_review",
            "medium",
            ["numeric_context_species_uncertain"],
            "Numeric/unit content lacks explicit species context.",
            "reference_interval",
            "high",
            False,
        )

    clinical_score = _clinical_score(normalized)
    if clinical_score < 2:
        return _decision(
            "rejected",
            "medium",
            ["low_clinical_value"],
            "Content has insufficient clinical or laboratory utility for RAG.",
            _content_type(metadata, body),
            "medium",
            False,
        )
    if _has_reference_tail_contamination(body):
        return _decision(
            "needs_human_review",
            "medium",
            ["bibliography_contamination"],
            "Clinical section is contaminated by a substantial bibliographic reference tail.",
            _content_type(metadata, body),
            "medium",
            False,
        )
    if "domain_uncertain" in flags and clinical_score < 4:
        return _decision(
            "needs_human_review",
            "medium",
            ["domain_uncertain"],
            "Potentially useful content has uncertain domain classification.",
            _content_type(metadata, body),
            "medium",
            False,
        )
    if _looks_truncated(body):
        return _decision(
            "needs_human_review",
            "medium",
            ["possible_truncation"],
            "Clinical text appears truncated at a risky point.",
            _content_type(metadata, body),
            "high",
            False,
        )
    return _decision(
        "approved_provisional",
        "medium",
        ["clinically_useful_text"],
        "Useful veterinary clinical text with sufficient context for provisional RAG.",
        _content_type(metadata, body),
        "medium" if species == "unknown" else "low",
        True,
    )


def _decision(
    decision: str,
    confidence: str,
    reason_codes: list[str],
    short_reason: str,
    content_type: str,
    risk_level: str,
    recommended_for_rag: bool,
) -> ReviewDecision:
    return ReviewDecision(
        decision=decision,
        confidence=confidence,
        reason_codes=reason_codes or ["unspecified"],
        short_reason=short_reason,
        content_type=content_type,
        risk_level=risk_level,
        recommended_for_rag=recommended_for_rag,
    )


def apply_review_frontmatter(
    *,
    metadata: dict[str, Any],
    decision: ReviewDecision,
    canonical_source_id: str,
    reviewed_at: str,
) -> dict[str, Any]:
    reviewed = dict(metadata)
    original_source_id = str(metadata.get("source_id") or "")
    reviewed["original_source_id"] = original_source_id
    reviewed["canonical_source_id"] = canonical_source_id
    reviewed["reviewer"] = AI_REVIEWER
    reviewed["expert_reviewed"] = False
    reviewed["ai_review_decision"] = decision.decision
    reviewed["ai_review_confidence"] = decision.confidence
    reviewed["ai_review_reason_codes"] = decision.reason_codes
    reviewed["ai_review_short_reason"] = decision.short_reason
    reviewed["ai_review_risk_level"] = decision.risk_level
    reviewed["rag_eligible"] = decision.recommended_for_rag
    if decision.decision == "approved_provisional":
        reviewed["status"] = "ai_approved_provisional"
        reviewed["review_required"] = False
        reviewed["approved_at"] = reviewed_at
        reviewed["curation_level"] = "ai_veterinary_screened_provisional"
    elif decision.decision == "rejected":
        reviewed["status"] = "rejected_by_ai_review"
        reviewed["review_required"] = False
        reviewed["rejected_at"] = reviewed_at
        reviewed["curation_level"] = "ai_rejected"
        reviewed["rejection_reason"] = decision.short_reason
    elif decision.decision == "needs_human_review":
        reviewed["status"] = "needs_human_review"
        reviewed["review_required"] = True
        reviewed["reviewed_at"] = reviewed_at
        reviewed["curation_level"] = "ai_screened_requires_human"
        reviewed["human_review_reason"] = decision.short_reason
    else:
        reviewed["status"] = "quarantine"
        reviewed["review_required"] = True
        reviewed["quarantined_at"] = reviewed_at
        reviewed["curation_level"] = "technical_quarantine"
        reviewed["quarantine_reason"] = decision.short_reason
    return reviewed


def filter_chunks_for_approved_candidates(
    *,
    chunks: list[dict[str, Any]],
    approved_original_paths: set[str],
    canonical_source_id: str,
    book_title: str,
) -> list[dict[str, Any]]:
    approved = {normalize_rel_path(path) for path in approved_original_paths}
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        section_file = normalize_rel_path(str(chunk.get("section_file") or ""))
        if section_file not in approved:
            continue
        source_file = str(chunk.get("source_file") or "")
        page_start, page_end = page_range_from_batch_name(source_file)
        records.append(
            {
                "source_id": canonical_source_id,
                "book_title": book_title,
                "candidate_path": section_file,
                "original_chunk_id": chunk.get("chunk_id"),
                "page_start": page_start,
                "page_end": page_end,
                "section_title": chunk.get("title"),
                "ai_review_status": "approved_provisional",
                "rag_eligible": True,
                "expert_reviewed": False,
                "text": chunk.get("text"),
                "headings": chunk.get("headings") or [],
                "domain": chunk.get("domain"),
                "species": chunk.get("species"),
                "quality_flags": chunk.get("quality_flags") or [],
            }
        )
    return records


def load_validation_by_file(project_root: Path) -> dict[str, dict[str, Any]]:
    report = read_json(project_root / "knowledge_base/reports/validation_report.json", {"records": []})
    return {str(item.get("file")): item for item in report.get("records", [])}


def candidate_paths_for_source(
    *,
    project_root: Path,
    source_id: str,
    batch_index: dict[str, Any],
) -> list[Path]:
    paths: list[Path] = []
    for path in (project_root / "knowledge_base/curated_candidates").rglob("*.md"):
        try:
            metadata, _body = parse_markdown_with_frontmatter(path)
        except ValueError:
            continue
        if canonical_source_for_metadata(metadata, batch_index) == source_id:
            paths.append(path)
    return sorted(paths)


def pending_paths_for_source(
    *,
    project_root: Path,
    source_id: str,
    batch_index: dict[str, Any],
) -> list[Path]:
    paths: list[Path] = []
    for path in (project_root / "knowledge_base/expert_review/pending").glob("*.md"):
        try:
            metadata, _body = parse_markdown_with_frontmatter(path)
        except ValueError:
            continue
        if canonical_source_for_metadata(metadata, batch_index) == source_id:
            paths.append(path)
    return sorted(paths)


def ensure_ai_review_dirs(project_root: Path, source_id: str) -> dict[str, Path]:
    root = project_ai_review_root(project_root)
    dirs = {
        "approved_provisional": root / "approved_provisional" / source_id,
        "rejected": root / "rejected" / source_id,
        "needs_human_review": root / "needs_human_review" / source_id,
        "quarantine": root / "quarantine" / source_id,
        "manifests": root / "manifests" / source_id,
        "reports": root / "reports" / source_id,
        "logs": root / "logs",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def copy_reviewed_markdown(
    *,
    source_path: Path,
    destination_dir: Path,
    metadata: dict[str, Any],
    body: str,
) -> Path:
    metadata_to_write = dict(metadata)
    metadata_to_write["ai_review_original_path"] = source_path.as_posix()
    destination = destination_dir / source_path.name
    if destination.exists():
        try:
            existing_metadata, _existing_body = parse_markdown_with_frontmatter(destination)
        except ValueError:
            existing_metadata = {}
        if existing_metadata.get("ai_review_original_path") != metadata_to_write["ai_review_original_path"]:
            destination = destination_dir / f"{source_path.stem}__{sha256_text(source_path.as_posix())[:8]}{source_path.suffix}"
    destination.write_text(dump_markdown(metadata_to_write, body), encoding="utf-8")
    return destination


def match_candidate_by_filename(pending_path: Path, candidate_paths: list[Path]) -> Path | None:
    matches = [path for path in candidate_paths if path.name == pending_path.name]
    if len(matches) != 1:
        return None
    return matches[0]


def write_json_artifact(path: Path, payload: Any) -> Path:
    return write_json(path, payload)


def write_jsonl_artifact(path: Path, records: list[dict[str, Any]]) -> Path:
    return write_jsonl(path, records)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_rel_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def page_range_from_batch_name(name: str) -> tuple[int | None, int | None]:
    match = re.search(r"pages_(\d{4})_(\d{4})", name or "")
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def hash_file(path: Path) -> str:
    return sha256_text(path.read_text(encoding="utf-8", errors="replace"))


def decision_to_manifest_record(
    *,
    project_root: Path,
    source_path: Path,
    destination_path: Path,
    metadata: dict[str, Any],
    body: str,
    canonical_source_id: str,
    book_title: str,
    decision: ReviewDecision,
    batch_info: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "path": relative_to_project(source_path, project_root),
        "reviewed_path": relative_to_project(destination_path, project_root),
        "source_id": canonical_source_id,
        "original_source_id": metadata.get("source_id"),
        "book_title": book_title,
        "decision": decision.decision,
        "confidence": decision.confidence,
        "reason_codes": decision.reason_codes,
        "short_reason": decision.short_reason,
        "content_type": decision.content_type,
        "risk_level": decision.risk_level,
        "recommended_for_rag": decision.recommended_for_rag,
        "original_status": metadata.get("status"),
        "new_status": _status_for_decision(decision.decision),
        "page_start": (batch_info or {}).get("page_start"),
        "page_end": (batch_info or {}).get("page_end"),
        "section_title": metadata.get("title"),
        "hash": sha256_text(body),
    }


def summarize_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = Counter(str(record.get("decision")) for record in records)
    reasons = Counter(
        reason
        for record in records
        for reason in record.get("reason_codes", [])
    )
    return {
        "approved_provisional": decisions.get("approved_provisional", 0),
        "rejected": decisions.get("rejected", 0),
        "needs_human_review": decisions.get("needs_human_review", 0),
        "quarantine": decisions.get("quarantine", 0),
        "top_reason_codes": reasons.most_common(20),
    }


def _status_for_decision(decision: str) -> str:
    return {
        "approved_provisional": "ai_approved_provisional",
        "rejected": "rejected_by_ai_review",
        "needs_human_review": "needs_human_review",
        "quarantine": "quarantine",
    }.get(decision, "quarantine")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _looks_like_contributor(title: str, body: str) -> bool:
    title_text = _norm(title)
    body_text = _norm(body)
    text = _norm(f"{title} {body}")
    credential_hits = len(re.findall(r"\b(?:dvm|dacvp|phd|ms|mrcvs|bvsc|vmd|bvetmed|ascp)\b", text))
    title_credential_hits = len(re.findall(r"\b(?:dvm|dacvp|phd|ms|mrcvs|bvsc|vmd|bvetmed|ascp)\b", title_text))
    affiliation_hits = len(re.findall(r"\b(?:university|department|professor|laboratories|college|institute|school)\b", text))
    role_hits = len(
        re.findall(
            r"\b(?:clinical pathologist|pathologist|professor|resident|diagnostic laboratory|laboratory director)\b",
            body_text,
        )
    )
    chapter_list_hits = sum(
        1
        for term in (
            "sample collection",
            "cell types",
            "criteria of malignancy",
            "selected infectious agents",
            "transtracheal",
            "bronchoalveolar",
            "kidneys",
            "spleen",
            "reproductive tract",
            "cutaneous",
        )
        if term in body_text
    )
    author_name_title = (
        bool(re.search(r"\band\b", title_text))
        and bool(re.search(r"\b[A-Z]\.\s*[A-Z]\.|[A-Z]{2,}", title))
        and len(re.findall(r"\b[A-Z][a-z]+|[A-Z]{2,}\b", title)) >= 3
    )
    clinical_list_hits = sum(
        1
        for term in (
            "functional anatomy",
            "hemopoietic system",
            "hematopoietic system",
            "thymus",
            "bovine leukemia virus",
            "feline leukemia virus",
            "major histocompatibility complex",
            "red blood cell",
        )
        if term in body_text
    )
    if author_name_title and word_count(body) < 90 and clinical_list_hits >= 3:
        return True
    if title_credential_hits >= 2 and word_count(body) < 140 and (role_hits >= 1 or chapter_list_hits >= 3):
        return True
    return credential_hits >= 2 and affiliation_hits >= 1 and word_count(body) < 120


def _looks_like_author_title(title: str) -> bool:
    stripped = (title or "").strip()
    normalized = _norm(stripped)
    if " and " not in normalized:
        return False
    if any(term in normalized for term in CLINICAL_TERMS | {"collection", "handling", "quality", "control", "diagnostic", "laboratory"}):
        return False
    parts = re.split(r"\s+and\s+", stripped, flags=re.I)
    if len(parts) != 2:
        return False
    for part in parts:
        tokens = re.findall(r"[A-Za-z][A-Za-z.-]*", part)
        if len(tokens) < 2 or len(tokens) > 4:
            return False
        if not all(token[:1].isupper() for token in tokens):
            return False
    return len(stripped.split()) <= 8


def _contains_editorial_noise(normalized: str) -> bool:
    if not normalized:
        return True
    return any(term in normalized for term in EDITORIAL_TERMS)


def _looks_like_bibliography(normalized: str) -> bool:
    if "references" not in normalized and "bibliography" not in normalized:
        return False
    hits = sum(normalized.count(term) for term in REFERENCE_TERMS)
    return hits >= 3


def _looks_like_reference_title(title: str) -> bool:
    normalized = _norm(title)
    if len(normalized) < 45:
        return False
    journal_hit = any(term in normalized for term in (" j ", " journal", " vet ", " pathol", " med ", " assoc", " res "))
    year_volume_hit = bool(re.search(r"\b(?:19|20)\d{2}\s*;\s*\d+", normalized))
    citation_punctuation = normalized.count(".") >= 2 or normalized.count(";") >= 1
    author_prefix = bool(re.match(r"^[a-z][a-z-]+(?:\s+[a-z]{1,3})?\s*(?:,|\.)", normalized))
    return author_prefix and citation_punctuation and (journal_hit or year_volume_hit)


def _has_reference_tail_contamination(body: str) -> bool:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(lines) < 3:
        return False
    reference_lines = [
        line
        for line in lines
        if re.match(r"^\d{1,3}\.\s+[A-Z][A-Za-z' -]+(?:\s+[A-Z]{1,4}\b|,)", line)
        and re.search(r"\b(?:19|20)\d{2}\b|;\s*\d+\s*:", line)
    ]
    if len(reference_lines) < 3:
        return False
    body_words = max(word_count(body), 1)
    reference_words = sum(word_count(line) for line in reference_lines)
    return reference_words / body_words >= 0.35


def _looks_like_fragment_title(title: str) -> bool:
    stripped = (title or "").strip()
    if len(stripped) < 60:
        return False
    starts_lower = bool(re.match(r"^[a-z]", stripped))
    sentence_like = stripped.endswith(".") or stripped.count(",") >= 2
    has_terminal_clause = bool(re.search(r"\b(?:and|or|of|to|with|in)\s*$", stripped, flags=re.I))
    return starts_lower and (sentence_like or has_terminal_clause)


def _looks_like_broken_extraction(body: str) -> bool:
    if "\x00" in body:
        return True
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(lines) < 4:
        return False
    short_lines = sum(1 for line in lines if len(line) <= 3)
    if short_lines / len(lines) > 0.45:
        return True
    words = re.findall(r"\b\w+\b", body)
    if not words:
        return True
    unique_ratio = len(set(words)) / max(len(words), 1)
    return len(words) > 80 and unique_ratio < 0.12


def _looks_like_malformed_table(body: str) -> bool:
    pipe_lines = [line for line in body.splitlines() if "|" in line]
    if len(pipe_lines) < 2:
        return False
    counts = [line.count("|") for line in pipe_lines]
    return max(counts) - min(counts) >= 3 or any(count < 2 for count in counts)


def _looks_like_damaged_title(title: str) -> bool:
    compact = re.sub(r"\s+", " ", (title or "").strip())
    normalized = compact.lower()
    if re.fullmatch(r"(?:[a-z]\s+){3,}\d(?:\s+\d+)*", normalized):
        return True
    return bool(re.fullmatch(r"(?:chapter|section)\s+\d+(?:\s+\d+)*", normalized))


def _looks_like_ocr_corruption(title: str, body: str) -> bool:
    text = f"{title}\n{body}"
    words = re.findall(r"\b[A-Za-z0-9][A-Za-z0-9'_-]*\b", text)
    if len(words) < 20:
        return False
    artifact_hits = len(
        re.findall(
            r"&(?:lt|gt|amp);|~|\\_|\"{2,}|\.{3,}|[<>{}=£«»·]|(?:\b\w*[A-Za-z]\w*\d\w*[A-Za-z]\w*\b)",
            text,
        )
    )
    punctured_word_hits = len(re.findall(r"[A-Za-z]{2,}[.:;,][A-Za-z]{2,}|[A-Za-z]\.[A-Za-z]{2,}|[A-Za-z]{2,}[,:;]\s*[A-Za-z]{1,3}\b", text))
    fragment_hits = len(
        re.findall(
            r"\b(?:pati~nt|r~ult|r~f~rence|likdy|th\.t|pred1ctne|p05itive|nq;ative|faJse|eryrhrocyte|roncentr|bodi\s*\.\.|\.nd|t\.bl|tabl~|diseuc5|dixa|ood|oolor|m~ntjon|purpost|l\.ukocyt|ptrform|d\.f|bl:astogt|tr:msform|hisliocytes|cop\.bj|mito,;s|erythrocyu|resorbnl|deuet|npeclet|concep\"|sampl\s*\.\.)\b",
            text,
            flags=re.I,
        )
    )
    score = artifact_hits + fragment_hits + punctured_word_hits
    return artifact_hits >= 8 or fragment_hits >= 3 or punctured_word_hits >= 5 or score / max(len(words), 1) > 0.08


def _has_numeric_units(body: str) -> bool:
    return bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:%|g/dl|mg/dl|mmol/l|x10|/ul|/µl|fl|pg|iu/l|u/l)\b", body, flags=re.I))


def _clinical_score(normalized: str) -> int:
    return sum(1 for term in CLINICAL_TERMS if term in normalized)


def _looks_truncated(body: str) -> bool:
    stripped = body.strip()
    if not stripped:
        return True
    return stripped.endswith(("/", "and", "or", "with", "of", "to", "in"))


def _content_type(metadata: dict[str, Any], body: str, forced: str | None = None) -> str:
    if forced:
        return forced
    title = _norm(str(metadata.get("title") or ""))
    if metadata.get("contains_tables") or "|" in body:
        return "table"
    if metadata.get("contains_ranges_or_units") or _has_numeric_units(body):
        return "reference_interval"
    if "bibliography" in title or "references" in title:
        return "bibliography"
    if _looks_like_broken_extraction(body):
        return "broken_extraction"
    if _clinical_score(_norm(body)) >= 2:
        return "clinical_text"
    return "other"


def copy_raw_artifact_to_quarantine(
    *,
    project_root: Path,
    path: Path,
    source_id: str,
    reason: str,
) -> dict[str, Any]:
    dirs = ensure_ai_review_dirs(project_root, source_id)
    destination = dirs["quarantine"] / path.name
    if path.exists() and path.is_file():
        if destination.exists():
            destination = dirs["quarantine"] / f"{path.stem}__{sha256_text(path.as_posix())[:8]}{path.suffix}"
        shutil.copy2(path, destination)
    return {
        "path": relative_to_project(path, project_root),
        "reviewed_path": relative_to_project(destination, project_root),
        "source_id": source_id,
        "decision": "quarantine",
        "confidence": "high",
        "reason_codes": [reason],
        "short_reason": reason,
        "content_type": "other",
        "risk_level": "high",
        "recommended_for_rag": False,
        "original_status": None,
        "new_status": "quarantine",
        "page_start": None,
        "page_end": None,
        "section_title": path.name,
        "hash": hash_file(path) if path.exists() and path.is_file() else None,
    }
