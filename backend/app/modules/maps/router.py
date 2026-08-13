from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.modules.auth.compat import get_current_user_id
from app.modules.pets.exceptions import PetNotFoundError
from app.modules.pets.service import require_owned_pet

from .repository import list_residence_zones
from .schemas import (
    NearbyVeterinaryCareRequest,
    NearbyVeterinaryCareResponse,
    ResidenceCandidateOut,
    ResidenceResolveRequest,
    ResidenceZoneOut,
)
from .service import (
    NearbyVeterinaryCareError,
    ResidenceValidationError,
    find_nearby_veterinary_care,
    resolve_address_candidates,
)

router = APIRouter(prefix="/residence", tags=["Residence"])


@router.get("/zones", response_model=list[ResidenceZoneOut])
def get_residence_zones() -> list[ResidenceZoneOut]:
    """Catalogo publico de zonas aproximadas disponibles para residencia."""
    return list_residence_zones()


@router.post("/resolve", response_model=list[ResidenceCandidateOut])
async def resolve_residence(
    body: ResidenceResolveRequest,
) -> list[ResidenceCandidateOut]:
    """Busca candidatos de dirección sin persistir la dirección exacta."""
    try:
        return await resolve_address_candidates(body.query, limit=body.limit)
    except ResidenceValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


@router.post("/nearby-veterinary-care", response_model=NearbyVeterinaryCareResponse)
async def nearby_veterinary_care(
    body: NearbyVeterinaryCareRequest,
    user_id: str = Depends(get_current_user_id),
) -> NearbyVeterinaryCareResponse:
    try:
        pet = await run_in_threadpool(require_owned_pet, body.pet_id, user_id)
        items, source, search_url = await find_nearby_veterinary_care(
            pet, radius_meters=body.radius_meters
        )
    except PetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mascota no encontrada.",
        ) from exc
    except NearbyVeterinaryCareError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return NearbyVeterinaryCareResponse(
        items=items,
        source=source,
        search_url=search_url,
        location_precision=str(pet.get("residence_precision") or "approximate"),
        message=(
            "Estas son ubicaciones públicas aproximadas; llama antes de trasladarte."
            if items
            else "No se pudieron confirmar centros ahora. Usa la búsqueda de OpenStreetMap o contacta un servicio local."
        ),
    )
