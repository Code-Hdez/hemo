"""Entrena el modelo oficial con reticulocitos y actualiza artefactos runtime.

El script mantiene compatibilidad con los nombres v2 usados por el backend
actual y tambien emite copias v3 versionadas para auditoria/rollback.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
MODELS = PROJECT_ROOT / "models"
OUTPUTS = PROJECT_ROOT / "outputs"

MODEL_LABELS = [
    "QC_REQUIERE_FROTIS",
    "PATRON_INFLAMATORIO",
    "PATRON_LEUCOGRAMA_ESTRES",
    "PATRON_ANEMIA_NO_REGENERATIVA",
    "PATRON_HEMOLISIS_MCHC",
    "PATRON_POLICITEMIA",
    "PATRON_ANEMIA_REGENERATIVA",
]
RULE_LABELS = ["QC_AGREGADOS_PLAQUETARIOS", "QC_INTERFERENCIA_GR"]
EXCLUDED_LABELS = ["QC_UNIDAD_NO_CONVERTIDA"]
RETIC_RAW_FEATURES = ["Reticulocytes", "Reticulocytes_pct"]
RETIC_DERIVED_FEATURES = [
    "flag_reticulocytosis_pct_gt2",
    "flag_reticulocytopenia_abs_lt10",
    "flag_regen_anemia_proxy",
]
RETIC_FEATURES = RETIC_RAW_FEATURES + RETIC_DERIVED_FEATURES
XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 8,
    "learning_rate": 0.03,
    "min_child_weight": 3,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "eval_metric": "aucpr",
    "verbosity": 0,
}
REGEN_PROMOTION_GATES = {
    "min_test_pr_auc": 0.70,
    "min_test_f1": 0.45,
    "min_test_recall": 0.65,
    "min_val_pr_auc": 0.80,
}


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_reticulocytes() -> pd.DataFrame:
    source = DATA_INTERIM / "featured_raw.csv"
    if not source.exists():
        raise FileNotFoundError(f"No existe {source}")
    cols = ["record_uuid"] + RETIC_RAW_FEATURES
    retic = pd.read_csv(source, usecols=cols)
    return retic.drop_duplicates(subset=["record_uuid"], keep="first")


def add_reticulocyte_features(df: pd.DataFrame, retic_lookup: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    merge_needed = any(col not in out.columns for col in RETIC_RAW_FEATURES)
    if merge_needed:
        out = out.merge(retic_lookup, on="record_uuid", how="left")

    out["Reticulocytes"] = pd.to_numeric(out["Reticulocytes"], errors="coerce")
    out["Reticulocytes_pct"] = pd.to_numeric(out["Reticulocytes_pct"], errors="coerce")
    out["flag_reticulocytosis_pct_gt2"] = (out["Reticulocytes_pct"] > 2.0).astype(float)
    out["flag_reticulocytopenia_abs_lt10"] = (out["Reticulocytes"] < 10.0).astype(float)
    out["flag_regen_anemia_proxy"] = (
        (pd.to_numeric(out["HCT"], errors="coerce") < 37.0)
        & (out["Reticulocytes_pct"] > 2.0)
    ).astype(float)
    return out


def canonical_features() -> tuple[list[str], dict[str, Any]]:
    doc = read_json(DATA_PROCESSED / "feature_columns.json")
    existing = [str(col) for col in doc["feature_columns"]]
    base = [col for col in existing if col not in RETIC_FEATURES]
    insert_after = "RDW"
    if insert_after in base:
        idx = base.index(insert_after) + 1
        features = base[:idx] + RETIC_RAW_FEATURES + base[idx:] + RETIC_DERIVED_FEATURES
    else:
        features = base + RETIC_FEATURES
    return features, doc


def impute_and_write_splits(features: list[str]) -> dict[str, pd.DataFrame]:
    retic_lookup = load_reticulocytes()
    splits = {
        split: add_reticulocyte_features(
            pd.read_csv(DATA_PROCESSED / f"{split}.csv"),
            retic_lookup,
        )
        for split in ("train", "val", "test")
    }

    medians = splits["train"][features].apply(pd.to_numeric, errors="coerce").median(numeric_only=True)
    medians = medians.reindex(features).fillna(0.0)
    imputer_df = pd.DataFrame({"feature": features, "mediana_train": medians.values})
    imputer_df.to_csv(DATA_PROCESSED / "imputer_medians.csv", index=False)

    for split, df in splits.items():
        out = df.copy()
        for feature in features:
            out[feature] = pd.to_numeric(out[feature], errors="coerce").fillna(medians[feature])
        metadata_cols = [col for col in ["record_uuid", "sample_date", "split"] if col in out.columns]
        label_cols = [col for col in read_json(DATA_PROCESSED / "label_columns.json")["all_labels"] if col in out.columns]
        out = out[metadata_cols + features + label_cols]
        out.to_csv(DATA_PROCESSED / f"{split}.csv", index=False)
        splits[split] = out
    return splits


def find_best_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[float, float, float, float]:
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    if len(thresholds) == 0:
        return 0.5, 0.0, 0.0, 0.0
    f1_scores = np.where(
        (precisions + recalls) > 0,
        2 * precisions * recalls / (precisions + recalls),
        0,
    )
    best_idx = int(np.argmax(f1_scores[:-1]))
    return (
        float(thresholds[best_idx]),
        float(f1_scores[best_idx]),
        float(precisions[best_idx]),
        float(recalls[best_idx]),
    )


def train_models(splits: dict[str, pd.DataFrame], features: list[str]) -> tuple[dict, dict, dict]:
    x_train = splits["train"][features]
    x_val = splits["val"][features]
    x_test = splits["test"][features]

    models: dict[str, Any] = {}
    thresholds: dict[str, float] = {}
    metrics: dict[str, dict[str, Any]] = {}

    for label in MODEL_LABELS:
        y_train = splits["train"][label].astype(int).values
        y_val = splits["val"][label].astype(int).values
        y_test = splits["test"][label].astype(int).values
        pos = int(y_train.sum())
        neg = int(len(y_train) - pos)
        clf = xgb.XGBClassifier(**XGB_PARAMS, scale_pos_weight=neg / max(pos, 1))
        clf.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)
        models[label] = clf

        prob_val = clf.predict_proba(x_val)[:, 1]
        prob_test = clf.predict_proba(x_test)[:, 1]
        threshold, val_f1, val_precision, val_recall = find_best_threshold(y_val, prob_val)
        pred_test = (prob_test >= threshold).astype(int)

        metrics[label] = {
            "pr_auc": round(float(average_precision_score(y_test, prob_test)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, prob_test)), 4),
            "f1_optimal_thresh": round(float(f1_score(y_test, pred_test, zero_division=0)), 4),
            "precision_optimal_thresh": round(float(precision_score(y_test, pred_test, zero_division=0)), 4),
            "recall_optimal_thresh": round(float(recall_score(y_test, pred_test, zero_division=0)), 4),
            "threshold_used": float(threshold),
            "n_positive_test": int(y_test.sum()),
            "val_pr_auc": round(float(average_precision_score(y_val, prob_val)), 4),
            "val_f1_threshold": round(float(val_f1), 4),
            "val_precision_threshold": round(float(val_precision), 4),
            "val_recall_threshold": round(float(val_recall), 4),
            "brier_val": float(brier_score_loss(y_val, prob_val)),
            "brier_test": float(brier_score_loss(y_test, prob_test)),
        }
        thresholds[label] = threshold

    return models, thresholds, metrics


def regen_gate(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = metrics["PATRON_ANEMIA_REGENERATIVA"]
    checks = {
        "test_pr_auc": row["pr_auc"] >= REGEN_PROMOTION_GATES["min_test_pr_auc"],
        "test_f1": row["f1_optimal_thresh"] >= REGEN_PROMOTION_GATES["min_test_f1"],
        "test_recall": row["recall_optimal_thresh"] >= REGEN_PROMOTION_GATES["min_test_recall"],
        "val_pr_auc": row["val_pr_auc"] >= REGEN_PROMOTION_GATES["min_val_pr_auc"],
    }
    return {
        "criteria": REGEN_PROMOTION_GATES,
        "metrics": row,
        "checks": checks,
        "passed": all(checks.values()),
    }


def build_policy(metrics: dict[str, dict[str, Any]], prauc_macro: float, gate: dict[str, Any]) -> dict[str, Any]:
    regen_status = "official_low_support" if gate["passed"] else "candidate_not_official"
    official_labels = MODEL_LABELS if gate["passed"] else [label for label in MODEL_LABELS if label != "PATRON_ANEMIA_REGENERATIVA"]
    excluded_labels = EXCLUDED_LABELS if gate["passed"] else EXCLUDED_LABELS + ["PATRON_ANEMIA_REGENERATIVA"]

    details: dict[str, dict[str, Any]] = {}
    for label in MODEL_LABELS:
        output_method = "model_with_postprocessing" if label == "PATRON_HEMOLISIS_MCHC" else "model"
        status = "official"
        note = "Salida oficial del modelo XGBoost v3."
        if label == "PATRON_POLICITEMIA":
            status = "official_promoted"
            note = "Soporte bajo-moderado; interpretar junto con contexto clinico."
        if label == "PATRON_ANEMIA_REGENERATIVA":
            status = regen_status
            note = (
                "Promovida por incorporar Reticulocytes y Reticulocytes_pct; "
                "n_test=6, reportar siempre con advertencia de bajo soporte."
                if gate["passed"]
                else "No cumplio gates de promocion; mantener como limitacion."
            )
        details[label] = {
            "output_method": output_method if label in official_labels else "excluded",
            "status": status,
            "pr_auc_test": metrics[label]["pr_auc"],
            "note": note,
            "rule_pattern": None,
        }

    details["QC_AGREGADOS_PLAQUETARIOS"] = {
        "output_method": "deterministic_rule",
        "status": "rule_based",
        "pr_auc_test": None,
        "note": "Se conserva como regex sobre idexx_comments; PDW no generalizo para agregados.",
        "rule_pattern": r"agregad|platelet.?clump|recuento.+plaquetas.+mayor",
    }
    details["QC_INTERFERENCIA_GR"] = {
        "output_method": "deterministic_rule",
        "status": "rule_based",
        "pr_auc_test": None,
        "note": "Regla deterministica por texto del analizador.",
        "rule_pattern": r"GR.?no.?lisad|unlysed.?red|gl[oó]bulos?.?roj[oa]s?.?no.?lisad",
    }
    details["QC_UNIDAD_NO_CONVERTIDA"] = {
        "output_method": "excluded",
        "status": "documented_limitation",
        "pr_auc_test": None,
        "note": "Error historico/no recurrente; no se entrena como salida oficial.",
        "rule_pattern": None,
    }

    return {
        "version": "3.0.0",
        "nb05b_timestamp": utc_now(),
        "n_model_labels": len(official_labels),
        "n_rule_labels": len(RULE_LABELS),
        "n_excluded_labels": len(excluded_labels),
        "official_model_labels": official_labels,
        "rule_labels": RULE_LABELS,
        "excluded_labels": excluded_labels,
        "prauc_macro_model": round(prauc_macro, 4),
        "reticulocyte_features": RETIC_FEATURES,
        "regen_promotion_gate": gate,
        "label_details": details,
    }


def write_model_artifacts(
    models: dict,
    thresholds: dict[str, float],
    metrics: dict[str, dict[str, Any]],
    features: list[str],
    splits: dict[str, pd.DataFrame],
) -> None:
    gate = regen_gate(metrics)
    if not gate["passed"]:
        raise RuntimeError(f"PATRON_ANEMIA_REGENERATIVA no cumplio gates: {gate}")

    prauc_macro = float(np.mean([metrics[label]["pr_auc"] for label in MODEL_LABELS]))
    policy = build_policy(metrics, prauc_macro, gate)

    thresholds_doc = {
        "version": "3.0.0",
        "source_split": "val",
        "model": "xgb_v3_reticulocytes",
        "note": "Thresholds seleccionados en validation para modelo oficial con reticulocitos.",
        "thresholds": {**thresholds, **{label: 1.0 for label in policy["excluded_labels"]}},
    }
    metrics_doc = {
        "version": "3.0.0",
        "model": "xgb_v3_reticulocytes",
        "n_labels": len(MODEL_LABELS),
        "labels": MODEL_LABELS,
        "prauc_macro": round(prauc_macro, 4),
        "reticulocyte_features": RETIC_FEATURES,
        "regen_promotion_gate": gate,
        "metrics": metrics,
    }
    metadata = {
        "version": "3.0.0",
        "model_type": "xgb_v3_reticulocytes",
        "nb05b_timestamp": utc_now(),
        "official_model_labels": policy["official_model_labels"],
        "rule_labels": RULE_LABELS,
        "excluded_labels": policy["excluded_labels"],
        "n_features": len(features),
        "feature_columns": features,
        "prauc_macro": round(prauc_macro, 4),
        "label_policy_version": policy["version"],
        "label_policy_file": "data/processed/final_label_policy.json",
        "reticulocyte_features": RETIC_FEATURES,
        "postprocessing_rules": [
            {
                "name": "mchc_artifact",
                "description": "MCHC > 50 fuerza PATRON_HEMOLISIS_MCHC a 0.0",
                "threshold": 50.0,
                "affects": "PATRON_HEMOLISIS_MCHC",
            }
        ],
        "train_n": len(splits["train"]),
        "val_n": len(splits["val"]),
        "test_n": len(splits["test"]),
        "xgboost_params": XGB_PARAMS,
    }

    model_v3 = MODELS / "best_model_v3.pkl"
    with model_v3.open("wb") as handle:
        pickle.dump(models, handle)
    shutil.copyfile(model_v3, MODELS / "best_model_v2.pkl")

    empty_calibrators: dict[str, Any] = {}
    with (MODELS / "calibrators_v3.pkl").open("wb") as handle:
        pickle.dump(empty_calibrators, handle)
    shutil.copyfile(MODELS / "calibrators_v3.pkl", MODELS / "calibrators_v2.pkl")

    write_json(MODELS / "model_metadata_v3.json", metadata)
    write_json(MODELS / "model_metadata_v2.json", metadata)
    write_json(DATA_PROCESSED / "decision_thresholds_v3.json", thresholds_doc)
    write_json(DATA_PROCESSED / "decision_thresholds_v2.json", thresholds_doc)
    write_json(DATA_PROCESSED / "metrics_test_v3.json", metrics_doc)
    write_json(DATA_PROCESSED / "metrics_test_v2.json", metrics_doc)
    write_json(DATA_PROCESSED / "final_label_policy.json", policy)

    comparison_rows = []
    old_metrics_path = DATA_PROCESSED / "metrics_test_final.json"
    old_metrics = read_json(old_metrics_path).get("metrics", {}) if old_metrics_path.exists() else {}
    for label in MODEL_LABELS:
        old = old_metrics.get(label, {})
        comparison_rows.append(
            {
                "label": label,
                "old_pr_auc": old.get("pr_auc"),
                "old_f1": old.get("f1_optimal_thresh"),
                "v3_pr_auc": metrics[label]["pr_auc"],
                "v3_f1": metrics[label]["f1_optimal_thresh"],
                "delta_pr_auc": None if "pr_auc" not in old else metrics[label]["pr_auc"] - old["pr_auc"],
                "delta_f1": None if "f1_optimal_thresh" not in old else metrics[label]["f1_optimal_thresh"] - old["f1_optimal_thresh"],
            }
        )
    pd.DataFrame(comparison_rows).to_csv(OUTPUTS / "reticulocyte_model_v3_comparison.csv", index=False)

    final_state = {
        "version": "3.0.0",
        "status": "READY_FOR_PRODUCTION",
        "model_file": "models/best_model_v3.pkl",
        "runtime_model_file": "models/best_model_v2.pkl",
        "policy_file": "data/processed/final_label_policy.json",
        "thresholds_file": "data/processed/decision_thresholds_v3.json",
        "runtime_thresholds_file": "data/processed/decision_thresholds_v2.json",
        "prauc_macro_official": round(prauc_macro, 4),
        "n_official_labels": len(policy["official_model_labels"]),
        "n_rule_labels": len(RULE_LABELS),
        "n_excluded_labels": len(policy["excluded_labels"]),
        "reticulocyte_features": RETIC_FEATURES,
        "regen_promotion_gate": gate,
    }
    write_json(OUTPUTS / "final_system_state.json", final_state)


def update_feature_and_label_configs(features: list[str], prior_feature_doc: dict[str, Any]) -> None:
    raw = [col for col in prior_feature_doc.get("cbc_raw", []) if col not in RETIC_FEATURES]
    derived = [col for col in prior_feature_doc.get("derived", []) if col not in RETIC_FEATURES]
    feature_doc = {
        **prior_feature_doc,
        "version": "3.0.0",
        "timestamp": utc_now(),
        "feature_columns": features,
        "n_features": len(features),
        "cbc_raw": raw[:9] + RETIC_RAW_FEATURES + raw[9:] if "RDW" in raw else raw + RETIC_RAW_FEATURES,
        "derived": derived + RETIC_DERIVED_FEATURES,
        "reticulocyte_features": RETIC_FEATURES,
    }
    write_json(DATA_PROCESSED / "feature_columns.json", feature_doc)

    label_doc = read_json(DATA_PROCESSED / "label_columns.json")
    label_doc["version"] = "3.0.0"
    label_doc["timestamp"] = utc_now()
    label_doc["official_labels"] = MODEL_LABELS
    label_doc["rule_labels"] = RULE_LABELS
    label_doc["excluded_labels"] = EXCLUDED_LABELS
    write_json(DATA_PROCESSED / "label_columns.json", label_doc)


def update_freeze_and_manifests() -> None:
    prereg = {
        "version": "3.0.0",
        "generated_at": utc_now(),
        "official_labels": MODEL_LABELS,
        "qc_rules": {
            "QC_AGREGADOS_PLAQUETARIOS": r"agregad|platelet.?clump|recuento.+plaquetas.+mayor",
            "QC_INTERFERENCIA_GR": r"GR.?no.?lisad|unlysed.?red|gl[oó]bulos?.?roj[oa]s?.?no.?lisad",
        },
        "excluded_labels": EXCLUDED_LABELS,
        "threshold_objectives": {
            "source_split": "val",
            "selection_policy": "Thresholds seleccionados sobre validation.",
            "model": "xgb_v3_reticulocytes",
        },
        "clinical_acceptance": {
            "must_not_diagnose": True,
            "must_refer_to_veterinarian": True,
            "citizen_facing_scope": "Explicacion orientativa de patrones hematologicos caninos.",
        },
        "model_metadata_version": "3.0.0",
        "label_policy_version": "3.0.0",
    }
    write_json(DATA_PROCESSED / "policy_preregistered_v3.json", prereg)

    freeze = {
        "version": "3.0.0",
        "generated_at": utc_now(),
        "policy_file": "data/processed/final_label_policy.json",
        "thresholds_file": "data/processed/decision_thresholds_v2.json",
        "model_metadata_file": "models/model_metadata_v2.json",
        "preregistered_file": "data/processed/policy_preregistered_v3.json",
        "policy_sha256": sha256_file(DATA_PROCESSED / "final_label_policy.json"),
        "thresholds_sha256": sha256_file(DATA_PROCESSED / "decision_thresholds_v2.json"),
        "model_metadata_sha256": sha256_file(MODELS / "model_metadata_v2.json"),
        "preregistered_sha256": sha256_file(DATA_PROCESSED / "policy_preregistered_v3.json"),
        "official_labels": MODEL_LABELS,
        "excluded_labels": EXCLUDED_LABELS,
        "source_split": "val",
    }
    write_json(DATA_PROCESSED / "policy_freeze_v3.json", freeze)

    runtime_artifacts = [
        "models/best_model_v2.pkl",
        "models/model_metadata_v2.json",
        "models/calibrators_v2.pkl",
        "data/processed/feature_columns.json",
        "data/processed/decision_thresholds_v2.json",
        "data/processed/imputer_medians.csv",
        "data/processed/final_label_policy.json",
    ]
    support_artifacts = [
        "models/best_model_v3.pkl",
        "models/model_metadata_v3.json",
        "models/calibrators_v3.pkl",
        "data/processed/decision_thresholds_v3.json",
        "data/processed/metrics_test_v2.json",
        "data/processed/metrics_test_v3.json",
        "data/processed/train.csv",
        "data/processed/val.csv",
        "data/processed/test.csv",
        "data/processed/policy_preregistered_v3.json",
        "data/processed/policy_freeze_v3.json",
        "outputs/final_system_state.json",
        "outputs/reticulocyte_model_v3_comparison.csv",
    ]
    manifest = {
        "version": "3.0.0",
        "generated_at": utc_now(),
        "runtime_artifacts": [
            {"path": rel, "sha256": sha256_file(PROJECT_ROOT / rel)}
            for rel in runtime_artifacts
        ],
        "support_artifacts": [
            {"path": rel, "sha256": sha256_file(PROJECT_ROOT / rel)}
            for rel in support_artifacts
            if (PROJECT_ROOT / rel).exists()
        ],
    }
    write_json(DATA_PROCESSED / "artifact_manifest_v2.json", manifest)
    write_json(DATA_PROCESSED / "artifact_manifest_v3.json", manifest)


def main() -> int:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    features, prior_feature_doc = canonical_features()
    splits = impute_and_write_splits(features)
    update_feature_and_label_configs(features, prior_feature_doc)
    models, thresholds, metrics = train_models(splits, features)
    write_model_artifacts(models, thresholds, metrics, features, splits)
    update_freeze_and_manifests()

    print("Modelo v3 con reticulocitos entrenado.")
    print(f"  features: {len(features)}")
    print(f"  etiquetas modelo: {len(MODEL_LABELS)}")
    print(f"  PR-AUC macro: {read_json(DATA_PROCESSED / 'metrics_test_v3.json')['prauc_macro']:.4f}")
    regen = read_json(DATA_PROCESSED / "metrics_test_v3.json")["metrics"]["PATRON_ANEMIA_REGENERATIVA"]
    print(
        "  PATRON_ANEMIA_REGENERATIVA: "
        f"PR-AUC={regen['pr_auc']:.4f}, F1={regen['f1_optimal_thresh']:.4f}, "
        f"recall={regen['recall_optimal_thresh']:.4f}, n_test={regen['n_positive_test']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
