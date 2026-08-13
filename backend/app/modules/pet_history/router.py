"""HTTP endpoints for persisted hematology history."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.modules.auth.compat import get_current_user_id, get_optional_user_id
from app.modules.hematology.schemas import AnalysisResult
from app.modules.pet_history import service

router = APIRouter(tags=["Pet History"])


@router.get("/history", response_model=list[AnalysisResult])
def get_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    pet_id: str | None = Query(default=None),
    user_id: str = Depends(get_current_user_id),
) -> list[dict]:
    return service.list_history(user_id, pet_id=pet_id, limit=limit, offset=offset)


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult)
def get_analysis(
    analysis_id: str,
    user_id: str | None = Depends(get_optional_user_id),
) -> dict:
    try:
        return service.get_analysis(analysis_id, user_id)
    except service.AnalysisNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )
    except service.AuthenticationRequiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para ver este análisis guardado.",
        )
    except service.AnalysisAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este análisis.",
        )
