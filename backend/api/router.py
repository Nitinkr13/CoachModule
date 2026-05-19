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
from engines.prompt_engine import build_simulation_prompt
from engines.simulation_engine import list_personas, resolve_simulation
from models.schemas import (
    ConversationRequest,
    ConversationResponse,
    DocumentSummary,
    DocumentUploadResponse,
    DocumentsResponse,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationRubricItem,
    HealthResponse,
    PersonaSummary,
    PersonasResponse,
    ScenarioSummary,
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


@router.get("/personas", response_model=PersonasResponse)
def personas() -> PersonasResponse:
    items = [
        PersonaSummary(
            id=persona.id,
            name=persona.name,
            description=persona.description,
            behavior=persona.behavior,
            cmTreatment=persona.cm_treatment,
            impact=persona.impact,
        )
        for persona in list_personas()
    ]
    return PersonasResponse(personas=items)


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
    try:
        context = resolve_simulation(payload.personaId, payload.scenarioId)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    template = load_text("templates", context.scenario.template_id)
    system_prompt = build_simulation_prompt(context.persona, context.scenario, template)
    session = create_session(
        persona_id=context.persona.id,
        persona_name=context.persona.name,
        scenario_id=context.scenario.id,
        scenario_name=context.scenario.name,
        evaluation_id=context.evaluation.id,
        system_prompt=system_prompt,
    )

    return SessionStartResponse(
        sessionId=session.id,
        persona=PersonaSummary(
            id=context.persona.id,
            name=context.persona.name,
            description=context.persona.description,
            behavior=context.persona.behavior,
            cmTreatment=context.persona.cm_treatment,
            impact=context.persona.impact,
        ),
        scenario=ScenarioSummary(
            id=context.scenario.id,
            name=context.scenario.name,
            goal=context.scenario.goal,
        ),
    )


@router.post("/evaluation", response_model=EvaluationResponse)
def evaluation(payload: EvaluationRequest) -> EvaluationResponse:
    history = payload.history
    context = None

    if payload.sessionId:
        session = get_session(payload.sessionId)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        history = session.history
        try:
            context = resolve_simulation(session.persona_id, session.scenario_id)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not context:
        raise HTTPException(status_code=400, detail="Missing sessionId for evaluation.")

    try:
        result = evaluate_session(context.persona, context.scenario, context.evaluation, history)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return EvaluationResponse(
        score=result.score,
        summary=result.summary,
        feedback=result.feedback,
        report=result.report,
        reportMarkdown=result.report_markdown,
        rubric=[
            EvaluationRubricItem(
                id=item.id,
                label=item.label,
                score=item.score,
                notes=item.notes,
            )
            for item in result.rubric
        ],
    )
