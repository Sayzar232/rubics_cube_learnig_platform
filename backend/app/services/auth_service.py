from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..auth.security import hash_password, verify_password
from ..models.user import User
from ..schemas.auth import LoginRequest, RegisterRequest


def create_user(db: Session, payload: RegisterRequest) -> User:
    normalized_email = payload.email.lower().strip()
    normalized_username = payload.username.strip()

    existing_user = db.scalar(
        select(User).where(
            or_(
                func.lower(User.email) == normalized_email,
                func.lower(User.username) == normalized_username.lower(),
            )
        )
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email или username уже существует.",
        )

    user = User(
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower().strip()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
        )
    return user

