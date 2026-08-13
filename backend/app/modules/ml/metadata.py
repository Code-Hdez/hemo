"""Helpers de trazabilidad para cohortes, fechas y geografia de hemogramas."""

from __future__ import annotations

import csv
import hashlib
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_DOG_ID_SALT = "hemovet-dog-id-v1"
DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S")


@dataclass(frozen=True)
class LocationResolution:
    raw_location_text: str
    city: str | None
    province: str | None
    latitude: float | None
    longitude: float | None
    location_source: str
    location_confidence: float


def normalize_text(value: Any) -> str:
    """Normaliza texto para llaves estables sin conservar acentos ni puntuacion."""
    if value is None:
        return ""
    try:
        if value != value:  # NaN sin depender de pandas
            return ""
    except Exception:
        pass
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def parse_hemogram_date(raw_value: Any) -> datetime | None:
    """Parsea fechas IDEXX historicas de 2 o 4 digitos, ISO date e ISO datetime."""
    text = str(raw_value or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def coalesce_sample_date(metadata: dict[str, Any]) -> datetime | None:
    """Elige la fecha clinica oficial de un hemograma, preferiendo resultado a recepcion."""
    return (
        parse_hemogram_date(metadata.get("date_result"))
        or parse_hemogram_date(metadata.get("date_receipt"))
        or parse_hemogram_date(metadata.get("sample_date"))
    )


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_ingestion_cohort(relative_path: str | Path) -> str:
    """Infiere cohortes conocidas desde la ruta relativa del PDF."""
    parts = [
        normalize_text(part).replace(" ", "_") for part in Path(relative_path).parts
    ]
    if "dic_may" in parts or "dic-may" in parts:
        return "dic_may_2026"
    if parts and parts[0] == "sin_limpieza":
        return "baseline_historico"
    return "unknown"


def make_record_id(
    *,
    source_dataset: Any,
    source_relative_path: Any = "",
    file_hash: Any = "",
    page_number: Any = "",
    patient_name: Any = "",
    sample_date: Any = "",
    existing_id: Any = "",
) -> str:
    """Crea un ID de hemograma estable; conserva IDs existentes cuando ya son utiles."""
    existing = str(existing_id or "").strip()
    if existing:
        return existing
    parts = [
        normalize_text(source_dataset),
        str(source_relative_path or ""),
        str(file_hash or ""),
        str(page_number or ""),
        normalize_text(patient_name),
        str(sample_date or ""),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]


def make_dog_id(
    *,
    patient_name: Any,
    pet_owner: Any = "",
    clinic: Any = "",
    source_dataset: Any = "IDEXX",
    fallback: Any = "",
    salt: str | None = None,
) -> str:
    """Agrupa visitas del mismo perro con hash irreversible y sal configurable."""
    resolved_salt = salt or os.getenv("HEMOVET_DOG_ID_SALT", DEFAULT_DOG_ID_SALT)
    key_parts = [
        normalize_text(source_dataset),
        normalize_text(patient_name),
        normalize_text(pet_owner),
        normalize_text(clinic),
    ]
    if not any(key_parts[1:]):
        key_parts.append(normalize_text(fallback))
    digest = hashlib.sha256((resolved_salt + "|" + "|".join(key_parts)).encode("utf-8"))
    return digest.hexdigest()[:20]


def read_location_overrides(path: Path) -> dict[str, dict[str, str]]:
    """Lee overrides por texto de ubicacion/clinica; retorna mapa normalizado."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    overrides: dict[str, dict[str, str]] = {}
    for row in rows:
        keys = [
            normalize_text(row.get("raw_location_text")),
            normalize_text(row.get("clinic")),
        ]
        for key in keys:
            if key:
                overrides[key] = row
    return overrides


def resolve_location_metadata(
    raw_location_text: Any,
    *,
    clinic: Any = "",
    overrides: dict[str, dict[str, str]] | None = None,
    geocode_fn: Any = None,
) -> LocationResolution:
    """Resuelve ciudad/coordenadas desde overrides manuales y geocoder local."""
    raw = str(raw_location_text or clinic or "").strip()
    normalized_keys = [normalize_text(raw), normalize_text(clinic)]
    overrides = overrides or {}

    for key in normalized_keys:
        row = overrides.get(key)
        if not row:
            continue
        lat = _float_or_none(row.get("latitude") or row.get("lat"))
        lon = _float_or_none(row.get("longitude") or row.get("lon") or row.get("lng"))
        confidence = _float_or_none(row.get("confidence")) or (
            0.95 if lat is not None and lon is not None else 0.7
        )
        return LocationResolution(
            raw_location_text=raw,
            city=_blank_to_none(row.get("city")),
            province=_blank_to_none(row.get("province")),
            latitude=lat,
            longitude=lon,
            location_source="manual_override",
            location_confidence=confidence,
        )

    if geocode_fn and raw:
        coords = geocode_fn(raw)
        if coords:
            return LocationResolution(
                raw_location_text=raw,
                city=None,
                province=None,
                latitude=float(coords[0]),
                longitude=float(coords[1]),
                location_source="local_geocoder",
                location_confidence=0.6,
            )

    return LocationResolution(
        raw_location_text=raw,
        city=None,
        province=None,
        latitude=None,
        longitude=None,
        location_source="unresolved" if raw else "missing",
        location_confidence=0.0,
    )


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _blank_to_none(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
