from fastapi import APIRouter, HTTPException

from engines.conversation_engine import generate_reply
from engines.evaluation_engine import evaluate_session
from models.schemas import (
    ConversationRequest,
    ConversationResponse,
    EvaluationRequest,
    EvaluationResponse,
    HealthResponse,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/conversation", response_model=ConversationResponse)
def conversation(payload: ConversationRequest) -> ConversationResponse:
    reply = generate_reply(payload.message)
    return ConversationResponse(reply=reply)


@router.post("/evaluation", response_model=EvaluationResponse)
def evaluation(payload: EvaluationRequest) -> EvaluationResponse:
    try:
        result = evaluate_session(payload.role, payload.fileName, payload.history)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EvaluationResponse(
        score=result.score,
        summary=result.summary,
        feedback=result.report_markdown,
    )
