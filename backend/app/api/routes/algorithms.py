from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_user, get_optional_user
from ...core.database import get_db
from ...models.algorithm import AlgorithmCategory
from ...models.user import User
from ...schemas.algorithm import AlgorithmRead, NextAlgorithmResponse
from ...services.algorithm_service import get_algorithm_details, get_next_algorithm, list_algorithms


router = APIRouter(prefix="/algorithms", tags=["algorithms"])


@router.get("", response_model=list[AlgorithmRead])
def get_algorithms(
    category: AlgorithmCategory | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> list[AlgorithmRead]:
    return list_algorithms(db, current_user, category)


@router.get("/next", response_model=NextAlgorithmResponse)
def get_next(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NextAlgorithmResponse:
    algorithm = get_next_algorithm(db, current_user)
    if algorithm is None:
        return NextAlgorithmResponse(
            completed=True,
            message="Поздравляем! Все алгоритмы изучены.",
            algorithm=None,
        )

    return NextAlgorithmResponse(
        completed=False,
        message="Следующий алгоритм готов к изучению.",
        algorithm=algorithm,
    )


@router.get("/{algorithm_id}", response_model=AlgorithmRead)
def get_algorithm(
    algorithm_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> AlgorithmRead:
    try:
        return get_algorithm_details(db, current_user, algorithm_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Алгоритм не найден.") from exc

