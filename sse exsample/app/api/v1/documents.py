"""
Document Upload Endpoints
=========================
PDF/PPT upload dan processing ke Qdrant
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String

from app.db import get_db_session
from app.db.models import User, Document
from app.models.schemas import DocumentResponse
from app.api.deps import get_current_user_from_token, get_rag_service
from app.services.rag_service import RAGService
from app.services.document_processor import DocumentService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint"
]


def process_document_background(
    doc_id: str,
    user_id: str,
    file_path: str,
    rag_service: RAGService,
    original_filename: Optional[str] = None,
):
    """
    Background task untuk process dokumen.
    """
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        doc_service = DocumentService()
        result = doc_service.process_and_index(
            doc_id=doc_id,
            user_id=user_id,
            file_path=file_path,
            original_filename=original_filename or "",
            db_session=db,
            rag_service=rag_service
        )
        logger.info(f"Document processing result: {result}")
    finally:
        db.close()


# ==============================================================================
# Endpoints
# ==============================================================================

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    is_global: bool = Form(False),  # Default ke Private
    room_id: Optional[str] = Form(None),
    user: User = Depends(get_current_user_from_token),
    rag_service: RAGService = Depends(get_rag_service),
    db: Session = Depends(get_db_session)
):
    """
    Upload dokumen PDF/PPT (Public atau Private).
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, PPT, PPTX")

    doc_id = str(uuid.uuid4())
    file_ext = file.filename.split(".")[-1]
    saved_filename = f"{doc_id}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    content = await file.read()
    
    # FIX 1: Max 50MB (50 * 1024 * 1024)
    MAX_FILE_SIZE = 1024 * 1024 * 1024
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 1024MB.")
        
    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        id=doc_id,
        user_id=str(user.id),
        filename=saved_filename,
        original_filename=file.filename, # Database udah aman
        file_size=len(content),
        file_type=file_ext,
        file_path=file_path,
        status="processing",
        is_global=is_global,
        room_ids=[room_id] if room_id else [],
        created_at=datetime.now(timezone.utc)
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # FIX 2: Lempar original_filename ke background task!
    background_tasks.add_task(
        process_document_background,
        doc_id=doc_id,
        user_id=str(user.id),
        file_path=file_path,
        original_filename=file.filename, # <--- TAMBAH INI DI SINI
        rag_service=rag_service
    )

    logger.info(f"Document {doc_id} queued for processing (Global: {is_global})")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "status": doc.status,
        "is_global": doc.is_global,
        "room_ids": doc.room_ids,
        "created_at": doc.created_at
    }

@router.get("/")
async def list_documents(
    room_name: Optional[str] = None,
    is_global: Optional[bool] = None,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """
    List dokumen dengan filter Public/Private dan Room.
    """
    query = db.query(Document)
    
    # Filter Public/Private
    if is_global is True:
        query = query.filter(Document.is_global == True)
    elif is_global is False:
        query = query.filter(Document.user_id == str(user.id), Document.is_global == False)
    else:
        query = query.filter(or_(Document.user_id == str(user.id), Document.is_global == True))
    
    # Filter by Room (JSON Array)
    if room_name:
        query = query.filter(cast(Document.room_ids, String).like(f'%"{room_name}"%'))
    
    docs = query.order_by(Document.created_at.desc()).all()
    
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "original_filename": d.original_filename,
            "file_type": d.file_type,
            "status": d.status,
            "total_pages": d.total_pages,
            "total_chunks": d.total_chunks,
            "created_at": d.created_at,
            "is_global": getattr(d, 'is_global', False),
            "room_ids": getattr(d, 'room_ids', [])
        }
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get detail dokumen (Milik sendiri atau Global)."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        or_(Document.user_id == str(user.id), Document.is_global == True)
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "status": doc.status,
        "total_pages": doc.total_pages,
        "total_chunks": doc.total_chunks,
        "created_at": doc.created_at,
        "is_global": getattr(doc, 'is_global', False),
        "room_ids": getattr(doc, 'room_ids', [])
    }


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Cek processing status dokumen."""
    doc = db.query(Document).filter(
        Document.id == doc_id,
        or_(Document.user_id == str(user.id), Document.is_global == True)
    ).first()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "status": doc.status,
        "total_chunks": doc.total_chunks,
        "processed_at": doc.processed_at
    }


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    user: User = Depends(get_current_user_from_token),
    rag_service: RAGService = Depends(get_rag_service),
    db: Session = Depends(get_db_session)
):
    """Hapus dokumen."""
    # User hanya bisa hapus miliknya sendiri (meski itu global yang dia buat)
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == str(user.id)
    ).first()

    if not doc:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document or not found")

    # Hapus dari Qdrant
    rag_service.delete_document(user_id=str(user.id), doc_id=doc_id)

    # Hapus dari DB
    db.delete(doc)
    db.commit()

    logger.info(f"Document {doc_id} deleted by user {user.id}")


# ==============================================================================
# Room Management
# ==============================================================================

from pydantic import BaseModel

class DocumentUpdateRoomRequest(BaseModel):
    room_ids: List[str]

@router.put("/{doc_id}/rooms")
async def update_document_rooms(
    doc_id: str,
    data: DocumentUpdateRoomRequest,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Update array room_ids milik dokumen."""
    # Cari dokumen: Milik sendiri ATAU Dokumen Global
    doc = db.query(Document).filter(
        Document.id == doc_id,
        or_(
            Document.user_id == str(user.id), 
            Document.is_global == True
        )
    ).first()

    if not doc:
        raise HTTPException(
            status_code=404, 
            detail="Dokumen tidak ditemukan atau kamu tidak punya akses."
        )

    # Update daftar room (misal: dari [] jadi ["Matematika"])
    doc.room_ids = data.room_ids
    db.commit()
    return {"id": doc.id, "room_ids": doc.room_ids}

