"""Gates de gobernanza para paridad de features y auditoria de leakage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite, sqrt
from pathlib import Path

import pandas as pd

from .features import build_features

FORBIDDEN_FEATURE_COLUMNS = {
    "record_uuid",
    "patient_name",
    "pet_owner",
    "attending_vet",
    "clinic",
    "pdf_filename",
    "page_number",
    "idexx_comments",
    "sample_date",
    "date_receipt",
    "date_result",
    "source_dataset",
    "split",
}

FORBIDDEN_PREFIXES = ("QC_", "PATRON_")
FORBIDDEN_STARTSWITH = ("morph_",)
FORBIDDEN_SUFFIXES = ("_flag",)


@dataclass
class GateCheck:
    """Resultado de un check individual dentro de un gate report."""

    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
        }


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Calcula SHA-256 de un archivo de forma incremental."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _add_check(
    checks: list[GateCheck],
    *,
    name: str,
    passed: bool,
    ok_detail: str,
    fail_detail: str,
) -> None:
    checks.append(
        GateCheck(
            name=name,
            passed=passed,
            detail=ok_detail if passed else fail_detail,
        )
    )


def _build_report(
    gate_name: str, checks: list[GateCheck], extra: dict | None = None
) -> dict:
    passed_count = sum(1 for check in checks if check.passed)
    failed_count = len(checks) - passed_count
    status = "pass" if failed_count == 0 else "fail"

    report = {
        "gate": gate_name,
        "status": status,
        "checked_at": _utc_now_iso(),
        "checks": [check.to_dict() for check in checks],
        "summary": {
            "total_checks": len(checks),
            "passed_checks": passed_count,
            "failed_checks": failed_count,
        },
    }

    if extra:
        report.update(extra)

    return report


def _read_csv_columns(path: Path) -> list[str]:
    return list(pd.read_csv(path, nrows=0).columns)


def _load_feature_columns(path: Path) -> list[str]:
    doc = _read_json(path)
    cols = doc.get("feature_columns")
    if not isinstance(cols, list):
        raise ValueError("feature_columns.json must include feature_columns as a list")
    return [str(col) for col in cols]


def _load_medians(path: Path) -> tuple[dict[str, float], pd.DataFrame]:
    medians_df = pd.read_csv(path)
    required_cols = {"feature", "mediana_train"}
    if not required_cols.issubset(medians_df.columns):
        raise ValueError(
            "imputer_medians.csv must contain feature and mediana_train columns"
        )

    medians: dict[str, float] = {}
    for _, row in medians_df.iterrows():
        feature = str(row["feature"])
        try:
            medians[feature] = float(row["mediana_train"])
        except Exception:
            medians[feature] = float("nan")

    return medians, medians_df


def _duplicates(items: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for item in items:
        if item in seen:
            dupes.add(item)
        seen.add(item)
    return sorted(dupes)


def write_gate_report(report: dict, output_path: Path) -> None:
    """Guarda el gate report como JSON formateado."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_feature_parity_gate(project_root: Path) -> dict:
    """Valida la paridad train-serving del contrato de features y artefactos runtime."""
    checks: list[GateCheck] = []
    required_files = [
        "data/processed/feature_columns.json",
        "models/model_metadata_v2.json",
        "data/processed/imputer_medians.csv",
        "data/processed/train.csv",
        "data/processed/val.csv",
        "data/processed/test.csv",
    ]

    missing = [rel for rel in required_files if not (project_root / rel).exists()]
    _add_check(
        checks,
        name="Artefactos requeridos disponibles",
        passed=len(missing) == 0,
        ok_detail="Todos los artefactos de entrada para paridad estan presentes.",
        fail_detail=f"Faltan artefactos requeridos: {missing}",
    )

    if missing:
        return _build_report(
            "feature_parity_v2",
            checks,
            {
                "n_features": 0,
                "feature_columns": [],
            },
        )

    feature_columns_path = project_root / "data" / "processed" / "feature_columns.json"
    model_metadata_path = project_root / "models" / "model_metadata_v2.json"
    medians_path = project_root / "data" / "processed" / "imputer_medians.csv"

    feature_doc = _read_json(feature_columns_path)
    model_doc = _read_json(model_metadata_path)
    feature_columns = _load_feature_columns(feature_columns_path)
    model_columns = [str(col) for col in model_doc.get("feature_columns", [])]
    medians, _ = _load_medians(medians_path)

    duplicated = _duplicates(feature_columns)
    _add_check(
        checks,
        name="Lista de features sin duplicados",
        passed=len(duplicated) == 0,
        ok_detail=f"La lista de features es unica ({len(feature_columns)} columnas).",
        fail_detail=f"Se encontraron nombres de features duplicados: {duplicated}",
    )

    feature_doc_n = feature_doc.get("n_features")
    _add_check(
        checks,
        name="feature_columns.json coincide con longitud real",
        passed=feature_doc_n == len(feature_columns),
        ok_detail=f"feature_columns.json reporta n_features={feature_doc_n} y coincide con la lista.",
        fail_detail=(
            "feature_columns.json n_features no coincide con la longitud real de la lista "
            f"({feature_doc_n} vs {len(feature_columns)})."
        ),
    )

    model_doc_n = model_doc.get("n_features")
    _add_check(
        checks,
        name="model_metadata_v2 coincide con longitud real",
        passed=model_doc_n == len(model_columns),
        ok_detail=f"model_metadata_v2.json reporta n_features={model_doc_n} y coincide con la lista.",
        fail_detail=(
            "model_metadata_v2.json n_features no coincide con su lista de features "
            f"({model_doc_n} vs {len(model_columns)})."
        ),
    )

    _add_check(
        checks,
        name="Paridad de orden de features (notebook vs runtime)",
        passed=feature_columns == model_columns,
        ok_detail="feature_columns.json y model_metadata_v2.json tienen el mismo orden de features.",
        fail_detail="Hay desajuste de orden entre feature_columns.json y model_metadata_v2.json.",
    )

    missing_medians = sorted(set(feature_columns) - set(medians))
    extra_medians = sorted(set(medians) - set(feature_columns))
    _add_check(
        checks,
        name="Medians del imputer cubren contrato exacto",
        passed=(len(missing_medians) == 0 and len(extra_medians) == 0),
        ok_detail="imputer_medians.csv incluye exactamente los mismos nombres de features.",
        fail_detail=(
            "imputer_medians.csv tiene desajuste de features. "
            f"Faltantes en medians: {missing_medians}. Extras en medians: {extra_medians}."
        ),
    )

    feature_row = build_features({}, feature_columns, medians)
    runtime_shape_ok = feature_row.shape == (1, len(feature_columns))
    runtime_order_ok = list(feature_row.columns) == feature_columns
    _add_check(
        checks,
        name="build_features runtime respeta contrato",
        passed=runtime_shape_ok and runtime_order_ok,
        ok_detail="build_features retorna una fila con shape esperado y orden exacto de columnas.",
        fail_detail=(
            "El output de build_features no coincide con el contrato de features. "
            f"shape={feature_row.shape}, expected=(1, {len(feature_columns)}). "
            "Se detecto desajuste en el orden de columnas."
        ),
    )

    split_missing: dict[str, list[str]] = {}
    for split_name in ("train", "val", "test"):
        split_path = project_root / "data" / "processed" / f"{split_name}.csv"
        split_cols = _read_csv_columns(split_path)
        split_missing[split_name] = [
            col for col in feature_columns if col not in split_cols
        ]

    missing_summary = {k: v for k, v in split_missing.items() if v}
    _add_check(
        checks,
        name="Todos los splits contienen contrato completo",
        passed=len(missing_summary) == 0,
        ok_detail="Los headers de train/val/test contienen cada feature del contrato.",
        fail_detail=f"Columnas de features faltantes por split: {missing_summary}",
    )

    return _build_report(
        "feature_parity_v2",
        checks,
        {
            "n_features": len(feature_columns),
            "feature_columns": feature_columns,
        },
    )


