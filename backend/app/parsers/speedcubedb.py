from __future__ import annotations

from urllib.parse import urljoin
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

from ..core.config import get_settings
from ..models.algorithm import AlgorithmCategory
from .image_generator import render_case_svg
from .schemas import ParsedAlgorithm
from ..services.algorithm_service import extract_numeric_suffix


settings = get_settings()

CATEGORY_URLS = {
    AlgorithmCategory.OLL: "https://speedcubedb.com/a/3x3/OLL",
    AlgorithmCategory.PLL: "https://speedcubedb.com/a/3x3/PLL",
}


class SpeedCubeDbParser:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.speedcubedb_user_agent})

    def parse_category(self, category: AlgorithmCategory) -> list[ParsedAlgorithm]:
        response = self.session.get(CATEGORY_URLS[category], timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select(".row.singlealgorithm")
        if not rows:
            raise RuntimeError(f"Не удалось найти алгоритмы на странице {CATEGORY_URLS[category]}")

        algorithms: list[ParsedAlgorithm] = []
        for fallback_number, row in enumerate(rows, start=1):
            name = self._extract_name(row)
            formula = self._extract_formula(row)
            if not name or not formula:
                continue

            algorithm_number = extract_numeric_suffix(name, fallback_number)
            sticker_state = self._extract_sticker_state(row)
            filename = f"{category.value.lower()}-{algorithm_number:02d}.svg"
            image_path = settings.algorithm_assets_dir / filename
            self._save_case_svg(row, image_path, sticker_state, name)

            algorithms.append(
                ParsedAlgorithm(
                    category=category,
                    algorithm_number=algorithm_number,
                    name=name,
                    group=self._extract_group(row),
                    formula=formula,
                    image_url=f"/assets/algorithms/{filename}",
                    sticker_state=sticker_state,
                    video_url=self._extract_video_url(row),
                )
            )

        return algorithms

    @staticmethod
    def _extract_name(row: Tag) -> str:
        if row.get("data-alg"):
            return row.get("data-alg", "").strip()

        heading = row.select_one("h2 a")
        if heading:
            return heading.get_text(" ", strip=True)
        return ""

    @staticmethod
    def _extract_formula(row: Tag) -> str:
        panel = row.select_one(".scdb-panel")
        if panel is None:
            alternative = row.select_one(".formatted-alg")
            return alternative.get_text(" ", strip=True) if alternative else ""

        parts = list(panel.stripped_strings)
        if len(parts) >= 2:
            return " ".join(parts[1:]).strip()

        text = panel.get_text(" ", strip=True)
        return text.replace("Standard Alg:", "", 1).strip()

    @staticmethod
    def _extract_group(row: Tag) -> str:
        """Return the SpeedCubeDB subgroup, e.g. ``Dot Case`` or ``T Shapes``."""
        subgroup = row.get("data-subgroup", "").strip()
        if subgroup:
            return subgroup

        group_link = row.select_one(".category-subtitle a[data-filter]")
        if group_link:
            return group_link.get_text(" ", strip=True)
        return "Uncategorized"

    @staticmethod
    def _save_case_svg(
        row: Tag,
        image_path: Path,
        sticker_state: dict[str, str],
        title: str,
    ) -> None:
        """Store the original 75px case diagram when it is present.

        The standalone Selenium parsers receive a browser-rendered page, while
        the seed parser uses the site's HTTP response.  SpeedCubeDB may omit
        the SVG from that response, so retain the sticker-data renderer as a
        reliable fallback.
        """
        svg = row.select_one("svg[width='75']")
        if svg is None:
            render_case_svg(sticker_state, title, image_path)
            return

        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_text(svg.prettify(), encoding="utf-8")

    @staticmethod
    def _extract_sticker_state(row: Tag) -> dict[str, str]:
        jcube = row.select_one(".jcube")
        if jcube is None:
            return {}

        return {
            "us": jcube.get("data-us", ""),
            "ub": jcube.get("data-ub", ""),
            "uf": jcube.get("data-uf", ""),
            "ul": jcube.get("data-ul", ""),
            "ur": jcube.get("data-ur", ""),
        }

    @staticmethod
    def _extract_video_url(row: Tag) -> str | None:
        video_link = row.select_one("a[href*='youtube.com']")
        if video_link is None:
            return None
        return urljoin("https://speedcubedb.com", video_link.get("href", ""))
