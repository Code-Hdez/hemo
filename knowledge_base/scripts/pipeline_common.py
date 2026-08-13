from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


VALID_DOMAINS = {
    "hematology",
    "cytology",
    "clinical_pathology",
    "renal",
    "hepatic",
    "endocrine",
    "inflammatory",
    "infectious",
    "coagulation",
    "urinalysis",
    "sample_collection",
    "laboratory_methods",
    "general",
    "unknown",
}

VALID_SPECIES = {"canine", "feline", "canine_feline", "other", "unknown"}
VALID_STATUSES = {"needs_expert_review", "approved", "rejected"}

REVIEWABLE_CLASSIFICATIONS = {"valid_candidate", "warning"}

SUSPICIOUS_TITLE_TERMS = {
    "bsava",
    "section",
    "copyright",
    "contributors",
    "contents",
    "table of contents",
    "references",
    "references and further reading",
    "further reading",
    "useful websites",
    "index",
    "preface",
    "acknowledgements",
    "acknowledgments",
    "dedication",
    "isbn",
    "notice",
    "publisher",
}

EDITORIAL_REJECTION_PATTERNS = (
    r"\bcopyright\b",
    r"\ball rights reserved\b",
    r"\binternational standard book number\b",
    r"\bisbn\b",
    r"\blibrary of congress\b",
    r"\bcontributors\b",
    r"\breferences and further reading\b",
    r"\bfurther reading\b",
    r"\buseful websites\b",
    r"\btable of contents\b",
    r"\bcontents\b",
    r"\bthis page intentionally left blank\b",
    r"\bactivate the ebook\b",
    r"\bexpert consult\b",
)

FRONTMATTER_FIELDS = [
    "source_id",
    "source_file",
    "source_path",
    "title",
    "domain",
    "species",
    "language",
    "status",
    "version",
    "source_type",
    "curation_level",
    "review_required",
    "reviewer",
    "approved_at",
    "chunking_policy",
    "created_by_pipeline",
    "contains_tables",
    "contains_ranges_or_units",
    "quality_flags",
    "curation_notes",
]

REQUIRED_USER_FRONTMATTER_FIELDS = [
    "source_id",
    "source_file",
    "source_path",
    "title",
    "domain",
    "species",
    "language",
    "status",
    "source_type",
    "curation_level",
    "review_required",
    "reviewer",
    "approved_at",
    "chunking_policy",
    "created_by_pipeline",
    "contains_tables",
    "contains_ranges_or_units",
    "quality_flags",
    "curation_notes",
]

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hematology": (
        "anemia",
        "erythrocyte",
        "erythrocytes",
        "leukocyte",
        "leukocytes",
        "platelet",
        "platelets",
        "hemogram",
        "cbc",
        "blood smear",
        "reticulocyte",
        "reticulocytes",
        "neutrophil",
        "neutrophils",
        "lymphocyte",
        "lymphocytes",
        "eosinophil",
        "eosinophils",
        "monocyte",
        "monocytes",
        "basophil",
        "basophils",
        "thrombocyte",
        "thrombocytes",
        "hemostasis",
        "haematology",
        "hematology",
    ),
    "cytology": (
        "cytology",
        "aspirate",
        "smear",
        "lymph node",
        "bone marrow",
        "effusion",
        "mass",
        "neoplasia",
        "inflammation",
        "sample preparation",
    ),
    "clinical_pathology": (
        "clinical pathology",
        "serum chemistry",
        "biochemistry",
        "laboratory diagnosis",
        "diagnostic test",
        "laboratory test",
    ),
    "sample_collection": (
        "collection",
        "anticoagulant",
        "edta",
        "sample handling",
        "storage",
        "preparation",
    ),
    "coagulation": (
        "coagulation",
        "hemostasis",
        "haemostasis",
        "pt",
        "aptt",
        "fibrinogen",
    ),
    "renal": ("renal", "kidney", "creatinine", "urea", "azotemia"),
    "hepatic": ("hepatic", "liver", "bilirubin", "alt", "alp", "bile acid"),
    "endocrine": ("endocrine", "thyroid", "adrenal", "cortisol", "insulin"),
    "inflammatory": ("inflammatory", "inflammation", "acute phase", "fibrinogen"),
    "infectious": ("infectious", "bacterial", "viral", "fungal", "protozoal"),
    "urinalysis": ("urinalysis", "urine", "specific gravity", "sediment"),
    "laboratory_methods": (
        "quality assurance",
        "laboratory method",
        "reference interval",
        "assay",
        "analytical",
    ),
}

