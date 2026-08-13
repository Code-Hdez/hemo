"""Construye el pool aumentado IDEXX + Dic-May con splits agrupados por perro.

Por defecto no pisa train/val/test canonicos. Escribe artefactos versionados para
revisar soporte de etiquetas, leakage por dog_id y el efecto real de Dic-May.
"""

from __future__ import annotations

import argparse
import hashlib
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

from app.modules.ml.metadata import make_dog_id, make_record_id, normalize_text  # noqa: E402


DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
OUTPUTS = PROJECT_ROOT / "outputs"

METADATA_COLUMNS = [
    "record_uuid",
    "record_id",
    "dog_id",
    "sample_date",
    "split",
    "ingestion_cohort",
    "source_relative_path",
    "clinic",
    "raw_location_text",
    "latitude",
    "longitude",
    "location_source",
    "location_confidence",
]

LABEL_TAXONOMY: dict[str, dict[str, Any]] = {
    "QC_REQUIERE_FROTIS": {
        "resultado_oficial": True,
        "patterns": [
            r"confirmar con.*frotis",
            r"confirmar con la gr[aá]fica",
            r"confirme los resultados con un frotis",
            r"confirmar con revisi[oó]n de frotis",
        ],
    },
    "QC_AGREGADOS_PLAQUETARIOS": {
        "resultado_oficial": True,
        "patterns": [r"agregados de plaquetas", r"plaquetas agregadas"],
    },
    "QC_INTERFERENCIA_GR": {
        "resultado_oficial": False,
        "patterns": [r"exceso de GR no lisados"],
    },
    "QC_UNIDAD_NO_CONVERTIDA": {
        "resultado_oficial": False,
        "patterns": [r"unit.*could not be converted", r"unidad.*no.*convert"],
    },
    "PATRON_INFLAMATORIO": {
        "resultado_oficial": True,
        "patterns": [r"monocitosis.*inflamaci[oó]n", r"considere la inflamaci[oó]n"],
    },
    "PATRON_LEUCOGRAMA_ESTRES": {
        "resultado_oficial": True,
        "patterns": [r"leucograma de estr[eé]s", r"respuesta glucocorticoide"],
    },
    "PATRON_ANEMIA_NO_REGENERATIVA": {
        "resultado_oficial": True,
        "patterns": [
            r"anemia sin reticulocitosis",
            r"probable anemia no regenerativa",
            r"anemia pre-regenerativa",
        ],
    },
    "PATRON_HEMOLISIS_MCHC": {
        "resultado_oficial": True,
        "patterns": [r"aumento de MCHC", r"considere hem[oó]lisis"],
    },
    "PATRON_POLICITEMIA": {
        "resultado_oficial": True,
        "patterns": [r"policitemia"],
    },
    "PATRON_ANEMIA_REGENERATIVA": {
        "resultado_oficial": True,
        "patterns": [r"anemia con reticulocitosis", r"probable anemia regenerativa"],
    },
}


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_feature_columns(project_root: Path) -> list[str]:
    doc = load_json(project_root / "data" / "processed" / "feature_columns.json")
    columns = doc.get("feature_columns")
    if not isinstance(columns, list):
        raise ValueError("feature_columns.json no contiene feature_columns como lista")
    return [str(col) for col in columns]


def load_label_columns(project_root: Path) -> tuple[list[str], list[str]]:
    doc = load_json(project_root / "data" / "processed" / "label_columns.json")
    all_labels = [str(label) for label in doc.get("all_labels", list(LABEL_TAXONOMY))]
    official_labels = [
        str(label)
        for label in doc.get(
            "official_labels",
            [label for label, meta in LABEL_TAXONOMY.items() if meta.get("resultado_oficial")],
        )
    ]
    return all_labels, official_labels


def label_record(comment_text: Any, label_columns: list[str]) -> dict[str, int]:
    if pd.isna(comment_text) or str(comment_text).strip() == "":
        return {label: 0 for label in label_columns}

    text = str(comment_text)
    labels: dict[str, int] = {}
    for label in label_columns:
        meta = LABEL_TAXONOMY.get(label, {})
        patterns = meta.get("patterns", [])
        match = re.search("|".join(patterns), text, re.IGNORECASE) if patterns else None
        labels[label] = 1 if match else 0
    return labels


