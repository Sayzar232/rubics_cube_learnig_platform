from __future__ import annotations

"""Серверная SEO-подготовка index.html для SPA-маршрутов.

FastAPI отдаёт один и тот же ``dist/index.html`` для всех SPA-маршрутов.
Этот модуль перед ответом подставляет в него уникальные для каждого
маршрута ``<title>``, description, canonical, Open Graph, robots-мету,
JSON-LD и серверный HTML-контент (каталог алгоритмов, страница алгоритма),
чтобы поисковые роботы видели уникальный контент без исполнения JS.
"""

import html
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..models.algorithm import Algorithm, AlgorithmCategory
from .algorithm_service import algorithm_sort_key

settings = get_settings()
SITE_URL = settings.site_url.rstrip("/")

_BASE_PATH = Path(settings.frontend_dir) / "index.html"
_cache: tuple[float, str] | None = None


def _base_html() -> str:
    """Кэшированный dist/index.html (перечитывается при изменении mtime)."""
    global _cache
    mtime = _BASE_PATH.stat().st_mtime
    if _cache is None or _cache[0] != mtime:
        _cache = (mtime, _BASE_PATH.read_text(encoding="utf-8"))
    return _cache[1]


# --- Регулярки для подмены блоков index.html ---------------------------------
_TITLE_RE = re.compile(r"<title>.*?</title>", re.S)
_DESCRIPTION_RE = re.compile(r'<meta\s+name="description"\s+content="[^"]*"\s*/?>')
_CANONICAL_RE = re.compile(r'<link\s+rel="canonical"\s+href="[^"]*"\s*/?>')
_LDJSON_RE = re.compile(r'<script\s+type="application/ld\+json">.*?</script>', re.S)
_OG_URL_RE = re.compile(r'<meta\s+property="og:url"\s+content="[^"]*"\s*/?>')
_OG_TITLE_RE = re.compile(r'<meta\s+property="og:title"\s+content="[^"]*"\s*/?>')
_OG_DESCRIPTION_RE = re.compile(r'<meta\s+property="og:description"\s+content="[^"]*"\s*/?>')
_TWITTER_TITLE_RE = re.compile(r'<meta\s+name="twitter:title"\s+content="[^"]*"\s*/?>')
_TWITTER_DESCRIPTION_RE = re.compile(r'<meta\s+name="twitter:description"\s+content="[^"]*"\s*/?>')
_ROBOTS_RE = re.compile(r'<meta\s+name="robots"\s+content="[^"]*"\s*/?>')
_APP_RE = re.compile(r'(<div id="app">).*(</body>)', re.S)

# Минимальные стили для серверного контента (виден до монтирования Vue).
_STATIC_STYLES = """<style>
  .seo-page{max-width:860px;margin:0 auto;padding:56px 24px;font-family:'Manrope',system-ui,sans-serif;color:#111827;line-height:1.6}
  .seo-page h1{font-size:32px;margin:0 0 14px;line-height:1.25}
  .seo-page h2{font-size:22px;margin:28px 0 10px}
  .seo-page p,.seo-page li{font-size:16px}
  .seo-page ul{list-style:none;padding:0}
  .seo-page li{margin:10px 0}
  .seo-page a{color:#2563eb;text-decoration:none}
  .seo-page a:hover{text-decoration:underline}
  .seo-page code{display:inline-block;background:#f3f4f6;border:1px solid #e5e7eb;border-radius:6px;padding:2px 8px;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px}
  .seo-page img{max-width:260px;border-radius:12px;border:1px solid #e5e7eb}
  .seo-page .seo-formula{font-size:18px;font-weight:600;margin:12px 0}
  .seo-breadcrumb{font-size:14px;color:#6b7280;margin-bottom:18px}
</style>"""


def _esc(value: str) -> str:
    return html.escape(str(value), quote=True)


# --- Серверный HTML-контент страниц ------------------------------------------

def _breadcrumbs_trail(items: list[tuple[str, str]]) -> str:
    parts = " · ".join(
        f'<a href="{_esc(url)}">{_esc(name)}</a>' if url else _esc(name)
        for name, url in items
    )
    return f'<nav class="seo-breadcrumb" aria-label="Хлебные крошки">{parts}</nav>'


def _algorithm_label(algorithm: Algorithm) -> str:
    return f"#{algorithm.algorithm_number:02d} — {_esc(algorithm.name)}"


def _category_label(category: AlgorithmCategory) -> str:
    return "OLL" if category == AlgorithmCategory.OLL else "PLL"


