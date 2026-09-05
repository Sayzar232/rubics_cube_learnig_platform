# -*- coding: utf-8 -*-
"""Интеграционная проверка SEO-маршрутов через TestClient (без живой БД)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path("backend").resolve()))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
failures = []


def check(name, condition, detail=""):
    print(f"[{'OK  ' if condition else 'FAIL'}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        failures.append(name)


r = client.get("/")
check("GET / -> 200", r.status_code == 200)
check("GET / -> лендинг с FAQ-схемой", "FAQPage" in r.text)

r = client.get("/algorithms")
check("GET /algorithms -> 200", r.status_code == 200)
check("GET /algorithms -> уникальный title", "Каталог алгоритмов CFOP" in r.text)

r = client.get("/learning")
check("GET /learning -> 200 + title", r.status_code == 200 and "Режим обучения" in r.text)

r = client.get("/auth")
check("GET /auth -> 200 + noindex", r.status_code == 200 and 'content="noindex, follow"' in r.text)

r = client.get("/nesuschestvuyushchaya-stranitsa")
check("GET unknown -> 404 (не soft-404)", r.status_code == 404, f"status={r.status_code}")
check("GET unknown -> noindex", 'content="noindex, follow"' in r.text)

r = client.get("/sitemap.xml")
check("GET /sitemap.xml -> 200 xml", r.status_code == 200 and "<urlset" in r.text)

r = client.get("/robots.txt")
check("GET /robots.txt -> 200", r.status_code == 200)

r = client.get("/api/health")
check("GET /api/health -> 200", r.status_code == 200)

print()
print("ИТОГО:", "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if not failures else f"ПРОВАЛЕНО: {failures}")
sys.exit(1 if failures else 0)
