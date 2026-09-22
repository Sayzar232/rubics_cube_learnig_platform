# -*- coding: utf-8 -*-
"""Проверка SEO-меты так, как её видит браузер — после исполнения JS.

Серверный HTML покрыт scripts/check_seo_routes.py и scripts/check_seo_http.py,
но canonical/title на страницах алгоритмов дописывает и клиентский код
(frontend/src/App.vue). Ошибка в нём в серверных тестах не видна — именно так в
прод когда-то попал canonical, указывающий с /algorithms/{id} на /algorithms.

Инвариант: после исполнения JS страница обязана сохранять canonical/og:url
серверного HTML (self-referencing URL), а title — содержать имя случая.

Запуск:
    python scripts/check_seo_client.py                        # проверить прод
    python scripts/check_seo_client.py --url http://localhost:8000
"""
from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.request
from urllib.parse import urlsplit

# путь -> фрагмент, который обязан быть в <title> после рендера
CASES = (
    ("/", "CubeLearn"),
    ("/algorithms", "Каталог алгоритмов CFOP"),
    ("/algorithms/1", "формула, схема и видеоурок"),
    ("/learning", "Режим обучения CFOP"),
)

CANONICAL_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"')

READ_META_JS = """
const link = document.querySelector('link[rel="canonical"]');
const robots = document.querySelector('meta[name="robots"]');
const ogUrl = document.querySelector('meta[property="og:url"]');
return {
  title: document.title,
  canonical: link ? link.href : null,
  ogUrl: ogUrl ? ogUrl.content : null,
  robots: robots ? robots.content : null,
  h1: Array.from(document.querySelectorAll('h1')).map((el) => el.textContent.trim()),
};
"""

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'OK  ' if condition else 'FAIL'}] {name}{(' — ' + detail) if detail and not condition else ''}")
    if not condition:
        failures.append(name)


def server_canonical(url: str) -> str | None:
    """Canonical из серверного HTML (без исполнения JS). None при сетевой ошибке."""
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                html = response.read().decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001 — сеть может отвалиться, проверка продолжится
            if attempt == 0:
                time.sleep(2)
            continue
        match = CANONICAL_RE.search(html)
        return match.group(1) if match else None
    print(f"    ! серверный HTML {url} не получен — сравнение с сервером пропущено")
    return None


def read_meta(driver, url: str) -> dict:
    """Открывает страницу и ждёт, пока клиентская мета перестанет меняться."""
    driver.get(url)
    previous = None
    deadline = time.time() + 25
    while time.time() < deadline:
        current = driver.execute_script(READ_META_JS)
        if current == previous and current["title"]:
            return current
        previous = current
        time.sleep(0.6)
    return previous or {}


def build_driver(headless: bool):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-first-run")
    options.add_argument("--log-level=3")
    return webdriver.Chrome(options=options)


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка отрендеренной SEO-меты (canonical/title) в браузере.")
    parser.add_argument("--url", default="https://cubelearn.site", help="Базовый адрес сайта")
    parser.add_argument("--site-url", default="",
                        help="Ожидаемый канонический адрес из фронтенд-конфига (VITE_SITE_URL), "
                             "если он отличается от адреса сервера (локальный предпросмотр)")
    parser.add_argument("--show-browser", action="store_true", help="Запустить Chrome с окном (по умолчанию headless)")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    site_override = args.site_url.rstrip("/")
    try:
        driver = build_driver(headless=not args.show_browser)
    except Exception as exc:  # noqa: BLE001 — Selenium может не найти браузер/драйвер
        print(f"SKIP: не удалось запустить Chrome ({exc}). Установите Google Chrome.")
        return 0

    try:
        for path, title_part in CASES:
            url = base + path
            server = server_canonical(url)
            expected = (site_override + path) if site_override else server
            meta = read_meta(driver, url)
            rendered = meta.get("canonical")
            print(f"\n--- {path}")
            print(f"    canonical в серверном HTML: {server!r}")
            print(f"    canonical после рендера:    {rendered!r}  (og:url={meta.get('ogUrl')!r})")
            print(f"    title: {meta.get('title')!r}")
            print(f"    h1:    {meta.get('h1')}")

            check(f"{path}: canonical есть после рендера", bool(rendered), str(rendered))
            check(f"{path}: canonical указывает на саму страницу",
                  urlsplit(rendered or "").path.rstrip("/") == urlsplit(url).path.rstrip("/"),
                  f"ожидали путь {urlsplit(url).path}, получили {urlsplit(rendered or '').path!r}")
            if expected:
                check(f"{path}: клиентский код не меняет canonical сервера",
                      rendered == expected, f"ожидали {expected!r}, получили {rendered!r}")
            else:
                print(f"    ! серверный canonical недоступен — сравнение с сервером пропущено")
            check(f"{path}: og:url совпадает с canonical", meta.get("ogUrl") == rendered, str(meta.get("ogUrl")))
            check(f"{path}: <title> содержит «{title_part}»", title_part in (meta.get("title") or ""),
                  str(meta.get("title")))
            check(f"{path}: ровно один непустой <h1>",
                  len([h for h in (meta.get("h1") or []) if h]) == 1, str(meta.get("h1")))

        # отдельная регрессия: страница алгоритма не должна объявлять канонической страницу каталога
        detail = read_meta(driver, base + "/algorithms/1")
        check("/algorithms/1: canonical не указывает на каталог",
              urlsplit(detail.get("canonical") or "").path.rstrip("/") != "/algorithms",
              str(detail.get("canonical")))
        check("/algorithms/1: <h1> содержит номер случая",
              any("#" in h for h in (detail.get("h1") or [])), str(detail.get("h1")))
    finally:
        driver.quit()

    print()
    print("ИТОГО:", "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ" if not failures else f"ПРОВАЛЕНО: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