# ==============================================================================
# Chunked Upload Endpoints
# ==============================================================================

CHUNK_TEMP_DIR = "uploads/chunks"
os.makedirs(CHUNK_TEMP_DIR, exist_ok=True)

@router.post("/upload/init")
async def init_chunked_upload(
    filename: str = Form(...),
    total_chunks: int = Form(...),
    file_size: int = Form(...),
    is_global: bool = Form(False),
    room_id: Optional[str] = Form(None),
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Init chunked upload — return upload_id dan doc_id."""
    file_ext = filename.split(".")[-1].lower()
    if file_ext not in ["pdf", "ppt", "pptx"]:
        raise HTTPException(status_code=400, detail="Invalid file type.")

    doc_id = str(uuid.uuid4())
    upload_id = str(uuid.uuid4())

    # Buat folder temp untuk chunks
    chunk_dir = os.path.join(CHUNK_TEMP_DIR, upload_id)
    os.makedirs(chunk_dir, exist_ok=True)

    # Simpan doc ke DB dengan status pending
    saved_filename = f"{doc_id}.{file_ext}"
    file_path = os.path.join("uploads", saved_filename)

    doc = Document(
        id=doc_id,
        user_id=str(user.id),
        filename=saved_filename,
        original_filename=filename,
        file_size=file_size,
        file_type=file_ext,
        file_path=file_path,
        status="pending",
        is_global=is_global,
        room_ids=[room_id] if room_id else [],
        created_at=datetime.now(timezone.utc)
    )
    db.add(doc)
    db.commit()

    return {
        "upload_id": upload_id,
        "doc_id": doc_id,
        "total_chunks": total_chunks
    }


@router.post("/upload/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user_from_token),
):
    """Terima satu chunk dan simpan ke temp folder."""
    chunk_dir = os.path.join(CHUNK_TEMP_DIR, upload_id)
    if not os.path.exists(chunk_dir):
        raise HTTPException(status_code=404, detail="Upload session not found.")

    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index:05d}")
    content = await file.read()
    with open(chunk_path, "wb") as f:
        f.write(content)

    return {"chunk_index": chunk_index, "received": True}


@router.post("/upload/finalize")
async def finalize_chunked_upload(
    background_tasks: BackgroundTasks,
    upload_id: str = Form(...),
    doc_id: str = Form(...),
    total_chunks: int = Form(...),
    user: User = Depends(get_current_user_from_token),
    rag_service: RAGService = Depends(get_rag_service),
    db: Session = Depends(get_db_session)
):
    """Gabungkan semua chunks jadi satu file, lalu proses."""
    chunk_dir = os.path.join(CHUNK_TEMP_DIR, upload_id)
    if not os.path.exists(chunk_dir):
        raise HTTPException(status_code=404, detail="Upload session not found.")

    # Ambil doc dari DB
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == str(user.id)
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Gabungkan chunks
    file_path = doc.file_path
    with open(file_path, "wb") as out:
        for i in range(total_chunks):
            chunk_path = os.path.join(chunk_dir, f"chunk_{i:05d}")
            if not os.path.exists(chunk_path):
                raise HTTPException(status_code=400, detail=f"Missing chunk {i}")
            with open(chunk_path, "rb") as cf:
                out.write(cf.read())

    # Update status jadi processing
    doc.status = "processing"
    db.commit()

    # Cleanup temp chunks
    import shutil
    shutil.rmtree(chunk_dir, ignore_errors=True)

    # Jalankan background processing
    background_tasks.add_task(
        process_document_background,
        doc_id=doc_id,
        user_id=str(user.id),
        file_path=file_path,
        original_filename=doc.original_filename,
        rag_service=rag_service
    )

    logger.info(f"Document {doc_id} finalized and queued for processing")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "status": doc.status,
        "is_global": doc.is_global,
        "room_ids": doc.room_ids,
        "created_at": doc.created_at
    }