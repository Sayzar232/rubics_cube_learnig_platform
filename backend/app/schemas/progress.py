from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from ..models.algorithm import AlgorithmCategory
from .algorithm import AlgorithmRead


class ProgressStatistics(BaseModel):
    oll_learned: int
    
    oll_total: int
    pll_learned: int
    pll_total: int
    learned_total: int
    total_algorithms: int
    overall_percentage: float


class ProgressRecordRead(BaseModel):
    algorithm_id: int
    algorithm_name: str
    category: AlgorithmCategory
    algorithm_number: int
    learned_at: datetime


class ProgressOverview(BaseModel):
    statistics: ProgressStatistics
    records: list[ProgressRecordRead]


class CompleteAlgorithmResponse(BaseModel):
    completed_algorithm_id: int
    next_algorithm: AlgorithmRead | None
    statistics: ProgressStatistics
    message: str

