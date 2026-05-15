from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
import os

from app.db import get_db_session
from app.db.models import User, Document, ChatSession
from app.api.deps import get_current_user_from_token, get_rag_service
from app.services.rag_service import RAGService
from app.services.document_processor import DocumentService
from app.core.config import settings
from sqlalchemy import cast, String, or_

router = APIRouter(prefix="/rooms", tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint"
]

def process_document_background(doc_id, user_id, file_path, rag_service):
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        doc_service = DocumentService()
        doc_service.process_and_index(
            doc_id=doc_id,
            user_id=user_id,
            file_path=file_path,
            db_session=db,
            rag_service=rag_service
        )
    finally:
        db.close()


@router.post("/{room_name}/documents", status_code=202)
async def upload_document(
    room_name: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_from_token),
    rag_service: RAGService = Depends(get_rag_service),
    db: Session = Depends(get_db_session)
):
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, PPT, PPTX")

    # Verify room exists
    room = db.query(ChatSession).filter(
        ChatSession.user_id == user.id,
        ChatSession.room_name == room_name,
        ChatSession.session_type == "global"
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Save file to disk
    doc_id = str(uuid4())
    file_ext = file.filename.split(".")[-1]
    saved_filename = f"{doc_id}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Save to DB — dengan room_id
    doc = Document(
        id=doc_id,
        user_id=user.id,
        filename=saved_filename,
        original_filename=file.filename,
        file_size=len(content),
        file_type=file.content_type,
        status="pending",
        file_path=file_path,
        room_ids=[room_name],
        is_global=False,
        created_at=datetime.now(timezone.utc)
    )
    db.add(doc)
    db.commit()

    # ✅ Trigger background processing (sama seperti global upload)
    background_tasks.add_task(
        process_document_background,
        doc_id=doc_id,
        user_id=str(user.id),
        file_path=file_path,
        rag_service=rag_service
    )

    # ✅ Response fields match frontend interface
    return {
        "id": doc_id,                        # bukan doc_id
        "original_filename": file.filename,  # bukan filename
        "file_type": file.content_type,      # ✅ ada sekarang
        "status": "pending",
        "room_id": room_name,
    }


@router.get("/{room_name}/documents")
async def list_documents(
    room_name: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    docs = db.query(Document).filter(
        or_(Document.user_id == user.id, Document.is_global == True),
        cast(Document.room_ids, String).like(f'%"{room_name}"%')
    ).order_by(Document.created_at.desc()).all()

    return {
        "room_name": room_name,
        "documents": [
            {
                "id": str(doc.id),
                "original_filename": doc.original_filename,
                "file_type": doc.file_type,
                "status": doc.status,
                "total_chunks": doc.total_chunks,
                "created_at": doc.created_at,
                "is_global": getattr(doc, "is_global", False),
            }
            for doc in docs
        ]
    }