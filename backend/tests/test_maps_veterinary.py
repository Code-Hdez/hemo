from __future__ import annotations

import asyncio

import httpx
import pytest
from fastapi import FastAPI

from app.modules.auth.compat import get_current_user_id
from app.modules.maps import router as maps_router
from app.modules.maps.schemas import VeterinaryPlaceOut
from app.modules.maps.service import (
    NearbyVeterinaryCareError,
    _veterinary_place_from_overpass,
    find_nearby_veterinary_care,
)
from app.modules.pets.exceptions import PetNotFoundError


def test_overpass_place_is_public_and_reports_distance() -> None:
    place = _veterinary_place_from_overpass(
        {"type": "node", "id": 123, "lat": 18.4861, "lon": -69.9313,
         "tags": {"amenity": "veterinary", "name": "Clínica Canina"}},
        lat=18.4850, lng=-69.9300,
    )
    assert place is not None
    assert place.name == "Clínica Canina"
    assert place.distance_meters > 0
    assert place.osm_url == "https://www.openstreetmap.org/node/123"


def test_nearby_veterinary_care_requires_location_consent() -> None:
    with pytest.raises(NearbyVeterinaryCareError, match="Activa la ubicación"):
        asyncio.run(
            find_nearby_veterinary_care(
                {"id": "pet-1", "residence_lat": 18.48, "residence_lng": -69.93}
            )
        )


def _maps_app() -> FastAPI:
    app = FastAPI()
    app.include_router(maps_router.router, prefix="/api/v1")

    async def current_user() -> str:
        return "owner-1"

    app.dependency_overrides[get_current_user_id] = current_user
    return app


def _post_nearby_care(payload: dict[str, object]) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=_maps_app())
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post(
                "/api/v1/residence/nearby-veterinary-care",
                json=payload,
            )

    return asyncio.run(request())


def test_nearby_veterinary_care_router_exposes_authenticated_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pet = {
        "id": "pet-1",
        "owner_id": "owner-1",
        "residence_consent_at": "2026-07-27T12:00:00",
        "residence_lat": 18.48,
        "residence_lng": -69.93,
        "residence_precision": "grid_2km",
    }
    monkeypatch.setattr(maps_router, "require_owned_pet", lambda *_: pet)

    async def immediate(function, *args):
        return function(*args)

    async def nearby_places(*_args, **_kwargs):
        return (
            [
                VeterinaryPlaceOut(
                    name="Clínica Canina",
                    lat=18.4861,
                    lng=-69.9313,
                    distance_meters=850,
                    address="Av. Principal",
                    osm_url="https://www.openstreetmap.org/node/123",
                )
            ],
            "openstreetmap",
            "https://www.openstreetmap.org/search?query=veterinaria",
        )

    monkeypatch.setattr(maps_router, "run_in_threadpool", immediate)
    monkeypatch.setattr(maps_router, "find_nearby_veterinary_care", nearby_places)

    response = _post_nearby_care(
        {"pet_id": "pet-1", "radius_meters": 5_000},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "name": "Clínica Canina",
                "lat": 18.4861,
                "lng": -69.9313,
                "distance_meters": 850,
                "address": "Av. Principal",
                "osm_url": "https://www.openstreetmap.org/node/123",
            }
        ],
        "source": "openstreetmap",
        "search_url": "https://www.openstreetmap.org/search?query=veterinaria",
        "location_precision": "grid_2km",
        "message": (
            "Estas son ubicaciones públicas aproximadas; llama antes de trasladarte."
        ),
    }


def test_nearby_veterinary_care_router_hides_unowned_pet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_pet(*_args):
        raise PetNotFoundError

    async def immediate(function, *args):
        return function(*args)

    monkeypatch.setattr(maps_router, "require_owned_pet", missing_pet)
    monkeypatch.setattr(maps_router, "run_in_threadpool", immediate)

    response = _post_nearby_care(
        {"pet_id": "other-pet", "radius_meters": 10_000},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Mascota no encontrada."}