def _catalog_content(algorithms: list[Algorithm]) -> str:
    parts = [
        _STATIC_STYLES,
        '<div class="seo-page">',
        _breadcrumbs_trail([("Главная", "/"), ("Каталог алгоритмов", "")]),
        "<h1>Каталог алгоритмов CFOP: все 57 OLL и 21 PLL</h1>",
        "<p>Полный набор алгоритмов последнего слоя для скоростной сборки кубика Рубика: "
        "57 случаев OLL (ориентация последнего слоя) и 21 случай PLL (перестановка последнего слоя). "
        "Для каждого алгоритма — схема, формула и видеоурок.</p>",
    ]
    for category, heading, intro in (
        (AlgorithmCategory.OLL, "OLL — ориентация последнего слоя (57 алгоритмов)",
         "Случаи OLL делают все жёлтые наклейки верхней грани ориентированными за один этап."),
        (AlgorithmCategory.PLL, "PLL — перестановка последнего слоя (21 алгоритм)",
         "Случаи PLL расставляют кубики последнего слоя по своим местам, когда ориентация уже выполнена."),
    ):
        items = [a for a in algorithms if a.category == category]
        parts.append(f"<h2>{_esc(heading)}</h2><p>{_esc(intro)}</p><ul>")
        for algorithm in items:
            parts.append(
                f'<li><a href="/algorithms/{algorithm.id}">'
                f"{_esc(_category_label(category))} {_algorithm_label(algorithm)}</a>"
                f' — <code>{_esc(algorithm.formula)}</code></li>'
            )
        parts.append("</ul>")
    parts.append(
        '<p>Изучайте алгоритмы в удобном режиме: <a href="/learning">режим обучения CubeLearn</a> '
        "подбирает следующий алгоритм и отмечает выученные.</p></div>"
    )
    return "\n".join(parts)


def _algorithm_content(algorithm: Algorithm) -> str:
    category_label = _category_label(algorithm.category)
    total = "57" if category_label == "OLL" else "21"
    stage = "ориентации" if category_label == "OLL" else "перестановки"
    alt = f"Диаграмма {category_label} #{algorithm.algorithm_number:02d} ({algorithm.name}) — вид сверху"
    return "\n".join([
        _STATIC_STYLES,
        '<div class="seo-page">',
        _breadcrumbs_trail([
            ("Главная", "/"),
            ("Каталог алгоритмов", "/algorithms"),
            (f"{category_label} #{algorithm.algorithm_number:02d}", ""),
        ]),
        f"<h1>{_esc(category_label)} #{algorithm.algorithm_number:02d} — {_esc(algorithm.name)}</h1>",
        f"<p>Группа: <b>{_esc(algorithm.group)}</b>. Один из {total} алгоритмов "
        f"{stage} последнего слоя в методе CFOP.</p>",
        f'<p class="seo-formula">Формула: <code>{_esc(algorithm.formula)}</code></p>',
        f'<p><img src="{_esc(algorithm.image_url)}" alt="{_esc(alt)}" loading="lazy"></p>',
        '<p>Смотрите видеоурок и отмечайте прогресс в <a href="/learning">режиме обучения</a> '
        'или вернитесь в <a href="/algorithms">каталог алгоритмов</a>.</p>',
        "</div>",
    ])


def _learning_content() -> str:
    return "\n".join([
        _STATIC_STYLES,
        '<div class="seo-page">',
        _breadcrumbs_trail([("Главная", "/"), ("Режим обучения", "")]),
        "<h1>Режим обучения CFOP</h1>",
        "<p>Тренажёр последовательно показывает алгоритмы OLL и PLL, которые вы ещё не выучили: "
        "диаграмма, формула и видеоурок для каждого случая. Отмечайте алгоритмы как выученные, "
        "копите дневной стрик и следите за прогрессом — все 78 алгоритмов бесплатны.</p>",
        '<p><a href="/algorithms">Открыть каталог алгоритмов</a></p>',
        "</div>",
    ])


def _service_content(title: str, text: str) -> str:
    return "\n".join([
        _STATIC_STYLES,
        '<div class="seo-page">',
        f"<h1>{_esc(title)}</h1>",
        f"<p>{_esc(text)}</p>",
        '<p><a href="/algorithms">Каталог алгоритмов</a> · <a href="/">Главная</a></p>',
        "</div>",
    ])


def _not_found_content() -> str:
    return "\n".join([
        _STATIC_STYLES,
        '<div class="seo-page">',
        "<h1>404 — страница не найдена</h1>",
        "<p>Такой страницы на сайте нет. Откройте каталог алгоритмов или главную страницу.</p>",
        '<p><a href="/algorithms">Каталог алгоритмов</a> · <a href="/">Главная</a></p>',
        "</div>",
    ])


# --- JSON-LD ------------------------------------------------------------------

def _ld_script(graph: list[dict]) -> str:
    payload = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">\n{payload}\n    </script>'


def _website_node() -> dict:
    return {
        "@type": "WebSite",
        "name": "CubeLearn",
        "url": f"{SITE_URL}/",
        "description": "Онлайн-платформа для изучения скоростной сборки кубика Рубика методом CFOP",
        "inLanguage": "ru",
    }


