# -*- coding: utf-8 -*-
"""Проверка SEO-рендера SPA-маршрутов (без БД, на фейковых алгоритмах)."""
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path("backend").resolve()))

from app.services.seo_service import render_spa_html, build_sitemap_xml  # noqa: E402

FAKE = [
    SimpleNamespace(id=1, category="OLL", algorithm_number=1, name="Sune", group="Fish shapes",
                    formula="R U R' U R U2 R'", image_url="/assets/algorithms/oll-01.svg",
                    created_at=datetime(2026, 1, 15)),
    SimpleNamespace(id=79, category="PLL", algorithm_number=1, name="Aa-perm", group="OPP swap",
                    formula="x R' U R' D2 R U' R' D2 R2", image_url="/assets/algorithms/pll-01.svg",
                    created_at=datetime(2026, 1, 15)),
]


class FakeResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class FakeDB:
    """Заглушка SQLAlchemy-сессии: db.scalars(...).all() -> FAKE."""

    def scalars(self, stmt):
        return FakeResult(FAKE)

failures = []


def check(name, condition, detail=""):
    status = "OK  " if condition else "FAIL"
    print(f"[{status}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        failures.append(name)


def has_once(html_text, pattern):
    return len(re.findall(pattern, html_text, re.S)) == 1


# /algorithms — каталог
html_text, status = render_spa_html("/algorithms", None)
check("catalog: 200", status == 200)
check("catalog: title уникальный", "Каталог алгоритмов CFOP" in html_text)
check("catalog: canonical /algorithms", '<link rel="canonical" href="https://cubelearn.site/algorithms" />' in html_text)
check("catalog: robots index", 'name="robots" content="index, follow"' in html_text)
check("catalog: JSON-LD валиден", has_once(html_text, r'application/ld\+json">.*?</script>')
      and json.loads(re.search(r'application/ld\+json">\s*(\{.*?\})\s*</script>', html_text, re.S).group(1)))
check("catalog: FAQ-схема удалена (только для главной)", "FAQPage" not in html_text)

# /algorithms/1 — страница алгоритма
html_text, status = render_spa_html("/algorithms/1", FakeDB())
check("detail: 200", status == 200)
check("detail: title с именем", "OLL #01 — Sune" in html_text)
check("detail: canonical /algorithms/1", 'href="https://cubelearn.site/algorithms/1"' in html_text)
check("detail: формула в контенте", "R U R' U R U2 R'" in html_text)
check("detail: h1", "<h1>OLL #01 — Sune</h1>" in html_text)
check("detail: img с alt", 'alt="Диаграмма OLL #01 (Sune) — вид сверху"' in html_text)
check("detail: BreadcrumbList", "BreadcrumbList" in html_text)
check("detail: старый лендинг удалён", "Освойте" not in html_text)

# /algorithms/999 — несуществующий алгоритм
html_text, status = render_spa_html("/algorithms/999", FAKE)
check("detail 404: статус 404", status == 404)
check("detail 404: noindex", 'content="noindex, follow"' in html_text)

# /learning
html_text, status = render_spa_html("/learning", None)
check("learning: 200 и уникальный title", status == 200 and "Режим обучения CFOP" in html_text)

# /auth, /profile, /verify — noindex
for route in ("/auth", "/profile", "/verify"):
    html_text, status = render_spa_html(route, None)
    check(f"{route}: 200 + noindex", status == 200 and 'content="noindex, follow"' in html_text)

# неизвестный путь — soft-404 устранён
html_text, status = render_spa_html("/dfgdfg/xxx", None)
check("unknown: 404", status == 404)
check("unknown: noindex 404", "404" in html_text and 'content="noindex, follow"' in html_text)

# слэш в конце нормализуется
_, status = render_spa_html("learning/", None)
check("trailing slash: 200", status == 200)

# sitemap
xml = build_sitemap_xml(FakeDB())
check("sitemap: все URL", xml.count("<loc>") == 3 + len(FAKE))
check("sitemap: lastmod присутствует", "<lastmod>2026-01-15</lastmod>" in xml)

# базовая целостность HTML
html_text, _ = render_spa_html("/algorithms/1", FakeDB())
check("html: один <title>", has_once(html_text, r"<title>.*?</title>"))
check("html: один canonical", len(re.findall(r'rel="canonical"', html_text)) == 1)
check("html: один ld+json", has_once(html_text, r'application/ld\+json">'))
check("html: скрипт Vue на месте", '<script type="module"' in html_text)

print()
print("ИТОГО:", "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if not failures else f"ПРОВАЛЕНО: {failures}")
sys.exit(1 if failures else 0)
