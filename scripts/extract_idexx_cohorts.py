"""Extraccion batch IDEXX recursiva por cohortes.

Este script reemplaza la dependencia de numeracion continua en NB01. Lee PDFs bajo
`Sin Limpieza/**/batch_*.pdf`, extrae todos los pacientes por pares de paginas y
preserva metadata de cohorte/ruta/hash para no colisionar `batch_1.pdf` historico
con `Dic-May/batch_1.pdf`.

Por defecto escribe un CSV separado y no toca `data/interim/idexx_extracted.csv`.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.hematology.extractor import (  # noqa: E402
    _extract_cbc_idexx,
    _extract_comments_idexx,
    _extract_header,
    _parse_age_years,
    _rename_to_canonical,
)
from app.modules.maps.geocoder import resolve_location  # noqa: E402
from app.modules.ml.metadata import (  # noqa: E402
    coalesce_sample_date,
    file_sha256,
    infer_ingestion_cohort,
    make_dog_id,
    make_record_id,
    resolve_location_metadata,
)


VALID_GENDERS = (
    "Male",
    "Female",
    "Unknown",
    "Intact Male",
    "Intact Female",
    "Neutered Male",
    "Spayed Female",
)


def discover_pdfs(project_root: Path, cohort: str | None = None) -> list[Path]:
    pdf_root = project_root / "Sin Limpieza"
    paths = sorted(pdf_root.rglob("batch_*.pdf"))
    if cohort:
        paths = [
            path for path in paths
            if infer_ingestion_cohort(path.relative_to(project_root)) == cohort
        ]
    return paths


def _clean_gender(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text if any(valid.lower() in text.lower() for valid in VALID_GENDERS) else None


def extract_pdf_records(pdf_path: Path, project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    rel = pdf_path.relative_to(project_root)
    file_hash = file_sha256(pdf_path)
    cohort = infer_ingestion_cohort(rel)
    batch_folder = pdf_path.parent.relative_to(project_root / "Sin Limpieza").as_posix()
    if batch_folder == ".":
        batch_folder = "."

    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as exc:
        return [], [{"source_relative_path": rel.as_posix(), "error": str(exc)}]

    try:
        for page_idx in range(0, len(pdf.pages), 2):
            try:
                text_results = pdf.pages[page_idx].extract_text() or ""
                if "Hematology" not in text_results:
                    continue

                raw_values = _extract_cbc_idexx(text_results)
                if not raw_values:
                    continue

                header = _extract_header(text_results)
                cbc_values = _rename_to_canonical(raw_values)
                age_years = _parse_age_years(header.get("age"))
                if age_years is not None:
                    cbc_values["age_years"] = age_years

                comments = None
                if page_idx + 1 < len(pdf.pages):
                    text_scatter = pdf.pages[page_idx + 1].extract_text() or ""
                    comments = _extract_comments_idexx(text_scatter)

                sample_dt = coalesce_sample_date(header)
                sample_date = sample_dt.date().isoformat() if sample_dt else ""
                location = resolve_location_metadata(
                    header.get("clinic"),
                    clinic=header.get("clinic"),
                    geocode_fn=resolve_location,
                )
                record_id = make_record_id(
                    source_dataset="IDEXX",
                    source_relative_path=rel.as_posix(),
                    file_hash=file_hash,
                    page_number=page_idx + 1,
                    patient_name=header.get("patient_name"),
                    sample_date=sample_date,
                )
                dog_id = make_dog_id(
                    patient_name=header.get("patient_name"),
                    pet_owner=header.get("pet_owner"),
                    clinic=header.get("clinic"),
                    source_dataset="IDEXX",
                    fallback=record_id,
                )

                record = {
                    "record_id": record_id,
                    "record_uuid": record_id,
                    "dog_id": dog_id,
                    "pdf_filename": pdf_path.name,
                    "source_relative_path": rel.as_posix(),
                    "file_hash": file_hash,
                    "batch_folder": batch_folder,
                    "ingestion_cohort": cohort,
                    "page_number": page_idx + 1,
                    "source_dataset": "IDEXX",
                    **header,
                    **cbc_values,
                    "gender": _clean_gender(header.get("gender")),
                    "sample_date": sample_date,
                    "raw_location_text": location.raw_location_text,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "location_source": location.location_source,
                    "location_confidence": location.location_confidence,
                    "idexx_comments": comments,
                    "has_scatter_plots": page_idx + 1 < len(pdf.pages),
                    "extraction_timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
                records.append(record)
            except Exception as exc:
                errors.append(
                    {
                        "source_relative_path": rel.as_posix(),
                        "page_number": page_idx + 1,
                        "error": str(exc),
                    }
                )
    finally:
        pdf.close()

    return records, errors


def extract_cohort(project_root: Path, cohort: str | None, output: Path, errors_output: Path) -> dict[str, Any]:
    pdfs = discover_pdfs(project_root, cohort)
    all_records: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []

    for idx, pdf_path in enumerate(pdfs, start=1):
        records, errors = extract_pdf_records(pdf_path, project_root)
        all_records.extend(records)
        all_errors.extend(errors)
        if idx % 25 == 0 or idx == len(pdfs):
            print(f"Procesados {idx}/{len(pdfs)} PDFs; registros={len(all_records)} errores={len(all_errors)}")

    df = pd.DataFrame(all_records)
    if not df.empty and "species" in df.columns:
        df = df[df["species"].astype(str).str.contains("Canine", case=False, na=False)].reset_index(drop=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    errors_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    pd.DataFrame(all_errors).to_csv(errors_output, index=False)

    summary = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "cohort_filter": cohort,
        "pdf_files": len(pdfs),
        "records_extracted": int(len(df)),
        "errors": len(all_errors),
        "output": str(output.relative_to(project_root)),
        "errors_output": str(errors_output.relative_to(project_root)),
        "cohort_counts": df.get("ingestion_cohort", pd.Series(dtype=object)).value_counts().to_dict()
        if not df.empty
        else {},
    }
    summary_path = project_root / "outputs" / f"extraction_summary_{cohort or 'all'}.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", default=None, help="Filtra una cohorte, por ejemplo dic_may_2026.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "interim" / "idexx_extracted_cohorted.csv",
    )
    parser.add_argument(
        "--errors-output",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "idexx_extraction_errors_cohorted.csv",
    )
    args = parser.parse_args()

    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    errors_output = args.errors_output if args.errors_output.is_absolute() else PROJECT_ROOT / args.errors_output
    summary = extract_cohort(PROJECT_ROOT, args.cohort, output, errors_output)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
