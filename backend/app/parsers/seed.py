from __future__ import annotations

import argparse
from typing import Iterable

from sqlalchemy import func, select

from ..core.database import SessionLocal
from ..models.algorithm import Algorithm, AlgorithmCategory
from .schemas import ParsedAlgorithm
from .speedcubedb import SpeedCubeDbParser


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
    parser = SpeedCubeDbParser()
    created = 0
    updated = 0

    with SessionLocal() as session:
        existing_count = session.scalar(select(func.count(Algorithm.id))) or 0
        if only_if_empty and existing_count > 0:
            return created, updated

        for category in (AlgorithmCategory.OLL, AlgorithmCategory.PLL):
            parsed_algorithms = parser.parse_category(category)
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
    parser = argparse.ArgumentParser(description="Seed OLL and PLL algorithms from SpeedCubeDB.")
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
