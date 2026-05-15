"""
Post-chat background tasks
==========================
Semua pekerjaan berat yang tidak perlu user tunggu.
Setiap fungsi buka DB session sendiri — aman dipanggil dari BackgroundTasks.
"""
import logging
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db.models import User, ChatMessage, ChatSession
from app.services.chat_service import ChatService
from app.services.session_summary_service import SessionSummaryService

logger = logging.getLogger(__name__)


def _get_db() -> Session:
    """Buka session baru. Caller wajib panggil .close()."""
    return SessionLocal()


def run_onboarding_extraction(
    session_id: str,
    user_id: str,
    chat_service: ChatService,
) -> None:
    """
    Ekstrak data onboarding dari 10 chat terakhir.
    Dipanggil hanya kalau user.onboarding_completed == False.
    """
    db = _get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.onboarding_completed:
            return

        convo_history = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
            .all()
        )
        convo_history.reverse()

        extracted = chat_service.extract_onboarding_data(convo_history)
        if not extracted:
            return

        if extracted.get("nickname"):
            user.nickname = extracted["nickname"]
        if extracted.get("kelas"):
            user.kelas = str(extracted["kelas"])
        if extracted.get("hardest_subjects"):
            user.hardest_subjects = extracted["hardest_subjects"]

        if user.nickname:
            user.onboarding_completed = True

        db.commit()
        logger.info(f"[PostChat] Onboarding updated for user {user_id}")

    except Exception as e:
        logger.error(f"[PostChat] Onboarding extraction failed: {e}")
        db.rollback()
    finally:
        db.close()


def run_progressive_summary(session_id: str) -> None:
    """
    Update progressive summary setiap 20 pesan.
    Membuka DB session sendiri.
    """
    db = _get_db()
    try:
        msg_count = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .count()
        )

        if msg_count == 0 or msg_count % 20 != 0:
            return

        all_msgs = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

        SessionSummaryService.update_progressive_summary(session_id, all_msgs, db)
        logger.info(f"[PostChat] Progressive summary updated for session {session_id}")

    except Exception as e:
        logger.error(f"[PostChat] Progressive summary failed: {e}")
        db.rollback()
    finally:
        db.close()


def run_all_post_chat_tasks(
    session_id: str,
    user_id: str,
    onboarding_completed: bool,
    chat_service: ChatService,
) -> None:
    """
    Entry point tunggal untuk BackgroundTasks.
    Jalankan semua pekerjaan post-chat secara berurutan dalam satu fungsi
    supaya FastAPI cukup register satu task.
    """
    if not onboarding_completed:
        run_onboarding_extraction(session_id, user_id, chat_service)

    run_progressive_summary(session_id)