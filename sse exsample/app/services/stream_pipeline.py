"""
StreamPipeline
==============
Menjalankan intent analysis, RAG search, dan context fetch secara paralel.
Hasilnya di-bundle ke satu dataclass bersih yang siap dipakai event_generator.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from app.services.chat_service import get_exam_history_context, ChatService
from app.services.session_summary_service import SessionSummaryService
from app.services.intent_classifier import classifier
from app.db.models import ChatMessage, RoomInsight
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    mode: str
    query_type: str
    context_text: str
    session_context: str
    exam_history: str
    room_memory: str
    rag_intent: str = "SEARCH"
    results: list = field(default_factory=list)


async def _fetch_rag(
    rag_service: RAGService,
    user_id: str,
    user_input: str,
    chat_history: str,
    active_doc_ids: list,
    mode: str,
) -> tuple:
    """RAG search — async langsung karena rag_service.search sudah async."""
    if not active_doc_ids or mode == "OUT_OF_SCOPE":
        return "OBROLAN", []
    try:
        rag_response = await rag_service.search(
            user_id=user_id,
            query=user_input,
            chat_history=chat_history,
            n_results=10,
            doc_ids=active_doc_ids
        )
        return rag_response.get("intent", "SEARCH"), rag_response.get("chunks", [])
    except Exception as e:
        logger.error(f"[Pipeline] RAG search error: {e}")
        return "SEARCH", []


async def _fetch_session_context(session_id: str, db: Session) -> str:
    """Session summary context — sync tapi ringan, langsung await."""
    try:
        return SessionSummaryService.get_context_for_prompt(session_id, db) or ""
    except Exception as e:
        logger.error(f"[Pipeline] Session context error: {e}")
        return ""


async def _fetch_exam_history(user_id: str, room_name: str, db: Session) -> str:
    """Exam history — query DB biasa."""
    try:
        return get_exam_history_context(user_id=user_id, room_name=room_name, db=db)
    except Exception as e:
        logger.error(f"[Pipeline] Exam history error: {e}")
        return ""


async def _fetch_room_memory(user_id: str, room_name: str, db: Session) -> str:
    """Room insight dari DB."""
    if not room_name:
        return ""
    try:
        latest_insight = (
            db.query(RoomInsight)
            .filter(RoomInsight.user_id == user_id, RoomInsight.room_name == room_name)
            .order_by(RoomInsight.created_at.desc())
            .first()
        )
        return latest_insight.insight_text if latest_insight and latest_insight.insight_text else ""
    except Exception as e:
        logger.error(f"[Pipeline] Room memory error: {e}")
        return ""


async def build_pipeline(
    user_input: str,
    user_id: str,
    session_id: str,
    current_room: str,
    active_doc_ids: list,
    rag_service: RAGService,
    db: Session,
    chat_history: str = "",
) -> PipelineResult:
    """
    Titik masuk utama. Semua fetch jalan paralel lewat asyncio.gather.
    chat_history dipakai QueryRewriter untuk anafora resolution & intent routing.
    """
    mode, query_type = classifier.analyze_intent(user_input, bool(active_doc_ids))

    # Gather paralel: RAG async + tiga DB query ringan
    (rag_intent, results), session_context, exam_history, room_memory = await asyncio.gather(
        _fetch_rag(rag_service, user_id, user_input, chat_history, active_doc_ids, mode),
        _fetch_session_context(session_id, db),
        _fetch_exam_history(user_id, current_room, db),
        _fetch_room_memory(user_id, current_room, db),
    )

    context_text = (
        "\n\n".join(
            [
                f"--- Excerpt {i+1} (Source: {r.get('metadata', {}).get('source', '?')} - Page: {r.get('metadata', {}).get('page', '?')}) ---\n{r.get('content', '')}"
                for i, r in enumerate(results)
            ]
        )
        if results
        else ""
    )
    print("====== CEK KONTEKS UNTUK ARMISA ======") # <--- TAMBAH INI
    print(context_text[:500]) # Print 500 karakter pertama # <--- TAMBAH INI
    # Upgrade mode kalau ada context
    if context_text and mode == "OBROLAN":
        mode = "BELAJAR"

    # CHAT intent dari rewriter → force OBROLAN mode, buang context
    if rag_intent == "CHAT":
        mode = "OBROLAN"
        context_text = ""

    return PipelineResult(
        mode=mode,
        query_type=query_type,
        context_text=context_text,
        session_context=session_context,
        exam_history=exam_history,
        room_memory=room_memory,
        rag_intent=rag_intent,
        results=results,
    )