"""Authentication HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.modules.llm_chat.models import ChatSession
from app.shared.dates import utc_now
from app.modules.auth import compat as security
from app.modules.auth import service
from app.modules.auth.schemas import (
    OnboardingTourUpdateRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(body: RegisterRequest) -> UserResponse:
    try:
        return service.register_user(
            email=str(body.email),
            password=body.password,
            full_name=body.full_name,
        )
    except service.EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese email.",
        )
    except service.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )


@router.post("/login", response_model=TokenResponse)
def login(response: Response, form: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    try:
        token = service.authenticate(form.username, form.password)
        response.set_cookie(
            key="hemovet_session",
            value=token.access_token,
            httponly=True,
            secure=settings.APP_ENV == "production",
            samesite="lax",
            path="/",
        )
        return token
    except service.InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    user_id: str = Depends(security.get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    auth_session_id = getattr(request.state, "auth_session_id", None)
    if auth_session_id:
        # Closed, not deleted. `chat_messages.session_id` and
        # `chat_turns.session_id` are ON DELETE CASCADE, so removing the
        # ChatSession row here permanently destroyed every transcript of that
        # login — the exact invariant the chat repository documents it must
        # never break ("it must never hard-delete a ChatSession row, because
        # that cascades ... and permanently destroys the transcript",
        # sqlalchemy_repositories.get_or_create). It is also the most likely
        # reason the assistant "forgets" past conversations between sessions.
        # `status` is already the soft filter both `get_or_create` and
        # `list_active` use, so closing here keeps the session out of
        # automatic resolution while the history survives in PostgreSQL.
        db.execute(
            update(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.auth_session_id == str(auth_session_id),
                ChatSession.status == "active",
            )
            .values(status="closed", updated_at=utc_now())
        )
        db.commit()
    response.delete_cookie("hemovet_session", path="/", samesite="lax")


@router.get("/me", response_model=UserResponse)
def me(user_id: str = Depends(security.get_current_user_id)) -> UserResponse:
    try:
        return service.get_user(user_id)
    except service.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )


@router.patch("/me/onboarding-tour", response_model=UserResponse)
def update_onboarding_tour(
    body: OnboardingTourUpdateRequest,
    user_id: str = Depends(security.get_current_user_id),
) -> UserResponse:
    try:
        return service.update_onboarding_tour(
            user_id,
            status=body.status,
            version=body.version,
        )
    except service.UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )
