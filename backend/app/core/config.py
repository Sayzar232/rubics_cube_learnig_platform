from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "CFOP Trainer"
    api_prefix: str = "/api"
    secret_key: str = Field(
        default="change-me-in-production-secret-key-32bytes", alias="SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60 * 24, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    auth_cookie_name: str = Field(default="cfop_session", alias="AUTH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    # --- Подтверждение email ---
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    smtp_use_ssl: bool = Field(default=False, alias="SMTP_USE_SSL")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(
        default="CubeLearn <no-reply@cubelearn.local>", alias="SMTP_FROM"
    )
    email_verification_expire_minutes: int = Field(
        default=60 * 24, alias="EMAIL_VERIFICATION_EXPIRE_MINUTES"
    )
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    # Канонический публичный адрес сайта: используется в canonical, og:url, JSON-LD и sitemap.
    site_url: str = Field(default="https://cubelearn.site", alias="SITE_URL")
    # Служебная документация FastAPI (/docs, /redoc, /openapi.json): в проде выключена,
    # локально включается ENABLE_API_DOCS=true.
    enable_api_docs: bool = Field(default=False, alias="ENABLE_API_DOCS")
    # Дополнительные хосты, к ответам которых добавляется X-Robots-Tag: noindex (через запятую).
    # Хост api.<домен SITE_URL> учитывается автоматически.
    noindex_hosts: str = Field(default="", alias="NOINDEX_HOSTS")
    email_api_url: str = Field(default="https://api.smtp.bz/v1/smtp/send", alias="EMAIL_API_URL")
    email_api_key: str = Field(default="", alias="EMAIL_API_KEY")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        alias="CORS_ORIGINS",
    )
    database_url: str = Field(
        default="postgresql+psycopg2://cfop_user:cfop_password@db:5432/cfop_db",
        alias="DATABASE_URL",
    )

    @field_validator("database_url")
    @classmethod
    def _force_psycopg2_driver(cls, value: str) -> str:
        """Явно фиксируем psycopg2 как драйвер для PostgreSQL.

        Render/Heroku и подобные хостинги отдают DATABASE_URL без указания драйвера
        (``postgresql://...`` или устаревший ``postgres://...``). В SQLAlchemy 2.1
        дефолтным драйвером для ``postgresql://`` стал ``psycopg`` (версии 3), которого
        нет в requirements, из-за чего приложение падало с
        ``ModuleNotFoundError: No module named 'psycopg'``. Проект собирается с
        ``psycopg2-binary``, поэтому приводим URL к виду ``postgresql+psycopg2://``.
        """
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg2://" + value[len(prefix) :]
        return value

    speedcubedb_user_agent: str = "CFOP Trainer/1.0"
    frontend_dir: Path = PROJECT_ROOT / "frontend" / "dist"
    algorithm_assets_dir: Path = PROJECT_ROOT / "frontend" / "public" / "assets" / "algorithms"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
