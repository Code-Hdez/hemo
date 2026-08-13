"""
Servicio de resolución y validación de residencia geográfica de mascotas.

Valida que las coordenadas o el código de zona suministrado correspondan al
territorio de la República Dominicana, calcula la precisión del punto y
construye los campos de residencia que se persisten en la tabla `pets`.

API pública
-----------
build_pet_residence_fields(zone_code, lat, lng, source, consent) -> dict
    Lanza ResidenceValidationError si los datos no son procesables.
search_residence_zones(query, limit)                               -> list[ResidenceCandidateOut]
"""

from __future__ import annotations

import hashlib
import logging
import math
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import httpx

from app.core.config import settings

from .repository import get_residence_zone, list_residence_zones
from .schemas import ResidenceCandidateOut, VeterinaryPlaceOut

logger = logging.getLogger("hemovet.residence")

_DR_MIN_LAT = 17.45
_DR_MAX_LAT = 20.10
_DR_MIN_LNG = -72.10
_DR_MAX_LNG = -68.00


class ResidenceValidationError(ValueError):
    pass


class NearbyVeterinaryCareError(ValueError):
    pass


def build_pet_residence_fields(
    *,
    zone_code: str | None,
    lat: float | None = None,
    lng: float | None = None,
    source: str | None = None,
    consent: bool | None,
) -> dict:
    """Convierte residencia consentida en campos aproximados seguros."""
    if consent is not True:
        return _empty_residence_fields()

    if lat is not None or lng is not None:
        if lat is None or lng is None:
            raise ResidenceValidationError(
                "Selecciona una ubicación válida en el mapa."
            )
        return _build_aggregated_residence_fields(lat=lat, lng=lng, source=source)

    zone = get_residence_zone(zone_code)
    if zone is None:
        raise ResidenceValidationError(
            "Selecciona una ubicación válida para participar en el mapa comunitario."
        )

    return {
        "residence_zone_code": zone.code,
        "residence_label": zone.label,
        "residence_lat": zone.lat,
        "residence_lng": zone.lng,
        "residence_precision": zone.precision,
        "residence_consent_at": datetime.now(),
    }


async def resolve_address_candidates(
    query: str, limit: int = 5
) -> list[ResidenceCandidateOut]:
    """Busca direcciones dominicanas. No persiste ni retorna nada automáticamente a BD."""
    normalized = " ".join(str(query or "").split())
    if len(normalized) < 3:
        raise ResidenceValidationError(
            "Escribe una dirección o sector con al menos 3 caracteres."
        )

    if not settings.RESIDENCE_GEOCODER_ENABLED:
        return _catalog_candidates(normalized, limit)

    timeout = settings.RESIDENCE_GEOCODER_TIMEOUT_SECONDS
    endpoint = settings.RESIDENCE_GEOCODER_URL
    user_agent = settings.RESIDENCE_GEOCODER_USER_AGENT
    query_text = normalized
    if (
        "dominicana" not in query_text.lower()
        and "dominican republic" not in query_text.lower()
    ):
        query_text = f"{query_text}, República Dominicana"

    params = {
        "q": query_text,
        "format": "jsonv2",
        "addressdetails": "1",
        "countrycodes": "do",
        "limit": str(max(1, min(int(limit), 8))),
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers={"User-Agent": user_agent}
        ) as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.info(
            "residence.geocoder.failed query_len=%d error=%s", len(normalized), exc
        )
        return _catalog_candidates(normalized, limit)

    candidates: list[ResidenceCandidateOut] = []
    for item in payload if isinstance(payload, list) else []:
        candidate = _candidate_from_geocoder_item(item)
        if candidate is not None:
            candidates.append(candidate)
    return candidates or _catalog_candidates(normalized, limit)


