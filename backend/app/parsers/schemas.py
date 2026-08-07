from __future__ import annotations

from dataclasses import dataclass

from ..models.algorithm import AlgorithmCategory


@dataclass(slots=True)
class ParsedAlgorithm:
    category: AlgorithmCategory
    algorithm_number: int
    name: str
    group: str
    formula: str
    image_url: str
    sticker_state: dict[str, str]
    video_url: str | None = None
