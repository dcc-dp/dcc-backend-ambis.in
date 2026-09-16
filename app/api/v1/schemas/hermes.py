from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class HermesAgentRequest(BaseModel):
    student_id: UUID
    student_answer: str = Field(..., min_length=1, max_length=2000)
    session_id: UUID | None = None
    problem_id: UUID | None = None
    exercise_id: UUID | None = None  # required when problem_id is None (starts a new problem)
    mode: str = Field(default="ask", pattern="^(ask|learning_path|diagnostic)$")  # only used to start a NEW session
    time_spent_ms: int | None = None
    stream: bool = True

    @model_validator(mode="after")
    def _require_exercise_or_problem(self):
        if self.problem_id is None and self.exercise_id is None:
            raise ValueError("either problem_id or exercise_id is required")
        return self


class HermesAgentSSEEvent(BaseModel):
    event: str = "token"
    data: dict[str, Any] = Field(default_factory=dict)


class InterventionPayload(BaseModel):
    kind: str
    rule_code: str
    reason: str
    text: str


class HermesNonStreamResponse(BaseModel):
    session_id: UUID
    problem_id: UUID
    attempt_id: UUID
    attempt_number: int
    is_correct: bool
    error_type: str | None
    misconception_code: str | None
    intervention: InterventionPayload | None  # None iff the attempt was correct — no scaffolding needed
    mastery: float
    confidence: float
    processing_time_ms: int
