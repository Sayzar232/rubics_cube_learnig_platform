from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.algorithm import Algorithm, AlgorithmCategory
from ..models.user import User
from ..models.user_progress import UserProgress
from ..schemas.algorithm import AlgorithmRead


# The order is defined in ``порядок.txt``.  Keep the spelling aliases here
# because SpeedCubeDB has used both singular/plural and slightly different
# spellings for some subgroup names over time.
GROUP_ORDER: dict[AlgorithmCategory, tuple[str, ...]] = {
    AlgorithmCategory.OLL: (
        "OCLL",
        "T-shapes",
        "Dot-cases",
        "Line-shapes",
        "Square-shapes",
        "All corners oriented",
        "Knight move shapes",
        "C-shapes",
        "P-shapes",
        "Lighting Shapes",
        "W-shapes",
        "Fish shapes",
        "Awkward Shapes",
        "L-shapes",
    ),
    AlgorithmCategory.PLL: (
        "EPLL",
        "Adj swap",
        "OPP swap",
    ),
}


def _normalized_group(group: str) -> str:
    """Normalize subgroup labels to compare parser output reliably."""
    normalized = re.sub(r"[^a-z0-9]", "", group.casefold())
    if normalized.endswith("s"):
        normalized = normalized[:-1]
    # ``Lighting`` is misspelled as ``Lightning`` on some source pages.
    if normalized == "lightningshape":
        return "lightingshape"
    if normalized == "adjacentswap":
        return "adjswap"
    if normalized == "oppositeswap":
        return "oppswap"
    return normalized


_GROUP_RANKS = {
    category: {
        _normalized_group(group): rank
        for rank, group in enumerate(groups)
    }
    for category, groups in GROUP_ORDER.items()
}


def algorithm_sort_key(algorithm: Algorithm) -> tuple[int, int, int]:
    """Sort algorithms by category, configured subgroup, then case number."""
    category_rank = {
        AlgorithmCategory.OLL: 0,
        AlgorithmCategory.PLL: 1,
    }.get(algorithm.category, 99)
    group_rank = _GROUP_RANKS.get(algorithm.category, {}).get(
        _normalized_group(algorithm.group),
        len(GROUP_ORDER.get(algorithm.category, ())),
    )
    return category_rank, group_rank, algorithm.algorithm_number


def serialize_algorithm(algorithm: Algorithm, is_learned: bool) -> AlgorithmRead:
    return AlgorithmRead(
        id=algorithm.id,
        category=algorithm.category,
        algorithm_number=algorithm.algorithm_number,
        name=algorithm.name,
        group=algorithm.group,
        formula=algorithm.formula,
        image_url=algorithm.image_url,
        video_url=algorithm.video_url,
        created_at=algorithm.created_at,
        is_learned=is_learned,
    )


def get_learned_algorithm_ids(db: Session, user: User) -> set[int]:
    rows = db.scalars(select(UserProgress.algorithm_id).where(UserProgress.user_id == user.id)).all()
    return set(rows)


def list_algorithms(
    db: Session,
    user: User,
    category: AlgorithmCategory | None = None,
) -> list[AlgorithmRead]:
    learned_ids = get_learned_algorithm_ids(db, user)
    stmt = select(Algorithm)
    if category is not None:
        stmt = stmt.where(Algorithm.category == category)
    algorithms = sorted(db.scalars(stmt).all(), key=algorithm_sort_key)
    return [serialize_algorithm(algorithm, algorithm.id in learned_ids) for algorithm in algorithms]


def get_algorithm_or_404(db: Session, algorithm_id: int) -> Algorithm:
    algorithm = db.get(Algorithm, algorithm_id)
    if algorithm is None:
        raise ValueError(f"Algorithm {algorithm_id} not found")
    return algorithm


def get_algorithm_details(db: Session, user: User, algorithm_id: int) -> AlgorithmRead:
    algorithm = get_algorithm_or_404(db, algorithm_id)
    learned_ids = get_learned_algorithm_ids(db, user)
    return serialize_algorithm(algorithm, algorithm.id in learned_ids)


def get_next_algorithm(db: Session, user: User) -> AlgorithmRead | None:
    learned_subquery = select(UserProgress.algorithm_id).where(UserProgress.user_id == user.id)
    algorithms = db.scalars(
        select(Algorithm).where(Algorithm.id.not_in(learned_subquery))
    ).all()
    algorithm = min(algorithms, key=algorithm_sort_key) if algorithms else None
    if algorithm is None:
        return None
    return serialize_algorithm(algorithm, is_learned=False)


def extract_numeric_suffix(name: str, fallback_number: int) -> int:
    match = re.search(r"(\d+)$", name)
    if match:
        return int(match.group(1))
    return fallback_number
