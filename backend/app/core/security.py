from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import hashlib
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(value: str) -> str:
    return _password_context.hash(value)


def verify_password(value: str, hashed: str) -> bool:
    return _password_context.verify(value, hashed)


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    user_id: str
    session_id: str


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    *,
    session_id: str | None = None,
) -> str:
    expires = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {"sub": subject, "sid": session_id or str(uuid4()), "exp": expires},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_principal(token: str) -> AuthPrincipal:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=401, detail="Token sin identificador de usuario."
        )
    sid = payload.get("sid")
    if not sid:
        # Transitional tokens remain isolated by token without exposing the token itself.
        sid = hashlib.sha256(token.encode("utf-8")).hexdigest()[:36]
    return AuthPrincipal(user_id=str(subject), session_id=str(sid)[:36])


def decode_access_token(token: str) -> str:
    return decode_access_principal(token).user_id