def run_leakage_gate(project_root: Path) -> dict:
    """Audita el contrato de features para riesgos de leakage directo y por proxy."""
    checks: list[GateCheck] = []
    required_files = [
        "data/processed/feature_columns.json",
        "data/processed/final_label_policy.json",
        "data/processed/imputer_medians.csv",
        "data/processed/train.csv",
        "data/processed/val.csv",
        "data/processed/test.csv",
    ]

    missing = [rel for rel in required_files if not (project_root / rel).exists()]
    _add_check(
        checks,
        name="Artefactos requeridos disponibles",
        passed=len(missing) == 0,
        ok_detail="Todos los artefactos de entrada para leakage audit estan presentes.",
        fail_detail=f"Faltan artefactos requeridos: {missing}",
    )

    if missing:
        return _build_report(
            "leakage_audit_v2", checks, {"n_features": 0, "n_labels": 0}
        )

    feature_columns = _load_feature_columns(
        project_root / "data" / "processed" / "feature_columns.json"
    )
    policy = _read_json(project_root / "data" / "processed" / "final_label_policy.json")
    medians, _ = _load_medians(
        project_root / "data" / "processed" / "imputer_medians.csv"
    )

    train_df = pd.read_csv(project_root / "data" / "processed" / "train.csv")
    val_df = pd.read_csv(project_root / "data" / "processed" / "val.csv")
    test_df = pd.read_csv(project_root / "data" / "processed" / "test.csv")

    forbidden_present = sorted(set(feature_columns) & FORBIDDEN_FEATURE_COLUMNS)
    _add_check(
        checks,
        name="Columnas prohibidas de leakage ausentes",
        passed=len(forbidden_present) == 0,
        ok_detail="No hay columnas de leakage directo ni metadata-only en el feature set.",
        fail_detail=f"Columnas prohibidas presentes en el feature set: {forbidden_present}",
    )

    forbidden_suffix = sorted(
        col for col in feature_columns if col.endswith(FORBIDDEN_SUFFIXES)
    )
    _add_check(
        checks,
        name="Columnas _flag del analizador ausentes",
        passed=len(forbidden_suffix) == 0,
        ok_detail="No se encontraron columnas del analizador terminadas en _flag.",
        fail_detail=f"Se detectaron candidatos de leakage por _flag: {forbidden_suffix}",
    )

    forbidden_morph = sorted(
        col for col in feature_columns if col.startswith(FORBIDDEN_STARTSWITH)
    )
    _add_check(
        checks,
        name="Columnas de morfologia externa ausentes",
        passed=len(forbidden_morph) == 0,
        ok_detail="No se encontraron columnas de morfologia DAP-only en training features.",
        fail_detail=f"Se detectaron candidatos de leakage por morfologia DAP: {forbidden_morph}",
    )

    label_set: set[str] = set()
    for key in (
        "official_model_labels",
        "rule_labels",
        "excluded_labels",
        "official_labels",
        "all_labels",
    ):
        vals = policy.get(key, [])
        if isinstance(vals, list):
            label_set.update(str(val) for val in vals)

    label_details = policy.get("label_details")
    if isinstance(label_details, dict):
        label_set.update(str(label) for label in label_details.keys())

    feature_label_intersection = sorted(set(feature_columns) & label_set)
    _add_check(
        checks,
        name="Ninguna etiqueta se reutiliza como feature",
        passed=len(feature_label_intersection) == 0,
        ok_detail="Ninguna columna de etiqueta official/rule/excluded aparece en el contrato de features.",
        fail_detail=f"Se detecto leakage por reutilizar etiquetas como features: {feature_label_intersection}",
    )

    target_like_names = sorted(
        col for col in feature_columns if col.startswith(FORBIDDEN_PREFIXES)
    )
    _add_check(
        checks,
        name="Sin nombres de feature tipo target",
        passed=len(target_like_names) == 0,
        ok_detail="Los nombres de features no usan prefijos target QC_/PATRON_.",
        fail_detail=f"Se detectaron nombres de feature parecidos a targets: {target_like_names}",
    )

    missing_split_cols = [col for col in feature_columns if col not in train_df.columns]
    _add_check(
        checks,
        name="Train split contiene todas las features",
        passed=len(missing_split_cols) == 0,
        ok_detail="Todas las columnas de features existen en train.csv.",
        fail_detail=f"Faltan columnas de features en train.csv: {missing_split_cols}",
    )

    non_numeric_features: list[str] = []
    for feature in feature_columns:
        if feature not in train_df.columns:
            continue
        numeric_view = pd.to_numeric(train_df[feature], errors="coerce")
        if numeric_view.isna().all():
            non_numeric_features.append(feature)

    _add_check(
        checks,
        name="Todas las features son numericas en train",
        passed=len(non_numeric_features) == 0,
        ok_detail="Cada feature puede interpretarse como numerica en train.csv.",
        fail_detail=f"Se detectaron columnas de features no numericas: {non_numeric_features}",
    )

    missing_medians = sorted(set(feature_columns) - set(medians))
    extra_medians = sorted(set(medians) - set(feature_columns))

    train_numeric = train_df.copy()
    for feature in feature_columns:
        if feature in train_numeric.columns:
            train_numeric[feature] = pd.to_numeric(
                train_numeric[feature], errors="coerce"
            )

    median_mismatch: dict[str, float] = {}
    for feature in feature_columns:
        if feature not in train_numeric.columns or feature not in medians:
            continue
        train_median = train_numeric[feature].median(skipna=True)
        if pd.isna(train_median):
            continue
        diff = abs(float(train_median) - float(medians[feature]))
        if diff > 1e-9:
            median_mismatch[feature] = diff

    _add_check(
        checks,
        name="Medians del imputer alineadas a train",
        passed=(
            len(missing_medians) == 0
            and len(extra_medians) == 0
            and len(median_mismatch) == 0
        ),
        ok_detail="imputer_medians.csv coincide con las medianas de train para todas las features numericas.",
        fail_detail=(
            "Se detecto desajuste en medians. "
            f"Faltantes en medians: {missing_medians}. Extras en medians: {extra_medians}. "
            f"Diferencias numericas (>1e-9): {median_mismatch}"
        ),
    )

    temporal_ok = False
    temporal_detail = "Faltan columnas del split temporal."
    if all("sample_date" in df.columns for df in (train_df, val_df, test_df)):
        train_max = pd.to_datetime(train_df["sample_date"], errors="coerce").max()
        val_min = pd.to_datetime(val_df["sample_date"], errors="coerce").min()
        val_max = pd.to_datetime(val_df["sample_date"], errors="coerce").max()
        test_min = pd.to_datetime(test_df["sample_date"], errors="coerce").min()

        temporal_ok = bool(val_min >= train_max and test_min >= val_max)
        temporal_detail = f"train_max={train_max}, val_min={val_min}, val_max={val_max}, test_min={test_min}"

    _add_check(
        checks,
        name="Split temporal sin solapamiento",
        passed=temporal_ok,
        ok_detail=f"Temporal split check OK ({temporal_detail}).",
        fail_detail=f"Se detecto solapamiento temporal ({temporal_detail}).",
    )

    present_labels = [label for label in sorted(label_set) if label in train_df.columns]
    label_echo_pairs: list[tuple[str, str]] = []
    label_inverse_pairs: list[tuple[str, str]] = []

    for label in present_labels:
        y_series = pd.to_numeric(train_df[label], errors="coerce")
        if y_series.isna().any() or y_series.nunique(dropna=True) < 2:
            continue

        for feature in feature_columns:
            if feature not in train_df.columns:
                continue
            x_series = pd.to_numeric(train_df[feature], errors="coerce")
            if x_series.isna().any() or x_series.nunique(dropna=True) < 2:
                continue

            if bool((x_series == y_series).all()):
                label_echo_pairs.append((feature, label))

            is_binary_x = set(x_series.unique()) <= {0.0, 1.0}
            is_binary_y = set(y_series.unique()) <= {0.0, 1.0}
            if (
                is_binary_x
                and is_binary_y
                and bool((x_series == (1.0 - y_series)).all())
            ):
                label_inverse_pairs.append((feature, label))

    _add_check(
        checks,
        name="Ningun feature replica una etiqueta",
        passed=(len(label_echo_pairs) == 0 and len(label_inverse_pairs) == 0),
        ok_detail="No se encontro label-echo directo ni proxy inverso de etiquetas en train features.",
        fail_detail=(
            "Se detecto posible target leakage via proxy deterministico. "
            f"Pares echo: {label_echo_pairs}. Pares inversos: {label_inverse_pairs}."
        ),
    )

    return _build_report(
        "leakage_audit_v2",
        checks,
        {
            "n_features": len(feature_columns),
            "n_labels": len(label_set),
            "evaluated_label_columns": present_labels,
        },
    )


