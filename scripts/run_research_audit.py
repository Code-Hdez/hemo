"""Genera artefactos de auditoria para cohortes, metadata y vigilancia.

El script no reentrena ni modifica train/val/test. Produce artefactos auxiliares:
- data/processed/ingestion_manifest.csv
- data/processed/analysis_metadata.csv
- data/metadata/location_overrides.csv (plantilla si no existe)
- outputs/cohort_comparison_dic_may.csv/json
- outputs/gate_* nuevos para cohortes, metadata, dog leakage y geocoding
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.maps.geocoder import resolve_location  # noqa: E402
from app.modules.ml.gates import (  # noqa: E402
    run_cohort_manifest_gate,
    run_dog_leakage_gate,
    run_geocoding_quality_gate,
    run_metadata_retention_gate,
    write_gate_report,
)
from app.modules.ml.metadata import (  # noqa: E402
    coalesce_sample_date,
    file_sha256,
    infer_ingestion_cohort,
    make_dog_id,
    make_record_id,
    normalize_text,
    read_location_overrides,
    resolve_location_metadata,
)


MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "ingestion_manifest.csv"
ANALYSIS_METADATA_PATH = PROJECT_ROOT / "data" / "processed" / "analysis_metadata.csv"
LOCATION_OVERRIDES_PATH = PROJECT_ROOT / "data" / "metadata" / "location_overrides.csv"
COHORT_COMPARISON_CSV = PROJECT_ROOT / "outputs" / "cohort_comparison_dic_may.csv"
COHORT_COMPARISON_JSON = PROJECT_ROOT / "outputs" / "cohort_comparison_dic_may.json"


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _batch_number(filename: str) -> int | None:
    match = re.search(r"batch_(\d+)", filename, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


def build_ingestion_manifest(project_root: Path = PROJECT_ROOT) -> pd.DataFrame:
    """Escanea PDFs de Sin Limpieza de forma recursiva y conserva rutas/hashes."""
    pdf_root = project_root / "Sin Limpieza"
    rows: list[dict[str, Any]] = []
    for path in sorted(pdf_root.rglob("*.pdf")):
        if path.name.endswith(":Zone.Identifier"):
            continue
        rel = path.relative_to(project_root)
        stat = path.stat()
        rows.append(
            {
                "source_relative_path": rel.as_posix(),
                "original_filename": path.name,
                "file_hash": file_sha256(path),
                "file_size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "batch_folder": path.parent.relative_to(pdf_root).as_posix()
                if path.parent != pdf_root
                else ".",
                "batch_number": _batch_number(path.name),
                "ingestion_cohort": infer_ingestion_cohort(rel),
            }
        )

    manifest = pd.DataFrame(rows)
    idexx_path = project_root / "data" / "interim" / "idexx_extracted.csv"
    dic_may_path = project_root / "data" / "interim" / "idexx_dic_may_extracted.csv"
    if idexx_path.exists() and not manifest.empty:
        idexx_df = pd.read_csv(idexx_path, usecols=["pdf_filename"])
        extracted_counts = idexx_df["pdf_filename"].value_counts().to_dict()
        is_baseline_root = manifest["batch_folder"].eq(".")
        manifest["extracted_records_current"] = 0
        manifest.loc[is_baseline_root, "extracted_records_current"] = (
            manifest.loc[is_baseline_root, "original_filename"]
            .map(extracted_counts)
            .fillna(0)
            .astype(int)
        )
        if dic_may_path.exists():
            dic_may_df = pd.read_csv(dic_may_path)
            if "source_relative_path" in dic_may_df.columns:
                dic_counts = dic_may_df["source_relative_path"].value_counts().to_dict()
                is_dic_may = manifest["ingestion_cohort"].eq("dic_may_2026")
                manifest.loc[is_dic_may, "extracted_records_current"] = (
                    manifest.loc[is_dic_may, "source_relative_path"]
                    .map(dic_counts)
                    .fillna(0)
                    .astype(int)
                )
        manifest["extraction_status_current"] = manifest["extracted_records_current"].map(
            lambda n: "extracted" if int(n) > 0 else "pending"
        )
    elif not manifest.empty:
        manifest["extracted_records_current"] = 0
        manifest["extraction_status_current"] = "pending"

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(MANIFEST_PATH, index=False)
    return manifest


def ensure_location_override_template(featured_df: pd.DataFrame) -> None:
    """Crea una plantilla editable de ubicaciones sin pisar correcciones existentes."""
    if LOCATION_OVERRIDES_PATH.exists():
        return

    LOCATION_OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "raw_location_text",
        "clinic",
        "city",
        "province",
        "latitude",
        "longitude",
        "confidence",
        "notes",
    ]
    clinics = (
        featured_df.loc[featured_df.get("source_dataset") == "IDEXX", "clinic"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .sort_values()
    )
    with LOCATION_OVERRIDES_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for clinic in clinics:
            coords = resolve_location(clinic)
            writer.writerow(
                {
                    "raw_location_text": clinic,
                    "clinic": clinic,
                    "city": "",
                    "province": "",
                    "latitude": coords[0] if coords else "",
                    "longitude": coords[1] if coords else "",
                    "confidence": "0.60" if coords else "",
                    "notes": "auto-template; revisar manualmente",
                }
            )


def build_analysis_metadata(project_root: Path = PROJECT_ROOT) -> pd.DataFrame:
    """Construye metadata no predictora para longitudinalidad, geografia y cohortes."""
    featured_path = project_root / "data" / "interim" / "featured_raw.csv"
    if not featured_path.exists():
        raise FileNotFoundError(f"No existe {featured_path}")

    featured_df = pd.read_csv(featured_path)
    ensure_location_override_template(featured_df)
    overrides = read_location_overrides(LOCATION_OVERRIDES_PATH)

    rows: list[dict[str, Any]] = []
    for _, row in featured_df.iterrows():
        source_dataset = str(row.get("source_dataset") or "unknown")
        pdf_filename = _clean_cell(row.get("pdf_filename"))
        source_relative_path = f"Sin Limpieza/{pdf_filename}" if source_dataset == "IDEXX" and pdf_filename else ""
        sample_dt = coalesce_sample_date(
            {
                "date_result": row.get("date_result"),
                "date_receipt": row.get("date_receipt"),
                "sample_date": row.get("sample_date"),
            }
        )
        if source_dataset == "DAP":
            # DAP en este proyecto tiene fecha anonimizada como precision_1/2/3.
            sample_date = ""
        else:
            sample_date = sample_dt.date().isoformat() if sample_dt else _clean_cell(row.get("sample_date"))
        record_uuid = str(row.get("record_uuid") or "").strip()
        record_id = make_record_id(
            source_dataset=source_dataset,
            source_relative_path=source_relative_path,
            page_number=row.get("page_number"),
            patient_name=row.get("patient_name"),
            sample_date=sample_date,
            existing_id=record_uuid,
        )
        dog_id = make_dog_id(
            patient_name=row.get("patient_name"),
            pet_owner=row.get("pet_owner"),
            clinic=row.get("clinic"),
            source_dataset=source_dataset,
            fallback=_clean_cell(row.get("original_id")) or _clean_cell(row.get("sample_id")) or record_uuid,
        )
        raw_location = row.get("clinic") if source_dataset == "IDEXX" else ""
        location = resolve_location_metadata(
            raw_location,
            clinic=row.get("clinic"),
            overrides=overrides,
            geocode_fn=resolve_location,
        )

        rows.append(
            {
                "record_id": record_id,
                "record_uuid": record_uuid or record_id,
                "dog_id": dog_id,
                "source_dataset": source_dataset,
                "ingestion_cohort": "baseline_historico" if source_dataset == "IDEXX" else "dap_external",
                "sample_date": sample_date,
                "date_receipt": _clean_cell(row.get("date_receipt")),
                "date_result": _clean_cell(row.get("date_result")),
                "source_relative_path": source_relative_path,
                "original_filename": pdf_filename,
                "batch_folder": ".",
                "page_number": row.get("page_number") if pd.notna(row.get("page_number")) else "",
                "clinic": _clean_cell(row.get("clinic")),
                "raw_location_text": location.raw_location_text,
                "city": location.city or "",
                "province": location.province or "",
                "latitude": location.latitude if location.latitude is not None else "",
                "longitude": location.longitude if location.longitude is not None else "",
                "location_source": location.location_source,
                "location_confidence": location.location_confidence,
                "breed": _clean_cell(row.get("breed")),
                "gender": _clean_cell(row.get("gender")),
                "age_years": row.get("age_years") if pd.notna(row.get("age_years")) else "",
                "metadata_version": "1.0.0",
            }
        )

    metadata = pd.DataFrame(rows)
    ANALYSIS_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata.to_csv(ANALYSIS_METADATA_PATH, index=False)
    return metadata


def build_cohort_comparison(manifest: pd.DataFrame, metadata: pd.DataFrame) -> dict[str, Any]:
    """Resume diferencias observables antes de extraer/mezclar Dic-May."""
    outputs: dict[str, Any] = {
        "generated_at": _utc_now(),
        "status": "dic_may_pending_extraction",
        "cohorts": {},
        "baseline_metrics": {},
        "notes": [
            "Dic-May se reporta como cohorte temporal nueva antes de reentrenar.",
            "Los nuevos PDFs aun no estan en train/val/test; el manifiesto evita colisiones de numeracion.",
        ],
    }

    for cohort, group in manifest.groupby("ingestion_cohort"):
        outputs["cohorts"][str(cohort)] = {
            "pdf_files": int(len(group)),
            "unique_hashes": int(group["file_hash"].nunique()),
            "extracted_records_current": int(group.get("extracted_records_current", pd.Series(dtype=int)).sum()),
            "pending_files_current": int((group.get("extraction_status_current", "") == "pending").sum()),
        }

    for cohort, group in metadata.groupby("ingestion_cohort"):
        lat = pd.to_numeric(group["latitude"], errors="coerce")
        lon = pd.to_numeric(group["longitude"], errors="coerce")
        geocoded = lat.notna() & lon.notna()
        parsed_dates = pd.to_datetime(group["sample_date"], errors="coerce")
        valid_dates = parsed_dates.dropna()
        outputs["cohorts"].setdefault(str(cohort), {})
        outputs["cohorts"][str(cohort)].update(
            {
                "metadata_records": int(len(group)),
                "unique_dogs": int(group["dog_id"].nunique()),
                "date_min": valid_dates.min().date().isoformat() if len(valid_dates) else None,
                "date_max": valid_dates.max().date().isoformat() if len(valid_dates) else None,
                "geocoded_rate": round(float(geocoded.mean()) if len(group) else 0.0, 6),
            }
        )

    metrics_path = PROJECT_ROOT / "data" / "processed" / "metrics_test_v2.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        outputs["baseline_metrics"] = {
            "model": metrics.get("model"),
            "prauc_macro": metrics.get("prauc_macro"),
            "n_labels": metrics.get("n_labels"),
        }

    rows = []
    for cohort, values in outputs["cohorts"].items():
        row = {"cohort": cohort}
        row.update(values)
        rows.append(row)
    COHORT_COMPARISON_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(COHORT_COMPARISON_CSV, index=False)
    COHORT_COMPARISON_JSON.write_text(
        json.dumps(outputs, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return outputs


def run_new_gates(project_root: Path = PROJECT_ROOT) -> dict[str, dict[str, Any]]:
    gate_specs = [
        ("gate_cohort_manifest_v1.json", run_cohort_manifest_gate),
        ("gate_metadata_retention_v1.json", run_metadata_retention_gate),
        ("gate_dog_leakage_v1.json", run_dog_leakage_gate),
        ("gate_geocoding_quality_v1.json", run_geocoding_quality_gate),
    ]
    reports: dict[str, dict[str, Any]] = {}
    for filename, gate_fn in gate_specs:
        report = gate_fn(project_root)
        write_gate_report(report, project_root / "outputs" / filename)
        reports[report["gate"]] = report
    return reports


def main() -> int:
    manifest = build_ingestion_manifest(PROJECT_ROOT)
    metadata = build_analysis_metadata(PROJECT_ROOT)
    comparison = build_cohort_comparison(manifest, metadata)
    reports = run_new_gates(PROJECT_ROOT)

    print("Research audit generado:")
    print(f"  PDFs manifestados: {len(manifest)}")
    print(f"  Metadata registros: {len(metadata)}")
    print(f"  Cohortes: {', '.join(sorted(comparison['cohorts']))}")
    for name, report in reports.items():
        print(f"  {name}: {report.get('status')}")
    if reports.get("dog_leakage_v1", {}).get("status") == "fail":
        print("  Nota: dog_leakage_v1 fallo; revisar split agrupado por dog_id antes de reentrenar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
