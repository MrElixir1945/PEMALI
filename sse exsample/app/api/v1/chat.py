"""
Chat & RAG Endpoints (Refactored)
==================================
Chat interface with RAG retrieval, streaming support.
Semua logic berat dipindah ke StreamPipeline dan post_chat_tasks.
"""
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.services.chat_service import ChatService
from app.services.stream_pipeline import build_pipeline
from app.services.post_chat_tasks import run_all_post_chat_tasks
from app.services.xp_service import XP
from app.services.sm2_service import SM2
from app.core.openai_client import get_async_client
from app.db import get_db_session
from app.db.models import ChatSession, ChatMessage, User
from app.models.schemas import ChatRequest, ChatResponse, ChatStreamingChunk
from app.services.rag_service import RAGService
from app.api.deps import get_current_user_from_token, get_db_session, get_rag_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def get_chat_service():
    return ChatService()


# ==============================================================================
# Non-streaming endpoint (tidak berubah banyak)
# ==============================================================================

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user_from_token),
    rag_service: RAGService = Depends(get_rag_service),
    chat_service: ChatService = Depends(get_chat_service),
    db: Session = Depends(get_db_session),
):
    rag_response = await rag_service.search(
        user_id=str(user.id),
        query=request.user_input,
        n_results=6,
        doc_ids=request.doc_ids or None
    )
    results = rag_response["chunks"]

    context_text = ""
    context_chunk_ids = []
    if results:
        context_parts = []
        for i, r in enumerate(results, 1):
            metadata = r.get("metadata", {})
            context_parts.append(
                f"--- Excerpt {i} (Source: {metadata.get('source', 'Unknown')} - Page: {metadata.get('page', '?')}) ---\n{r.get('content', '')}"
            )
            if "id" in r:
                context_chunk_ids.append(r["id"])
        context_text = "\n\n".join(context_parts)

    has_context = bool(context_text)
    mode = "BELAJAR" if has_context else "OBROLAN"
    query_type = rag_service.get_query_type(request.user_input)

    if request.session_id:
        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == str(user.id),
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(
            id=str(uuid4()),
            user_id=str(user.id),
            title=request.user_input[:50],
            mode=mode,
            created_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    current_room = session.room_name or ""
    from app.services.chat_service import get_exam_history_context
    exam_history = get_exam_history_context(user_id=str(user.id), room_name=current_room, db=db)

    ai_response = chat_service.generate_response(
        user_input=request.user_input,
        context=context_text,
        mode=mode,
        query_type=query_type,
        has_context=has_context,
        username=user.nickname or user.username,
        room_name=current_room,
        exam_context=exam_history,
    )

    xp_gained = 15 if mode == "BELAJAR" else 5
    message = ChatMessage(
        id=str(uuid4()),
        session_id=session.id,
        user_id=str(user.id),
        role="user",
        content=request.user_input,
        context_chunk_ids=context_chunk_ids,
        query_type=query_type,
        mode=mode,
        xp_gained=0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)

    assistant_msg = ChatMessage(
        id=str(uuid4()),
        session_id=session.id,
        user_id=str(user.id),
        role="assistant",
        content=ai_response,
        context_chunk_ids=context_chunk_ids,
        query_type=query_type,
        mode=mode,
        xp_gained=xp_gained,
    )
    db.add(assistant_msg)
    if user:
        user.total_xp = (user.total_xp or 0) + xp_gained
    db.commit()

    msg_count = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).count()
    if msg_count > 0 and msg_count % 10 == 0:
        all_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        summary = chat_service.generate_session_summary(all_messages)
        if summary:
            db.query(ChatSession).filter(ChatSession.id == session.id).update({"summary": summary})
            db.commit()

    return ChatResponse(
        reply=ai_response,
        mode=mode,
        query_type=query_type,
        session_id=session.id,
        xp_gained=xp_gained,
        cached=False,
        visuals=[],
    )


# ==============================================================================
# Rating endpoint
# ==============================================================================

