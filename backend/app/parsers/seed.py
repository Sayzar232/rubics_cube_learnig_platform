from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from sqlalchemy import func, select

from ..core.database import SessionLocal
from ..models.algorithm import Algorithm, AlgorithmCategory
from .schemas import ParsedAlgorithm
from .speedcubedb import SpeedCubeDbParser

# Данные 41 случая F2L, извлечённые парсером SpeedCubeDB (parse_f2l_page.js --cases).
# Хранятся в репозитории, чтобы сид F2L работал офлайн и не зависел от сайта-источника.
_F2L_CASES_PATH = Path(__file__).with_name("f2l_cases.json")


def load_f2l_cases() -> list[ParsedAlgorithm]:
    """Список из 41 алгоритма F2L из f2l_cases.json."""
    raw_cases = json.loads(_F2L_CASES_PATH.read_text(encoding="utf-8"))
    cases: list[ParsedAlgorithm] = []
    for row in raw_cases:
        cases.append(
            ParsedAlgorithm(
                category=AlgorithmCategory.F2L,
                algorithm_number=int(row["number"]),
                name=str(row["name"]),
                group=str(row["group"]),
                formula=str(row["formula"]),
                image_url=str(row["image_url"]),
                # Состояние наклеек F2L хранится в situations.json и серверу не нужно
                # (сервис диаграмм рисует SVG из situations.json, а не из стейта).
                sticker_state={},
                video_url=row.get("video_url") or None,
            )
        )
    return cases


def upsert_algorithm(existing: Algorithm | None, parsed: ParsedAlgorithm) -> tuple[Algorithm, bool]:
    if existing is None:
        algorithm = Algorithm(
            category=parsed.category,
            algorithm_number=parsed.algorithm_number,
            name=parsed.name,
            group=parsed.group,
            formula=parsed.formula,
            image_url=parsed.image_url,
            video_url=parsed.video_url,
        )
        return algorithm, True

    existing.algorithm_number = parsed.algorithm_number
    existing.group = parsed.group
    existing.formula = parsed.formula
    existing.image_url = parsed.image_url
    existing.video_url = parsed.video_url
    return existing, False


def seed_algorithms(only_if_empty: bool = False) -> tuple[int, int]:
    created = 0
    updated = 0

    with SessionLocal() as session:
        existing_count = session.scalar(select(func.count(Algorithm.id))) or 0

        # F2L сидится всегда: данные локальные (f2l_cases.json), upsert идемпотентен,
        # поэтому существующая БД досевается 41 случаем при каждом запуске — без сети.
        # F2L идёт первым: algorithm_sort_key назначает ему category_rank 0, и в каталоге
        # случай F2L #01 становится первым среди 119 алгоритмов.
        # OLL/PLL парсятся с SpeedCubeDB, если (--only-if-empty) таблица пуста либо флага нет.
        batches: list[tuple[AlgorithmCategory, Iterable[ParsedAlgorithm]]] = [
            (AlgorithmCategory.F2L, load_f2l_cases()),
        ]
        if not (only_if_empty and existing_count > 0):
            parser = SpeedCubeDbParser()
            for category in (AlgorithmCategory.OLL, AlgorithmCategory.PLL):
                batches.append((category, parser.parse_category(category)))

        for category, parsed_algorithms in batches:
            for parsed in parsed_algorithms:
                existing = session.scalar(
                    select(Algorithm).where(
                        Algorithm.category == parsed.category,
                        Algorithm.name == parsed.name,
                    )
                )
                algorithm, is_created = upsert_algorithm(existing, parsed)
                if is_created:
                    session.add(algorithm)
                    created += 1
                else:
                    updated += 1

        session.commit()

    return created, updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed F2L, OLL and PLL algorithms from SpeedCubeDB.")
    parser.add_argument(
        "--only-if-empty",
        action="store_true",
        help="Skip parsing when the algorithms table already has data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created, updated = seed_algorithms(only_if_empty=args.only_if_empty)
    print(f"Algorithms imported. Created: {created}, updated: {updated}")


if __name__ == "__main__":
    main()
