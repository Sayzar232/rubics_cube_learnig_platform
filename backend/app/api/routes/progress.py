from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_user
from ...core.database import get_db
from ...models.user import User
from ...schemas.progress import CompleteAlgorithmResponse, ProgressOverview, ProgressStatistics
from ...services.algorithm_service import get_next_algorithm
from ...services.progress_service import (
    get_completion_message,
    get_progress_overview,
    get_progress_statistics,
    mark_algorithm_complete,
)


router = APIRouter(prefix="/progress", tags=["progress"])


@router.post("/complete/{algorithm_id}", response_model=CompleteAlgorithmResponse)
def complete_algorithm(
    algorithm_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompleteAlgorithmResponse:
    mark_algorithm_complete(db, current_user, algorithm_id)
    message, _ = get_completion_message(db, current_user)
    return CompleteAlgorithmResponse(
        completed_algorithm_id=algorithm_id,
        next_algorithm=get_next_algorithm(db, current_user),
        statistics=get_progress_statistics(db, current_user),
        message=message,
    )


@router.get("", response_model=ProgressOverview)
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressOverview:
    return get_progress_overview(db, current_user)


@router.get("/statistics", response_model=ProgressStatistics)
def get_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressStatistics:
    return get_progress_statistics(db, current_user)

