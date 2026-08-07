"""Parse OLL and PLL cube diagrams from SVG files into ``situations.json``.

The source diagrams are expected in ``frontend/dist/assets/algorithms`` and
have the layout used by SpeedCubeDB: the 3x3 U face is in the middle, with
the B, F, L and R stickers drawn as narrow strips around it.

Run from the project root::

    python parse_svg.py

The output is a JSON object keyed by SVG filename, for example ``oll-01`` or
``pll-21``.  Every value has the following shape::

    {"U": ["N", ...], "F": ["N", ...], "R": ["N", ...],
     "B": ["N", ...], "L": ["N", ...]}

OLL uses ``Y`` for yellow and ``N`` for a non-yellow sticker.  PLL retains
all sticker colours: ``Y``, ``O``, ``R``, ``G`` and ``B``.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = PROJECT_ROOT / "frontend" / "dist" / "assets" / "algorithms"
DEFAULT_OUTPUT = PROJECT_ROOT / "situations.json"

# Colours used in the downloaded SpeedCubeDB SVGs.  Values are the first
# letters required by the application's situation format.
COLOURS = {
    "#ffff00": "Y",
    "#888888": "N",
    "#ee8800": "O",
    "#d00000": "R",
    "#11aa00": "G",
    "#2040d0": "B",
}
FACE_ORDER = ("U", "F", "R", "B", "L")


def _number(rect: ET.Element, name: str, source: Path) -> float:
    try:
        return float(rect.attrib[name])
    except (KeyError, ValueError) as error:
        raise ValueError(f"{source}: rect without a valid {name!r} attribute") from error


def _colour(rect: ET.Element, source: Path) -> str:
    raw = rect.attrib.get("fill", "").lower()
    try:
        return COLOURS[raw]
    except KeyError as error:
        raise ValueError(f"{source}: unsupported sticker colour {raw!r}") from error


def _clusters(values: Iterable[float], expected: int, source: Path, axis: str) -> dict[float, int]:
    """Map the repeated coordinates of U-face sub-rectangles to 3 cells."""
    unique = sorted(set(values))
    if len(unique) != expected * 2:
        raise ValueError(
            f"{source}: expected {expected * 2} U-face {axis} coordinates, got {len(unique)}"
        )
    return {value: index // 2 for index, value in enumerate(unique)}


def _strip(values: list[tuple[float, str]], face: str, source: Path) -> list[str]:
    if len(values) != 3:
        raise ValueError(f"{source}: expected 3 stickers for {face}, got {len(values)}")
    return [colour for _, colour in sorted(values)]


def parse_svg(source: Path) -> dict[str, list[str]]:
    """Return the five visible faces encoded by one SpeedCubeDB SVG."""
    try:
        root = ET.parse(source).getroot()
    except ET.ParseError as error:
        raise ValueError(f"{source}: invalid SVG") from error

    rectangles = []
    for rect in root.iter():
        if rect.tag.rsplit("}", 1)[-1] != "rect":
            continue
        # Ignore the black frame before classifying narrow rectangles: it has
        # an aspect ratio similar to a side sticker.
        if rect.attrib.get("fill", "").lower() not in COLOURS:
            continue
        x, y = _number(rect, "x", source), _number(rect, "y", source)
        width, height = _number(rect, "width", source), _number(rect, "height", source)
        # The 3x3 U face consists of 36 small, nearly square sub-rectangles.
        if 0.75 <= width / height <= 1.33 and max(width, height) < 30:
            rectangles.append((x, y, width, height, _colour(rect, source)))

    if len(rectangles) != 36:
        raise ValueError(f"{source}: expected 36 U-face sub-rectangles, got {len(rectangles)}")

    x_cells = _clusters((item[0] for item in rectangles), 3, source, "x")
    y_cells = _clusters((item[1] for item in rectangles), 3, source, "y")
    u_colours: dict[tuple[int, int], set[str]] = defaultdict(set)
    for x, y, _width, _height, colour in rectangles:
        u_colours[y_cells[y], x_cells[x]].add(colour)

    u = []
    for row in range(3):
        for column in range(3):
            colours = u_colours[row, column]
            if len(colours) != 1:
                raise ValueError(f"{source}: ambiguous U sticker at row {row}, column {column}")
            u.append(colours.pop())

    min_x = min(item[0] for item in rectangles)
    max_x = max(item[0] + item[2] for item in rectangles)
    min_y = min(item[1] for item in rectangles)
    max_y = max(item[1] + item[3] for item in rectangles)
    strips: dict[str, list[tuple[float, str]]] = defaultdict(list)

    for rect in root.iter():
        if rect.tag.rsplit("}", 1)[-1] != "rect":
            continue
        if rect.attrib.get("fill", "").lower() not in COLOURS:
            continue
        x, y = _number(rect, "x", source), _number(rect, "y", source)
        width, height = _number(rect, "width", source), _number(rect, "height", source)
        # Side stickers are narrow rectangles; black frame rectangles are much
        # larger and do not meet this condition.
        if width > height * 2 and height < 10:
            face, position = ("B", x) if y < min_y else ("F", x) if y > max_y else (None, None)
        elif height > width * 2 and width < 10:
            face, position = ("L", y) if x < min_x else ("R", y) if x > max_x else (None, None)
        else:
            continue
        if face is not None:
            strips[face].append((position, _colour(rect, source)))

    situation = {"U": u}
    situation.update({face: _strip(strips[face], face, source) for face in ("F", "R", "B", "L")})
    if source.stem.startswith("oll-"):
        invalid = {colour for values in situation.values() for colour in values} - {"Y", "N"}
        if invalid:
            raise ValueError(f"{source}: OLL contains non-OLL colours {sorted(invalid)}")
    return situation


def parse_directory(input_dir: Path) -> dict[str, dict[str, list[str]]]:
    files = sorted(input_dir.glob("*.svg"), key=lambda path: (path.stem[:3], int(path.stem[4:])))
    if not files:
        raise FileNotFoundError(f"No SVG files found in {input_dir}")
    return {path.stem: parse_svg(path) for path in files if path.stem.startswith(("oll-", "pll-"))}


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse OLL/PLL SVG situations into JSON.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    situations = parse_directory(args.input_dir)
    args.output.write_text(json.dumps(situations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(situations)} situations to {args.output}")


if __name__ == "__main__":
    main()
