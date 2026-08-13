from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_principal
from app.db.session import get_db
from app.modules.users.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)


async def get_current_user_id(
    request: Request,
    bearer_token: str | None = Depends(optional_oauth2_scheme),
) -> str:
    token = request.cookies.get("hemovet_session") or bearer_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    principal = decode_access_principal(token)
    request.state.auth_session_id = principal.session_id
    return principal.user_id


async def get_optional_user_id(
    request: Request,
    bearer_token: str | None = Depends(optional_oauth2_scheme),
) -> str | None:
    token = request.cookies.get("hemovet_session") or bearer_token
    if not token:
        return None
    try:
        principal = decode_access_principal(token)
        request.state.auth_session_id = principal.session_id
        return principal.user_id
    except HTTPException:
        return None


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=403, detail="No tienes permiso para ver el panel tecnico."
        )
    return user
