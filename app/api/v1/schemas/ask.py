from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    context: str = Field(default="", max_length=10000)
    mode: str = Field(default="general", pattern="^(general|learning_path|code)$")


class AskResponse(BaseModel):
    answer: str
    references: list[str] = []
    processing_time_ms: int
    mode_used: str
