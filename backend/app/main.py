from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.router import api_router
from .core.config import get_settings
from .core.database import SessionLocal
from .services.seo_service import build_sitemap_xml, render_spa_html


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
    """StaticFiles с fallback на index.html для SPA-маршрутов (History API).

    Известные маршруты (/algorithms, /learning, ...) отдаются с уникальными
    SEO-мета и серверным контентом (render_spa_html), все остальные
    несуществующие пути — с честным статусом 404 (вместо прежнего soft-404).
    """

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api"):
                return await self._spa_response(path)
            raise
        if response.status_code == 404 and not path.startswith("api"):
            return await self._spa_response(path)
        return response

    async def _spa_response(self, path: str) -> Response:
        db: Session | None = None
        try:
            db = SessionLocal()
            html_text, status_code = render_spa_html(path, db)
        except Exception:
            # База недоступна: render_spa_html деградирует без db (без списка алгоритмов).
            html_text, status_code = render_spa_html(path, None)
        finally:
            if db is not None:
                db.close()
        return Response(html_text, status_code=status_code, media_type="text/html")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap() -> Response:
    """Динамический sitemap: статические страницы + все алгоритмы с lastmod."""
    db: Session | None = None
    try:
        db = SessionLocal()
        xml = build_sitemap_xml(db)
    except Exception:
        xml = build_sitemap_xml(None)
    finally:
        if db is not None:
            db.close()
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})


if frontend_dir.exists():
    app.mount("/", SPAStaticFiles(directory=frontend_dir, html=True), name="frontend")