SOURCE_HINTS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (
        ("bsava manual", "canine and feline clinical pathology"),
        "bsava_manual_canine_feline_clinical_pathology_3e",
        "BSAVA Manual of Canine and Feline Clinical Pathology",
    ),
    (
        ("cowell", "tyler", "diagnostic cytology"),
        "cowell_tylers_diagnostic_cytology_hematology_dog_cat_5e",
        "Cowell and Tyler's Diagnostic Cytology and Hematology of the Dog and Cat",
    ),
    (
        ("duncan", "prasse", "veterinary laboratory medicine"),
        "duncan_prasses_veterinary_laboratory_medicine_clinical_pathology_5e",
        "Duncan Prasse's Veterinary Laboratory Medicine: Clinical Pathology",
    ),
    (
        ("fundamentals of veterinary clinical pathology",),
        "fundamentals_veterinary_clinical_pathology_2e",
        "Fundamentals of Veterinary Clinical Pathology",
    ),
    (
        ("schalm", "veterinary hematology"),
        "schalms_veterinary_hematology_6e",
        "Schalm's Veterinary Hematology",
    ),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def kb_root(project_root: Path) -> Path:
    return project_root / "knowledge_base"


def ensure_directories(project_root: Path) -> None:
    root = kb_root(project_root)
    directories = [
        root / "processing" / "precleaned_md",
        root / "processing" / "split_sections",
        root / "processing" / "rejected",
        root / "processing" / "rejected" / "auto",
        root / "processing" / "logs",
        root / "expert_review" / "pending",
        root / "expert_review" / "approved",
        root / "expert_review" / "rejected",
        root / "chunks" / "candidates",
        root / "chunks" / "approved",
        root / "reports",
        root / "docling_json",
        root / "staging_md",
        root / "scripts",
    ]
    directories.extend(root / "curated_candidates" / domain for domain in sorted(VALID_DOMAINS))
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def ensure_prompt_template(project_root: Path) -> Path:
    ensure_directories(project_root)
    path = kb_root(project_root) / "scripts" / "curation_prompt_template.txt"
    if not path.exists():
        path.write_text(CURATION_PROMPT_TEMPLATE, encoding="utf-8")
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records)
        + ("\n" if records else ""),
        encoding="utf-8",
    )
    return path