def _breadcrumb_node(items: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                **({"item": f"{SITE_URL}{url}"} if url else {}),
            }
            for position, (name, url) in enumerate(items, start=1)
        ],
    }


def _catalog_ld(algorithms: list[Algorithm]) -> str:
    item_list = {
        "@type": "ItemList",
        "name": "Алгоритмы CFOP: OLL и PLL",
        "numberOfItems": len(algorithms),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": f"{_category_label(a.category)} #{a.algorithm_number:02d} — {a.name}",
                "url": f"{SITE_URL}/algorithms/{a.id}",
            }
            for position, a in enumerate(algorithms, start=1)
        ],
    }
    return _ld_script([
        _website_node(),
        {
            "@type": "CollectionPage",
            "name": "Каталог алгоритмов CFOP — все 57 OLL и 21 PLL",
            "url": f"{SITE_URL}/algorithms",
            "inLanguage": "ru",
            "mainEntity": item_list,
        },
        _breadcrumb_node([("Главная", "/"), ("Каталог алгоритмов", "/algorithms")]),
    ])


def _algorithm_ld(algorithm: Algorithm) -> str:
    category_label = _category_label(algorithm.category)
    name = f"{category_label} #{algorithm.algorithm_number:02d} — {algorithm.name}"
    url = f"{SITE_URL}/algorithms/{algorithm.id}"
    return _ld_script([
        _website_node(),
        {
            "@type": "WebPage",
            "name": name,
            "url": url,
            "inLanguage": "ru",
            "description": f"Формула алгоритма {name}: {algorithm.formula}. Диаграмма и видеоурок.",
            "isPartOf": {"@type": "CollectionPage", "url": f"{SITE_URL}/algorithms"},
        },
        _breadcrumb_node([
            ("Главная", "/"),
            ("Каталог алгоритмов", "/algorithms"),
            (f"{category_label} #{algorithm.algorithm_number:02d}", ""),
        ]),
    ])


def _simple_ld(name: str, url: str) -> str:
    return _ld_script([
        _website_node(),
        {"@type": "WebPage", "name": name, "url": f"{SITE_URL}{url}", "inLanguage": "ru"},
        _breadcrumb_node([("Главная", "/"), (name, "")]),
    ])


# --- Сборка страницы -----------------------------------------------------------

def _replace_first(html_text: str, pattern: re.Pattern[str], replacement: str) -> str:
    return pattern.sub(lambda m, r=replacement: r, html_text, count=1)


def _apply(html_text: str, *, title: str, description: str, canonical_path: str,
           content: str, ld_json: str | None, robots: str) -> str:
    head_values = [
        (_TITLE_RE, f"<title>{_esc(title)}</title>"),
        (_DESCRIPTION_RE, f'<meta name="description" content="{_esc(description)}" />'),
        (_CANONICAL_RE, f'<link rel="canonical" href="{SITE_URL}{_esc(canonical_path)}" />'),
        (_OG_URL_RE, f'<meta property="og:url" content="{SITE_URL}{_esc(canonical_path)}" />'),
        (_OG_TITLE_RE, f'<meta property="og:title" content="{_esc(title)}" />'),
        (_OG_DESCRIPTION_RE, f'<meta property="og:description" content="{_esc(description)}" />'),
        (_TWITTER_TITLE_RE, f'<meta name="twitter:title" content="{_esc(title)}" />'),
        (_TWITTER_DESCRIPTION_RE, f'<meta name="twitter:description" content="{_esc(description)}" />'),
    ]
    for pattern, replacement in head_values:
        html_text = _replace_first(html_text, pattern, replacement)

    robots_meta = f'<meta name="robots" content="{_esc(robots)}" />'
    if _ROBOTS_RE.search(html_text):
        html_text = _replace_first(html_text, _ROBOTS_RE, robots_meta)
    else:
        html_text = html_text.replace("</head>", f"    {robots_meta}\n  </head>", 1)

    if ld_json is not None:
        html_text = _replace_first(html_text, _LDJSON_RE, ld_json)

    return _APP_RE.sub(
        lambda m: m.group(1) + "\n" + content + "\n    " + m.group(2),
        html_text,
        count=1,
    )


def _load_algorithms(db: Session) -> list[Algorithm]:
    return sorted(db.scalars(select(Algorithm)).all(), key=algorithm_sort_key)


def _not_found_page() -> tuple[str, int]:
    html_text = _apply(
        _base_html(),
        title="Страница не найдена — 404 · CubeLearn",
        description="Запрошенная страница не найдена на CubeLearn.",
        canonical_path="/404",
        content=_not_found_content(),
        ld_json=None,
        robots="noindex, follow",
    )
    return html_text, 404


