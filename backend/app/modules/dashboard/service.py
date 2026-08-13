"""Dashboard data loading and aggregation use cases."""

import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from app.modules.dashboard import repository
from app.modules.dashboard.schemas import (
    BreedDistributionResponse,
    BreedEntry,
    DomainShiftEntry,
    ExternalValidation,
    LabelActivationEntry,
    LabelActivationResponse,
    LabelMetrics,
    ModelQualityResponse,
    TemporalAnalyticsResponse,
    TemporalPoint,
)
from app.shared.analysis_output import HIDDEN_LABELS
from app.shared.dates import parse_iso_datetime

_analytics_cache: dict[str, Any] = {}


def load_analytics_cache(project_root: Path) -> dict[str, Any]:
    cache: dict[str, Any] = {}
    outputs_dir = project_root / "outputs"
    cv_path = outputs_dir / "cv_results_v3_summary.csv"
    cache["cv_results"] = (
        list(csv.DictReader(cv_path.open(encoding="utf-8"))) if cv_path.exists() else []
    )
    calibration: dict[str, dict] = {}
    cal_path = outputs_dir / "calibration_metrics_v3.csv"
    if cal_path.exists():
        with cal_path.open(encoding="utf-8") as source:
            for row in csv.DictReader(source):
                if row.get("label"):
                    calibration[row["label"]] = row
    cache["calibration"] = calibration
    for key, filename, derived_key in (
        ("domain_shift", "domain_shift_table.csv", "_feature"),
        ("activation_rates", "activation_rates_comparison.csv", "_label"),
    ):
        rows: list[dict] = []
        path = outputs_dir / filename
        if path.exists():
            with path.open(encoding="utf-8") as source:
                for row in csv.DictReader(source):
                    items = list(row.items())
                    value = items[0][1] if items else ""
                    if value:
                        rows.append({**row, derived_key: value})
        cache[key] = rows
    for key, path in (
        ("final_state", outputs_dir / "final_system_state.json"),
        ("model_metadata", project_root / "models" / "model_metadata_v2.json"),
    ):
        try:
            cache[key] = (
                json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            )
        except (OSError, json.JSONDecodeError):
            cache[key] = {}
    return cache


def gate_status_from_file(path: Path) -> str:
    if not path.exists():
        return "unknown"
    try:
        value = str(
            json.loads(path.read_text(encoding="utf-8")).get("status", "unknown")
        ).lower()
        return value if value in {"pass", "fail", "warn"} else "unknown"
    except (OSError, json.JSONDecodeError):
        return "unknown"


def load_gate_statuses(project_root: Path) -> dict[str, str]:
    outputs = project_root / "outputs"
    return {
        key: gate_status_from_file(outputs / filename)
        for key, filename in (
            ("feature_parity", "gate_feature_parity_v2.json"),
            ("leakage_audit", "gate_leakage_audit_v2.json"),
            ("manifest_integrity", "gate_manifest_integrity_v2.json"),
            ("policy_freeze", "gate_policy_freeze_v3.json"),
            ("drift_basic", "gate_basic_drift_v3.json"),
        )
    }


def refresh(project_root: Path) -> None:
    global _analytics_cache
    _analytics_cache = load_analytics_cache(project_root)
    repository.save_metric("model_analytics_cache", _analytics_cache)
    repository.save_metric("operational_gates", load_gate_statuses(project_root))


def analytics_cache() -> dict[str, Any]:
    return repository.get_metric("model_analytics_cache") or _analytics_cache


def gate_statuses() -> dict[str, str]:
    payload = repository.get_metric("operational_gates") or {}
    return {str(key): str(value) for key, value in payload.items()}