@router.post("/messages/{message_id}/rating")
async def rate_message(
    message_id: str,
    data: dict,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session),
):
    rating = data.get("rating")
    if not rating or not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating harus 1-5")

    message = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    sm2_result = SM2.hitung_review(
        rating=rating,
        ease_factor_sekarang=message.sm2_ease_factor or 2.5,
        repetisi_sebelumnya=message.sm2_repetitions or 0,
    )

    message.rating = rating
    message.sm2_ease_factor = sm2_result["ease_factor_baru"]
    message.sm2_repetitions = (message.sm2_repetitions or 0) + 1
    message.sm2_next_review = sm2_result["tanggal_review_berikutnya"]
    message.last_reviewed_at = datetime.now(timezone.utc)
    message.is_reviewable = True
    db.commit()

    return {
        "success": True,
        "message_id": message_id,
        "rating": rating,
        "next_review_date": sm2_result["tanggal_review_berikutnya"],
        "ease_factor_baru": sm2_result["ease_factor_baru"],
    }


# ==============================================================================
# Streaming endpoint — refactored
# ==============================================================================

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_from_token),
    rag_service: RAGService = Depends(get_rag_service),
    chat_service: ChatService = Depends(get_chat_service),
    db: Session = Depends(get_db_session),
):
    session_id = str(request.session_id) if request.session_id else str(uuid4())
    username = user.nickname or (user.username.split("@")[0] if user.username else "kak")
    onboarding_completed_snapshot = user.onboarding_completed  # snapshot sebelum stream

    # --- Resolve atau buat session ---
    session_obj = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == str(user.id),
    ).first()

    if not session_obj:
        session_obj = ChatSession(
            id=session_id,
            user_id=str(user.id),
            title=request.user_input[:50],
            mode="OBROLAN",
            created_at=datetime.now(timezone.utc),
            document_ids=request.doc_ids,
        )
        db.add(session_obj)
        db.commit()

    current_room = session_obj.room_name or ""
    active_doc_ids = request.doc_ids if request.doc_ids is not None else (session_obj.document_ids or [])

    # --- Ambil 20 pesan terakhir, reuse untuk rewriter & system prompt Armisa ---
    recent_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
        .all()[::-1]
    )
    chat_history_str = "\n".join(
        f"{'User' if m.role == 'user' else 'Armisa'}: {m.content[:300]}"
        for m in recent_messages
    )

    # --- Jalankan pipeline paralel sebelum streaming dimulai ---
    pipeline = await build_pipeline(
        user_input=request.user_input,
        user_id=str(user.id),
        session_id=session_id,
        current_room=current_room,
        active_doc_ids=active_doc_ids,
        rag_service=rag_service,
        db=db,
        chat_history=chat_history_str,
    )

    async def event_generator():
        # Simpan user message ke DB
        user_msg_db = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            user_id=str(user.id),
            role="user",
            content=request.user_input,
            mode=pipeline.mode,
            query_type=pipeline.query_type,
            xp_gained=0,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user_msg_db)
        db.commit()

        # --- Handle mode UJIAN ---
        if pipeline.mode == "UJIAN":
            exam_keywords = [
                "ujian", "soal", "kuis", "quiz", "latihan", "test", "tes",
                "uji", "tantang", "evaluasi", "ulangan", "tugas",
            ]
            wants_exam = any(kw in request.user_input.lower() for kw in exam_keywords)

            if wants_exam:
                from app.services.exam_agent_service import generate_exam_agentic
                try:
                    exam_result = await generate_exam_agentic(
                        user_id=str(user.id),
                        room_name=current_room,
                        session_id=session_id,
                        topics=[current_room] if current_room else ["Umum"],
                        db=db,
                        rag_service=rag_service,
                        user_hint=request.user_input,
                    )
                    assistant_msg_db = ChatMessage(
                        id=str(uuid4()),
                        session_id=session_id,
                        user_id=str(user.id),
                        role="assistant",
                        content=exam_result["narasi"],
                        mode="UJIAN",
                        query_type="quiz_request",
                        xp_gained=10,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(assistant_msg_db)
                    db.commit()

                    yield f"event: token\ndata: {json.dumps({'content': exam_result['narasi']})}\n\n"
                    yield f"event: done\ndata: {json.dumps({'full_reply': exam_result['narasi'], 'mode': 'UJIAN', 'exam': True, 'quiz_id': exam_result['quiz_id'], 'questions': exam_result['questions'], 'title': exam_result['title']})}\n\n"
                    return
                except Exception as e:
                    logger.error(f"[Chat] Exam error: {e}")
            else:
                logger.info(f"[Intent Fallback] UJIAN diturunkan ke BELAJAR: '{request.user_input}'")
                user_msg_db.mode = "BELAJAR"
                user_msg_db.query_type = "simple"
                db.commit()

        # --- Build system prompt dari pipeline result ---
        user_profile_str = f"Kelas: {getattr(user, 'kelas', '')}\nMapel Sulit: {getattr(user, 'hardest_subjects', '')}"
        system_prompt = chat_service._build_system_prompt(
            mode=pipeline.mode,
            query_type=pipeline.query_type,
            has_context=bool(pipeline.context_text),
            session_context=pipeline.session_context,
            room_context=pipeline.room_memory,
            recent_messages_text=chat_service._build_conversation_context(recent_messages),
            username=username,
            room_name=current_room,
            onboarding_completed=user.onboarding_completed or False,
            user_profile_data=user_profile_str,
            exam_context=pipeline.exam_history,
        )

        user_message = chat_service._build_user_message(
            request.user_input, pipeline.context_text, bool(pipeline.context_text)
        )

        yield f"event: metadata\ndata: {json.dumps({'mode': pipeline.mode, 'query_type': pipeline.query_type})}\n\n"

        # --- Stream dari LLM (singleton client) ---
        try:
            aclient = get_async_client(
                api_key=chat_service.client.api_key,
                base_url=str(chat_service.client.base_url),
            )

            response_stream = await aclient.chat.completions.create(
                model=chat_service.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                stream=True,
            )

            full_response = ""
            async for chunk in response_stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    txt = chunk.choices[0].delta.content
                    full_response += txt
                    yield f"event: token\ndata: {json.dumps({'content': txt})}\n\n"

            xp_gained = 15 if pipeline.mode == "BELAJAR" else 5

            assistant_msg_db = ChatMessage(
                id=str(uuid4()),
                session_id=session_id,
                user_id=str(user.id),
                role="assistant",
                content=full_response,
                mode=pipeline.mode,
                query_type=pipeline.query_type,
                xp_gained=xp_gained,
                created_at=datetime.now(timezone.utc),
            )
            db.add(assistant_msg_db)
            if user:
                user.total_xp = (user.total_xp or 0) + xp_gained
            db.commit()

            # ← yield done langsung, tanpa nunggu onboarding/summary
            yield f"event: done\ndata: {json.dumps({'full_reply': full_response, 'mode': pipeline.mode, 'xp_gained': xp_gained})}\n\n"

        except Exception as e:
            logger.error(f"[Chat] Streaming error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    async def consuming_generator():
        """
        Wrap event_generator supaya kita bisa schedule background task
        SETELAH seluruh stream selesai dikonsumsi client.
        """
        async for chunk in event_generator():
            yield chunk

        # Dijadwalkan di sini — stream sudah selesai, done sudah dikirim
        background_tasks.add_task(
            run_all_post_chat_tasks,
            session_id=session_id,
            user_id=str(user.id),
            onboarding_completed=onboarding_completed_snapshot,
            chat_service=chat_service,
        )

    return StreamingResponse(
        consuming_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ==============================================================================
# Session endpoints
# ==============================================================================

@router.get("/sessions")
async def get_sessions(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session),
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == str(user.id))
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [
        {"id": s.id, "title": s.title, "mode": s.mode, "created_at": s.created_at, "document_ids": s.document_ids}
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    before_id: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == str(user.id)
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
    if before_id:
        cursor_msg = db.query(ChatMessage).filter(ChatMessage.id == before_id).first()
        if cursor_msg:
            query = query.filter(ChatMessage.created_at < cursor_msg.created_at)

    messages = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
    messages.reverse()
    total_count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
    has_more = len(messages) == limit and total_count > limit

    return {
        "session_id": session_id,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "mode": m.mode,
                "rating": m.rating,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
        "has_more": has_more,
        "total_count": total_count,
        "oldest_id": str(messages[0].id) if messages else None,
    }


class DocumentSyncRequest(BaseModel):
    document_ids: List[str] = []


@router.put("/sessions/{session_id}/documents")
async def update_session_documents(
    session_id: str,
    data: DocumentSyncRequest,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.user_id == str(user.id)
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.document_ids = data.document_ids
    db.commit()
    return {"session_id": session_id, "document_ids": data.document_ids}