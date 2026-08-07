from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models.algorithm import Algorithm, AlgorithmCategory
from ..models.user import User
from ..models.user_progress import UserProgress
from ..schemas.progress import ProgressOverview, ProgressRecordRead, ProgressStatistics
from .algorithm_service import get_next_algorithm


def get_progress_statistics(db: Session, user: User) -> ProgressStatistics:
    total_rows = db.execute(
        select(Algorithm.category, func.count(Algorithm.id)).group_by(Algorithm.category)
    ).all()
    learned_rows = db.execute(
        select(Algorithm.category, func.count(UserProgress.id))
        .join(UserProgress, UserProgress.algorithm_id == Algorithm.id)
        .where(UserProgress.user_id == user.id)
        .group_by(Algorithm.category)
    ).all()

    totals = {category: count for category, count in total_rows}
    learned = {category: count for category, count in learned_rows}

    oll_total = totals.get(AlgorithmCategory.OLL, 0)
    pll_total = totals.get(AlgorithmCategory.PLL, 0)
    oll_learned = learned.get(AlgorithmCategory.OLL, 0)
    pll_learned = learned.get(AlgorithmCategory.PLL, 0)

    learned_total = oll_learned + pll_learned
    total_algorithms = oll_total + pll_total
    overall_percentage = round((learned_total / total_algorithms) * 100, 1) if total_algorithms else 0.0

    return ProgressStatistics(
        oll_learned=oll_learned,
        oll_total=oll_total,
        pll_learned=pll_learned,
        pll_total=pll_total,
        learned_total=learned_total,
        total_algorithms=total_algorithms,
        overall_percentage=overall_percentage,
    )


def get_progress_overview(db: Session, user: User) -> ProgressOverview:
    rows = db.execute(
        select(UserProgress, Algorithm)
        .join(Algorithm, Algorithm.id == UserProgress.algorithm_id)
        .where(UserProgress.user_id == user.id)
        .order_by(UserProgress.learned_at.desc())
    ).all()

    records = [
        ProgressRecordRead(
            algorithm_id=algorithm.id,
            algorithm_name=algorithm.name,
            category=algorithm.category,
            algorithm_number=algorithm.algorithm_number,
            learned_at=progress.learned_at,
        )
        for progress, algorithm in rows
    ]

    return ProgressOverview(statistics=get_progress_statistics(db, user), records=records)


def mark_algorithm_complete(db: Session, user: User, algorithm_id: int) -> None:
    algorithm = db.get(Algorithm, algorithm_id)
    if algorithm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Алгоритм не найден.")

    existing_progress = db.scalar(
        select(UserProgress).where(
            UserProgress.user_id == user.id,
            UserProgress.algorithm_id == algorithm_id,
        )
    )
    if existing_progress is None:
        db.add(UserProgress(user_id=user.id, algorithm_id=algorithm_id))
        db.commit()


def get_completion_message(db: Session, user: User) -> tuple[str, bool]:
    next_algorithm = get_next_algorithm(db, user)
    if next_algorithm is None:
        return "Поздравляем! Все алгоритмы изучены.", True
    return "Алгоритм отмечен как изученный. Открываем следующий.", False

