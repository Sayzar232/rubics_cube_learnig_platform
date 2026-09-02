from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.router import api_router
from .core.config import get_settings


settings = get_settings()
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/api/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


frontend_dir = Path(settings.frontend_dir)


class SPAStaticFiles(StaticFiles):
    """StaticFiles с fallback на index.html: позволяет открывать глубокие ссылки
    History API (/learning, /algorithms, /verify?token=...) напрямую из браузера."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # StaticFiles бросает 404, если файла нет (и нет 404.html)
            if exc.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise
        if response.status_code == 404 and not path.startswith("api"):
            return await super().get_response("index.html", scope)
        return response


if frontend_dir.exists():
    app.mount("/", SPAStaticFiles(directory=frontend_dir, html=True), name="frontend")
