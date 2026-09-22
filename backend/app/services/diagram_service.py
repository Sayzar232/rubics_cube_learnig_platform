from __future__ import annotations

"""Серверная отрисовка SVG-диаграммы случая (OLL/PLL) для SEO-страниц.

Диаграмма совпадает с той, что рисует Vue-компонент CubeDiagram
(frontend/src/App.vue): те же координаты, размеры и цвета наклеек.
Данные о наклейках берутся из situations.json — того же файла, который
импортирует фронтенд (при сборке Vite кладёт копию в dist/data/situations.json,
поэтому бэкенду не нужен доступ к frontend/src).

Файлы-картинки (algorithm.image_url) при этом не используются: раньше серверный
HTML ссылался на /assets/algorithms/*.svg, а эти файлы не попадают в репозиторий
(см. .gitignore) и в проде отдавали 404.
"""

import json
from html import escape
from pathlib import Path
from typing import Any

from ..core.config import get_settings

settings = get_settings()

# Цвета наклеек. Синхронизировано с STICKER_COLORS в frontend/src/App.vue.
STICKER_COLORS = {
    "Y": "#FFFF00",
    "N": "#8D8D8D",
    "G": "#11AA00",
    "R": "#D00000",
    "B": "#2040D0",
    "O": "#EE8800",
}
_EMPTY_COLOR = STICKER_COLORS["N"]

# Порядок поиска: сначала копия из сборки (frontend/dist/data/situations.json —
# есть и в Docker-образе бэкенда), затем исходник из репозитория (локальная разработка).
_SITUATION_PATHS = (
    Path(settings.frontend_dir) / "data" / "situations.json",
    Path(settings.frontend_dir).parent / "src" / "situations.json",
)

_cache: tuple[Path, float, dict[str, Any]] | None = None


def _load_situations() -> dict[str, Any]:
    """situations.json с кэшем по (путь, mtime). Пустой dict, если файла нет."""
    global _cache
    for path in _SITUATION_PATHS:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if _cache is not None and _cache[0] == path and _cache[1] == mtime:
            return _cache[2]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            _cache = (path, mtime, data)
            return data
    return {}


def situation_key(category_label: str, algorithm_number: int) -> str:
    """Ключ случая в situations.json, напр. ('OLL', 1) -> 'oll-01'."""
    return f"{category_label.lower()}-{algorithm_number:02d}"


def _sticker_color(value: Any) -> str:
    return STICKER_COLORS.get(str(value), _EMPTY_COLOR)


def _column(index: int) -> int:
    return 106 + (index % 3) * 136


def _row(index: int) -> int:
    return 86 + (index // 3) * 136


def _side_row(index: int) -> int:
    return 86 + index * 136


def render_diagram_svg(category_label: str, algorithm_number: int, label: str) -> str | None:
    """Inline-SVG диаграммы случая или None, если данных для случая нет."""
    state = _load_situations().get(situation_key(category_label, algorithm_number))
    if not isinstance(state, dict):
        return None
    top = state.get("U")
    if not isinstance(top, list) or not top:
        return None

    caption = f"{label} — схема случая {category_label}"
    parts = [
        # Внутренний <title> не ставим: доступное имя даёт aria-label, а страница
        # обязана иметь ровно один <title> (в <head>) — это проверяет check_seo_routes.py.
        '<svg class="cube-diagram" xmlns="http://www.w3.org/2000/svg" width="320" height="283" '
        f'viewBox="0 0 637 563" role="img" aria-label="{escape(caption, quote=True)}">',
        '<rect x="99" y="21" width="409" height="59" fill="#000"/>',
        '<rect x="41" y="79" width="525" height="409" fill="#000"/>',
        '<rect x="99" y="488" width="409" height="59" fill="#000"/>',
    ]
    for index, value in enumerate(top[:9]):
        parts.append(
            f'<rect x="{_column(index)}" y="{_row(index)}" width="123" height="123" '
            f'rx="16" ry="16" fill="{_sticker_color(value)}"/>'
        )
    for face, y in (("B", 28), ("F", 494)):
        for index, value in enumerate((state.get(face) or [])[:3]):
            parts.append(
                f'<rect x="{_column(index)}" y="{y}" width="123" height="45" '
                f'rx="8" ry="8" fill="{_sticker_color(value)}"/>'
            )
    for face, x in (("L", 48), ("R", 514)):
        for index, value in enumerate((state.get(face) or [])[:3]):
            parts.append(
                f'<rect x="{x}" y="{_side_row(index)}" width="45" height="123" '
                f'rx="8" ry="8" fill="{_sticker_color(value)}"/>'
            )
    parts.append("</svg>")
    return "".join(parts)