def to_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def build_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    numeric = [
        "RBC",
        "WBC",
        "Platelets",
        "HGB",
        "HCT",
        "MCV",
        "MCH",
        "MCHC",
        "RDW",
        "Neutrophils",
        "Neutrophils_pct",
        "Lymphocytes",
        "Lymphocytes_pct",
        "Monocytes",
        "Monocytes_pct",
        "Eosinophils",
        "Basophils",
        "MPV",
        "PDW",
        "age_years",
    ]
    out = to_numeric_columns(out, numeric)

    out["flag_thrombocytopenia"] = (out["Platelets"] < 200).astype(int)
    out["flag_thrombocytopenia_severe"] = (out["Platelets"] < 100).astype(int)
    out["flag_lymphopenia"] = (out["Lymphocytes"] < 1.0).astype(int)
    out["flag_lymphocytosis"] = (out["Lymphocytes"] > 5.0).astype(int)
    out["flag_neutrophilia"] = (out["Neutrophils"] > 11.0).astype(int)
    out["flag_neutropenia"] = (out["Neutrophils"] < 2.9).astype(int)
    out["flag_leukocytosis"] = (out["WBC"] > 17.0).astype(int)
    out["flag_leukopenia"] = (out["WBC"] < 5.5).astype(int)
    out["flag_anemia"] = (out["HGB"] < 12.0).astype(int)
    out["flag_microcytic"] = (out["MCV"] < 62.0).astype(int)
    out["flag_macrocytic"] = (out["MCV"] > 82.0).astype(int)
    out["flag_hypochromic"] = (out["MCHC"] < 31.0).astype(int)
    out["flag_macro_platelets"] = (out["MPV"] > 12.5).astype(int)

    eps = 0.01
    out["ratio_NLR"] = out["Neutrophils"] / (out["Lymphocytes"] + eps)
    out["ratio_PLR"] = out["Platelets"] / (out["Lymphocytes"] + eps)
    out["ratio_MLR"] = out["Monocytes"] / (out["Lymphocytes"] + eps)
    out["ratio_MPV_PLT"] = out["MPV"] / (out["Platelets"] + eps)
    out["pattern_stress_leukogram"] = (
        (out["Neutrophils"] > 11.0)
        & (out["Lymphocytes"] < 1.0)
        & (out["Eosinophils"] < 0.5)
    ).astype(int)
    return out


