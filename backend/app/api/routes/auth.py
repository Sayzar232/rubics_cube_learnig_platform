from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_user
from ...auth.jwt import (
    create_access_token,
    create_email_verification_token,
    decode_email_verification_token,
)
from ...core.config import get_settings
from ...core.database import get_db
from ...models.user import User
from ...schemas.auth import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    TokenResponse,
    UserRead,
    VerifyRequest,
)
from ...services.auth_service import authenticate_user, create_user
from ...services.email_service import send_verification_email


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


def schedule_verification_email(
    background_tasks: BackgroundTasks,
    *,
    to_email: str,
    username: str,
    user_id: int,
) -> None:
    """Ставит в очередь фоновую отправку письма со ссылкой подтверждения."""
    token = create_email_verification_token(str(user_id))
    base_url = settings.frontend_url.rstrip("/")
    verification_url = f"{base_url}/#/verify?token={token}"
    background_tasks.add_task(
        send_verification_email,
        to_email=to_email,
        username=username,
        verification_url=verification_url,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    user = create_user(db, payload)
    schedule_verification_email(
        background_tasks,
        to_email=user.email,
        username=user.username,
        user_id=user.id,
    )
    return RegisterResponse(
        user=UserRead.model_validate(user),
        message=(
            "Аккаунт создан. Мы отправили письмо со ссылкой для подтверждения "
            f"на {user.email}. Подтвердите почту, чтобы войти."
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload)
    token = create_access_token(str(user.id))
    set_auth_cookie(response, token)
    return TokenResponse(user=UserRead.model_validate(user))


@router.post("/verify", response_model=TokenResponse)
def verify_email(
    payload: VerifyRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Подтверждение почты по токену из письма. Успех = авто-вход (cookie)."""
    claims = decode_email_verification_token(payload.token)
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Аккаунт не найден или был удалён.",
        )

    if not user.is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)

    token = create_access_token(str(user.id))
    set_auth_cookie(response, token)
    return TokenResponse(user=UserRead.model_validate(user))


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Повторная отправка письма. Ответ одинаков всегда — не раскрываем существование аккаунтов."""
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower().strip()))
    if user is not None and not user.is_verified:
        schedule_verification_email(
            background_tasks,
            to_email=user.email,
            username=user.username,
            user_id=user.id,
        )
    return MessageResponse(
        message="Если такой аккаунт существует и почта ещё не подтверждена — мы отправили новое письмо со ссылкой."
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
