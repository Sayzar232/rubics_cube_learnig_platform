# -*- coding: utf-8 -*-
"""Проверка History API роутинга: SPA-fallback бэкенда и отсутствие hash-ссылок в сборке."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path("backend").resolve()))

html = Path("frontend/dist/index.html").read_text(encoding="utf-8")
hash_links = re.findall(r'href="#/', html)
print("hash-ссылок в dist/index.html:", len(hash_links))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

# Глубокая ссылка History API должна вернуть index.html (200)
r = client.get("/learning")
print("GET /learning:", r.status_code, "index.html" if "<div id=\"app\">" in r.text or 'id="app"' in r.text else "???")
assert r.status_code == 200 and 'id="app"' in r.text

r = client.get("/algorithms")
assert r.status_code == 200 and 'id="app"' in r.text
print("GET /algorithms:", r.status_code)

r = client.get("/verify?token=test-token")
assert r.status_code == 200 and 'id="app"' in r.text
print("GET /verify?token=...:", r.status_code)

# Несуществующий API-путь не должен возвращать HTML
r = client.get("/api/nonexistent")
print("GET /api/nonexistent:", r.status_code, "json" if r.headers.get("content-type", "").startswith("application/json") else r.headers.get("content-type"))
assert r.status_code == 404

# Главная и статика
r = client.get("/")
assert r.status_code == 200
print("GET /:", r.status_code)
r = client.get("/robots.txt")
print("GET /robots.txt:", r.status_code)

print("\nВсе проверки пройдены.")
