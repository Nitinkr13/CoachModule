from typing import Any, Dict, List, Optional

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


class PersonaSummary(BaseModel):
    id: str
    name: str
    description: str
    behavior: str
    cmTreatment: str
    impact: str


class PersonasResponse(BaseModel):
    personas: List[PersonaSummary]


class ScenarioSummary(BaseModel):
    id: str
    name: str
    goal: str


class EvaluationTurn(BaseModel):
    speaker: str
    text: str


class EvaluationRequest(BaseModel):
    sessionId: Optional[str] = None
    history: List[EvaluationTurn] = Field(default_factory=list)


class EvaluationRubricItem(BaseModel):
    id: str
    label: str
    score: int
    notes: str


class EvaluationResponse(BaseModel):
    score: int
    summary: str
    feedback: str
    report: Dict[str, Any] = Field(default_factory=dict)
    reportMarkdown: Optional[str] = None
    rubric: List[EvaluationRubricItem] = Field(default_factory=list)


class SessionStartRequest(BaseModel):
    personaId: str
    scenarioId: Optional[str] = None


class SessionStartResponse(BaseModel):
    sessionId: str
    persona: PersonaSummary
    scenario: ScenarioSummary