def model_quality() -> ModelQualityResponse:
    cache = analytics_cache()
    calibration = cache.get("calibration", {})
    labels = [
        LabelMetrics(
            name=row["label"],
            pr_auc=round(float(row.get("pr_auc_mean", 0)), 4),
            roc_auc=round(float(row.get("roc_auc_mean", 0)), 4),
            f1=round(float(row.get("f1_mean", 0)), 4),
            ece=round(float(calibration.get(row["label"], {}).get("ece_test", 0)), 4),
            status="official",
        )
        for row in cache.get("cv_results", [])
        if row.get("label") and row["label"] not in HIDDEN_LABELS
    ]
    shifts = [
        DomainShiftEntry(
            feature=row.get("_feature", "").strip(),
            d=round(float(row.get("effect_size", 0)), 4),
            severity=str(row.get("level", "leve")),
        )
        for row in cache.get("domain_shift", [])
        if row.get("_feature", "").strip()
    ]
    metadata = cache.get("model_metadata", {})
    macro = (
        round(sum(label.pr_auc for label in labels) / len(labels), 4)
        if labels
        else round(float(metadata.get("prauc_macro", 0.9495)), 4)
    )
    return ModelQualityResponse(
        version=str(metadata.get("version", "2.0.0")),
        prauc_macro=macro,
        labels=labels,
        external_validation=ExternalValidation(
            dataset="Dog Aging Project (DAP)",
            n=1301,
            coherence_check="PASS",
            domain_shifts=[s for s in shifts if s.severity in {"SEVERO", "MODERADO"}][
                :8
            ],
        ),
        gates=gate_statuses(),
    )


def label_activation() -> LabelActivationResponse:
    return LabelActivationResponse(
        labels=[
            LabelActivationEntry(
                name=row["_label"].strip(),
                rate_idexx=round(float(row.get("idexx_rate", 0)), 4),
                rate_dap=round(float(row.get("dap_rate", 0)), 4),
                diagnosis=str(row.get("diagnosis", "")),
            )
            for row in analytics_cache().get("activation_rates", [])
            if row.get("_label", "").strip() not in HIDDEN_LABELS
        ]
    )


def temporal(
    granularity: Literal["week", "month"], period_days: int
) -> TemporalAnalyticsResponse:
    cutoff = datetime.now() - timedelta(days=period_days)
    records: list[tuple[datetime, dict[str, Any]]] = []
    for record in repository.list_analyses():
        created_at = parse_iso_datetime(record.get("created_at"))
        if created_at and created_at >= cutoff:
            records.append((created_at, record))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for created_at, record in records:
        iso = created_at.isocalendar()
        key = (
            created_at.strftime("%Y-%m")
            if granularity == "month"
            else f"{iso[0]}-W{iso[1]:02d}"
        )
        grouped.setdefault(key, []).append(record)
    timeline: list[TemporalPoint] = []
    for period, period_records in sorted(grouped.items()):
        confidences = [
            float(r.get("confidence", 0))
            for r in period_records
            if r.get("confidence") is not None
        ]
        findings: Counter = Counter(
            finding.get("label", "Sin hallazgos")
            for record in period_records
            for finding in record.get("findings", [])
            if finding.get("label") not in HIDDEN_LABELS
        )
        timeline.append(
            TemporalPoint(
                period=period,
                n_analyses=len(period_records),
                mean_confidence=round(
                    sum(confidences) / len(confidences) if confidences else 0, 3
                ),
                qc_flag_pct=round(
                    sum(bool(r.get("qc_flags")) for r in period_records)
                    / len(period_records),
                    3,
                ),
                top_finding=(
                    findings.most_common(1)[0][0] if findings else "Sin hallazgos"
                ),
            )
        )
    return TemporalAnalyticsResponse(
        timeline=timeline, granularity=granularity, period_days=period_days
    )


def breed_distribution(period_days: int) -> BreedDistributionResponse:
    breeds = repository.count_pet_breeds()
    total = sum(count for _, count in breeds)
    return BreedDistributionResponse(
        breeds=(
            [
                BreedEntry(name=name, count=count, pct=round(count / total * 100, 1))
                for name, count in breeds
            ]
            if total
            else []
        ),
        period_days=period_days,
        total=total,
    )