async def find_nearby_veterinary_care(
    pet: dict[str, Any], *, radius_meters: int = 10_000
) -> tuple[list[VeterinaryPlaceOut], str, str]:
    """Busca POIs veterinarios públicos sin revelar la ubicación de la mascota."""
    if not pet.get("residence_consent_at"):
        raise NearbyVeterinaryCareError(
            "Activa la ubicación aproximada de tu mascota para buscar atención cercana."
        )
    try:
        lat = float(pet["residence_lat"])
        lng = float(pet["residence_lng"])
    except (KeyError, TypeError, ValueError):
        raise NearbyVeterinaryCareError(
            "No hay una ubicación aproximada utilizable para esta mascota."
        )
    if not _is_inside_dr_bounds(lat, lng):
        raise NearbyVeterinaryCareError("La ubicación aproximada no es válida.")

    radius = max(1_000, min(int(radius_meters), 25_000))
    label = str(pet.get("residence_label") or "República Dominicana")
    search_url = "https://www.openstreetmap.org/search?query=" + quote_plus(
        f"veterinaria {label}"
    )
    endpoint = settings.VETERINARY_PLACES_OVERPASS_URL
    timeout = min(
        30.0,
        max(1.0, settings.VETERINARY_PLACES_TIMEOUT_SECONDS),
    )
    query_timeout = max(1, math.ceil(timeout))
    query = f"""[out:json][timeout:{query_timeout}];
    (node[\"amenity\"=\"veterinary\"](around:{radius},{lat:.5f},{lng:.5f});
     way[\"amenity\"=\"veterinary\"](around:{radius},{lat:.5f},{lng:.5f});
     relation[\"amenity\"=\"veterinary\"](around:{radius},{lat:.5f},{lng:.5f}););
    out center tags;"""
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": settings.RESIDENCE_GEOCODER_USER_AGENT},
        ) as client:
            response = await client.post(endpoint, data={"data": query})
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        logger.info("veterinary_places.lookup_failed error=%s", exc)
        return [], "openstreetmap_unavailable", search_url

    places = [
        place
        for item in (payload.get("elements", []) if isinstance(payload, dict) else [])
        for place in [_veterinary_place_from_overpass(item, lat=lat, lng=lng)]
        if place is not None
    ]
    places.sort(key=lambda place: (place.distance_meters, place.name.lower()))
    return places[:12], "openstreetmap", search_url


def _catalog_candidates(query: str, limit: int) -> list[ResidenceCandidateOut]:
    terms = [term for term in query.lower().split() if len(term) >= 3]
    matches = []
    for zone in list_residence_zones():
        haystack = f"{zone.label} {zone.municipality} {zone.province}".lower()
        if terms and all(term in haystack for term in terms):
            matches.append(
                ResidenceCandidateOut(
                    id=f"catalog-{zone.code}",
                    label=zone.label,
                    lat=zone.lat,
                    lng=zone.lng,
                    precision=zone.precision,
                    source="catalog",
                )
            )
    return matches[: max(1, min(int(limit), 8))]


def _veterinary_place_from_overpass(
    item: Any, *, lat: float, lng: float
) -> VeterinaryPlaceOut | None:
    if not isinstance(item, dict) or item.get("id") is None:
        return None
    tags = item.get("tags") if isinstance(item.get("tags"), dict) else {}
    try:
        place_lat = float(item.get("lat", item.get("center", {}).get("lat")))
        place_lng = float(item.get("lon", item.get("center", {}).get("lon")))
    except (TypeError, ValueError, AttributeError):
        return None
    address = ", ".join(
        str(value).strip()
        for value in (
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
            tags.get("addr:city"),
        )
        if value
    )
    return VeterinaryPlaceOut(
        name=str(tags.get("name") or "Centro veterinario"),
        lat=round(place_lat, 6),
        lng=round(place_lng, 6),
        distance_meters=round(_haversine_meters(lat, lng, place_lat, place_lng)),
        address=address or None,
        osm_url=f"https://www.openstreetmap.org/{item.get('type') or 'node'}/{item['id']}",
    )


def _empty_residence_fields() -> dict:
    return {
        "residence_zone_code": None,
        "residence_label": None,
        "residence_lat": None,
        "residence_lng": None,
        "residence_precision": None,
        "residence_consent_at": None,
    }


