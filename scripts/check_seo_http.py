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
check("GET /sitemap.xml -> lastmod у каждого URL",
      r.text.count("<lastmod>") == r.text.count("<loc>") and "<lastmod>" in r.text)

r = client.head("/sitemap.xml")
check("HEAD /sitemap.xml -> 200 (не 404)",
      r.status_code == 200 and r.headers.get("content-type", "").startswith("application/xml"),
      f"status={r.status_code}")

r = client.get("/robots.txt")
check("GET /robots.txt -> 200", r.status_code == 200)
check("robots.txt -> Disallow: /api/", "Disallow: /api/" in r.text)
check("robots.txt -> Sitemap указан", "Sitemap: https://cubelearn.site/sitemap.xml" in r.text)

r = client.get("/docs")
check("GET /docs -> 404 (служебная документация выключена)", r.status_code == 404)
r = client.get("/openapi.json")
check("GET /openapi.json -> 404", r.status_code == 404)
r = client.get("/redoc")
check("GET /redoc -> 404", r.status_code == 404)

r = client.get("/", headers={"host": "api.cubelearn.site"})
check("api-хост -> X-Robots-Tag: noindex",
      r.headers.get("x-robots-tag") == "noindex, nofollow", r.headers.get("x-robots-tag", "нет"))

r = client.get("/", headers={"host": "cubelearn.site"})
check("основной хост -> без X-Robots-Tag", "x-robots-tag" not in r.headers)

r = client.get("/algorithms", headers={"host": "api.cubelearn.site",
                                       "x-forwarded-host": "cubelearn.site"})
check("прокси Vercel (forwarded=основной домен) -> без X-Robots-Tag",
      "x-robots-tag" not in r.headers, r.headers.get("x-robots-tag", "нет"))

r = client.get("/sitemap.xml", headers={"host": "api.cubelearn.site",
                                        "x-forwarded-host": "cubelearn.site"})
check("sitemap через прокси -> без X-Robots-Tag",
      "x-robots-tag" not in r.headers, r.headers.get("x-robots-tag", "нет"))

r = client.get("/api/health")
check("GET /api/health -> 200", r.status_code == 200)

print()
print("ИТОГО:", "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if not failures else f"ПРОВАЛЕНО: {failures}")
sys.exit(1 if failures else 0)
