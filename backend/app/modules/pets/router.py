"""Pet HTTP endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.modules.auth.compat import get_current_user_id
from app.modules.pets import repository, service
from app.modules.pets.exceptions import InvalidResidenceError, PetNotFoundError
from app.modules.pets.schemas import (
    PetCreate,
    PetProfileExtractionResponse,
    PetResponse,
)

router = APIRouter(tags=["Pets"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Mascota no encontrada.",
    )


@router.get("/breeds", response_model=list[str])
def list_breeds() -> list[str]:
    return repository.list_breeds()


@router.get("/pets", response_model=list[PetResponse])
def list_pets(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    return service.list_pets(user_id)


@router.post("/pets", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
def create_pet(
    body: PetCreate,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        return service.create_pet(body, user_id)
    except InvalidResidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.post("/pets/extract-profile", response_model=PetProfileExtractionResponse)
async def extract_pet_profile(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> PetProfileExtractionResponse:
    del user_id
    try:
        return await run_in_threadpool(
            service.extract_profile_from_file,
            contents=await file.read(),
            content_type=file.content_type or "",
            filename=file.filename,
        )
    except service.PetProfileExtractionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    finally:
        await file.close()


@router.get("/pets/{pet_id}", response_model=PetResponse)
def get_pet(pet_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    try:
        return service.get_pet(pet_id, user_id)
    except PetNotFoundError:
        raise _not_found()


@router.put("/pets/{pet_id}", response_model=PetResponse)
def update_pet(
    pet_id: str,
    body: PetCreate,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        return service.update_pet(pet_id, body, user_id)
    except PetNotFoundError:
        raise _not_found()
    except InvalidResidenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.post("/pets/{pet_id}/photo", response_model=PetResponse)
async def upload_pet_photo(
    pet_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        return await service.save_photo(pet_id, file, user_id)
    except PetNotFoundError:
        raise _not_found()
    except service.PetPhotoError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.delete("/pets/{pet_id}/photo", response_model=PetResponse)
def delete_pet_photo(
    pet_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        return service.delete_photo(pet_id, user_id)
    except PetNotFoundError:
        raise _not_found()


@router.delete("/pets/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(pet_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    try:
        service.delete_pet(pet_id, user_id)
    except PetNotFoundError:
        raise _not_found()