def render_spa_html(path: str, db: Session | None) -> tuple[str, int]:
    """Возвращает (html, status_code) для SPA-маршрута.

    ``path`` — путь без домена, например ``/algorithms/3``.
    ``db`` может быть ``None``, если база недоступна (деградация без краша).
    """
    route = "/" + path.strip("/")
    algorithms: list[Algorithm] = []
    if db is not None:
        try:
            algorithms = _load_algorithms(db)
        except Exception:
            algorithms = []

    if route == "/algorithms":
        return _apply(
            _base_html(),
            title="Каталог алгоритмов CFOP — все 57 OLL и 21 PLL с формулами · CubeLearn",
            description="Полный каталог алгоритмов метода CFOP: 57 случаев OLL и 21 случай PLL "
                        "с формулами, схемами и видеоуроками. Бесплатно, на русском языке.",
            canonical_path="/algorithms",
            content=_catalog_content(algorithms),
            ld_json=_catalog_ld(algorithms) if algorithms else _simple_ld("Каталог алгоритмов CFOP", "/algorithms"),
            robots="index, follow",
        ), 200

    match = re.fullmatch(r"/algorithms/(\d+)", route)
    if match:
        algorithm_id = int(match.group(1))
        algorithm = next((a for a in algorithms if a.id == algorithm_id), None)
        if algorithm is None:
            return _not_found_page()
        category_label = _category_label(algorithm.category)
        name = f"{category_label} #{algorithm.algorithm_number:02d} — {algorithm.name}"
        return _apply(
            _base_html(),
            title=f"{name}: формула, схема и видеоурок · CubeLearn",
            description=f"Алгоритм {name} (группа {algorithm.group}): формула "
                        f"{algorithm.formula}, диаграмма случая и видеоурок. Изучайте CFOP на CubeLearn.",
            canonical_path=f"/algorithms/{algorithm.id}",
            content=_algorithm_content(algorithm),
            ld_json=_algorithm_ld(algorithm),
            robots="index, follow",
        ), 200

    if route == "/learning":
        return _apply(
            _base_html(),
            title="Режим обучения CFOP — учите алгоритмы по одному · CubeLearn",
            description="Тренажёр подбирает следующий алгоритм OLL или PLL, показывает диаграмму, "
                        "формулу и видеоурок. Отмечайте прогресс и копите стрик — бесплатно.",
            canonical_path="/learning",
            content=_learning_content(),
            ld_json=_simple_ld("Режим обучения CFOP", "/learning"),
            robots="index, follow",
        ), 200

    if route == "/auth":
        return _apply(
            _base_html(),
            title="Вход и регистрация · CubeLearn",
            description="Создайте бесплатный аккаунт CubeLearn, чтобы отслеживать прогресс изучения алгоритмов CFOP.",
            canonical_path="/auth",
            content=_service_content("Вход и регистрация", "Аккаунт нужен, чтобы отмечать выученные алгоритмы и видеть статистику."),
            ld_json=None,
            robots="noindex, follow",
        ), 200

    if route == "/profile":
        return _apply(
            _base_html(),
            title="Профиль и прогресс · CubeLearn",
            description="Личный кабинет CubeLearn: прогресс по OLL и PLL, достижения и статистика.",
            canonical_path="/profile",
            content=_service_content("Профиль и прогресс", "Здесь отображается ваш прогресс изучения алгоритмов."),
            ld_json=None,
            robots="noindex, follow",
        ), 200

    if route == "/verify":
        return _apply(
            _base_html(),
            title="Подтверждение почты · CubeLearn",
            description="Подтверждение email-адреса аккаунта CubeLearn.",
            canonical_path="/verify",
            content=_service_content("Подтверждение почты", "Проверяем вашу ссылку подтверждения."),
            ld_json=None,
            robots="noindex, follow",
        ), 200

    return _not_found_page()


def build_sitemap_xml(db: Session) -> str:
    """Динамический sitemap.xml: главная, каталог, обучение и все алгоритмы с lastmod."""
    urls: list[tuple[str, str | None]] = [
        (f"{SITE_URL}/", None),
        (f"{SITE_URL}/algorithms", None),
        (f"{SITE_URL}/learning", None),
    ]
    try:
        for algorithm in _load_algorithms(db):
            lastmod = algorithm.created_at.strftime("%Y-%m-%d") if algorithm.created_at else None
            urls.append((f"{SITE_URL}/algorithms/{algorithm.id}", lastmod))
    except Exception:
        pass

    entries = []
    for loc, lastmod in urls:
        entry = f"  <url>\n    <loc>{_esc(loc)}</loc>\n"
        if lastmod:
            entry += f"    <lastmod>{lastmod}</lastmod>\n"
        entries.append(entry + "  </url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries)
        + "\n</urlset>\n"
    )




