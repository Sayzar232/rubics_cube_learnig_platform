"""Generate OLL diagrams as SVG files.

The input format is a dictionary with five keys:

    U: nine stickers of the upper face, read left-to-right, top-to-bottom
    B: three stickers behind the upper face (drawn above U)
    F: three stickers in front of the lower face (drawn below U)
    L: three stickers on the left side, read top-to-bottom
    R: three stickers on the right side, read top-to-bottom

Use ``Y`` for a yellow sticker and ``N`` for a non-yellow sticker.
The module has no third-party dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


COLOR_MAP = {
    "Y": "#FFE94A",  # yellow sticker
    "N": "#D9D9D9",  # non-yellow sticker
}

# Canvas and layout. Values are chosen to match the proportions in the
# reference image: large rounded central stickers and narrow side stickers.
SIZE = 512
CANVAS_COLOR = "#1E1E1E"
BACKGROUND = "#111111"
STICKER_GAP = 7
CELL = 64
STICKER_RADIUS = 12
EDGE_STICKER = 18
EDGE_RADIUS = 9

FACE_X = 133
FACE_Y = 133
FACE_SIZE = 3 * CELL + 2 * STICKER_GAP  # 206


def _rect(parent: Element, x: int, y: int, width: int, height: int,
          fill: str, radius: int) -> None:
    SubElement(
        parent,
        "rect",
        {
            "x": str(x),
            "y": str(y),
            "width": str(width),
            "height": str(height),
            "rx": str(radius),
            "ry": str(radius),
            "fill": fill,
        },
    )


def _validate(state: Mapping[str, Sequence[str]]) -> None:
    expected_lengths = {"U": 9, "B": 3, "F": 3, "L": 3, "R": 3}
    missing = set(expected_lengths) - set(state)
    extra = set(state) - set(expected_lengths)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing keys: {sorted(missing)}")
        if extra:
            details.append(f"unknown keys: {sorted(extra)}")
        raise ValueError("Invalid OLL dictionary (" + "; ".join(details) + ")")

    for face, length in expected_lengths.items():
        stickers = state[face]
        if len(stickers) != length:
            raise ValueError(f"{face} must contain {length} values, got {len(stickers)}")
        invalid = set(stickers) - set(COLOR_MAP)
        if invalid:
            raise ValueError(f"{face} contains invalid values: {sorted(invalid)}; use Y or N")


def generate_svg(state: Mapping[str, Sequence[str]], filename: str | Path) -> Path:
    """Render one OLL dictionary and save it to *filename*.

    ``B`` is rendered above the U face and ``F`` below it, as in the
    convention described in the question.
    """
    _validate(state)
    filename = Path(filename)

    svg = Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(SIZE),
            "height": str(SIZE),
            "viewBox": f"0 0 {SIZE} {SIZE}",
        },
    )
    # Dark canvas plus the compact black frame behind the cube net.
    # _rect(svg, 0, 0, SIZE, SIZE, CANVAS_COLOR, 0)
    # _rect(
    #     svg,
    #     FACE_X - EDGE_STICKER - 2 * STICKER_GAP,
    #     FACE_Y - EDGE_STICKER - 2 * STICKER_GAP,
    #     FACE_SIZE + 2 * (EDGE_STICKER + 2 * STICKER_GAP),
    #     FACE_SIZE + 2 * (EDGE_STICKER + 2 * STICKER_GAP),
    #     BACKGROUND,
    #     16,
    # )

    columns = [FACE_X + i * (CELL + STICKER_GAP) for i in range(3)]
    rows = [FACE_Y + i * (CELL + STICKER_GAP) for i in range(3)]

    # U: the 3x3 face.
    for index, value in enumerate(state["U"]):
        row, column = divmod(index, 3)
        _rect(svg, columns[column], rows[row], CELL, CELL,
              COLOR_MAP[value], STICKER_RADIUS)

    # B is behind U and therefore goes at the top; F goes at the bottom.
    top_y = FACE_Y - STICKER_GAP - EDGE_STICKER
    bottom_y = FACE_Y + FACE_SIZE + STICKER_GAP
    for column, value in enumerate(state["B"]):
        _rect(svg, columns[column], top_y, CELL, EDGE_STICKER,
              COLOR_MAP[value], EDGE_RADIUS)
    for column, value in enumerate(state["F"]):
        _rect(svg, columns[column], bottom_y, CELL, EDGE_STICKER,
              COLOR_MAP[value], EDGE_RADIUS)

    # L and R: the side strips, from top to bottom.
    left_x = FACE_X - STICKER_GAP - EDGE_STICKER
    right_x = FACE_X + FACE_SIZE + STICKER_GAP
    for row, value in enumerate(state["L"]):
        _rect(svg, left_x, rows[row], EDGE_STICKER, CELL,
              COLOR_MAP[value], EDGE_RADIUS)
    for row, value in enumerate(state["R"]):
        _rect(svg, right_x, rows[row], EDGE_STICKER, CELL,
              COLOR_MAP[value], EDGE_RADIUS)

    filename.parent.mkdir(parents=True, exist_ok=True)
    xml = minidom.parseString(tostring(svg, encoding="utf-8")).toprettyxml(
        indent="  ", encoding="utf-8"
    )
    filename.write_bytes(xml)
    return filename


def generate_many(olls: Mapping[str, Mapping[str, Sequence[str]]],
                  output_dir: str | Path = "svg") -> list[Path]:
    """Generate one ``<name>.svg`` file for every named OLL dictionary."""
    output_dir = Path(output_dir)
    return [
        generate_svg(state, output_dir / f"{name}.svg")
        for name, state in olls.items()
    ]


# Example from the question. Add more dictionaries to OLLS to generate them
# all with one run of the script.
oll_51 = {
    "U": ["N", "Y", "N", "N", "Y", "N", "N", "Y", "N"],
    "F": ["Y", "N", "N"],
    "R": ["Y", "Y", "Y"],
    "B": ["Y", "N", "N"],
    "L": ["N", "Y", "N"],
}

OLLS = {"oll_51": oll_51}


if __name__ == "__main__":
    created = generate_many(OLLS)
    for path in created:
        print(f"Created: {path}")