def run_manifest_integrity_gate(project_root: Path) -> dict:
    """Valida integridad del artifact_manifest_v2 por existencia y checksum SHA-256."""
    checks: list[GateCheck] = []
    manifest_path = project_root / "data" / "processed" / "artifact_manifest_v2.json"

    _add_check(
        checks,
        name="Manifiesto de artefactos presente",
        passed=manifest_path.exists(),
        ok_detail="artifact_manifest_v2.json esta disponible.",
        fail_detail="No se encontro data/processed/artifact_manifest_v2.json.",
    )

    if not manifest_path.exists():
        return _build_report(
            "artifact_manifest_integrity_v2",
            checks,
            {"verified_entries": 0, "missing_entries": [], "checksum_mismatches": []},
        )

    manifest = _read_json(manifest_path)
    runtime_entries = manifest.get("runtime_artifacts", [])
    support_entries = manifest.get("support_artifacts", [])

    _add_check(
        checks,
        name="Manifiesto contiene runtime_artifacts",
        passed=isinstance(runtime_entries, list) and len(runtime_entries) > 0,
        ok_detail=f"runtime_artifacts contiene {len(runtime_entries)} entradas.",
        fail_detail="runtime_artifacts no existe o esta vacio.",
    )
    _add_check(
        checks,
        name="Manifiesto contiene support_artifacts",
        passed=isinstance(support_entries, list) and len(support_entries) > 0,
        ok_detail=f"support_artifacts contiene {len(support_entries)} entradas.",
        fail_detail="support_artifacts no existe o esta vacio.",
    )

    entries: list[dict] = []
    if isinstance(runtime_entries, list):
        entries.extend(runtime_entries)
    if isinstance(support_entries, list):
        entries.extend(support_entries)

    malformed_entries: list[str] = []
    missing_entries: list[str] = []
    checksum_mismatches: list[dict] = []
    verified = 0

    for entry in entries:
        path = entry.get("path")
        expected_sha = entry.get("sha256")
        if not path or not expected_sha:
            malformed_entries.append(str(entry))
            continue

        abs_path = project_root / str(path)
        if not abs_path.exists():
            missing_entries.append(str(path))
            continue

        actual_sha = _sha256_file(abs_path)
        if actual_sha != expected_sha:
            checksum_mismatches.append(
                {
                    "path": str(path),
                    "expected_sha256": expected_sha,
                    "actual_sha256": actual_sha,
                }
            )
            continue

        verified += 1

    _add_check(
        checks,
        name="Entradas del manifiesto bien formadas",
        passed=len(malformed_entries) == 0,
        ok_detail="Todas las entradas tienen path y sha256.",
        fail_detail=f"Entradas malformed detectadas: {malformed_entries}",
    )

    _add_check(
        checks,
        name="Artefactos del manifiesto existen en disco",
        passed=len(missing_entries) == 0,
        ok_detail="Todos los artefactos declarados existen.",
        fail_detail=f"Faltan artefactos declarados en manifiesto: {missing_entries}",
    )

    _add_check(
        checks,
        name="Checksums SHA-256 validos",
        passed=len(checksum_mismatches) == 0,
        ok_detail="Todos los checksums coinciden con el manifiesto.",
        fail_detail=f"Se detectaron mismatches SHA-256: {checksum_mismatches}",
    )

    return _build_report(
        "artifact_manifest_integrity_v2",
        checks,
        {
            "manifest_version": manifest.get("version"),
            "verified_entries": verified,
            "total_entries": len(entries),
            "missing_entries": missing_entries,
            "checksum_mismatches": checksum_mismatches,
        },
    )


