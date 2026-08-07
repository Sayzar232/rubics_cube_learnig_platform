from __future__ import annotations

from html import escape
from pathlib import Path


COLOR_MAP = {
    "y": "#FFD500",
    "w": "#FFFFFF",
    "r": "#C41E3A",
    "o": "#FF7A00",
    "g": "#009B48",
    "b": "#0051BA",
    "l": "#D9DEE7",
}


def normalize_face(face: str, size: int = 9) -> str:
    normalized = (face or "").lower().strip()
    if len(normalized) < size:
        normalized = normalized.ljust(size, "l")
    return normalized[:size]


def sticker_color(symbol: str) -> str:
    return COLOR_MAP.get(symbol.lower(), "#D9DEE7")


def render_case_svg(sticker_state: dict[str, str], title: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    top = normalize_face(sticker_state.get("us", ""))
    back = normalize_face(sticker_state.get("ub", ""))[:3]
    front = normalize_face(sticker_state.get("uf", ""))[:3]
    left = normalize_face(sticker_state.get("ul", ""))[:3]
    right = normalize_face(sticker_state.get("ur", ""))[:3]

    svg_parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="250" viewBox="0 0 320 250">',
        '<rect width="320" height="250" rx="24" fill="#F7F9FC"/>',
        '<rect x="12" y="12" width="296" height="226" rx="20" fill="white" stroke="#E2E8F0"/>',
        '<text x="28" y="40" fill="#0F172A" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="700">'
        f"{escape(title)}</text>",
    ]

    top_origin_x = 110
    top_origin_y = 70
    top_cell = 26
    gap = 4

    for index, symbol in enumerate(top):
        row = index // 3
        col = index % 3
        x = top_origin_x + col * (top_cell + gap)
        y = top_origin_y + row * (top_cell + gap)
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{top_cell}" height="{top_cell}" rx="6" '
            f'fill="{sticker_color(symbol)}" stroke="#1E293B" stroke-width="1.5"/>'
        )

    mini = 18
    step = mini + 4

    for offset, symbol in enumerate(back):
        x = top_origin_x + 4 + offset * step
        svg_parts.append(
            f'<rect x="{x}" y="42" width="{mini}" height="{mini}" rx="5" '
            f'fill="{sticker_color(symbol)}" stroke="#94A3B8" stroke-width="1.2"/>'
        )

    for offset, symbol in enumerate(front):
        x = top_origin_x + 4 + offset * step
        svg_parts.append(
            f'<rect x="{x}" y="170" width="{mini}" height="{mini}" rx="5" '
            f'fill="{sticker_color(symbol)}" stroke="#94A3B8" stroke-width="1.2"/>'
        )

    for offset, symbol in enumerate(left):
        y = top_origin_y + 4 + offset * step
        svg_parts.append(
            f'<rect x="72" y="{y}" width="{mini}" height="{mini}" rx="5" '
            f'fill="{sticker_color(symbol)}" stroke="#94A3B8" stroke-width="1.2"/>'
        )

    for offset, symbol in enumerate(right):
        y = top_origin_y + 4 + offset * step
        svg_parts.append(
            f'<rect x="230" y="{y}" width="{mini}" height="{mini}" rx="5" '
            f'fill="{sticker_color(symbol)}" stroke="#94A3B8" stroke-width="1.2"/>'
        )

    svg_parts.extend(
        [
            '<text x="143" y="34" fill="#64748B" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-weight="600">BACK</text>',
            '<text x="141" y="205" fill="#64748B" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-weight="600">FRONT</text>',
            '<text x="46" y="110" fill="#64748B" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-weight="600">LEFT</text>',
            '<text x="254" y="110" fill="#64748B" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-weight="600">RIGHT</text>',
            '<text x="28" y="224" fill="#94A3B8" font-family="Segoe UI, Arial, sans-serif" font-size="11">'
            "Generated from parsed cube stickers</text>",
            "</svg>",
        ]
    )

    output_path.write_text("".join(svg_parts), encoding="utf-8")

