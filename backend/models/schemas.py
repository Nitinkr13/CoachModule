from typing import List

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ConversationRequest(BaseModel):
    message: str


class ConversationResponse(BaseModel):
    reply: str


class EvaluationTurn(BaseModel):
    speaker: str
    text: str


class EvaluationRequest(BaseModel):
    role: str
    fileName: str
    history: List[EvaluationTurn]


class EvaluationResponse(BaseModel):
    score: int
    summary: str
    feedback: str