def remove_path(path: Path) -> int:
    """Remove a generated file or directory and return removed file count."""
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        path.unlink()
        return 1
    files = [item for item in path.rglob("*") if item.is_file() or item.is_symlink()]
    shutil.rmtree(path)
    return len(files)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def slugify(text: str, *, fallback: str = "untitled", max_length: int = 70) -> str:
    normalized = normalize_text(text)
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    if not slug:
        slug = fallback
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("_")
    return slug or fallback


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+(?:[-'/]\w+)?\b", text or ""))


def approx_token_count(text: str) -> int:
    # Good enough for offline candidate chunks; embeddings are not generated here.
    return max(1, int(word_count(text) * 1.25))


def relative_to_project(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def infer_source(text: str, source_file: str) -> tuple[str, str]:
    normalized = normalize_text(text[:12000])
    for hints, source_id, title in SOURCE_HINTS:
        if all(hint in normalized for hint in hints):
            return source_id, title
    stem = Path(source_file).stem
    return slugify(stem), stem.replace("_", " ").replace("-", " ").title()


def classify_domain(text: str) -> str:
    normalized = normalize_text(text)
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            keyword_norm = normalize_text(keyword)
            if " " in keyword_norm:
                score += normalized.count(keyword_norm) * 2
            else:
                score += len(re.findall(rf"\b{re.escape(keyword_norm)}\b", normalized))
        if score:
            scores[domain] = score
    if not scores:
        return "unknown"
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]


def classify_species(text: str) -> str:
    normalized = normalize_text(text)
    canine = bool(re.search(r"\b(dog|dogs|canine|canines)\b", normalized))
    feline = bool(re.search(r"\b(cat|cats|feline|felines)\b", normalized))
    if canine and feline:
        return "canine_feline"
    if canine:
        return "canine"
    if feline:
        return "feline"
    return "unknown"


def parse_markdown_with_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise ValueError(f"Missing YAML frontmatter: {path}")
    try:
        frontmatter, body = raw[4:].split("\n---\n", 1)
    except ValueError as exc:
        raise ValueError(f"Unclosed YAML frontmatter: {path}") from exc
    metadata = yaml.safe_load(frontmatter)
    if not isinstance(metadata, dict):
        raise ValueError(f"Invalid YAML frontmatter: {path}")
    return metadata, body.strip()


def dump_markdown(metadata: dict[str, Any], body: str) -> str:
    ordered = {key: metadata.get(key) for key in metadata.keys()}
    yaml_text = yaml.safe_dump(
        ordered,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    return f"---\n{yaml_text}\n---\n\n{body.strip()}\n"


def has_heading(text: str) -> bool:
    return re.search(r"^#\s+\S+", text or "", flags=re.MULTILINE) is not None


def extract_title(text: str, fallback: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if match:
            return clean_title(match.group(1))
        if _is_useful_title_line(stripped):
            return clean_title(stripped)
    return clean_title(fallback)


def clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip(" #:\t")
    title = re.sub(r"^[0-9ivxlcdmIVXLCDM]+[.)]\s+", "", title)
    return title[:120] or "Untitled section"


def is_suspicious_title(title: str) -> bool:
    normalized = normalize_text(title)
    if not normalized:
        return True
    if normalized in SUSPICIOUS_TITLE_TERMS:
        return True
    if _is_table_like_title(title):
        return True
    if re.fullmatch(r"(?:section|chapter|part|page)\s*[0-9ivxlcdm. -]*", normalized):
        return True
    if re.fullmatch(r"[0-9ivxlcdm]{1,8}", normalized):
        return True
    return False


def editorial_rejection_reason(title: str, text: str) -> str | None:
    normalized_title = normalize_text(title)
    normalized_text = normalize_text(text)
    if normalized_title.startswith("references") or normalized_title in {
        "further reading",
        "useful websites",
    }:
        return "references_or_website_content"
    if _is_table_like_title(title):
        return "broken_table_title"
    if is_suspicious_title(title):
        return f"suspicious_title:{normalized_title or 'empty'}"
    for pattern in EDITORIAL_REJECTION_PATTERNS:
        if re.search(pattern, normalized_text):
            if pattern in {r"\bcontributors\b", r"\bcontents\b", r"\btable of contents\b"}:
                return "editorial_or_index_content"
            if len(normalized_text.split()) < 600:
                return "editorial_boilerplate_content"
    if _looks_like_index_text(text):
        return "index_like_content"
    if _looks_like_contributors_text(text):
        return "contributors_like_content"
    return None


def _is_table_like_title(title: str) -> bool:
    stripped = (title or "").strip()
    if not stripped:
        return False
    if stripped.startswith("|") or stripped.endswith("|"):
        return True
    if stripped.count("|") >= 2:
        return True
    normalized = normalize_text(stripped)
    if re.search(r"\b(?:sen|spec|ppv|npv)\s*[=:]\s*\d", normalized) and word_count(stripped) <= 12:
        return True
    return False


def _looks_like_index_text(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    dot_leaders = sum(1 for line in lines if re.search(r"\.{4,}\s*\d{1,4}\s*$", line))
    page_refs = sum(1 for line in lines if re.search(r"\b\d{1,4}\s*$", line))
    return dot_leaders >= 3 or (len(lines) >= 8 and page_refs / max(len(lines), 1) > 0.65)


def _looks_like_contributors_text(text: str) -> bool:
    normalized = normalize_text(text)
    credential_hits = len(re.findall(r"\b(?:dvm|dacvp|phd|ms|mrcvs|bvsc|diplomate)\b", normalized))
    return credential_hits >= 4 and "contributor" in normalized


def write_rejected_section(
    *,
    project_root: Path,
    source_name: str,
    section_number: int,
    title: str,
    body: str,
    reason: str,
) -> Path:
    root = kb_root(project_root)
    rejected_dir = root / "processing" / "rejected" / "auto"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    destination = rejected_dir / f"{Path(source_name).stem}__section_{section_number:04d}__rejected.md"
    metadata = {
        "source_file": source_name,
        "section_number": section_number,
        "title": title,
        "rejection_reason": reason,
        "status": "rejected",
        "created_by_pipeline": True,
    }
    destination.write_text(dump_markdown(metadata, body), encoding="utf-8")
    return destination


def _is_useful_title_line(line: str) -> bool:
    if len(line) < 4 or len(line) > 140:
        return False
    if line.strip().startswith("|") or line.count("|") >= 2:
        return False
    normalized = normalize_text(line)
    noisy_terms = {
        "copyright",
        "isbn",
        "all rights reserved",
        "this page intentionally left blank",
    }
    if any(term in normalized for term in noisy_terms):
        return False
    if re.fullmatch(r"\d{1,4}|[ivxlcdm]{1,10}", normalized):
        return False
    return bool(re.search(r"[A-Za-z]", line))


def contains_table_hint(text: str) -> bool:
    table_patterns = (
        r"^\s*\|.+\|\s*$",
        r"\btable\s+\d+",
        r"(?:\S+\s{2,}){3,}\S+",
    )
    return any(re.search(pattern, text or "", flags=re.IGNORECASE | re.MULTILINE) for pattern in table_patterns)


def contains_ranges_or_units(text: str) -> bool:
    return bool(
        re.search(
            r"\b\d+(?:\.\d+)?\s*(?:-|to|/)\s*\d*(?:\.\d+)?\s*(?:mg/dl|g/dl|mmol/l|x10\^?\d*/l|%|fl|pg|u/l|iu/l)?\b|"
            r"\b(?:mg/dl|g/dl|mmol/l|x10\^?\d*/l|%|fl|pg|u/l|iu/l)\b",
            text or "",
            flags=re.IGNORECASE,
        )
    )


def noise_ratio(text: str) -> float:
    if not text:
        return 1.0
    visible = [char for char in text if not char.isspace()]
    if not visible:
        return 1.0
    alnum = sum(1 for char in visible if char.isalnum())
    return 1.0 - (alnum / len(visible))


def quality_flags_for_text(
    text: str,
    *,
    domain: str,
    species: str,
    section_word_count: int | None = None,
) -> list[str]:
    normalized = normalize_text(text)
    flags: list[str] = []
    if noise_ratio(text) > 0.42:
        flags.append("noisy_source")
    if contains_table_hint(text):
        flags.append("possible_broken_table")
        flags.append("requires_manual_table_review")
    if species == "unknown":
        flags.append("species_uncertain")
    if domain == "unknown":
        flags.append("domain_uncertain")
    if re.search(r"\b(contents|table of contents)\b", normalized):
        flags.append("possible_index_content")
    if re.search(r"\b(copyright|all rights reserved|isbn)\b", normalized):
        flags.append("possible_copyright_content")
    count = section_word_count if section_word_count is not None else word_count(text)
    if count < 60:
        flags.append("very_short_section")
    if count > 4500:
        flags.append("very_long_section")
    return sorted(set(flags))


def markdown_heading_path(lines: list[str]) -> str:
    headings: list[str] = []
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line.strip())
        if match:
            level = len(match.group(1))
            headings = headings[: level - 1]
            headings.append(clean_title(match.group(2)))
    return " > ".join(headings) if headings else "Document"


CURATION_PROMPT_TEMPLATE = """Actua como curador tecnico de una base de conocimiento RAG veterinaria.

Vas a recibir texto extraido de un documento de patologia clinica, hematologia o citologia veterinaria. El texto puede contener ruido OCR, headers, footers, numeros de pagina, fragmentos de indice, tablas rotas y saltos de linea defectuosos.

Objetivo:
Convertir el texto en una seccion Markdown limpia, util para RAG, sin inventar informacion.

Reglas:
1. No agregues informacion que no este en el texto fuente.
2. No inventes diagnosticos, valores, especies, rangos ni interpretaciones.
3. No resumas en exceso si se pierden detalles clinicos relevantes.
4. Elimina headers, footers, numeros de pagina, marcas OCR y texto irrelevante.
5. Conserva terminos tecnicos.
6. Conserva unidades, rangos, nombres de pruebas y abreviaturas.
7. Si hay tablas recuperables, conviertelas a Markdown limpio.
8. Si una tabla esta demasiado danada, conviertela en lista estructurada y marca que requiere revision.
9. Separa el contenido en titulos y subtitulos claros.
10. No incluyas copyright, contributors, indices ni paginas en blanco.
11. Devuelve unicamente Markdown valido.
12. No cambies el idioma del contenido fuente.
13. Manten la informacion veterinaria fiel al original.
14. Si la especie no esta clara, usa unknown.
15. Si el dominio no esta claro, usa unknown.

Frontmatter obligatorio:

---
source_id: "{SOURCE_ID}"
source_file: "{SOURCE_FILE}"
source_path: "{SOURCE_PATH}"
title: "{TITLE}"
domain: "{DOMAIN}"
species: "{SPECIES}"
language: "en"
status: "needs_expert_review"
version: "1"
source_type: "textbook"
curation_level: "llm_candidate"
review_required: true
reviewer: null
approved_at: null
chunking_policy: "section_based"
created_by_pipeline: true
contains_tables: {CONTAINS_TABLES}
contains_ranges_or_units: {CONTAINS_RANGES_OR_UNITS}
quality_flags: {QUALITY_FLAGS}
curation_notes: "{CURATION_NOTES}"
---

Texto fuente:

<<<
{RAW_TEXT}
>>>

Devuelve solo el Markdown final.
"""
