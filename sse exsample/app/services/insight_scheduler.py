"""
Insight Scheduler Service
=========================
Smart session selector + parallel async summary.

Flow tiap 6 jam:
1. Ambil semua user aktif (last_activity < 3 hari)
2. Untuk tiap user → ambil semua rooms
3. Untuk tiap room → smart_select_sessions()
   - Filter: last_message < 3 hari
   - Sort by recency, top 10
4. asyncio.gather() → parallel summarize semua sesi
5. Build room insight dari hasil agregasi
6. Simpan ke room_insights
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.orm import Session

from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from app.db import SessionLocal
from app.db.models import User, ChatSession, ChatMessage, RoomInsight
from app.services.session_summary_service import SessionSummaryService
from app.services.room_summary_service import RoomSummaryService

WITA = ZoneInfo("Asia/Makassar")

logger = logging.getLogger(__name__)

STALE_DAYS = 3       # Sesi dengan last_message > 3 hari → skip
TOP_N_SESSIONS = 10  # Max sesi per room yang di-summary


# ================================================================
# SMART SELECTOR
# ================================================================

def smart_select_sessions(
    sessions: List[ChatSession],
    db: Session
) -> List[ChatSession]:
    """
    Filter + sort sessions:
    - Buang sesi tanpa pesan
    - Buang sesi yang last_message > STALE_DAYS
    - Sort by last_message DESC
    - Ambil top TOP_N
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)
    scored = []

    for session in sessions:
        last_msg = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at.desc()).first()

        if not last_msg:
            continue  # Sesi kosong → skip

        last_msg_time = last_msg.created_at
        if last_msg_time.tzinfo is None:
            last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)

        if last_msg_time < cutoff:
            continue  # Stale → skip

        scored.append((session, last_msg_time))

    # Sort by recency DESC → ambil top N
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored[:TOP_N_SESSIONS]]


# ================================================================
# PARALLEL SESSION SUMMARY
# ================================================================

async def summarize_session_async(
    session: ChatSession,
    db: Session
) -> dict:
    """
    Async wrapper untuk summarize 1 sesi.
    Jalankan di thread pool biar ga block event loop.
    """
    loop = asyncio.get_event_loop()

    def _sync():
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(ChatMessage.created_at.asc()).all()

        if not messages:
            return {}

        # Kalau udah ada summary fresh (< 6 jam) → skip, pakai cache
        if session.summary and session.summary_updated_at:
            updated_at = session.summary_updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - updated_at
            if age.total_seconds() < 6 * 3600:
                try:
                    import json
                    return json.loads(session.summary)
                except Exception:
                    pass

        return SessionSummaryService.build_session_summary(
            session.id, messages, db
        )

    return await loop.run_in_executor(None, _sync)


async def parallel_summarize_sessions(
    sessions: List[ChatSession],
    db: Session
) -> List[dict]:
    """
    Fire semua session summary sekaligus pakai asyncio.gather().
    """
    tasks = [summarize_session_async(s, db) for s in sessions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summaries = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Session summary error [{sessions[i].id}]: {result}")
            continue
        if result:
            summaries.append(result)

    return summaries


# ================================================================
# PER-ROOM JOB
# ================================================================

async def process_room(
    room_name: str,
    user_id: str,
    db: Session
):
    """Process 1 room: select sessions → parallel summary → build insight."""
    try:
        # 1. Ambil semua sesi di room ini
        all_sessions = db.query(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.room_name == room_name
        ).all()

        if not all_sessions:
            return

        # 2. Smart select
        selected = smart_select_sessions(all_sessions, db)
        if not selected:
            logger.info(f"[Scheduler] Room {room_name} — semua sesi stale, skip")
            return

        logger.info(
            f"[Scheduler] Room {room_name} — "
            f"{len(all_sessions)} sesi total, {len(selected)} dipilih"
        )

        # 3. Parallel summarize
        await parallel_summarize_sessions(selected, db)

        # 4. Build room insight (pakai RoomSummaryService yang udah ada)
        RoomSummaryService.build_room_summary(
            room_name=room_name,
            user_id=user_id,
            db=db,
            trigger_type="scheduled"
        )

        logger.info(f"[Scheduler] Room {room_name} — insight generated ✅")

    except Exception as e:
        logger.error(f"[Scheduler] Error processing room {room_name}: {e}")


# ================================================================
# PER-USER JOB
# ================================================================

async def process_user(user_id: str):
    """Process semua rooms milik 1 user."""
    db = SessionLocal()
    try:
        # Ambil semua rooms unik milik user ini
        rooms = db.query(ChatSession.room_name).filter(
            ChatSession.user_id == user_id,
            ChatSession.room_name.isnot(None)
        ).distinct().all()

        room_names = [r[0] for r in rooms]
        if not room_names:
            return

        logger.info(f"[Scheduler] User {user_id} — {len(room_names)} rooms")

        for room_name in room_names:
            await process_room(room_name, user_id, db)

    finally:
        db.close()


# ================================================================
# MAIN JOB — dipanggil APScheduler tiap 6 jam
# ================================================================

async def run_insight_job():
    """
    Main scheduled job.
    Ambil semua user aktif → process parallel per user.
    """
    logger.info("[Scheduler] ⏰ Insight job started")
    db = SessionLocal()

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)

        # Ambil user yang aktif dalam 3 hari terakhir
        active_users = db.query(User).filter(
            User.last_activity_date >= cutoff.date()
        ).all()

        if not active_users:
            logger.info("[Scheduler] Tidak ada user aktif, skip")
            return

        logger.info(f"[Scheduler] {len(active_users)} user aktif ditemukan")

    finally:
        db.close()

    # Process tiap user (sequential per user, parallel per session)
    for user in active_users:
        await process_user(str(user.id))

    logger.info("[Scheduler] ✅ Insight job selesai")


# ================================================================
# SYNC WRAPPER — untuk APScheduler yang sync
# ================================================================

def run_insight_job_sync():
    """Sync wrapper — dipanggil APScheduler."""
    asyncio.run(run_insight_job())

def register_jobs(scheduler):
    """
    Daftarkan semua insight jobs ke APScheduler.
    Dipanggil dari main.py saat startup.
    """
    for hour in [3, 12, 18]:
        scheduler.add_job(
            run_insight_job_sync,
            trigger=CronTrigger(hour=hour, minute=0, timezone=WITA),
            id=f"insight_job_{hour}",
            replace_existing=True,
        )
    logger.info("[Scheduler] Jobs registered: 03:00, 12:00, 18:00 WITA")