def prepare_baseline(project_root: Path, feature_columns: list[str], label_columns: list[str]) -> pd.DataFrame:
    labeled_path = project_root / "data" / "processed" / "labeled_idexx.csv"
    metadata_path = project_root / "data" / "processed" / "analysis_metadata.csv"
    if not labeled_path.exists():
        raise FileNotFoundError(f"No existe {labeled_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"No existe {metadata_path}. Ejecuta scripts/run_research_audit.py")

    labeled = pd.read_csv(labeled_path)
    metadata = pd.read_csv(metadata_path)
    metadata = metadata[metadata["source_dataset"].eq("IDEXX")].copy()
    keep = [
        "record_uuid",
        "record_id",
        "dog_id",
        "ingestion_cohort",
        "source_relative_path",
        "clinic",
        "raw_location_text",
        "latitude",
        "longitude",
        "location_source",
        "location_confidence",
    ]
    merged = labeled.merge(metadata[[c for c in keep if c in metadata.columns]], on="record_uuid", how="left")
    merged["record_id"] = merged["record_id"].fillna(merged["record_uuid"])
    merged["ingestion_cohort"] = merged["ingestion_cohort"].fillna("baseline_historico")
    for label in label_columns:
        if label not in merged.columns:
            merged[label] = 0
    for feature in feature_columns:
        if feature not in merged.columns:
            merged[feature] = pd.NA
    return merged


def prepare_dic_may(project_root: Path, feature_columns: list[str], label_columns: list[str]) -> pd.DataFrame:
    dic_path = project_root / "data" / "interim" / "idexx_dic_may_extracted.csv"
    if not dic_path.exists():
        raise FileNotFoundError(f"No existe {dic_path}. Ejecuta scripts/extract_idexx_cohorts.py")

    dic = pd.read_csv(dic_path)
    dic = dic[dic.get("species", "Canine").fillna("Canine").astype(str).str.contains("Canine", case=False)].copy()
    dic["ingestion_cohort"] = "dic_may_2026"
    if "record_uuid" not in dic.columns:
        dic["record_uuid"] = ""
    dic["record_uuid"] = dic.apply(
        lambda row: row["record_uuid"]
        if str(row.get("record_uuid") or "").strip()
        else make_record_id(
            source_dataset="IDEXX",
            source_relative_path=row.get("source_relative_path"),
            file_hash=row.get("file_hash"),
            page_number=row.get("page_number"),
            patient_name=row.get("patient_name"),
            sample_date=row.get("sample_date"),
        ),
        axis=1,
    )
    if "record_id" not in dic.columns:
        dic["record_id"] = dic["record_uuid"]
    if "dog_id" not in dic.columns:
        dic["dog_id"] = dic.apply(
            lambda row: make_dog_id(
                patient_name=row.get("patient_name"),
                pet_owner=row.get("pet_owner"),
                clinic=row.get("clinic"),
                source_dataset="IDEXX",
                fallback=row.get("record_uuid"),
            ),
            axis=1,
        )

    dic = build_engineered_features(dic)

    label_dicts = dic.get("idexx_comments", pd.Series([""] * len(dic), index=dic.index)).apply(
        lambda text: label_record(text, label_columns)
    )
    derived_labels = pd.DataFrame(label_dicts.tolist(), index=dic.index)
    for label in label_columns:
        if label in dic.columns:
            dic[label] = pd.to_numeric(dic[label], errors="coerce").fillna(derived_labels[label]).astype(int)
        else:
            dic[label] = derived_labels[label].astype(int)
    for feature in feature_columns:
        if feature not in dic.columns:
            dic[feature] = pd.NA
    return dic


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def split_by_dog_id(
    df: pd.DataFrame,
    label_columns: list[str],
    *,
    train_frac: float,
    val_frac: float,
    seed: int,
) -> pd.DataFrame:
    if train_frac <= 0 or val_frac <= 0 or train_frac + val_frac >= 1:
        raise ValueError("Las fracciones deben cumplir train>0, val>0 y train+val<1")

    out = df.copy()
    missing = out["dog_id"].isna() | out["dog_id"].astype(str).str.strip().eq("")
    out.loc[missing, "dog_id"] = "missing-" + out.loc[missing, "record_uuid"].astype(str)
    out["dog_id"] = out["dog_id"].astype(str)

    splits = ["train", "val", "test"]
    fractions = {"train": train_frac, "val": val_frac, "test": 1.0 - train_frac - val_frac}
    label_totals = out[label_columns].sum().astype(float)
    row_total = float(len(out))
    targets = {
        split: {
            "rows": row_total * frac,
            "labels": label_totals * frac,
        }
        for split, frac in fractions.items()
    }
    assigned_rows = {split: 0.0 for split in splits}
    assigned_labels = {split: pd.Series(0.0, index=label_columns) for split in splits}

    group_rows = []
    for dog_id, group in out.groupby("dog_id", sort=False):
        labels = group[label_columns].sum().astype(float)
        group_rows.append(
            {
                "dog_id": dog_id,
                "n": float(len(group)),
                "labels": labels,
                "tie": stable_hash(f"{seed}|{dog_id}"),
            }
        )
    group_rows.sort(key=lambda item: (-item["n"], item["tie"]))

    assignments: dict[str, str] = {}
    nonzero_labels = label_totals[label_totals > 0].index.tolist()
    for item in group_rows:
        best_split = "train"
        best_score = float("inf")
        for split in splits:
            next_rows = assigned_rows[split] + item["n"]
            remaining_capacity = max(targets[split]["rows"] - assigned_rows[split], 0.0)
            row_score = -remaining_capacity / max(row_total, 1.0)
            if nonzero_labels:
                next_labels = assigned_labels[split] + item["labels"]
                label_score = (
                    (next_labels[nonzero_labels] - targets[split]["labels"][nonzero_labels]).abs()
                    / label_totals[nonzero_labels].clip(lower=1.0)
                ).mean()
            else:
                label_score = 0.0
            overfill = max(0.0, next_rows - targets[split]["rows"]) / max(targets[split]["rows"], 1.0)
            score = float(row_score + (label_score * 0.05) + (overfill * 10.0))
            if score < best_score:
                best_score = score
                best_split = split
        assignments[item["dog_id"]] = best_split
        assigned_rows[best_split] += item["n"]
        assigned_labels[best_split] = assigned_labels[best_split] + item["labels"]

    out["split"] = out["dog_id"].map(assignments)
    return out


def compute_label_balance(
    baseline: pd.DataFrame,
    dic_may: pd.DataFrame,
    combined: pd.DataFrame,
    label_columns: list[str],
) -> pd.DataFrame:
    rows = []
    for label in label_columns:
        historical = int(pd.to_numeric(baseline[label], errors="coerce").fillna(0).sum())
        new = int(pd.to_numeric(dic_may[label], errors="coerce").fillna(0).sum())
        total = int(pd.to_numeric(combined[label], errors="coerce").fillna(0).sum())
        rows.append(
            {
                "label": label,
                "historical_positive": historical,
                "dic_may_positive": new,
                "combined_positive": total,
                "absolute_gain": new,
                "relative_gain_pct": round((new / historical * 100.0), 3) if historical else None,
                "status": "sin_incremento_dic_may" if new == 0 else "incremento_dic_may",
            }
        )
    return pd.DataFrame(rows)


def build_distribution(
    df: pd.DataFrame,
    label_columns: list[str],
    *,
    min_positive_per_split: int,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "generated_at": utc_now(),
        "min_positive_per_split": min_positive_per_split,
        "labels": {},
    }
    for label in label_columns:
        entry: dict[str, Any] = {
            "total": int(df[label].sum()),
            "pct_total": round(float(df[label].mean() * 100.0), 3),
        }
        low_splits = []
        for split in ("train", "val", "test"):
            split_df = df[df["split"].eq(split)]
            positives = int(split_df[label].sum())
            entry[split] = positives
            if positives < min_positive_per_split:
                low_splits.append(split)
        entry["low_support_splits"] = low_splits
        output["labels"][label] = entry
    return output


def build_leakage_report(df: pd.DataFrame) -> dict[str, Any]:
    split_sets = df.groupby("dog_id")["split"].agg(lambda values: sorted(set(values)))
    crossing = split_sets[split_sets.map(len) > 1]
    return {
        "gate": "augmented_dog_leakage_v1",
        "status": "pass" if crossing.empty else "fail",
        "checked_at": utc_now(),
        "records": int(len(df)),
        "unique_dogs": int(df["dog_id"].nunique()),
        "dogs_crossing_splits": int(len(crossing)),
        "top_crossing_dogs": {str(k): ",".join(v) for k, v in crossing.head(20).items()},
    }


def write_augmented_outputs(
    project_root: Path,
    augmented: pd.DataFrame,
    feature_columns: list[str],
    official_labels: list[str],
    *,
    min_positive_per_split: int,
    write_canonical: bool,
) -> None:
    data_processed = project_root / "data" / "processed"
    outputs_dir = project_root / "outputs"
    data_processed.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    label_cols_all = [col for col in LABEL_TAXONOMY if col in augmented.columns]
    augmented.to_csv(data_processed / "labeled_idexx_augmented.csv", index=False)

    medians = (
        augmented.loc[augmented["split"].eq("train"), feature_columns]
        .apply(pd.to_numeric, errors="coerce")
        .median(numeric_only=True)
        .rename("mediana_train")
        .reset_index()
        .rename(columns={"index": "feature"})
    )
    fallback_medians_path = data_processed / "imputer_medians.csv"
    if fallback_medians_path.exists():
        fallback = pd.read_csv(fallback_medians_path).set_index("feature")["mediana_train"]
        medians["mediana_train"] = medians.apply(
            lambda row: fallback.get(row["feature"], 0.0)
            if pd.isna(row["mediana_train"])
            else row["mediana_train"],
            axis=1,
        )
    medians["mediana_train"] = pd.to_numeric(medians["mediana_train"], errors="coerce").fillna(0.0)
    medians.to_csv(data_processed / "imputer_medians_augmented.csv", index=False)

    median_map = dict(zip(medians["feature"], medians["mediana_train"], strict=True))
    split_ready = augmented.copy()
    for feature in feature_columns:
        split_ready[feature] = pd.to_numeric(split_ready[feature], errors="coerce").fillna(
            median_map[feature]
        )

    split_paths = {
        "train": data_processed / "train_augmented.csv",
        "val": data_processed / "val_augmented.csv",
        "test": data_processed / "test_augmented.csv",
    }
    split_output_cols = [
        col for col in METADATA_COLUMNS if col in split_ready.columns
    ] + feature_columns + official_labels
    for split, path in split_paths.items():
        split_ready.loc[split_ready["split"].eq(split), split_output_cols].to_csv(path, index=False)

    write_json(
        data_processed / "label_distribution_v3.json",
        build_distribution(split_ready, label_cols_all, min_positive_per_split=min_positive_per_split),
    )
    write_json(outputs_dir / "gate_augmented_dog_leakage_v1.json", build_leakage_report(split_ready))

    if write_canonical:
        canonical_cols = [
            col for col in METADATA_COLUMNS if col in split_ready.columns
        ] + feature_columns + official_labels
        for split in ("train", "val", "test"):
            split_ready.loc[split_ready["split"].eq(split), canonical_cols].to_csv(
                data_processed / f"{split}.csv",
                index=False,
            )
        medians.to_csv(data_processed / "imputer_medians.csv", index=False)


def build_augmented_training_set(
    project_root: Path,
    *,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    seed: int = 42,
    min_positive_per_split: int = 15,
    write_canonical: bool = False,
    allow_empty_dic_may_labels: bool = False,
) -> dict[str, Any]:
    feature_columns = load_feature_columns(project_root)
    all_labels, official_labels = load_label_columns(project_root)

    baseline = prepare_baseline(project_root, feature_columns, all_labels)
    dic_may = prepare_dic_may(project_root, feature_columns, all_labels)
    dic_comment_count = int(
        dic_may.get("idexx_comments", pd.Series([], dtype=object))
        .fillna("")
        .astype(str)
        .str.strip()
        .ne("")
        .sum()
    )
    dic_positive_labels = int(dic_may[all_labels].sum().sum())

    combined = pd.concat([baseline, dic_may], ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=["record_id"], keep="first")
    combined = split_by_dog_id(
        combined,
        all_labels,
        train_frac=train_frac,
        val_frac=val_frac,
        seed=seed,
    )

    balance = compute_label_balance(baseline, dic_may, combined, all_labels)
    outputs_dir = project_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    balance.to_csv(outputs_dir / "label_balance_before_after_dic_may.csv", index=False)

    blocked = dic_positive_labels == 0 and not allow_empty_dic_may_labels
    status = "blocked_missing_dic_may_labels" if blocked else "ready"
    balance_payload = {
        "generated_at": utc_now(),
        "status": status,
        "baseline_records": int(len(baseline)),
        "dic_may_records": int(len(dic_may)),
        "combined_records": int(len(combined)),
        "dic_may_comments_nonempty": dic_comment_count,
        "dic_may_positive_labels": dic_positive_labels,
        "labels": balance.to_dict(orient="records"),
        "notes": [
            "Dic-May se usa como aumento del pool, no como test externo.",
            "La mejora por etiquetas bajas solo es valida si dic_may_positive_labels > 0.",
        ],
    }
    write_json(outputs_dir / "label_balance_before_after_dic_may.json", balance_payload)

    if write_canonical and blocked:
        raise RuntimeError(
            "Dic-May no tiene etiquetas positivas/comentarios utiles. "
            "No se sobreescriben train/val/test sin --allow-empty-dic-may-labels."
        )

    write_augmented_outputs(
        project_root,
        combined,
        feature_columns,
        official_labels,
        min_positive_per_split=min_positive_per_split,
        write_canonical=write_canonical,
    )

    return balance_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--train-frac", type=float, default=0.70)
    parser.add_argument("--val-frac", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-positive-per-split", type=int, default=15)
    parser.add_argument("--write-canonical", action="store_true")
    parser.add_argument("--allow-empty-dic-may-labels", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_augmented_training_set(
        args.project_root,
        train_frac=args.train_frac,
        val_frac=args.val_frac,
        seed=args.seed,
        min_positive_per_split=args.min_positive_per_split,
        write_canonical=args.write_canonical,
        allow_empty_dic_may_labels=args.allow_empty_dic_may_labels,
    )
    print("Dataset aumentado generado:")
    print(f"  estado: {payload['status']}")
    print(f"  historico: {payload['baseline_records']}")
    print(f"  dic_may: {payload['dic_may_records']}")
    print(f"  combinado: {payload['combined_records']}")
    print(f"  comentarios Dic-May no vacios: {payload['dic_may_comments_nonempty']}")
    print(f"  etiquetas positivas Dic-May: {payload['dic_may_positive_labels']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