def run_policy_freeze_gate(project_root: Path) -> dict:
    """Valida consistencia entre politica oficial, thresholds y freeze documentado."""
    checks: list[GateCheck] = []
    required_files = {
        "policy": "data/processed/final_label_policy.json",
        "thresholds": "data/processed/decision_thresholds_v2.json",
        "metadata": "models/model_metadata_v2.json",
        "preregistered": "data/processed/policy_preregistered_v3.json",
        "freeze": "data/processed/policy_freeze_v3.json",
    }

    missing = [
        rel for rel in required_files.values() if not (project_root / rel).exists()
    ]
    _add_check(
        checks,
        name="Artefactos de policy freeze presentes",
        passed=len(missing) == 0,
        ok_detail="Politica, thresholds, metadata y freeze v3 estan disponibles.",
        fail_detail=f"Faltan artefactos de policy freeze: {missing}",
    )

    if missing:
        return _build_report(
            "policy_freeze_v3",
            checks,
            {
                "policy_version": None,
                "thresholds_version": None,
                "official_labels": [],
                "missing_files": missing,
            },
        )

    policy_path = project_root / required_files["policy"]
    thresholds_path = project_root / required_files["thresholds"]
    metadata_path = project_root / required_files["metadata"]
    prereg_path = project_root / required_files["preregistered"]
    freeze_path = project_root / required_files["freeze"]

    policy_doc = _read_json(policy_path)
    thresholds_doc = _read_json(thresholds_path)
    metadata_doc = _read_json(metadata_path)
    prereg_doc = _read_json(prereg_path)
    freeze_doc = _read_json(freeze_path)

    policy_version = str(policy_doc.get("version", "unknown"))
    metadata_policy_version = str(metadata_doc.get("label_policy_version", "unknown"))

    _add_check(
        checks,
        name="Version de politica alineada con model_metadata",
        passed=policy_version == metadata_policy_version,
        ok_detail=(
            "model_metadata_v2.json y final_label_policy.json declaran la misma version "
            f"({policy_version})."
        ),
        fail_detail=(
            "Desalineacion de version de politica entre metadata y politica: "
            f"metadata={metadata_policy_version}, policy={policy_version}."
        ),
    )

    thresholds_source = str(thresholds_doc.get("source_split", "")).lower()
    _add_check(
        checks,
        name="Thresholds congelados en validation",
        passed=thresholds_source == "val",
        ok_detail="decision_thresholds_v2.json declara source_split=val.",
        fail_detail=f"source_split invalido para freeze: {thresholds_source}. Debe ser 'val'.",
    )

    official_labels = [
        str(label) for label in policy_doc.get("official_model_labels", [])
    ]
    threshold_map = thresholds_doc.get("thresholds", {})
    missing_thresholds = sorted(
        label for label in official_labels if label not in threshold_map
    )
    _add_check(
        checks,
        name="Thresholds cubren todas las etiquetas oficiales",
        passed=len(missing_thresholds) == 0,
        ok_detail=f"Thresholds cubren {len(official_labels)} etiquetas oficiales.",
        fail_detail=f"Faltan thresholds para etiquetas oficiales: {missing_thresholds}",
    )

    excluded_labels = [str(label) for label in policy_doc.get("excluded_labels", [])]
    excluded_not_frozen: dict[str, float] = {}
    for label in excluded_labels:
        value = threshold_map.get(label)
        if value is None:
            excluded_not_frozen[label] = float("nan")
            continue
        if abs(float(value) - 1.0) > 1e-12:
            excluded_not_frozen[label] = float(value)

    _add_check(
        checks,
        name="Etiquetas excluidas congeladas en 1.0",
        passed=len(excluded_not_frozen) == 0,
        ok_detail="Todas las etiquetas excluidas estan congeladas en threshold=1.0.",
        fail_detail=f"Etiquetas excluidas sin freeze correcto: {excluded_not_frozen}",
    )

    prereg_required_keys = {
        "official_labels",
        "qc_rules",
        "excluded_labels",
        "threshold_objectives",
        "clinical_acceptance",
    }
    missing_prereg_keys = sorted(prereg_required_keys - set(prereg_doc.keys()))
    _add_check(
        checks,
        name="Politica pre-registrada contiene secciones obligatorias",
        passed=len(missing_prereg_keys) == 0,
        ok_detail="policy_preregistered_v3.json incluye objetivos, reglas QC y aceptacion clinica.",
        fail_detail=f"Faltan secciones en policy_preregistered_v3.json: {missing_prereg_keys}",
    )

    prereg_official = sorted(
        str(label) for label in prereg_doc.get("official_labels", [])
    )
    _add_check(
        checks,
        name="Politica pre-registrada alinea etiquetas oficiales",
        passed=sorted(official_labels) == prereg_official,
        ok_detail="official_labels pre-registradas coinciden con la politica oficial runtime.",
        fail_detail=(
            "official_labels en pre-registro no coinciden con final_label_policy.json. "
            f"policy={sorted(official_labels)}, prereg={prereg_official}."
        ),
    )

    policy_sha = _sha256_file(policy_path)
    thresholds_sha = _sha256_file(thresholds_path)
    freeze_policy_sha = str(freeze_doc.get("policy_sha256", ""))
    freeze_thresholds_sha = str(freeze_doc.get("thresholds_sha256", ""))

    freeze_hash_ok = (
        freeze_policy_sha == policy_sha and freeze_thresholds_sha == thresholds_sha
    )
    _add_check(
        checks,
        name="Archivo de freeze referencia hashes actuales",
        passed=freeze_hash_ok,
        ok_detail="policy_freeze_v3.json coincide con hashes actuales de policy y thresholds.",
        fail_detail=(
            "policy_freeze_v3.json no coincide con hashes actuales. "
            f"policy expected={policy_sha}, freeze={freeze_policy_sha}; "
            f"thresholds expected={thresholds_sha}, freeze={freeze_thresholds_sha}."
        ),
    )

    return _build_report(
        "policy_freeze_v3",
        checks,
        {
            "policy_version": policy_version,
            "thresholds_version": thresholds_doc.get("version"),
            "official_labels": official_labels,
            "policy_sha256": policy_sha,
            "thresholds_sha256": thresholds_sha,
            "freeze_file": str(freeze_path.relative_to(project_root)),
        },
    )


