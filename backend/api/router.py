import io
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pypdf import PdfReader

from app.store import (
    create_session,
    create_uploaded_document,
    get_document,
    get_session,
    list_documents,
)
from configs.loader import load_text
from engines.conversation_engine import generate_reply
from engines.evaluation_engine import evaluate_session
from engines.prompt_engine import build_live_system_prompt
from models.schemas import (
    ConversationRequest,
    ConversationResponse,
    DocumentSummary,
    DocumentUploadResponse,
    DocumentsResponse,
    EvaluationRequest,
    EvaluationResponse,
    HealthResponse,
    SessionStartRequest,
    SessionStartResponse,
)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/conversation", response_model=ConversationResponse)
def conversation(payload: ConversationRequest) -> ConversationResponse:
    reply = generate_reply(payload.message)
    return ConversationResponse(reply=reply)


def _extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _extract_text_from_bytes(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore").strip()


@router.get("/documents", response_model=DocumentsResponse)
def documents() -> DocumentsResponse:
    docs = [
        DocumentSummary(id=doc.id, name=doc.name, source=doc.source)
        for doc in list_documents()
    ]
    return DocumentsResponse(documents=docs)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    filename = file.filename or "document.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".pdf"}:
        raise HTTPException(status_code=400, detail="Unsupported document type.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if suffix == ".pdf":
        text = _extract_text_from_pdf(data)
    else:
        text = _extract_text_from_bytes(data)

    if not text:
        raise HTTPException(status_code=400, detail="No text extracted from document.")

    document = create_uploaded_document(filename, text)
    return DocumentUploadResponse(
        document=DocumentSummary(
            id=document.id,
            name=document.name,
            source=document.source,
        )
    )


@router.post("/session/start", response_model=SessionStartResponse)
def session_start(payload: SessionStartRequest) -> SessionStartResponse:
    document = get_document(payload.documentId)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    template = load_text("templates", "live_session")
    system_prompt = build_live_system_prompt(payload.role, document.text, template)
    session = create_session(payload.role, document, system_prompt)

    return SessionStartResponse(
        sessionId=session.id,
        document=DocumentSummary(
            id=document.id,
            name=document.name,
            source=document.source,
        ),
    )


@router.post("/evaluation", response_model=EvaluationResponse)
def evaluation(payload: EvaluationRequest) -> EvaluationResponse:
    role = payload.role or "Unknown"
    file_name = payload.fileName or "Unknown"
    history = payload.history

    if payload.sessionId:
        session = get_session(payload.sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        role = session.role
        file_name = session.document.name
        history = session.history

    try:
        result = evaluate_session(role, file_name, history)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EvaluationResponse(
        score=result.score,
        summary=result.summary,
        feedback=result.report_markdown,
    )
