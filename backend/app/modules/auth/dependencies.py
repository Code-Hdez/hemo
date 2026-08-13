"""Authentication and authorization dependencies."""

from typing import Any

from fastapi import Depends, HTTPException, status

from app.modules.auth import compat as security
from app.modules.auth import repository


def require_admin(
    user_id: str = Depends(security.get_current_user_id),
) -> dict[str, Any]:
    user = repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )
    if user.get("role", "user") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver el panel tecnico.",
        )
    return user
