"""
Lógica de negocio para la vigilancia epidemiológica comunitaria.

Convierte los hallazgos de un análisis en eventos georeferenciados y los
agrega por zona de residencia de la mascota. La agregación aplica un jitter
configurable sobre las coordenadas para proteger la privacidad del dueño
antes de exponer los datos en el mapa público.

API pública
-----------
create_events_for_analysis(analysis, pet) -> int
sync_events_for_analysis(analysis, pet)  -> int
sync_events_for_pet(pet, analyses)       -> int
get_epidemiology_points(...)             -> list[EpidemiologyPoint]
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Literal

from app.core.config import settings

from .repository import (
    delete_events_for_analysis,
    delete_events_for_pet,
    list_events,
    list_analyses,
    save_events,
)
from .schemas import (
    EpidemiologyPoint,
    SurveillanceGeoPoint,
    SurveillanceReport,
    SurveillanceSignal,
)
from app.modules.dashboard import service as dashboard_service

_HIDDEN_FINDINGS = {"QC_REQUIERE_FROTIS", "Frotis recomendado"}
_SEVERITY_RANK = {"danger": 3, "warn": 2, "info": 1}
_PUBLIC_DISPLAY_DECIMALS = 2


def create_events_for_analysis(
    analysis: dict[str, Any], pet: dict[str, Any] | None
) -> int:
    """Sincroniza eventos epidemiologicos desde un analisis vinculado a mascota."""
    return sync_events_for_analysis(analysis, pet)


def sync_events_for_analysis(
    analysis: dict[str, Any], pet: dict[str, Any] | None
) -> int:
    """Reemplaza los eventos derivados de un analisis para evitar duplicados obsoletos."""
    analysis_id = str(analysis.get("id") or "")
    if analysis_id:
        delete_events_for_analysis(analysis_id)
    events = build_events_for_analysis(analysis, pet)
    return save_events(events)


def sync_events_for_pet(pet: dict[str, Any], analyses: list[dict[str, Any]]) -> int:
    """Reconstruye los eventos de una mascota al cambiar residencia o consentimiento."""
    pet_id = str(pet.get("id") or "")
    if pet_id:
        delete_events_for_pet(pet_id)

    events: list[dict] = []
    for analysis in analyses:
        events.extend(build_events_for_analysis(analysis, pet))
    return save_events(events)


def build_events_for_analysis(
    analysis: dict[str, Any], pet: dict[str, Any] | None
) -> list[dict]:
    if not pet or not pet.get("residence_consent_at"):
        return []
    if (
        not pet.get("residence_zone_code")
        or pet.get("residence_lat") is None
        or pet.get("residence_lng") is None
    ):
        return []

    analysis_id = analysis.get("id")
    if not analysis_id:
        return []

    occurred_at = _parse_datetime(analysis.get("created_at")) or datetime.now()
    findings = [
        item
        for item in (analysis.get("findings") or [])
        if isinstance(item, dict)
        and item.get("label")
        and item.get("label") not in _HIDDEN_FINDINGS
    ]

    events: list[dict] = []
    seen: set[str] = set()
    for finding in findings:
        label = str(finding.get("label") or "").strip()
        if not label or label in seen:
            continue
        seen.add(label)
        events.append(
            {
                "analysis_id": analysis_id,
                "pet_id": pet.get("id"),
                "zone_code": pet["residence_zone_code"],
                "zone_label": pet.get("residence_label") or pet["residence_zone_code"],
                "lat": float(pet["residence_lat"]),
                "lng": float(pet["residence_lng"]),
                "finding": label,
                "severity": _normalize_severity(finding.get("severity")),
                "occurred_at": occurred_at,
            }
        )
    return events


def get_epidemiology_points(
    *,
    finding: str | None = None,
    period_days: int = 90,
    min_count: int | None = None,
    min_pet_count: int | None = None,
) -> list[EpidemiologyPoint]:
    """Agrega eventos en celdas publicas amplias y aplica k-anonimato."""
    min_report_count = min_count if min_count is not None else _default_min_count()
    min_distinct_pets = (
        min_pet_count if min_pet_count is not None else _default_min_pet_count()
    )
    cutoff = datetime.now() - timedelta(days=period_days)
    finding_filter = _norm(finding)

    grouped: dict[str, dict[str, Any]] = {}
    for event in list_events(limit=10000, offset=0):
        occurred_at = _parse_datetime(event.get("occurred_at"))
        if occurred_at is not None and occurred_at < cutoff:
            continue
        if finding_filter and _norm(event.get("finding")) != finding_filter:
            continue

        zone_code = str(event.get("zone_code") or "")
        event_finding = str(event.get("finding") or "")
        if not zone_code or not event_finding:
            continue
        try:
            event_lat = float(event.get("lat"))
            event_lng = float(event.get("lng"))
        except (TypeError, ValueError):
            continue

        public_zone_code, public_lat, public_lng = _public_zone(event_lat, event_lng)
        current = grouped.get(public_zone_code)
        if current is None:
            zone_label = _public_zone_label(public_zone_code, event.get("zone_label"))
            grouped[public_zone_code] = {
                "zone_code": public_zone_code,
                "zone_label": zone_label,
                "lat": public_lat,
                "lng": public_lng,
                "analysis_ids": set(),
                "pet_ids": set(),
                "pet_coords": {},
                "finding_counts": defaultdict(int),
                "severity_counts": defaultdict(int),
            }
            current = grouped[public_zone_code]
        analysis_id = str(event.get("analysis_id") or event.get("id") or "")
        if analysis_id:
            current["analysis_ids"].add(analysis_id)
        pet_id = str(event.get("pet_id") or "")
        if pet_id:
            current["pet_ids"].add(pet_id)
            current["pet_coords"].setdefault(pet_id, (event_lat, event_lng))
        elif analysis_id:
            current["pet_coords"].setdefault(
                f"analysis:{analysis_id}", (event_lat, event_lng)
            )
        current["finding_counts"][event_finding] += 1
        current["severity_counts"][_normalize_severity(event.get("severity"))] += 1

    points: list[EpidemiologyPoint] = []
    for item in grouped.values():
        report_count = len(item["analysis_ids"])
        pet_count = len(item["pet_ids"])
        if report_count < min_report_count or pet_count < min_distinct_pets:
            continue
        severity = _top_severity(item["severity_counts"])
        top_finding = _top_finding(item["finding_counts"])
        intensity_level, intensity_score = _intensity(
            report_count, pet_count, item["severity_counts"]
        )
        display_lat, display_lng = _display_center(item)
        points.append(
            EpidemiologyPoint(
                zone_code=item["zone_code"],
                zone_label=item["zone_label"],
                lat=display_lat,
                lng=display_lng,
                finding=top_finding,
                count=int(report_count),
                report_count=int(report_count),
                pet_count=int(pet_count),
                intensity_level=intensity_level,
                intensity_score=intensity_score,
                severity=severity,
                location_name=item["zone_label"],
            )
        )

    return sorted(
        points, key=lambda point: (-point.count, point.zone_label, point.finding)
    )


def _default_min_count() -> int:
    return max(1, settings.MAP_MIN_ZONE_COUNT)


def _default_min_pet_count() -> int:
    return max(1, settings.MAP_MIN_DISTINCT_PETS)


def _public_grid_degrees() -> float:
    return min(0.15, max(0.03, settings.MAP_PUBLIC_GRID_DEGREES))


def _public_zone(lat: float, lng: float) -> tuple[str, float, float]:
    grid = _public_grid_degrees()
    lat_idx = math.floor(lat / grid)
    lng_idx = math.floor(lng / grid)
    center_lat = round((lat_idx + 0.5) * grid, 5)
    center_lng = round((lng_idx + 0.5) * grid, 5)
    zone_code = f"do-public-grid-{_encode_index(lat_idx)}-{_encode_index(lng_idx)}"
    return zone_code, center_lat, center_lng


def _display_center(item: dict[str, Any]) -> tuple[float, float]:
    coords = list((item.get("pet_coords") or {}).values())
    if not coords:
        return float(item["lat"]), float(item["lng"])
    avg_lat = sum(lat for lat, _ in coords) / len(coords)
    avg_lng = sum(lng for _, lng in coords) / len(coords)
    return round(avg_lat, _PUBLIC_DISPLAY_DECIMALS), round(
        avg_lng, _PUBLIC_DISPLAY_DECIMALS
    )


def _public_zone_label(zone_code: str, source_label: Any) -> str:
    source = str(source_label or "").strip()
    base = source.split(" - zona ")[0].strip() if source else "Republica Dominicana"
    suffix = hashlib.sha1(zone_code.encode("utf-8")).hexdigest()[:4].upper()
    return f"{base} - zona {suffix}"


def _intensity(
    report_count: int, pet_count: int, severity_counts: dict[str, int]
) -> tuple[str, float]:
    total_events = sum(severity_counts.values())
    danger_share = (
        (severity_counts.get("danger", 0) / total_events) if total_events else 0.0
    )
    score = round((report_count * 0.45) + (pet_count * 0.45) + (danger_share * 4), 2)
    if pet_count >= 8 or (pet_count >= 6 and danger_share >= 0.5):
        return "high", score
    if (
        pet_count >= 5
        or (pet_count >= 4 and report_count >= 10)
        or (pet_count >= 4 and danger_share >= 0.5)
    ):
        return "moderate", score
    return "low", score


def _encode_index(value: int) -> str:
    return f"p{value}" if value >= 0 else f"m{abs(value)}"


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


def _normalize_severity(value: Any) -> str:
    severity = str(value or "info").lower()
    return severity if severity in _SEVERITY_RANK else "info"


def _top_severity(counts: dict[str, int]) -> str:
    if not counts:
        return "info"
    return max(
        counts, key=lambda severity: (_SEVERITY_RANK.get(severity, 0), counts[severity])
    )


def _top_finding(counts: dict[str, int]) -> str:
    if not counts:
        return "Hallazgos registrados"
    return max(counts, key=lambda finding: (counts[finding], finding))


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def surveillance_report(period_days: int) -> SurveillanceReport:
    """Build a population-level operational report from persisted analyses."""
    now = datetime.now()
    cutoff = now - timedelta(days=period_days)
    timeline = [
        (created_at, record)
        for record in list_analyses()
        if (created_at := _parse_datetime(record.get("created_at"))) is not None
    ]
    recent = [record for created_at, record in timeline if created_at >= cutoff]
    baseline = [record for created_at, record in timeline if created_at < cutoff]
    if not recent:
        recent = [
            record
            for _, record in sorted(timeline, key=lambda item: item[0], reverse=True)[
                :200
            ]
        ]
    if not baseline:
        baseline = list(recent)

    def rate(records: list[dict], predicate) -> float:
        return (
            sum(bool(predicate(record)) for record in records) / len(records)
            if records
            else 0.0
        )

    no_prediction = rate(recent, lambda record: record.get("status") == "no_prediction")
    no_prediction_base = rate(
        baseline, lambda record: record.get("status") == "no_prediction"
    )
    partial = rate(recent, lambda record: record.get("status") == "partial_imputation")
    partial_base = rate(
        baseline, lambda record: record.get("status") == "partial_imputation"
    )
    qc_flags = rate(recent, lambda record: bool(record.get("qc_flags")))
    qc_flags_base = rate(baseline, lambda record: bool(record.get("qc_flags")))
    geocoded = rate(
        recent,
        lambda record: record.get("latitude") is not None
        and record.get("longitude") is not None,
    )
    locations: Counter[str] = Counter(
        str(record.get("location") or "Desconocida").strip() or "Desconocida"
        for record in recent
    )
    top_share = max(locations.values()) / len(recent) if locations and recent else 0.0
    signals = [
        SurveillanceSignal(
            metric="no_prediction_rate",
            value=round(no_prediction, 4),
            baseline=round(no_prediction_base, 4),
            status=_status(no_prediction, no_prediction_base, 0.10, 0.20, 0.05, 0.10),
            action="Revisar salud de artefactos, disponibilidad de modelo y calidad de parsing del extractor.",
        ),
        SurveillanceSignal(
            metric="partial_imputation_rate",
            value=round(partial, 4),
            baseline=round(partial_base, 4),
            status=_status(partial, partial_base, 0.15, 0.30, 0.07, 0.12),
            action="Auditar cobertura de campos CBC nucleares por fuente y reforzar normalizacion de ingesta.",
        ),
        SurveillanceSignal(
            metric="qc_flag_rate",
            value=round(qc_flags, 4),
            baseline=round(qc_flags_base, 4),
            status=_status(qc_flags, qc_flags_base, 0.45, 0.65, 0.10, 0.20),
            action="Escalar revision de laboratorio: reforzar control pre-analitico y trazabilidad de muestras.",
        ),
        SurveillanceSignal(
            metric="geocoded_rate",
            value=round(geocoded, 4),
            baseline=None,
            status="pass" if not recent else "warn" if geocoded < 0.70 else "pass",
            action="Mejorar captura de ubicacion para vigilancia geoespacial reproducible.",
        ),
        SurveillanceSignal(
            metric="top_location_share",
            value=round(top_share, 4),
            baseline=None,
            status=(
                "pass"
                if not recent
                else "warn"
                if geocoded == 0
                else (
                    "fail"
                    if top_share > 0.75
                    else "warn" if top_share > 0.55 else "pass"
                )
            ),
            action="Verificar sesgo de muestreo geografico y ampliar cobertura territorial de captura.",
        ),
    ]
    counts = Counter(signal.status for signal in signals)
    overall: Literal["pass", "warn", "fail"] = (
        "fail" if counts["fail"] else "warn" if counts["warn"] else "pass"
    )
    return SurveillanceReport(
        generated_at=now.isoformat(),
        period_days=period_days,
        cohort_size=len(recent),
        status=overall,
        status_counts={
            key: int(counts.get(key, 0)) for key in ("pass", "warn", "fail")
        },
        temporal_signals=signals,
        geographic_hotspots=[
            SurveillanceGeoPoint(
                location=location, count=count, pct=round(count / len(recent), 4)
            )
            for location, count in locations.most_common(10)
        ],
        gate_status=dashboard_service.gate_statuses(),
    )


def _status(
    value: float,
    baseline: float,
    warn_abs: float,
    fail_abs: float,
    warn_delta: float,
    fail_delta: float,
) -> Literal["pass", "warn", "fail"]:
    delta = value - baseline
    if value >= fail_abs or delta >= fail_delta:
        return "fail"
    if value >= warn_abs or delta >= warn_delta:
        return "warn"
    return "pass"
