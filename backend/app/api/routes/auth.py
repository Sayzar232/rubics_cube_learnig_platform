from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_user
from ...auth.jwt import create_access_token
from ...core.database import get_db
from ...models.user import User
from ...schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead
from ...services.auth_service import authenticate_user, create_user
from ...core.config import get_settings


router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="none",
        path="/",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    user = create_user(db, payload)
    token = create_access_token(str(user.id))
    set_auth_cookie(response, token)
    return TokenResponse(user=UserRead.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload)
    token = create_access_token(str(user.id))
    set_auth_cookie(response, token)
    return TokenResponse(user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
