"""
Scheduler & Progress Endpoints
==============================
API untuk SM-2, XP, Streak tracking.

Endpoints:
- POST /api/v1/scheduler/mark-reviewed (user rate pesan)
- GET /api/v1/scheduler/due-items (list messages untuk review)
- GET /api/v1/progress/stats (XP, level, streak stats)
"""

import logging
from datetime import datetime, date, timedelta, timezone
from uuid import uuid4
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.db.models import User, ChatMessage, ChatSession
from app.services.sm2_service import SM2
from app.services.xp_service import XP
from app.services.user_progress_service import UserProgress
from app.api.deps import get_current_user_from_token

from app.services.session_summary_service import SessionSummaryService
import json


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduler", tags=["Scheduler & Progress"])


# ============================================================================
# SCHEDULER ENDPOINTS
# ============================================================================

@router.post("/mark-reviewed")
async def mark_message_reviewed(
    message_id: str,
    rating: int,  # 1-5 (user bilang mudah/susah)
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """
    User rate pesan yang sudah dibaca/dipelajari.
    
    INPUT:
    - message_id: ID pesan yang di-rate
    - rating: 1-5 (1=sangat susah, 5=sangat mudah)
    
    OUTPUT:
    - next_review_date: kapan harus review lagi
    - ease_factor_baru: nilai baru untuk algorithm
    """
    
    # Cek message exists dan milik user ini
    message = db.query(ChatMessage).filter(
        ChatMessage.id == message_id,
        ChatMessage.session_id == (
            db.query(ChatSession.id).filter(ChatSession.user_id == str(user.id))
        )
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Validasi rating
    if not (1 <= rating <= 5):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating harus 1-5"
        )
    
    # SM-2 calculation
    sm2_result = SM2.hitung_review(
        rating=rating,
        ease_factor_sekarang=message.sm2_ease_factor or 2.5,
        repetisi_sebelumnya=message.sm2_repetitions or 0
    )
    
    # Update message
    message.rating = rating
    message.sm2_ease_factor = sm2_result["ease_factor_baru"]
    message.sm2_repetitions = (message.sm2_repetitions or 0) + 1
    message.sm2_next_review = sm2_result["tanggal_review_berikutnya"]
    message.last_reviewed_at = datetime.now(timezone.utc)
    message.is_reviewable = True
    
    db.commit()
    
    logger.info(f"Message {message_id} reviewed by user {user.id} with rating {rating}")
    
    return {
        "success": True,
        "message_id": message_id,
        "rating": rating,
        "next_review_date": sm2_result["tanggal_review_berikutnya"],
        "ease_factor_baru": sm2_result["ease_factor_baru"],
        "deskripsi": sm2_result["deskripsi"]
    }


@router.get("/due-items")
async def get_scheduler_due_items(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get messages grouped by room + Leitner boxes."""
    
    today = datetime.now(timezone.utc)
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id.in_(
            db.query(ChatSession.id).filter(ChatSession.user_id == str(user.id))
        ),
        ChatMessage.is_reviewable == True,
        ChatMessage.sm2_next_review <= today
    ).order_by(ChatMessage.sm2_next_review).all()
    
    # Group by room
    rooms_data = {}
    
    for msg in messages:
        session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
        room_name = session.room_name if session else "Unknown"
        
        # Initialize room jika belum ada
        if room_name not in rooms_data:
            rooms_data[room_name] = {
                "room_name": room_name,
                "boxes": {
                    "box1": {"name": "🔴 URGENT", "items": [], "count": 0},
                    "box2": {"name": "🟠 PERLU REVIEW", "items": [], "count": 0},
                    "box3": {"name": "🟡 CONSOLIDATING", "items": [], "count": 0},
                    "box4": {"name": "🟢 REMEMBERED", "items": [], "count": 0},
                    "box5": {"name": "✅ MASTERY", "items": [], "count": 0}
                }
            }
        
        # Map to box
        if msg.sm2_next_review:
            interval = (msg.sm2_next_review.date() - today.date()).days
        else:
            interval = 0
        
        if interval < 1:
            box_key = "box1"
        elif interval < 3:
            box_key = "box2"
        elif interval < 7:
            box_key = "box3"
        elif interval < 14:
            box_key = "box4"
        else:
            box_key = "box5"
        
        item = {
            "message_id": str(msg.id),
            "content": msg.content[:80],
            "session_name": session.title if session else "Unknown",
            "rating": msg.rating or 0,
            "next_review": msg.sm2_next_review.isoformat()
        }
        
        rooms_data[room_name]["boxes"][box_key]["items"].append(item)
        rooms_data[room_name]["boxes"][box_key]["count"] += 1
    
    return {"rooms": list(rooms_data.values())}


@router.get("/stats-detailed")
async def get_scheduler_stats(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """
    Get detailed scheduler stats untuk dashboard.
    
    OUTPUT:
    - total_items: total messages yang bisa di-review
    - items_due_today: berapa yg due hari ini
    - next_review: kapan review berikutnya
    - box_distribution: distribusi per box
    """
    
    today = datetime.now(timezone.utc)
    
    # Hitung total reviewable
    total_items = db.query(ChatMessage).filter(
        ChatMessage.session_id.in_(
            db.query(ChatSession.id).filter(ChatSession.user_id == str(user.id))
        ),
        ChatMessage.is_reviewable == True
    ).count()
    
    # Hitung due hari ini
    items_due_today = db.query(ChatMessage).filter(
        ChatMessage.session_id.in_(
            db.query(ChatSession.id).filter(ChatSession.user_id == str(user.id))
        ),
        ChatMessage.is_reviewable == True,
        ChatMessage.sm2_next_review <= today
    ).count()
    
    # Next review date
    next_review = db.query(ChatMessage).filter(
        ChatMessage.session_id.in_(
            db.query(ChatSession.id).filter(ChatSession.user_id == str(user.id))
        ),
        ChatMessage.is_reviewable == True,
        ChatMessage.sm2_next_review > today
    ).order_by(ChatMessage.sm2_next_review).first()
    
    return {
        "total_items": total_items,
        "items_due_today": items_due_today,
        "next_review_date": next_review.sm2_next_review if next_review else None,
        "estimated_daily_review_time": items_due_today * 2  # Rough estimate: 2 min per item
    }


# ============================================================================
# PROGRESS ENDPOINTS
# ============================================================================

@router.get("/progress/stats")
async def get_progress_stats(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """
    Get user progress stats untuk dashboard.
    
    OUTPUT:
    - level, XP, progress bar
    - current streak, longest streak
    - status message
    - milestone terdekat
    """
    
    # Refresh streak dulu (cek apakah hari ini update atau reset)
    today = date.today()
    streak_result = UserProgress.update_streak(user.last_activity_date, today)
    
    # Update di DB kalau ada perubahan
    if streak_result["streak"] is not None:
        user.current_streak = streak_result["streak"]
        if streak_result["streak"] > user.longest_streak:
            user.longest_streak = streak_result["streak"]
        user.last_activity_date = today
        db.commit()
    
    # Build stats
    stats = UserProgress.build_user_stats(
        total_xp=user.total_xp or 0,
        current_streak=user.current_streak or 0,
        longest_streak=user.longest_streak or 0
    )
    
    return {
        "user_id": str(user.id),
        "username": user.username,
        "stats": stats,
        "milestone_badge": UserProgress.get_badge_milestone(user.current_streak or 0)
    }


@router.post("/progress/add-xp")
async def add_xp(
    xp_amount: int,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """
    Tambah XP ke user (called setelah chat message).
    
    INPUT:
    - xp_amount: berapa XP yang mau ditambah
    
    OUTPUT:
    - new_total_xp
    - level_up: True jika naik level
    """
    
    old_xp = user.total_xp or 0
    old_level = (old_xp // 5000) + 1
    
    new_xp = old_xp + xp_amount
    new_level = (new_xp // 5000) + 1
    
    user.total_xp = new_xp
    user.level = new_level
    
    db.commit()
    
    level_up = new_level > old_level
    
    logger.info(f"User {user.id} gained {xp_amount} XP (total: {new_xp})")
    
    return {
        "xp_gained": xp_amount,
        "old_total_xp": old_xp,
        "new_total_xp": new_xp,
        "old_level": old_level,
        "new_level": new_level,
        "level_up": level_up
    }


# ============================================================================
# Utility: Update last activity (call ini setiap kali user chat)
# ============================================================================

@router.post("/activity/update")
async def update_last_activity(
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """
    Update last_activity_date untuk streak tracking.
    Call ini setelah user send chat message.
    """
    
    today = date.today()
    user.last_activity_date = today
    db.commit()
    
    return {"last_activity_date": today}


@router.get("/session/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db_session)
):
    """Get session summary dengan gap detection."""
    
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get all messages in session
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    if len(messages) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 5 messages, got {len(messages)}"
        )
    
    # Build summary
    summary = SessionSummaryService.build_summary(session_id, messages, db)
    
    return summary