from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from models.schemas import EvaluationTurn


@dataclass
class StoredDocument:
    id: str
    name: str
    text: str
    source: str


@dataclass
class SessionData:
    id: str
    role: str
    document: StoredDocument
    system_prompt: str
    history: List[EvaluationTurn] = field(default_factory=list)


_PRESET_DOCUMENTS: Dict[str, StoredDocument] = {}
_UPLOADED_DOCUMENTS: Dict[str, StoredDocument] = {}
_SESSIONS: Dict[str, SessionData] = {}


def _load_preset_documents() -> None:
    if _PRESET_DOCUMENTS:
        return

    docs_root = Path(__file__).resolve().parents[1] / "configs" / "documents"
    if not docs_root.exists():
        return

    for path in sorted(docs_root.glob("*.txt")):
        doc_id = _slugify_id(path.stem, prefix="preset")
        _PRESET_DOCUMENTS[doc_id] = StoredDocument(
            id=doc_id,
            name=path.name,
            text=path.read_text(encoding="utf-8"),
            source="preset",
        )


def _slugify_id(value: str, prefix: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)
    safe = "-".join(segment for segment in safe.split("-") if segment)
    return f"{prefix}-{safe.lower() or 'doc'}"


def list_documents() -> List[StoredDocument]:
    _load_preset_documents()
    return [*_PRESET_DOCUMENTS.values(), *_UPLOADED_DOCUMENTS.values()]


def get_document(document_id: str) -> StoredDocument | None:
    _load_preset_documents()
    return _PRESET_DOCUMENTS.get(document_id) or _UPLOADED_DOCUMENTS.get(document_id)


def create_uploaded_document(name: str, text: str) -> StoredDocument:
    doc_id = f"upload-{uuid4().hex}"
    document = StoredDocument(id=doc_id, name=name, text=text, source="upload")
    _UPLOADED_DOCUMENTS[doc_id] = document
    return document


def create_session(role: str, document: StoredDocument, system_prompt: str) -> SessionData:
    session_id = uuid4().hex
    session = SessionData(
        id=session_id,
        role=role,
        document=document,
        system_prompt=system_prompt,
    )
    _SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> SessionData | None:
    return _SESSIONS.get(session_id)


def append_session_turn(session_id: str, speaker: str, text: str) -> None:
    session = _SESSIONS.get(session_id)
    if not session:
        return
    session.history.append(EvaluationTurn(speaker=speaker, text=text))