def _build_aggregated_residence_fields(
    *, lat: float, lng: float, source: str | None
) -> dict:
    lat_f = _coerce_coordinate(lat, "latitud")
    lng_f = _coerce_coordinate(lng, "longitud")
    if not _is_inside_dr_bounds(lat_f, lng_f):
        raise ResidenceValidationError(
            "La ubicación debe estar dentro de República Dominicana."
        )

    grid = _grid_degrees()
    lat_idx = math.floor(lat_f / grid)
    lng_idx = math.floor(lng_f / grid)
    center_lat = round((lat_idx + 0.5) * grid, 5)
    center_lng = round((lng_idx + 0.5) * grid, 5)
    zone_code = f"do-grid-{_encode_index(lat_idx)}-{_encode_index(lng_idx)}"
    label = _public_zone_label(zone_code, center_lat, center_lng)
    approx_km = max(1, round(grid * 111))

    return {
        "residence_zone_code": zone_code,
        "residence_label": label,
        "residence_lat": center_lat,
        "residence_lng": center_lng,
        "residence_precision": f"grid_{approx_km}km",
        "residence_consent_at": datetime.now(),
    }


def _candidate_from_geocoder_item(item: Any) -> ResidenceCandidateOut | None:
    if not isinstance(item, dict):
        return None
    try:
        lat = float(item.get("lat"))
        lng = float(item.get("lon"))
    except (TypeError, ValueError):
        return None
    if not _is_inside_dr_bounds(lat, lng):
        return None

    address = item.get("address") if isinstance(item.get("address"), dict) else {}
    label = _candidate_label(item, address)
    raw_id = str(item.get("place_id") or f"{label}|{lat:.6f}|{lng:.6f}")
    candidate_id = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]
    precision = str(item.get("type") or item.get("class") or "address")

    return ResidenceCandidateOut(
        id=candidate_id,
        label=label,
        lat=lat,
        lng=lng,
        precision=precision,
        source="nominatim",
    )


def _candidate_label(item: dict[str, Any], address: dict[str, Any]) -> str:
    parts = [
        address.get("road"),
        address.get("neighbourhood") or address.get("suburb") or address.get("quarter"),
        address.get("city")
        or address.get("town")
        or address.get("municipality")
        or address.get("village"),
        address.get("state"),
    ]
    clean_parts = [str(part).strip() for part in parts if str(part or "").strip()]
    if clean_parts:
        return ", ".join(dict.fromkeys(clean_parts))
    return str(item.get("display_name") or "Ubicacion encontrada").strip()


def _public_zone_label(zone_code: str, lat: float, lng: float) -> str:
    nearest = _nearest_catalog_zone(lat, lng)
    area = nearest.municipality if nearest is not None else "República Dominicana"
    suffix = hashlib.sha1(zone_code.encode("utf-8")).hexdigest()[:4].upper()
    return f"{area} - zona {suffix}"


def _nearest_catalog_zone(lat: float, lng: float):
    zones = list_residence_zones()
    if not zones:
        return None
    return min(zones, key=lambda zone: _distance_sq(lat, lng, zone.lat, zone.lng))


def _distance_sq(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    lng_scale = math.cos(math.radians((lat_a + lat_b) / 2))
    return (lat_a - lat_b) ** 2 + ((lng_a - lng_b) * lng_scale) ** 2


def _haversine_meters(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    radius_m = 6_371_000
    lat_delta = math.radians(lat_b - lat_a)
    lng_delta = math.radians(lng_b - lng_a)
    value = (
        math.sin(lat_delta / 2) ** 2
        + math.cos(math.radians(lat_a))
        * math.cos(math.radians(lat_b))
        * math.sin(lng_delta / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(value))


def _coerce_coordinate(value: float, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ResidenceValidationError(f"La {label} seleccionada no es válida.")
    if not math.isfinite(number):
        raise ResidenceValidationError(f"La {label} seleccionada no es válida.")
    return number


def _is_inside_dr_bounds(lat: float, lng: float) -> bool:
    return _DR_MIN_LAT <= lat <= _DR_MAX_LAT and _DR_MIN_LNG <= lng <= _DR_MAX_LNG


def _grid_degrees() -> float:
    return min(0.25, max(0.005, settings.MAP_AGGREGATION_GRID_DEGREES))


def _encode_index(value: int) -> str:
    return f"p{value}" if value >= 0 else f"m{abs(value)}"
