from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class LearningPathBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    topic: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., pattern="^(beginner|intermediate|advanced)$")


class LearningPathCreate(LearningPathBase):
    pass


class LearningPathResponse(LearningPathBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
