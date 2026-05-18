from typing import List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ConversationRequest(BaseModel):
    message: str


class ConversationResponse(BaseModel):
    reply: str


class DocumentSummary(BaseModel):
    id: str
    name: str
    source: str


class DocumentsResponse(BaseModel):
    documents: List[DocumentSummary]


class DocumentUploadResponse(BaseModel):
    document: DocumentSummary


class EvaluationTurn(BaseModel):
    speaker: str
    text: str


class EvaluationRequest(BaseModel):
    sessionId: Optional[str] = None
    role: Optional[str] = None
    fileName: Optional[str] = None
    history: List[EvaluationTurn] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    score: int
    summary: str
    feedback: str


class SessionStartRequest(BaseModel):
    role: str
    documentId: str


class SessionStartResponse(BaseModel):
    sessionId: str
    document: DocumentSummary
