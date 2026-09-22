"""Локальный предпросмотр прод-раскладки для браузерных SEO-проверок (без БД).

Отдаёт frontend/dist и на SPA-маршруты возвращает серверно отрисованный HTML
(как FastAPI-бэкенд: render_spa_html), а на /api/algorithms* — заглушку API,
чтобы клиентский код отработал полностью. Нужен для scripts/check_seo_client.py.

Запуск: python scripts/preview_server.py [--port 8000]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.seo_service import render_spa_html  # noqa: E402

DIST = ROOT / "frontend" / "dist"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


def build_algorithms() -> list[SimpleNamespace]:
    """Заглушка таблицы algorithms: по всем случаям из situations.json."""
    situations = json.loads((DIST / "data" / "situations.json").read_text(encoding="utf-8"))
    items = []
    for index, key in enumerate(sorted(situations), start=1):
        category, number = key.split("-")
        items.append(SimpleNamespace(
            id=index,
            category=category.upper(),
            algorithm_number=int(number),
            name=key,
            group="preview",
            formula="R U R' U'",
            image_url=f"/assets/algorithms/{key}.svg",
            video_url=None,
            created_at=datetime(2026, 1, 15),
        ))
    return items


ALGORITHMS = build_algorithms()


class FakeResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeSession:
    """Мини-заглушка SQLAlchemy-сессии для render_spa_html."""

    def scalars(self, stmt):
        return FakeResult(ALGORITHMS)


def api_payload(algorithm: SimpleNamespace) -> dict:
    return {
        "id": algorithm.id,
        "category": algorithm.category,
        "algorithm_number": algorithm.algorithm_number,
        "name": algorithm.name,
        "group": algorithm.group,
        "formula": algorithm.formula,
        "image_url": algorithm.image_url,
        "video_url": algorithm.video_url,
        "is_learned": False,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # тихий режим
        pass

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — сигнатура BaseHTTPRequestHandler
        path = self.path.split("?")[0]

        if path == "/api/algorithms":
            payload = [api_payload(a) for a in ALGORITHMS]
            self._send(200, json.dumps(payload, ensure_ascii=False).encode(), "application/json")
            return
        if path.startswith("/api/algorithms/"):
            algorithm_id = int(path.rsplit("/", 1)[-1])
            found = next((a for a in ALGORITHMS if a.id == algorithm_id), None)
            self._send(200 if found else 404,
                       json.dumps(api_payload(found) if found else {}, ensure_ascii=False).encode(),
                       "application/json")
            return
        if path.startswith("/api/"):
            self._send(404, b"{}", "application/json")
            return

        # Статика из сборки
        candidate = (DIST / path.lstrip("/")) if path != "/" else None
        if candidate is not None and candidate.is_file():
            self._send(200, candidate.read_bytes(),
                       CONTENT_TYPES.get(candidate.suffix, "application/octet-stream"))
            return

        # SPA-маршруты: индекс отдаёт Vercel, остальное рендерит бэкенд
        if path == "/":
            self._send(200, (DIST / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        html_text, status = render_spa_html(path, FakeSession())
        self._send(status, html_text.encode("utf-8"), "text/html; charset=utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Локальный предпросмотр dist + заглушка API.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    print(f"Предпросмотр {DIST} на http://localhost:{args.port} (Ctrl+C — остановить)")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
