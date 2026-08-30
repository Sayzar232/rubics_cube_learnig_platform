from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from ..core.config import get_settings


settings = get_settings()

EMAIL_VERIFICATION_TOKEN_TYPE = "email_verify"


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_email_verification_token(subject: str) -> str:
    """Токен для ссылки подтверждения почты (отдельный тип, короткий срок жизни)."""
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.email_verification_expire_minutes
    )
    payload = {
        "sub": subject,
        "exp": expires_at,
        "type": EMAIL_VERIFICATION_TOKEN_TYPE,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_email_verification_token(token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка подтверждения истекла. Запросите новое письмо.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка подтверждения недействительна.",
        ) from exc

    if payload.get("type") != EMAIL_VERIFICATION_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Это не ссылка подтверждения почты.",
        )

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка подтверждения повреждена.",
        )

    return {"sub": str(subject)}


def decode_access_token(token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить токен доступа.",
        ) from exc

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не содержит идентификатор пользователя.",
        )

    return {"sub": str(subject)}