def _cohen_d(a: pd.Series, b: pd.Series) -> float:
    """Calcula el efecto estandarizado de diferencia de medias (Cohen's d)."""
    a_clean = pd.to_numeric(a, errors="coerce").dropna()
    b_clean = pd.to_numeric(b, errors="coerce").dropna()

    if len(a_clean) < 2 or len(b_clean) < 2:
        return float("nan")

    var_a = float(a_clean.var(ddof=1))
    var_b = float(b_clean.var(ddof=1))
    pooled = sqrt(max((var_a + var_b) / 2.0, 0.0))

    if pooled <= 1e-12:
        return (
            0.0
            if abs(float(a_clean.mean()) - float(b_clean.mean())) <= 1e-12
            else float("inf")
        )

    return float((a_clean.mean() - b_clean.mean()) / pooled)


def run_basic_drift_gate(project_root: Path) -> dict:
    """Evalua drift estadistico basico entre train/val/test sobre features oficiales."""
    checks: list[GateCheck] = []
    required_files = [
        "data/processed/feature_columns.json",
        "data/processed/train.csv",
        "data/processed/val.csv",
        "data/processed/test.csv",
    ]

    missing = [rel for rel in required_files if not (project_root / rel).exists()]
    _add_check(
        checks,
        name="Artefactos requeridos para drift disponibles",
        passed=len(missing) == 0,
        ok_detail="feature_columns y splits train/val/test estan disponibles.",
        fail_detail=f"Faltan artefactos para drift gate: {missing}",
    )

    if missing:
        return _build_report(
            "basic_drift_v3",
            checks,
            {
                "evaluated_features": 0,
                "severe_drift_test": [],
                "severe_drift_val": [],
                "missing_files": missing,
            },
        )

    feature_columns = _load_feature_columns(
        project_root / "data" / "processed" / "feature_columns.json"
    )
    train_df = pd.read_csv(project_root / "data" / "processed" / "train.csv")
    val_df = pd.read_csv(project_root / "data" / "processed" / "val.csv")
    test_df = pd.read_csv(project_root / "data" / "processed" / "test.csv")

    missing_cols = [
        col
        for col in feature_columns
        if col not in train_df.columns
        or col not in val_df.columns
        or col not in test_df.columns
    ]
    _add_check(
        checks,
        name="Splits contienen todas las columnas de features",
        passed=len(missing_cols) == 0,
        ok_detail="train/val/test incluyen todas las columnas del contrato de features.",
        fail_detail=f"Columnas ausentes en algun split: {missing_cols}",
    )

    if missing_cols:
        return _build_report(
            "basic_drift_v3",
            checks,
            {
                "evaluated_features": 0,
                "severe_drift_test": [],
                "severe_drift_val": [],
                "missing_columns": missing_cols,
            },
        )

    drift_rows: list[dict] = []
    for feature in feature_columns:
        d_val = _cohen_d(train_df[feature], val_df[feature])
        d_test = _cohen_d(train_df[feature], test_df[feature])
        if not isfinite(d_val) or not isfinite(d_test):
            continue
        drift_rows.append(
            {
                "feature": feature,
                "abs_d_val": abs(float(d_val)),
                "abs_d_test": abs(float(d_test)),
            }
        )

    _add_check(
        checks,
        name="Cantidad minima de features evaluadas",
        passed=len(drift_rows)
        >= min(len(feature_columns), max(10, len(feature_columns) // 3)),
        ok_detail=f"Se evaluaron {len(drift_rows)} features con datos numericos validos.",
        fail_detail=(
            "Features evaluadas insuficientes para inferir drift robusto. "
            f"evaluadas={len(drift_rows)}, contrato={len(feature_columns)}."
        ),
    )

    severe_drift_val = sorted(
        row["feature"] for row in drift_rows if row["abs_d_val"] >= 1.0
    )
    severe_drift_test = sorted(
        row["feature"] for row in drift_rows if row["abs_d_test"] >= 1.0
    )

    _add_check(
        checks,
        name="Drift severo controlado en validation",
        passed=len(severe_drift_val) <= 8,
        ok_detail=f"Drift severo en validation dentro de tolerancia ({len(severe_drift_val)} features).",
        fail_detail=(
            "Drift severo excesivo en validation. " f"features={severe_drift_val}"
        ),
    )

    _add_check(
        checks,
        name="Drift severo controlado en test",
        passed=len(severe_drift_test) <= 10,
        ok_detail=f"Drift severo en test dentro de tolerancia ({len(severe_drift_test)} features).",
        fail_detail=("Drift severo excesivo en test. " f"features={severe_drift_test}"),
    )

    avg_abs_d_val = (
        sum(row["abs_d_val"] for row in drift_rows) / len(drift_rows)
        if drift_rows
        else float("inf")
    )
    avg_abs_d_test = (
        sum(row["abs_d_test"] for row in drift_rows) / len(drift_rows)
        if drift_rows
        else float("inf")
    )

    _add_check(
        checks,
        name="Drift promedio global bajo umbral operativo",
        passed=avg_abs_d_val <= 0.80 and avg_abs_d_test <= 0.95,
        ok_detail=(
            "Drift promedio de train->val/test dentro de umbral. "
            f"avg_val={avg_abs_d_val:.3f}, avg_test={avg_abs_d_test:.3f}."
        ),
        fail_detail=(
            "Drift promedio excede umbral operativo. "
            f"avg_val={avg_abs_d_val:.3f}, avg_test={avg_abs_d_test:.3f}."
        ),
    )

    top_test_drift = sorted(
        drift_rows,
        key=lambda row: row["abs_d_test"],
        reverse=True,
    )[:10]

    return _build_report(
        "basic_drift_v3",
        checks,
        {
            "evaluated_features": len(drift_rows),
            "severe_drift_val": severe_drift_val,
            "severe_drift_test": severe_drift_test,
            "avg_abs_d_val": (
                round(avg_abs_d_val, 6) if isfinite(avg_abs_d_val) else None
            ),
            "avg_abs_d_test": (
                round(avg_abs_d_test, 6) if isfinite(avg_abs_d_test) else None
            ),
            "top_test_drift": top_test_drift,
        },
    )


def run_cohort_manifest_gate(project_root: Path) -> dict:
    """Valida que el manifiesto de PDFs preserve cohortes y rutas sin colisiones."""
    checks: list[GateCheck] = []
    manifest_path = project_root / "data" / "processed" / "ingestion_manifest.csv"

    _add_check(
        checks,
        name="Manifest de ingesta disponible",
        passed=manifest_path.exists(),
        ok_detail="ingestion_manifest.csv esta disponible.",
        fail_detail="No se encontro data/processed/ingestion_manifest.csv.",
    )
    if not manifest_path.exists():
        return _build_report("cohort_manifest_v1", checks, {"total_files": 0})

    manifest = pd.read_csv(manifest_path)
    required = {
        "source_relative_path",
        "original_filename",
        "file_hash",
        "ingestion_cohort",
        "batch_folder",
    }
    missing_cols = sorted(required - set(manifest.columns))
    _add_check(
        checks,
        name="Columnas obligatorias presentes",
        passed=len(missing_cols) == 0,
        ok_detail="El manifiesto incluye rutas, hashes y cohorte.",
        fail_detail=f"Faltan columnas obligatorias: {missing_cols}",
    )
    if missing_cols:
        return _build_report(
            "cohort_manifest_v1", checks, {"total_files": len(manifest)}
        )

    duplicate_paths = int(manifest["source_relative_path"].duplicated().sum())
    _add_check(
        checks,
        name="Rutas relativas unicas",
        passed=duplicate_paths == 0,
        ok_detail="Cada PDF tiene una ruta relativa unica.",
        fail_detail=f"Se detectaron {duplicate_paths} rutas relativas duplicadas.",
    )

    hash_values = manifest["file_hash"].fillna("").astype(str)
    empty_hashes = int((hash_values.str.len() < 32).sum())
    _add_check(
        checks,
        name="Hashes de archivo disponibles",
        passed=empty_hashes == 0,
        ok_detail="Todos los PDFs tienen hash SHA-256.",
        fail_detail=f"Hay {empty_hashes} filas sin hash valido.",
    )

    cohort_counts = manifest["ingestion_cohort"].value_counts().to_dict()
    dic_may_n = int(cohort_counts.get("dic_may_2026", 0))
    baseline_n = int(cohort_counts.get("baseline_historico", 0))
    _add_check(
        checks,
        name="Cohorte Dic-May detectada",
        passed=dic_may_n > 0,
        ok_detail=f"Dic-May contiene {dic_may_n} PDFs.",
        fail_detail="No se detectaron PDFs de la cohorte dic_may_2026.",
    )
    _add_check(
        checks,
        name="Cohorte historica detectada",
        passed=baseline_n > 0,
        ok_detail=f"Baseline historico contiene {baseline_n} PDFs.",
        fail_detail="No se detectaron PDFs de baseline_historico.",
    )

    duplicate_names = int(manifest["original_filename"].duplicated().sum())
    return _build_report(
        "cohort_manifest_v1",
        checks,
        {
            "total_files": int(len(manifest)),
            "cohort_counts": {str(k): int(v) for k, v in cohort_counts.items()},
            "duplicate_original_filenames": duplicate_names,
        },
    )


def run_metadata_retention_gate(project_root: Path) -> dict:
    """Valida que la metadata longitudinal/geografica exista fuera del feature set."""
    checks: list[GateCheck] = []
    metadata_path = project_root / "data" / "processed" / "analysis_metadata.csv"
    features_path = project_root / "data" / "processed" / "feature_columns.json"

    missing_files = [
        str(path.relative_to(project_root))
        for path in (metadata_path, features_path)
        if not path.exists()
    ]
    _add_check(
        checks,
        name="Artefactos de metadata disponibles",
        passed=len(missing_files) == 0,
        ok_detail="analysis_metadata.csv y feature_columns.json estan disponibles.",
        fail_detail=f"Faltan artefactos de metadata: {missing_files}",
    )
    if missing_files:
        return _build_report("metadata_retention_v1", checks, {"metadata_rows": 0})

    metadata_df = pd.read_csv(metadata_path)
    feature_columns = set(_load_feature_columns(features_path))
    required_cols = {
        "record_id",
        "record_uuid",
        "dog_id",
        "source_dataset",
        "ingestion_cohort",
        "sample_date",
        "raw_location_text",
        "location_source",
        "location_confidence",
    }
    missing_cols = sorted(required_cols - set(metadata_df.columns))
    _add_check(
        checks,
        name="Columnas longitudinales/geograficas presentes",
        passed=len(missing_cols) == 0,
        ok_detail="La metadata preserva IDs, fecha, cohorte y ubicacion.",
        fail_detail=f"Faltan columnas en analysis_metadata.csv: {missing_cols}",
    )

    metadata_feature_overlap = sorted(required_cols & feature_columns)
    _add_check(
        checks,
        name="Metadata no entra al contrato de features",
        passed=len(metadata_feature_overlap) == 0,
        ok_detail="IDs, fechas y geografia estan fuera de feature_columns.",
        fail_detail=f"Metadata incluida como feature: {metadata_feature_overlap}",
    )

    idexx = (
        metadata_df[metadata_df.get("source_dataset", "") == "IDEXX"]
        if "source_dataset" in metadata_df
        else metadata_df
    )
    missing_dog_id = int(idexx.get("dog_id", pd.Series(dtype=object)).isna().sum())
    _add_check(
        checks,
        name="dog_id disponible para IDEXX",
        passed=len(idexx) > 0 and missing_dog_id == 0,
        ok_detail=f"dog_id disponible para {len(idexx)} registros IDEXX.",
        fail_detail=f"Registros IDEXX sin dog_id: {missing_dog_id}",
    )

    parsed_dates = pd.to_datetime(
        idexx.get("sample_date", pd.Series(dtype=object)), errors="coerce"
    )
    missing_dates = int(parsed_dates.isna().sum())
    _add_check(
        checks,
        name="sample_date parseable para IDEXX",
        passed=len(idexx) > 0 and missing_dates == 0,
        ok_detail="Todas las fechas IDEXX son parseables.",
        fail_detail=f"Fechas IDEXX invalidas o ausentes: {missing_dates}",
    )

    return _build_report(
        "metadata_retention_v1",
        checks,
        {
            "metadata_rows": int(len(metadata_df)),
            "idexx_rows": int(len(idexx)),
            "unique_dogs_idexx": (
                int(idexx["dog_id"].nunique()) if "dog_id" in idexx else 0
            ),
        },
    )


def run_dog_leakage_gate(project_root: Path) -> dict:
    """Audita si un mismo perro aparece en mas de un split supervisado."""
    checks: list[GateCheck] = []
    metadata_path = project_root / "data" / "processed" / "analysis_metadata.csv"
    split_paths = {
        "train": project_root / "data" / "processed" / "train.csv",
        "val": project_root / "data" / "processed" / "val.csv",
        "test": project_root / "data" / "processed" / "test.csv",
    }
    missing = [
        str(path.relative_to(project_root))
        for path in [metadata_path, *split_paths.values()]
        if not path.exists()
    ]
    _add_check(
        checks,
        name="Artefactos para leakage por perro disponibles",
        passed=len(missing) == 0,
        ok_detail="Metadata y splits estan disponibles.",
        fail_detail=f"Faltan artefactos: {missing}",
    )
    if missing:
        return _build_report("dog_leakage_v1", checks, {"dogs_crossing_splits": 0})

    metadata_df = pd.read_csv(metadata_path)
    if "record_uuid" not in metadata_df.columns or "dog_id" not in metadata_df.columns:
        _add_check(
            checks,
            name="Metadata contiene record_uuid y dog_id",
            passed=False,
            ok_detail="record_uuid y dog_id presentes.",
            fail_detail="analysis_metadata.csv debe incluir record_uuid y dog_id.",
        )
        return _build_report("dog_leakage_v1", checks, {"dogs_crossing_splits": 0})

    split_rows: list[pd.DataFrame] = []
    for split_name, path in split_paths.items():
        split_df = pd.read_csv(path, usecols=["record_uuid"])
        split_df["split"] = split_name
        split_rows.append(split_df)
    splits = pd.concat(split_rows, ignore_index=True)
    joined = splits.merge(
        metadata_df[["record_uuid", "dog_id"]], on="record_uuid", how="left"
    )

    missing_dog = int(joined["dog_id"].isna().sum())
    _add_check(
        checks,
        name="Todos los split records tienen dog_id",
        passed=missing_dog == 0,
        ok_detail="Cada registro de train/val/test se mapea a dog_id.",
        fail_detail=f"Registros de split sin dog_id: {missing_dog}",
    )

    dog_split_counts = (
        joined.dropna(subset=["dog_id"]).groupby("dog_id")["split"].nunique()
    )
    crossing = dog_split_counts[dog_split_counts > 1]
    _add_check(
        checks,
        name="Ningun dog_id cruza splits",
        passed=len(crossing) == 0,
        ok_detail="No se detecto fuga por perro entre train/val/test.",
        fail_detail=f"{len(crossing)} dog_id aparecen en mas de un split.",
    )

    top_crossing = (
        joined[joined["dog_id"].isin(crossing.index)]
        .groupby("dog_id")["split"]
        .apply(lambda values: ",".join(sorted(set(values))))
        .head(20)
        .to_dict()
    )

    return _build_report(
        "dog_leakage_v1",
        checks,
        {
            "split_records": int(len(joined)),
            "unique_dogs": int(joined["dog_id"].nunique(dropna=True)),
            "dogs_crossing_splits": int(len(crossing)),
            "top_crossing_dogs": {str(k): str(v) for k, v in top_crossing.items()},
        },
    )


def run_geocoding_quality_gate(project_root: Path) -> dict:
    """Audita cobertura geografica para vigilancia espacial reproducible."""
    checks: list[GateCheck] = []
    metadata_path = project_root / "data" / "processed" / "analysis_metadata.csv"
    _add_check(
        checks,
        name="Metadata geografica disponible",
        passed=metadata_path.exists(),
        ok_detail="analysis_metadata.csv esta disponible.",
        fail_detail="No se encontro data/processed/analysis_metadata.csv.",
    )
    if not metadata_path.exists():
        return _build_report("geocoding_quality_v1", checks, {"geocoded_rate": 0.0})

    metadata_df = pd.read_csv(metadata_path)
    idexx = (
        metadata_df[metadata_df.get("source_dataset", "") == "IDEXX"]
        if "source_dataset" in metadata_df
        else metadata_df
    )
    lat = pd.to_numeric(idexx.get("latitude", pd.Series(dtype=object)), errors="coerce")
    lon = pd.to_numeric(
        idexx.get("longitude", pd.Series(dtype=object)), errors="coerce"
    )
    has_coords = lat.notna() & lon.notna()
    geocoded_rate = float(has_coords.mean()) if len(idexx) else 0.0
    _add_check(
        checks,
        name="Tasa geocodificada IDEXX suficiente",
        passed=geocoded_rate >= 0.80,
        ok_detail=f"geocoded_rate IDEXX={geocoded_rate:.3f}.",
        fail_detail=f"geocoded_rate IDEXX insuficiente: {geocoded_rate:.3f}.",
    )

    top_location_share = 0.0
    if "raw_location_text" in idexx and len(idexx) > 0:
        counts = idexx["raw_location_text"].fillna("Desconocida").value_counts()
        top_location_share = float(counts.iloc[0] / len(idexx)) if len(counts) else 0.0
    _add_check(
        checks,
        name="Concentracion geografica documentada",
        passed=top_location_share <= 0.98,
        ok_detail=f"top_location_share={top_location_share:.3f}.",
        fail_detail=(
            "La cohorte esta casi completamente concentrada en una ubicacion "
            f"(top_location_share={top_location_share:.3f}); documentar sesgo."
        ),
    )

    status = "pass" if all(check.passed for check in checks) else "warn"
    report = _build_report(
        "geocoding_quality_v1",
        checks,
        {
            "idexx_rows": int(len(idexx)),
            "geocoded_rate": round(geocoded_rate, 6),
            "top_location_share": round(top_location_share, 6),
        },
    )
    report["status"] = status
    return report
