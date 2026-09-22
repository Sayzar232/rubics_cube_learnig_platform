# -*- coding: utf-8 -*-
"""Проверяет, что закоммиченный frontend/dist актуален и целостен.

Прод-раскладка: Vercel собирает фронтенд сам, а бэкенд (Render/Docker) раздаёт
закоммиченный frontend/dist — он же служит базой для серверной SEO-отрисовки.
Если dist устарел относительно frontend/src, прод отдаёт на /algorithms,
/learning, /auth другой JS-бандл, чем на главной: в браузере мета/canonical
расходятся с тем, что видит поисковый робот (именно так canonical детальных
страниц указывал на каталог).

Запуск:
    python scripts/check_frontend_dist.py            # собрать фронтенд и сверить с git
    python scripts/check_frontend_dist.py --no-build  # только целостность dist
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'OK  ' if condition else 'FAIL'}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        failures.append(name)


def npm_command() -> str:
    return shutil.which("npm.cmd") or shutil.which("npm") or "npm"


def build_frontend() -> None:
    npm = npm_command()
    print(f"$ {npm} run build  (cwd={FRONTEND})")
    result = subprocess.run([npm, "run", "build"], cwd=FRONTEND, shell=os.name == "nt")
    if result.returncode != 0:
        sys.exit("Сборка фронтенда упала — проверка dist не выполнялась.")


def git_dirty_dist() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "frontend/dist"],
        cwd=ROOT, capture_output=True, text=True, shell=os.name == "nt",
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_dist_integrity() -> None:
    index = DIST / "index.html"
    check("dist/index.html существует", index.is_file())
    if not index.is_file():
        return
    html = index.read_text(encoding="utf-8")

    check("dist/index.html: лендинг вставлен (<!--LANDING_CONTENT--> заменён)",
          "LANDING_CONTENT" not in html and 'class="hero-title' in html)
    check("dist/index.html: FAQ-схема на месте", "FAQPage" in html)
    check("dist/index.html: canonical главной", '<link rel="canonical" href="https://cubelearn.site/" />' in html)

    missing = [
        ref for ref in set(re.findall(r'(?:src|href)="(/assets/[^"]+)"', html))
        if not (DIST / ref.lstrip("/")).is_file()
    ]
    check("dist: все ссылки на /assets/* существуют", not missing, ", ".join(sorted(missing)))

    situations = DIST / "data" / "situations.json"
    check("dist/data/situations.json существует", situations.is_file())
    if situations.is_file():
        try:
            data = json.loads(situations.read_text(encoding="utf-8"))
        except ValueError as exc:
            check("dist/data/situations.json валиден", False, str(exc))
        else:
            check("dist/data/situations.json: 78 случаев", len(data) == 78, str(len(data)))

    robots = DIST / "robots.txt"
    check("dist/robots.txt содержит Disallow: /api/",
          robots.is_file() and "Disallow: /api/" in robots.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка актуальности и целостности frontend/dist.")
    parser.add_argument("--no-build", action="store_true", help="Не пересобирать фронтенд")
    args = parser.parse_args()

    if not args.no_build:
        build_frontend()
        dirty = git_dirty_dist()
        check("frontend/dist совпадает со сборкой (нет незакоммиченных изменений)", not dirty,
              "; ".join(dirty))

    check_dist_integrity()

    print()
    print("ИТОГО:", "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if not failures else f"ПРОВАЛЕНО: {failures}")
    if failures and not args.no_build:
        print("\nПодсказка: соберите фронтенд (npm run build) и закоммитьте frontend/dist —")
        print("иначе Render отдаёт устаревший бандл и мета страниц расходится с браузером.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
