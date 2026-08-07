from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ..models.algorithm import AlgorithmCategory


class AlgorithmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: AlgorithmCategory
    algorithm_number: int
    name: str
    group: str
    formula: str
    image_url: str
    video_url: str | None
    created_at: datetime
    is_learned: bool = False


class NextAlgorithmResponse(BaseModel):
    completed: bool
    message: str
    algorithm: AlgorithmRead | None
