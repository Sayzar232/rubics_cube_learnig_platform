from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .jwt import decode_access_token
from ..core.database import get_db
from ..models.user import User
from ..core.config import get_settings


settings = get_settings()


def get_current_user(
    token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация.",
        )
    payload = decode_access_token(token)
    user = db.scalar(select(User).where(User.id == int(payload["sub"])))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь по токену не найден.",
        )
    return user


def get_optional_user(
    token: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
    db: Session = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of 401 for anonymous visitors."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        return db.scalar(select(User).where(User.id == int(payload["sub"])))
    except Exception:
        return None
