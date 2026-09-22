from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
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

# Хосты, которые не должны попадать в индекс: публичный адрес бэкенда
# (api.cubelearn.site) отдаёт те же HTML-страницы, что и основной домен.
noindex_hosts = {host.strip().lower() for host in settings.noindex_hosts.split(",") if host.strip()}
_site_netloc = urlparse(settings.site_url).netloc.lower()
if _site_netloc:
    noindex_hosts.add(f"api.{_site_netloc}")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    # В проде /docs, /redoc и /openapi.json закрыты: тонкие служебные страницы
    # не должны индексироваться. Локально включаются через ENABLE_API_DOCS=true.
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tag_duplicate_hosts_as_noindex(request: Request, call_next):
    """X-Robots-Tag: noindex для дублирующих хостов (например, api.cubelearn.site).

    Важно: Vercel проксирует /algorithms, /learning и /sitemap.xml основного
    домена на бэкенд, подставляя исходный хост в x-forwarded-host. Такие запросы
    закрывать нельзя — иначе весь сайт, кроме главной, выпадает из индекса.
    """
    response = await call_next(request)
    host = request.headers.get("host", "").split(":")[0].lower()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",")[0].strip().split(":")[0].lower()
    public_host = forwarded_host or host
    if public_host in noindex_hosts:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response

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


@app.api_route("/sitemap.xml", methods=["GET", "HEAD"], include_in_schema=False)
def sitemap(request: Request) -> Response:
    """Динамический sitemap: статические страницы + все алгоритмы с lastmod."""
    headers = {"Cache-Control": "public, max-age=3600"}
    if request.method == "HEAD":
        # Часть краулеров, соцсети и мониторинги сначала спрашивают HEAD:
        # отдаём заголовки без тела (раньше такой запрос уходил в SPA-fallback и получал 404).
        return Response(media_type="application/xml", headers=headers)

    db: Session | None = None
    try:
        db = SessionLocal()
        xml = build_sitemap_xml(db)
    except Exception:
        xml = build_sitemap_xml(None)
    finally:
        if db is not None:
            db.close()
    return Response(xml, media_type="application/xml", headers=headers)


if frontend_dir.exists():
    app.mount("/", SPAStaticFiles(directory=frontend_dir, html=True), name="frontend")
